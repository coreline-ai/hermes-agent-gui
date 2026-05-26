import json
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer


def test_singlefile_missing_html_returns_actionable_503(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_GUI_PASSWORD", "test-pass")
    monkeypatch.setenv("HERMES_GUI_FAKE_BACKEND", "echo")
    monkeypatch.setenv("HERMES_GUI_STATE_DIR", str(tmp_path / "state"))

    for mod in list(sys.modules.keys()):
        if mod.startswith("api") or mod in {"server", "serve_singlefile"}:
            sys.modules.pop(mod, None)

    from api import config as config_mod  # noqa: WPS433
    from server import build_router  # noqa: WPS433
    from serve_singlefile import _wrap_handler  # noqa: WPS433

    cfg = config_mod.load()
    router = build_router(cfg)
    missing_html = tmp_path / "missing.html"
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _wrap_handler(router, missing_html))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        try:
            urllib.request.urlopen(base + "/")
            raise AssertionError("expected HTTP 503")
        except urllib.error.HTTPError as exc:
            body = json.loads(exc.read().decode("utf-8"))
            assert exc.code == 503
            assert body["error"] == "singlefile_html_missing"
            assert "build:singlefile" in body["hint"]

        health = urllib.request.urlopen(base + "/api/health")
        assert health.status == 200
    finally:
        httpd.shutdown()
        httpd.server_close()
