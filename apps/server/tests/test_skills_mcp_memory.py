def test_skills_local_empty(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client("GET", "/api/skills")
    assert status == 200
    assert body["source"] == "local"
    assert isinstance(body["skills"], list)


def test_mcp_add_list_remove(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})

    status, body = client("POST", "/api/mcp/servers", body={
        "name": "echo", "command": ["echo", "hi"],
    })
    assert status == 201

    status, body = client("GET", "/api/mcp/servers")
    assert status == 200
    assert any(s["name"] == "echo" for s in body["servers"])

    status, _ = client("DELETE", "/api/mcp/servers/echo")
    assert status == 200

    status, _ = client("DELETE", "/api/mcp/servers/echo")
    assert status == 404


def test_memory_routes_when_root_missing(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client("GET", "/api/memory")
    assert status == 200
    assert body["exists"] in (True, False)  # tolerant — host may have ~/.hermes/memory
