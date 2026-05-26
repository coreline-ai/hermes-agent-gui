def test_login_logout_cycle(client):
    status, body = client("GET", "/api/auth/me")
    assert status == 401

    status, _ = client("POST", "/api/auth/login", body={"password": "wrong"})
    assert status == 401

    status, body = client("POST", "/api/auth/login", body={"password": "test-pass"})
    assert status == 200
    assert body["user"]["name"] == "local"

    status, body = client("GET", "/api/auth/me")
    assert status == 200
    assert body["user"]["name"] == "local"

    status, _ = client("POST", "/api/auth/logout")
    assert status == 200


def test_oauth_passkey_stubs(client):
    status, body = client("GET", "/api/auth/oauth/github/start")
    assert status == 501
    assert body["error"] == "oauth_not_configured"
