from __future__ import annotations

from api.browser.allowlist import validate_url
from api.browser.session import BrowserPool, IDLE_SECONDS


def test_allowlist_and_private_ip(monkeypatch):
    monkeypatch.setenv("HERMES_GUI_BROWSER_ALLOWLIST", "github.com,example.com")
    assert validate_url("https://github.com/openai")[0] is True
    ok, err = validate_url("https://not-allowed.test")
    assert ok is False and err == "domain_not_allowed"
    monkeypatch.setenv("HERMES_GUI_BROWSER_ALLOWLIST", "10.0.0.1")
    ok, err = validate_url("http://10.0.0.1")
    assert ok is False and err == "private_ip_blocked"


def test_idle_timeout_sweeps():
    pool = BrowserPool()
    sess = pool.get()
    sess.updated_at -= IDLE_SECONDS + 1
    pool.sweep()
    assert sess.id not in pool.sessions


def test_browser_routes_forbidden(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client("POST", "/api/browser/navigate", body={"url": "https://not-allowed.test"})
    assert status == 403
    assert body["error"] == "domain_not_allowed"
