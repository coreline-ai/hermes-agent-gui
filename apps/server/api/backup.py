"""Backup tar.gz export — Phase 20."""

from __future__ import annotations

import json
import tarfile
import time
from http import HTTPStatus
from io import BytesIO
from pathlib import Path

from . import auth as auth_module
from .config import Config, STATE_DIR
from .messaging.credentials import hermes_home
from .profile_archive import ARCHIVE_EXCLUDE_PATTERNS, _checkpoint_sqlite, _file_sha256, _is_excluded
from .router import Request, Response, Router


def _add_tree(tf: tarfile.TarFile, root: Path, prefix: str, manifest: dict[str, str]) -> None:
    if not root.exists():
        return
    for item in root.rglob("*"):
        if not item.is_file():
            continue
        rel = f"{prefix}/{item.relative_to(root).as_posix()}"
        if _is_excluded(rel):
            continue
        tf.add(item, arcname=rel)
        manifest[rel] = _file_sha256(item)


def build_backup() -> bytes:
    _checkpoint_sqlite(STATE_DIR / "sessions.db")
    manifest: dict[str, str] = {}
    bio = BytesIO()
    with tarfile.open(fileobj=bio, mode="w:gz") as tf:
        _add_tree(tf, STATE_DIR, "hermes-agent-gui", manifest)
        home = hermes_home()
        for name in ("skills", "memory", "profiles"):
            _add_tree(tf, home / name, f"hermes/{name}", manifest)
        payload = json.dumps({"version": "1.0", "created_at": int(time.time()), "files": manifest, "exclude_patterns": ARCHIVE_EXCLUDE_PATTERNS}, indent=2).encode("utf-8")
        info = tarfile.TarInfo("MANIFEST.json")
        info.size = len(payload)
        info.mtime = int(time.time())
        tf.addfile(info, BytesIO(payload))
    return bio.getvalue()


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("GET", "/api/backup/export")
    def _export(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        return Response(HTTPStatus.OK, build_backup(), headers=[("Content-Type", "application/gzip"), ("Content-Disposition", "attachment; filename=hermes-agent-gui-backup.tar.gz")])

    return router
