def test_tasks_lane_transitions(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})

    status, body = client("POST", "/api/tasks", body={"title": "hello", "lane": "backlog"})
    assert status == 201
    tid = body["id"]

    status, body = client("GET", "/api/tasks")
    assert status == 200
    assert "backlog" in body["lanes"]
    assert any(t["id"] == tid for t in body["tasks"])

    status, _ = client("PUT", f"/api/tasks/{tid}", body={"lane": "done"})
    assert status == 200

    status, body = client("GET", "/api/tasks")
    assert status == 200
    done_ids = [t["id"] for t in body["by_lane"]["done"]]
    assert tid in done_ids

    status, _ = client("DELETE", f"/api/tasks/{tid}")
    assert status == 200


def test_tasks_bad_lane_rejected(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client("POST", "/api/tasks", body={"title": "x", "lane": "WRONG"})
    assert status == 400
    assert body["error"] == "bad_lane"


def test_cron_create_then_remove(client_exec):
    client_exec("POST", "/api/auth/login", body={"password": "test-pass"})

    status, body = client_exec("POST", "/api/cron", body={
        "name": "smoke", "schedule": "*/5 * * * *", "command": "echo tick",
    })
    assert status == 201
    jid = body["id"]

    status, body = client_exec("GET", "/api/cron")
    assert status == 200
    assert any(j["id"] == jid for j in body["jobs"])

    status, _ = client_exec("DELETE", f"/api/cron/{jid}")
    assert status == 200


def test_cron_rejects_bad_schedule(client_exec):
    client_exec("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client_exec("POST", "/api/cron", body={
        "name": "bad", "schedule": "not-a-schedule", "command": "echo",
    })
    assert status == 400
    assert body["error"] == "bad_schedule"


def test_cron_disabled_by_default(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client("POST", "/api/cron", body={
        "name": "blocked", "schedule": "*/5 * * * *", "command": "echo blocked",
    })
    assert status == 403
    assert body["error"] == "exec_disabled"
