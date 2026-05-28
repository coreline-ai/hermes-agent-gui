"""Profile archive export/import routes — Phase 15c.

The archive intentionally excludes device-specific authentication state and
runtime scratch files.  The tar.gz payload contains a MANIFEST.json with a
SHA-256 checksum for every regular file; import verifies those checksums before
copying anything into the live state directories.
"""

from __future__ import annotations

import base64
import fnmatch
import hashlib
import json
import os
import secrets
import shutil
import socket
import sqlite3
import tarfile
import tempfile
import time
import uuid
from dataclasses import dataclass
from email.parser import BytesParser
from email.policy import default as email_policy
from http import HTTPStatus
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Iterable

from . import auth as auth_module
from .config import Config, SECRET_FILE, STATE_DIR
from .messaging.credentials import hermes_home
from .router import Request, Response, Router
from .sessions.lifecycle import SESSIONS_DB, SessionStore

ARCHIVE_VERSION = "1.0"
MAX_ARCHIVE_BYTES = 200 * 1024 * 1024

# Keep in sync with docs/review/11-implementation-plan-full.md and Phase 20 backup.
ARCHIVE_EXCLUDE_PATTERNS = [
    ".env",
    ".env.*",
    "secret",
    "passkeys.json",
    ".login-lock.json",
    "*.key",
    "*.pem",
    "*.pid",
    "*.lock",
    "*.log",
    "*token*",
    "session-aliases.json",
    "memory_vss.db-shm",
    "memory_vss.db-wal",
    "sessions.db-shm",
    "sessions.db-wal",
]

HERMES_ARCHIVE_SUBDIRS = ("skills", "memory", "profiles")


@dataclass(frozen=True)
class ProfileInfo:
    name: str
    session_count: int
    has_profile_dir: bool
    updated_at: int | None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "session_count": self.session_count,
            "has_profile_dir": self.has_profile_dir,
            "updated_at": self.updated_at,
        }


class ArchiveError(ValueError):
    """User-correctable archive validation failure."""


# ── common helpers ──────────────────────────────────────────────────────────


def _sanitize_profile_name(name: str) -> str:
    clean = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in name.strip())
    clean = clean.strip(".-_") or "default"
    return clean[:64]


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def _is_excluded(archive_path: str) -> bool:
    # Match both full archive path and every basename/part so e.g.
    # hermes-agent-gui/secret is excluded by the literal "secret" pattern.
    normalized = archive_path.replace(os.sep, "/").lstrip("/")
    parts = PurePosixPath(normalized).parts
    name = parts[-1] if parts else normalized
    for pat in ARCHIVE_EXCLUDE_PATTERNS:
        if fnmatch.fnmatch(normalized, pat) or fnmatch.fnmatch(name, pat):
            return True
        if any(fnmatch.fnmatch(part, pat) for part in parts):
            return True
    return False


def _validate_archive_path(name: str) -> str:
    if not name or name.startswith("/"):
        raise ArchiveError("archive member path is absolute or empty")
    p = PurePosixPath(name)
    if any(part in {"", ".", ".."} for part in p.parts):
        raise ArchiveError(f"unsafe archive path: {name}")
    return p.as_posix()


def _checkpoint_sqlite(path: Path) -> None:
    if not path.exists():
        return
    try:
        with sqlite3.connect(path) as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except sqlite3.Error:
        # Some optional DB files may not be SQLite yet; archive the main file as-is.
        return


def _atomic_replace_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".{dest.name}.{uuid.uuid4().hex}.tmp")
    shutil.copy2(src, tmp)
    os.replace(tmp, dest)


def _copy_tree_contents(src: Path, dest: Path) -> None:
    if not src.exists():
        return
    for item in src.rglob("*"):
        rel = item.relative_to(src)
        target = dest / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif item.is_file():
            _atomic_replace_file(item, target)


