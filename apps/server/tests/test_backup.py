from __future__ import annotations

import io
import tarfile
import zipfile

from api.backup import build_backup
from api.debug_dump import build_debug_dump
from api.config import load


def test_backup_contains_manifest_and_excludes_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_GUI_STATE_DIR", str(tmp_path / "state"))
    data = build_backup()
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        names = tf.getnames()
    assert "MANIFEST.json" in names
    assert not any(name.endswith("/secret") for name in names)


def test_debug_dump_zip_redacts_env(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_GUI_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("HERMES_API_TOKEN", "sk-abcdefghijklmnop")
    cfg = load()
    data = build_debug_dump(cfg)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert "manifest.json" in zf.namelist()
        env = zf.read("redacted-env.txt").decode("utf-8")
    assert "sk-abcdefghijklmnop" not in env
