from types import SimpleNamespace

from api.auth import session_cookie_header
from api.router import Request


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


def test_csrf_guard_blocks_cross_site_cookie_unsafe_request(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})

    status, body = client(
        "POST",
        "/api/auth/logout",
        headers={"Origin": "https://evil.example", "Sec-Fetch-Site": "cross-site"},
    )

    assert status == 403
    assert body["error"] == "csrf_blocked"


def test_session_cookie_helper_marks_forwarded_https_secure():
    req = Request(
        method="POST",
        path="/api/auth/login",
        query={},
        headers={"x-forwarded-proto": "https"},
        raw=SimpleNamespace(client_address=("127.0.0.1", 12345)),
    )

    assert "Secure" in session_cookie_header(req, "cookie-value")
