from __future__ import annotations

import io
import json
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

from api.profile_archive import (
    ARCHIVE_EXCLUDE_PATTERNS,
    ArchiveError,
    export_profile_archive,
    import_profile_archive,
)
from api.sessions.lifecycle import SessionStore


def _tar_names(blob: bytes) -> list[str]:
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
        return tf.getnames()


def _manifest(blob: bytes) -> dict:
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
        f = tf.extractfile("MANIFEST.json")
        assert f is not None
        return json.loads(f.read().decode("utf-8"))


def _make_archive_with_file(name: str, data: bytes, *, checksum_data: bytes | None = None) -> bytes:
    checksum_source = checksum_data if checksum_data is not None else data
    import hashlib

    manifest = {
        "version": "1.0",
        "exported_at": 1,
        "source_host": "test",
        "gui_version": "test",
        "profile_name": "default",
        "excludes": ARCHIVE_EXCLUDE_PATTERNS,
        "checksums": {name: "sha256:" + hashlib.sha256(checksum_source).hexdigest()},
    }
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        manifest_bytes = json.dumps(manifest).encode("utf-8")
        info = tarfile.TarInfo("MANIFEST.json")
        info.size = len(manifest_bytes)
        tf.addfile(info, io.BytesIO(manifest_bytes))
        file_info = tarfile.TarInfo(name)
        file_info.size = len(data)
        tf.addfile(file_info, io.BytesIO(data))
    return buf.getvalue()


def test_profile_export_excludes_device_specific_files(tmp_path: Path):
    state = tmp_path / "state"
    hermes = tmp_path / "hermes"
    state.mkdir()
    hermes.mkdir()
    (state / "keep.txt").write_text("keep", encoding="utf-8")
    (hermes / "config.yaml").write_text("messaging: {}\n", encoding="utf-8")
    for name in [
        "secret",
        "passkeys.json",
        ".login-lock.json",
        "app.log",
        "run.pid",
        "busy.lock",
        "session-aliases.json",
        "memory_vss.db-shm",
        "memory_vss.db-wal",
        "sessions.db-shm",
        "sessions.db-wal",
    ]:
        (state / name).write_text("excluded", encoding="utf-8")

    blob, manifest = export_profile_archive("default", state_dir=state, hermes_dir=hermes)
    names = _tar_names(blob)

    assert "MANIFEST.json" in names
    assert "hermes-agent-gui/keep.txt" in names
    assert manifest["excludes"] == ARCHIVE_EXCLUDE_PATTERNS
    for archive_name in names:
        for pattern in ARCHIVE_EXCLUDE_PATTERNS:
            assert pattern not in archive_name or archive_name == "MANIFEST.json"
    assert not any(name.endswith(("secret", "passkeys.json", ".log", ".lock", ".pid", ".db-wal", ".db-shm")) for name in names)


def test_profile_import_roundtrip_sessions_db_bit_exact(tmp_path: Path):
    src_state = tmp_path / "src-state"
    src_hermes = tmp_path / "src-hermes"
    dst_state = tmp_path / "dst-state"
    dst_hermes = tmp_path / "dst-hermes"
    store = SessionStore(src_state / "sessions.db")
    sess = store.create(title="Roundtrip", profile="default")
    store.append_messages(sess.id, [])

    blob, _ = export_profile_archive("default", state_dir=src_state, hermes_dir=src_hermes)
    original = (src_state / "sessions.db").read_bytes()
    result = import_profile_archive(blob, state_dir=dst_state, hermes_dir=dst_hermes)

    assert result["imported_profile"] == "default"
    assert (dst_state / "sessions.db").read_bytes() == original


def test_profile_import_rotates_device_secret(tmp_path: Path):
    src_state = tmp_path / "src-state"
    src_hermes = tmp_path / "src-hermes"
    dst_state = tmp_path / "dst-state"
    dst_hermes = tmp_path / "dst-hermes"
    src_state.mkdir()
    (src_state / "secret").write_text("original-device-secret", encoding="utf-8")
    (src_state / "sessions.db").write_bytes(b"not sqlite but archived")

    blob, _ = export_profile_archive("default", state_dir=src_state, hermes_dir=src_hermes)
    assert "hermes-agent-gui/secret" not in _tar_names(blob)
    import_profile_archive(blob, state_dir=dst_state, hermes_dir=dst_hermes)

    new_secret = (dst_state / "secret").read_text(encoding="utf-8")
    assert new_secret != "original-device-secret"
    assert len(new_secret) >= 32


def test_profile_import_rejects_manifest_checksum_mismatch(tmp_path: Path):
    blob = _make_archive_with_file(
        "hermes-agent-gui/keep.txt",
        b"tampered",
        checksum_data=b"original",
    )
    try:
        import_profile_archive(blob, state_dir=tmp_path / "state", hermes_dir=tmp_path / "hermes")
    except ArchiveError as exc:
        assert "checksum mismatch" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ArchiveError")


def test_profile_import_rejects_tar_path_traversal(tmp_path: Path):
    blob = _make_archive_with_file("../../../etc/passwd", b"nope")
    try:
        import_profile_archive(blob, state_dir=tmp_path / "state", hermes_dir=tmp_path / "hermes")
    except ArchiveError as exc:
        assert "unsafe archive path" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ArchiveError")


def test_profile_name_conflict_auto_renames_with_warning(tmp_path: Path):
    src_state = tmp_path / "src-state"
    src_hermes = tmp_path / "src-hermes"
    dst_state = tmp_path / "dst-state"
    dst_hermes = tmp_path / "dst-hermes"
    SessionStore(src_state / "sessions.db").create(title="Import me", profile="default")
    SessionStore(dst_state / "sessions.db").create(title="Existing", profile="default")

    blob, _ = export_profile_archive("default", state_dir=src_state, hermes_dir=src_hermes)
    result = import_profile_archive(blob, state_dir=dst_state, hermes_dir=dst_hermes)

    assert result["imported_profile"].startswith("default-imported")
    assert result["warnings"]


def test_profile_export_route_returns_gzip(server, tmp_path: Path):
    _, _, base = server
    # Login manually to retain the cookie for the binary request.
    login = urllib.request.Request(
        base + "/api/auth/login",
        data=b'{"password":"test-pass"}',
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(login, timeout=5) as resp:
        cookie = resp.headers["Set-Cookie"].split(";", 1)[0]

    req = urllib.request.Request(
        base + "/api/profiles/default/export",
        data=b"{}",
        method="POST",
        headers={"Cookie": cookie, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        blob = resp.read()
        assert resp.status == 200
        assert resp.headers["Content-Type"] == "application/gzip"
        assert "attachment" in resp.headers["Content-Disposition"]

    assert "MANIFEST.json" in _tar_names(blob)
    assert _manifest(blob)["profile_name"] == "default"
