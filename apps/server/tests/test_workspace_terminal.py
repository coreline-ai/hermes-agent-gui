from types import SimpleNamespace

from api.config import Config
from api.router import Request
from api.terminal import register_routes as register_terminal_routes


def test_workspace_crud(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})

    status, body = client("GET", "/api/workspace/list?path=.")
    assert status == 200

    status, _ = client("PUT", "/api/workspace/write", body={"path": "hello.md", "content": "# hi"})
    assert status == 200

    status, body = client("GET", "/api/workspace/read?path=hello.md")
    assert status == 200
    assert body["content"] == "# hi"

    status, body = client("GET", "/api/workspace/read?path=../../../etc/passwd")
    assert status == 400
    assert body["error"] == "bad_path"


def test_terminal_disabled_by_default(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client("GET", "/api/terminal/status")
    assert status == 200
    assert body["exec_enabled"] is False
    assert body["exec_available"] is False
    assert body["blocked_reason"] == "exec_disabled"
    assert "pwd" in body["allowlist"]

    status, body = client("POST", "/api/terminal/exec", body={"cmd": "ls"})
    assert status == 403
    assert body["error"] == "exec_disabled"


def test_pty_disabled_by_default(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client("POST", "/api/pty", body={"cmd": "/bin/sh"})
    assert status == 403
    assert body["error"] == "exec_disabled"


def test_api_numeric_validation_returns_400(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})

    for method, path, body in [
        ("GET", "/api/inspector/logs?lines=abc", None),
        ("POST", "/api/brain/query", {"q": "x", "depth": "abc"}),
        ("GET", "/api/sessions/search?q=x&limit=abc", None),
        ("POST", "/api/memory/search", {"q": "x", "k": "abc"}),
    ]:
        status, resp = client(method, path, body=body)
        assert status == 400
        assert resp["error"] == "invalid_int"


def test_pty_input_and_resize_validation(client_exec):
    client_exec("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client_exec("POST", "/api/pty", body={"cmd": ["/bin/sh", "-i"]})
    assert status == 201
    sid = body["id"]
    try:
        status, resp = client_exec("POST", f"/api/pty/{sid}/input", body={"b64": "%%%"})
        assert status == 400
        assert resp["error"] == "invalid_base64"

        status, resp = client_exec("POST", f"/api/pty/{sid}/resize", body={"cols": "abc", "rows": 24})
        assert status == 400
        assert resp["error"] == "invalid_int"
    finally:
        client_exec("DELETE", f"/api/pty/{sid}")


def test_terminal_allowlist(client_exec):
    client_exec("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client_exec("GET", "/api/terminal/status")
    assert status == 200
    assert body["exec_enabled"] is True
    assert body["exec_available"] is True
    assert body["exec_allow_remote"] is False
    assert body["blocked_reason"] is None

    status, body = client_exec("POST", "/api/terminal/exec", body={"cmd": "ls"})
    assert status == 200
    assert body["exit_code"] == 0

    status, body = client_exec("POST", "/api/terminal/exec", body={"cmd": "rm -rf /"})
    assert status == 403
    assert body["error"] == "command_not_in_allowlist"


def test_terminal_status_reports_remote_bind_block():
    cfg = Config(
        password=None,
        bearer_token="tok",
        secret=b"secret",
        fake_backend="echo",
        hermes_api_url=None,
        hermes_api_token=None,
        hermes_dashboard_url=None,
        fail_open=False,
        exec_enabled=True,
        exec_allow_remote=False,
    )
    router = register_terminal_routes(cfg)
    resolved = router.resolve("GET", "/api/terminal/status")
    assert resolved is not None
    handler, params = resolved
    req = Request(
        method="GET",
        path="/api/terminal/status",
        query={},
        headers={"authorization": "Bearer tok"},
        raw=SimpleNamespace(
            server=SimpleNamespace(server_address=("0.0.0.0", 8800)),
            client_address=("127.0.0.1", 12345),
        ),
    )
    req.params = params

    resp = handler(req)
    assert resp is not None
    assert resp.status == 200
    assert isinstance(resp.body, dict)
    assert resp.body["exec_enabled"] is True
    assert resp.body["exec_available"] is False
    assert resp.body["blocked_reason"] == "exec_remote_bind_disabled"
    assert resp.body["bind_host"] == "0.0.0.0"
