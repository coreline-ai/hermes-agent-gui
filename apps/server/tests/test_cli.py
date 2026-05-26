from __future__ import annotations

import json

from apps.server.cli import main


def test_doctor_outputs_capabilities(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_GUI_STATE_DIR", str(tmp_path / "state"))
    assert main(["doctor"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is True
    assert "python" in data


def test_clear_login_locks(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_GUI_STATE_DIR", str(tmp_path / "state"))
    assert main(["clear-login-locks"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True
