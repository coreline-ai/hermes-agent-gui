from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from api.browser import actions
from api.browser.allowlist import validate_url
from api.browser.session import BrowserPool, BrowserSession, IDLE_SECONDS


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


def test_browser_redirect_revalidates_private_ip(monkeypatch):
    class RedirectHandler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(302)
            self.send_header("Location", "http://10.0.0.1/metadata")
            self.end_headers()

        def log_message(self, *_args):  # noqa: ANN002
            return None

    monkeypatch.setenv("HERMES_GUI_BROWSER_ALLOWLIST", "127.0.0.1,10.0.0.1")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        sess = BrowserSession(id="test")
        try:
            actions.navigate(sess, f"http://127.0.0.1:{httpd.server_address[1]}/start")
        except PermissionError as exc:
            assert str(exc) == "private_ip_blocked"
        else:  # pragma: no cover
            raise AssertionError("expected private redirect to be blocked")
    finally:
        httpd.shutdown()
        httpd.server_close()
