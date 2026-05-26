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
    status, body = client("POST", "/api/terminal/exec", body={"cmd": "ls"})
    assert status == 403
    assert body["error"] == "exec_disabled"


def test_pty_disabled_by_default(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client("POST", "/api/pty", body={"cmd": "/bin/sh"})
    assert status == 403
    assert body["error"] == "exec_disabled"


def test_terminal_allowlist(client_exec):
    client_exec("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client_exec("POST", "/api/terminal/exec", body={"cmd": "ls"})
    assert status == 200
    assert body["exit_code"] == 0

    status, body = client_exec("POST", "/api/terminal/exec", body={"cmd": "rm -rf /"})
    assert status == 403
    assert body["error"] == "command_not_in_allowlist"
