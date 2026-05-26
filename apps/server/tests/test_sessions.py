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
