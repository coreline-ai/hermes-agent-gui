import pytest


def test_csp_report_open_and_logged(client):
    status, _ = client("POST", "/api/csp-report", body={
        "csp-report": {"document-uri": "https://example", "violated-directive": "script-src"},
    })
    assert status in (204, 200)


def test_csp_rate_limited(client):
    # Open endpoint — fill the bucket. 100/60s allowance, so 110 should trip.
    last_status = 204
    for _ in range(110):
        last_status, _ = client("POST", "/api/csp-report", body={"x": "y"})
        if last_status == 429:
            break
    assert last_status == 429


def test_client_event_requires_auth(client):
    status, body = client("POST", "/api/client-event", body={"event": "page_view"})
    assert status == 401


def test_client_event_after_login(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client("POST", "/api/client-event", body={
        "event": "page_view", "source": "test", "url_path": "/chat",
    })
    assert status == 200
    assert body == {"ok": True}


def test_client_event_rejects_empty(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client("POST", "/api/client-event", body={"unknown": "x"})
    assert status == 400
    assert body["error"] == "empty_event"


def test_security_headers_present(server):
    import urllib.request
    _, _, base = server
    resp = urllib.request.urlopen(base + "/api/health")
    csp = resp.headers.get("Content-Security-Policy") or ""
    assert "default-src 'self'" in csp
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
