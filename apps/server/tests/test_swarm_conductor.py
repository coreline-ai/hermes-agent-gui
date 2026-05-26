def test_conductor_decompose(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client("POST", "/api/conductor/missions", body={
        "prompt": "build the chat UI. review the auth flow. test the cron scheduler.",
    })
    assert status == 201
    roles = [s["role"] for s in body["sub_tasks"]]
    assert "builder" in roles
    assert "reviewer" in roles
    assert "qa" in roles


def test_conductor_dispatch_disabled_by_default(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client("POST", "/api/conductor/missions", body={
        "prompt": "do one thing.",
        "dispatch": True,
    })
    assert status == 403
    assert body["error"] == "exec_disabled"


def test_swarm_worker_spawn_disabled_by_default(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client("POST", "/api/swarm/workers", body={
        "role": "builder", "cmd": ["echo", "hi"],
    })
    assert status == 403
    assert body["error"] == "exec_disabled"


def test_conductor_dispatch_spawns_workers(client_exec):
    client_exec("POST", "/api/auth/login", body={"password": "test-pass"})
    # Override worker template so the dispatched commands actually run + exit.
    import os as _os
    _os.environ["HERMES_SWARM_WORKER_CMD"] = "echo {role}: {text}"
    status, body = client_exec("POST", "/api/conductor/missions", body={
        "prompt": "do one thing.",
        "dispatch": True,
    })
    assert status == 201
    assert body["dispatched"] is not None
    assert len(body["dispatched"]["workers"]) == len(body["sub_tasks"])

    mid = body["id"]
    status, status_body = client_exec("GET", f"/api/conductor/missions/{mid}")
    assert status == 200
    assert status_body["mission_id"] == mid


def test_swarm_worker_spawn_and_kill(client_exec):
    client_exec("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client_exec("POST", "/api/swarm/workers", body={
        "role": "builder", "cmd": ["echo", "hi"],
    })
    assert status == 201
    wid = body["id"]
    status, _ = client_exec("DELETE", f"/api/swarm/workers/{wid}")
    assert status == 200
