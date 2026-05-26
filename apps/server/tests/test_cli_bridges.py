from __future__ import annotations

from api.cli_bridges.registry import BRIDGES


def test_cli_bridge_base_conformance():
    assert set(BRIDGES) == {"claude_code", "codex", "gemini", "opencode", "openclaw"}
    for bridge in BRIDGES.values():
        for method in ("spawn", "send", "recv_stream", "kill", "detect"):
            assert callable(getattr(bridge, method))


def test_missing_binary_route(client_exec, monkeypatch):
    monkeypatch.setenv("PATH", "")
    client_exec("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client_exec("POST", "/api/cli-bridges/codex/run", body={"prompt": "hello"})
    assert status == 404
    assert body["error"] == "binary_not_found"