def _rotate_secret(state_dir: Path) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    secret_path = state_dir / SECRET_FILE.name
    secret_path.write_text(secrets.token_hex(32), encoding="utf-8")
    try:
        secret_path.chmod(0o600)
    except OSError:
        pass


# ── profile metadata / clone ────────────────────────────────────────────────


def list_profiles(*, state_dir: Path = STATE_DIR, hermes_dir: Path | None = None) -> list[ProfileInfo]:
    hermes_dir = hermes_dir or hermes_home()
    counts: dict[str, dict[str, int | bool | None]] = {}

    db = state_dir / SESSIONS_DB.name
    if db.exists():
        try:
            with sqlite3.connect(db) as conn:
                for profile, count, updated in conn.execute(
                    "SELECT profile, COUNT(*), MAX(updated_at) FROM sessions GROUP BY profile"
                ):
                    name = str(profile or "default")
                    counts[name] = {
                        "session_count": int(count or 0),
                        "has_profile_dir": False,
                        "updated_at": int(updated) if updated is not None else None,
                    }
        except sqlite3.Error:
            pass

    profiles_root = hermes_dir / "profiles"
    if profiles_root.exists():
        for child in profiles_root.iterdir():
            if not child.is_dir():
                continue
            row = counts.setdefault(
                child.name,
                {"session_count": 0, "has_profile_dir": False, "updated_at": None},
            )
            row["has_profile_dir"] = True

    if not counts:
        counts["default"] = {"session_count": 0, "has_profile_dir": False, "updated_at": None}

    return [
        ProfileInfo(
            name=name,
            session_count=int(row["session_count"] or 0),
            has_profile_dir=bool(row["has_profile_dir"]),
            updated_at=row["updated_at"] if isinstance(row["updated_at"], int) else None,
        )
        for name, row in sorted(counts.items(), key=lambda item: item[0].lower())
    ]


def _profile_names(state_dir: Path, hermes_dir: Path) -> set[str]:
    names: set[str] = set()
    db = state_dir / SESSIONS_DB.name
    if db.exists():
        try:
            with sqlite3.connect(db) as conn:
                names.update(str(row[0] or "default") for row in conn.execute("SELECT DISTINCT profile FROM sessions"))
        except sqlite3.Error:
            pass
    profiles_root = hermes_dir / "profiles"
    if profiles_root.exists():
        names.update(child.name for child in profiles_root.iterdir() if child.is_dir())
    return names


