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


def test_cron_background_runner_blocks_remote_bind(tmp_path, monkeypatch):
    import importlib

    monkeypatch.setenv("HERMES_GUI_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("HERMES_GUI_ENABLE_EXEC", "1")
    monkeypatch.setenv("HERMES_GUI_HOST", "0.0.0.0")
    monkeypatch.delenv("HERMES_GUI_ALLOW_REMOTE_EXEC", raising=False)

    import api.config as config_mod
    import api.sessions.lifecycle as lifecycle_mod
    import api.cron as cron_mod

    importlib.reload(config_mod)
    importlib.reload(lifecycle_mod)
    cron_mod = importlib.reload(cron_mod)
    cfg = config_mod.load()
    cron_mod._ensure_schema()  # noqa: SLF001
    jid = "remote-block"
    with cron_mod._conn() as conn:  # noqa: SLF001
        conn.execute(
            "INSERT INTO cron_jobs(id,name,schedule,command,enabled) VALUES (?,?,?,?,1)",
            (jid, "remote", "* * * * *", "echo should-not-run"),
        )

    cron_mod._run_job(jid, "echo should-not-run", cfg)  # noqa: SLF001

    with cron_mod._conn() as conn:  # noqa: SLF001
        row = conn.execute("SELECT last_exit_code,last_output FROM cron_jobs WHERE id=?", (jid,)).fetchone()
    assert row == (-1, "exec_remote_bind_disabled")
