def test_session_crud(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})

    status, sess = client("POST", "/api/sessions", body={"title": "hello"})
    assert status == 201
    sid = sess["id"]

    status, body = client("GET", "/api/sessions")
    assert status == 200
    assert any(s["id"] == sid for s in body["sessions"])

    status, body = client("PUT", f"/api/sessions/{sid}", body={"title": "renamed"})
    assert status == 200
    assert body["title"] == "renamed"

    status, _ = client("DELETE", f"/api/sessions/{sid}")
    assert status == 200


def test_session_stream_route_precedes_session_id_route(server):
    import json
    import urllib.request

    _, _, base = server
    login_req = urllib.request.Request(
        base + "/api/auth/login",
        data=json.dumps({"password": "test-pass"}).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(login_req, timeout=5) as login_resp:
        cookie = login_resp.headers["Set-Cookie"].split(";", 1)[0]

    stream_req = urllib.request.Request(base + "/api/sessions/_stream", headers={"Cookie": cookie})
    with urllib.request.urlopen(stream_req, timeout=5) as stream_resp:
        assert stream_resp.status == 200
        assert stream_resp.readline().decode("utf-8").strip() == "event: ready"


def test_session_health_drift_repair(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    _, sess = client("POST", "/api/sessions", body={"title": "drift"})
    sid = sess["id"]
    status, body = client(
        "POST",
        f"/api/sessions/{sid}/health",
        body={
            "browser_messages": [
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": "ok"},
                {"role": "user", "content": "second"},
            ],
            "compact_context_messages": 1,
        },
    )
    assert status == 200
    assert body["drift"] is True
    assert body["drift_kind"] == "browser_ahead"
    assert body["repaired"] is True


def test_chat_auto_creates_persistent_session(server):
    import json
    import urllib.request

    _, _, base = server
    login_req = urllib.request.Request(
        base + "/api/auth/login",
        data=json.dumps({"password": "test-pass"}).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(login_req, timeout=5) as login_resp:
        cookie = login_resp.headers["Set-Cookie"].split(";", 1)[0]

    stream_req = urllib.request.Request(
        base + "/api/chat/stream",
        data=json.dumps(
            {
                "auto_create_session": True,
                "title": "auto persisted",
                "provider_id": "provider-x",
                "model": "model-y",
                "messages": [{"role": "user", "content": "auto create me"}],
            }
        ).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Cookie": cookie},
    )
    sid = ""
    with urllib.request.urlopen(stream_req, timeout=10) as resp:
        event = "message"
        data_lines: list[str] = []
        while True:
            line = resp.readline().decode("utf-8")
            if line == "":
                break
            line = line.rstrip("\n")
            if not line:
                if data_lines and event == "done":
                    sid = json.loads("\n".join(data_lines))["session_id"]
                    break
                event = "message"
                data_lines = []
                continue
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].strip())

    assert sid
    get_req = urllib.request.Request(base + f"/api/sessions/{sid}", headers={"Cookie": cookie})
    with urllib.request.urlopen(get_req, timeout=5) as resp:
        status = resp.status
        restored = json.loads(resp.read().decode("utf-8"))
    assert status == 200
    assert restored["title"] == "auto persisted"
    assert [m["role"] for m in restored["messages"][-2:]] == ["user", "assistant"]


def test_chat_auto_create_cleans_up_session_on_stream_error(server_gateway_down):
    import json
    import urllib.request

    _, _, base = server_gateway_down
    login_req = urllib.request.Request(
        base + "/api/auth/login",
        data=json.dumps({"password": "test-pass"}).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(login_req, timeout=5) as login_resp:
        cookie = login_resp.headers["Set-Cookie"].split(";", 1)[0]

    stream_req = urllib.request.Request(
        base + "/api/chat/stream",
        data=json.dumps(
            {
                "auto_create_session": True,
                "title": "should be removed",
                "messages": [{"role": "user", "content": "fail then cleanup"}],
            }
        ).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Cookie": cookie},
    )
    saw_error = False
    with urllib.request.urlopen(stream_req, timeout=10) as resp:
        event = "message"
        data_lines: list[str] = []
        while True:
            line = resp.readline().decode("utf-8")
            if line == "":
                break
            line = line.rstrip("\n")
            if not line:
                if data_lines and event == "error":
                    saw_error = True
                    break
                event = "message"
                data_lines = []
                continue
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].strip())

    assert saw_error
    list_req = urllib.request.Request(base + "/api/sessions", headers={"Cookie": cookie})
    with urllib.request.urlopen(list_req, timeout=5) as resp:
        listed = json.loads(resp.read().decode("utf-8"))
    assert listed["sessions"] == []
