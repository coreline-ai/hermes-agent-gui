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