def _unique_profile_name(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    stem = f"{base}-imported"
    candidate = stem
    i = 2
    while candidate in existing:
        candidate = f"{stem}-{i}"
        i += 1
    return candidate


def clone_profile(source: str, new_name: str, *, state_dir: Path = STATE_DIR, hermes_dir: Path | None = None) -> str:
    hermes_dir = hermes_dir or hermes_home()
    source = _sanitize_profile_name(source)
    target = _sanitize_profile_name(new_name)
    existing = _profile_names(state_dir, hermes_dir)
    if source not in existing:
        raise ArchiveError("source_profile_not_found")
    if target in existing:
        raise ArchiveError("profile_name_taken")

    src_profile_dir = hermes_dir / "profiles" / source
    dst_profile_dir = hermes_dir / "profiles" / target
    if src_profile_dir.exists():
        shutil.copytree(src_profile_dir, dst_profile_dir)
    else:
        dst_profile_dir.mkdir(parents=True, exist_ok=True)

    db = state_dir / SESSIONS_DB.name
    if db.exists():
        store = SessionStore(db)
        with sqlite3.connect(db, isolation_level=None) as conn:
            rows = conn.execute(
                "SELECT title, created_at, updated_at, messages_json, metadata_json FROM sessions WHERE profile=?",
                (source,),
            ).fetchall()
            for title, created_at, updated_at, messages_json, metadata_json in rows:
                conn.execute(
                    "INSERT INTO sessions(id,title,profile,created_at,updated_at,messages_json,metadata_json)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (uuid.uuid4().hex[:16], title, target, created_at, updated_at, messages_json, metadata_json),
                )
        del store
    return target


# ── export ──────────────────────────────────────────────────────────────────


def _iter_archive_files(state_dir: Path, hermes_dir: Path) -> Iterable[tuple[Path, str]]:
    roots = [(state_dir, "hermes-agent-gui")]
    roots.extend((hermes_dir / name, f"hermes/{name}") for name in HERMES_ARCHIVE_SUBDIRS)
    for root, prefix in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            arcname = f"{prefix}/{path.relative_to(root).as_posix()}"
            if _is_excluded(arcname):
                continue
            yield path, arcname


def export_profile_archive(
    profile_name: str,
    *,
    state_dir: Path = STATE_DIR,
    hermes_dir: Path | None = None,
) -> tuple[bytes, dict]:
    hermes_dir = hermes_dir or hermes_home()
    profile_name = _sanitize_profile_name(profile_name)
    state_dir.mkdir(parents=True, exist_ok=True)
    hermes_dir.mkdir(parents=True, exist_ok=True)

    # Ensure the main SQLite file contains the latest pages before WAL files are excluded.
    _checkpoint_sqlite(state_dir / "sessions.db")
    _checkpoint_sqlite(state_dir / "memory_vss.db")

    files = list(_iter_archive_files(state_dir, hermes_dir))
    checksums = {arcname: _file_sha256(path) for path, arcname in files}
    manifest = {
        "version": ARCHIVE_VERSION,
        "exported_at": int(time.time()),
        "source_host": socket.gethostname(),
        "gui_version": "0.1.0-phase-15c",
        "profile_name": profile_name,
        "excludes": ARCHIVE_EXCLUDE_PATTERNS,
        "checksums": checksums,
        "note": "Re-login required after import (device-specific secret regenerates).",
    }

    buf = BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        info = tarfile.TarInfo("MANIFEST.json")
        info.size = len(payload)
        info.mtime = int(time.time())
        info.mode = 0o600
        tf.addfile(info, BytesIO(payload))
        for path, arcname in files:
            tf.add(path, arcname=arcname, recursive=False)
    return buf.getvalue(), manifest


# ── import ──────────────────────────────────────────────────────────────────


def _load_and_verify_archive(payload: bytes, tmp: Path) -> dict:
    try:
        with tarfile.open(fileobj=BytesIO(payload), mode="r:gz") as tf:
            members = tf.getmembers()
            seen_files: set[str] = set()
            manifest_member = next((m for m in members if m.name == "MANIFEST.json"), None)
            if manifest_member is None or not manifest_member.isfile():
                raise ArchiveError("manifest missing")
            mf = tf.extractfile(manifest_member)
            if mf is None:
                raise ArchiveError("manifest unreadable")
            manifest = json.loads(mf.read().decode("utf-8"))
            if str(manifest.get("version") or "") != ARCHIVE_VERSION:
                raise ArchiveError("manifest missing or unsupported version")
            checksums = manifest.get("checksums")
            if not isinstance(checksums, dict):
                raise ArchiveError("manifest missing checksums")

            for member in members:
                safe_name = _validate_archive_path(member.name)
                if member.issym() or member.islnk() or member.isdev():
                    raise ArchiveError(f"unsupported archive member: {safe_name}")
                if safe_name == "MANIFEST.json":
                    continue
                if _is_excluded(safe_name):
                    raise ArchiveError(f"archive contains excluded file: {safe_name}")
                target = tmp / safe_name
                try:
                    target.relative_to(tmp)
                except ValueError as exc:
                    raise ArchiveError(f"unsafe archive path: {safe_name}") from exc
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if not member.isfile():
                    raise ArchiveError(f"unsupported archive member: {safe_name}")
                expected = checksums.get(safe_name)
                if not isinstance(expected, str):
                    raise ArchiveError(f"checksum missing for {safe_name}")
                src = tf.extractfile(member)
                if src is None:
                    raise ArchiveError(f"cannot read {safe_name}")
                data = src.read()
                actual = _sha256(data)
                if actual != expected:
                    raise ArchiveError(f"checksum mismatch for {safe_name}")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                seen_files.add(safe_name)

            extra = set(str(k) for k in checksums.keys()) - seen_files
            if extra:
                raise ArchiveError(f"checksums reference missing files: {sorted(extra)[0]}")
            return manifest
    except (tarfile.TarError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ArchiveError("invalid_archive") from exc


def _sessions_count(db: Path) -> int:
    if not db.exists():
        return 0
    try:
        with sqlite3.connect(db) as conn:
            row = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()
            return int(row[0] or 0) if row else 0
    except sqlite3.Error:
        return 0


def _merge_sessions_db(src_db: Path, dest_db: Path, *, old_profile: str, new_profile: str) -> None:
    SessionStore(dest_db)  # Ensure schema.
    with sqlite3.connect(src_db) as src, sqlite3.connect(dest_db, isolation_level=None) as dest:
        rows = src.execute(
            "SELECT id,title,profile,created_at,updated_at,messages_json,metadata_json FROM sessions"
        ).fetchall()
        existing_ids = {str(row[0]) for row in dest.execute("SELECT id FROM sessions").fetchall()}
        for sid, title, profile, created_at, updated_at, messages_json, metadata_json in rows:
            target_id = str(sid)
            if target_id in existing_ids:
                target_id = uuid.uuid4().hex[:16]
            target_profile = new_profile if str(profile or "default") == old_profile else str(profile or "default")
            dest.execute(
                "INSERT INTO sessions(id,title,profile,created_at,updated_at,messages_json,metadata_json)"
                " VALUES (?,?,?,?,?,?,?)",
                (target_id, title, target_profile, created_at, updated_at, messages_json, metadata_json),
            )
            existing_ids.add(target_id)


def _copy_imported_state(tmp: Path, state_dir: Path, hermes_dir: Path, *, old_profile: str, new_profile: str, conflict: bool) -> None:
    src_state = tmp / "hermes-agent-gui"
    src_hermes = tmp / "hermes"
    state_dir.mkdir(parents=True, exist_ok=True)
    hermes_dir.mkdir(parents=True, exist_ok=True)

    # Hermes home: rename profiles/<old_profile> if import had to avoid a collision.
    if src_hermes.exists():
        for item in src_hermes.rglob("*"):
            if not item.is_file():
                continue
            rel = item.relative_to(src_hermes)
            parts = rel.parts
            if len(parts) >= 2 and parts[0] == "profiles" and parts[1] == old_profile:
                target_rel = Path("profiles") / new_profile / Path(*parts[2:])
            else:
                target_rel = rel
            _atomic_replace_file(item, hermes_dir / target_rel)

    if not src_state.exists():
        return

    src_sessions = src_state / "sessions.db"
    dest_sessions = state_dir / "sessions.db"
    for item in src_state.rglob("*"):
        if not item.is_file():
            continue
        rel = item.relative_to(src_state)
        if rel.as_posix() == "sessions.db":
            continue
        _atomic_replace_file(item, state_dir / rel)

    if src_sessions.exists():
        if not conflict and _sessions_count(dest_sessions) == 0:
            _atomic_replace_file(src_sessions, dest_sessions)
            for suffix in ("-wal", "-shm"):
                try:
                    (dest_sessions.parent / f"{dest_sessions.name}{suffix}").unlink()
                except FileNotFoundError:
                    pass
        else:
            _merge_sessions_db(src_sessions, dest_sessions, old_profile=old_profile, new_profile=new_profile)


def import_profile_archive(
    payload: bytes,
    *,
    state_dir: Path = STATE_DIR,
    hermes_dir: Path | None = None,
) -> dict:
    hermes_dir = hermes_dir or hermes_home()
    if len(payload) > MAX_ARCHIVE_BYTES:
        raise ArchiveError("archive_too_large")
    with tempfile.TemporaryDirectory(prefix="hermes-profile-import-") as td:
        tmp = Path(td)
        manifest = _load_and_verify_archive(payload, tmp)
        source_profile = _sanitize_profile_name(str(manifest.get("profile_name") or "default"))
        existing = _profile_names(state_dir, hermes_dir)
        imported_profile = _unique_profile_name(source_profile, existing)
        warnings: list[str] = []
        conflict = imported_profile != source_profile
        if conflict:
            warnings.append(f"profile name conflict; imported as '{imported_profile}'")
        _copy_imported_state(
            tmp,
            state_dir,
            hermes_dir,
            old_profile=source_profile,
            new_profile=imported_profile,
            conflict=conflict,
        )
        _rotate_secret(state_dir)
        return {
            "imported_profile": imported_profile,
            "manifest": manifest,
            "warnings": warnings,
            "relogin_required": True,
        }


# ── HTTP routes ─────────────────────────────────────────────────────────────


def _extract_archive_payload(req: Request) -> bytes:
    raw = req.body_bytes(MAX_ARCHIVE_BYTES)
    ctype = req.headers.get("content-type", "")
    if "multipart/form-data" in ctype.lower():
        header_blob = f"Content-Type: {ctype}\nMIME-Version: 1.0\n\n".encode("utf-8") + raw
        msg = BytesParser(policy=email_policy).parsebytes(header_blob)
        if not msg.is_multipart():
            raise ArchiveError("multipart payload expected")
        for part in msg.iter_parts():
            params = dict(part.get_params(header="content-disposition") or [])
            if params.get("name") == "file":
                return part.get_payload(decode=True) or b""
        raise ArchiveError("multipart file field missing")
    if "application/json" in ctype.lower():
        try:
            body = json.loads(raw.decode("utf-8")) if raw else {}
            encoded = str(body.get("archive_b64") or "")
            if not encoded:
                raise ArchiveError("archive_b64 required")
            return base64.b64decode(encoded, validate=True)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            raise ArchiveError("invalid_archive_b64") from exc
    return raw


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("GET", "/api/profiles")
    def _list(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        return Response(HTTPStatus.OK, {"profiles": [p.to_dict() for p in list_profiles()]})

    @router.route("POST", "/api/profiles/{name}/clone")
    def _clone(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            body = req.json()
            target = str(body.get("new_name") or "")
            if not target.strip():
                return Response(HTTPStatus.BAD_REQUEST, {"error": "new_name_required"})
            name = clone_profile(req.params["name"], target)
            return Response(HTTPStatus.CREATED, {"name": name})
        except ArchiveError as exc:
            status = HTTPStatus.NOT_FOUND if str(exc) == "source_profile_not_found" else HTTPStatus.CONFLICT
            return Response(status, {"error": str(exc)})
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})

    def _export(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        payload, manifest = export_profile_archive(req.params["name"])
        filename = f"hermes-profile-{manifest['profile_name']}-{time.strftime('%Y%m%d')}.tar.gz"
        return Response(
            HTTPStatus.OK,
            payload,
            headers=[
                ("Content-Type", "application/gzip"),
                ("Content-Disposition", f'attachment; filename="{filename}"'),
            ],
        )

    router.add("POST", "/api/profiles/{name}/export", _export)
    router.add("GET", "/api/profiles/{name}/export", _export)

    @router.route("POST", "/api/profiles/import")
    def _import(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            payload = _extract_archive_payload(req)
            result = import_profile_archive(payload)
            return Response(HTTPStatus.CREATED, result)
        except ArchiveError as exc:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_archive", "detail": str(exc)})
        except ValueError as exc:
            return Response(HTTPStatus.PAYLOAD_TOO_LARGE, {"error": "archive_too_large", "detail": str(exc)})

    return router
