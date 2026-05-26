import sys
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer


def test_static_spa_serving_and_api_passthrough(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><div id=\"root\">SPA</div>", encoding="utf-8")
    (assets / "app.js").write_text("console.log('ok')", encoding="utf-8")

    monkeypatch.setenv("HERMES_GUI_PASSWORD", "test-pass")
    monkeypatch.setenv("HERMES_GUI_FAKE_BACKEND", "echo")
    monkeypatch.setenv("HERMES_GUI_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("HERMES_GUI_WEB_DIST", str(dist))
    monkeypatch.delenv("HERMES_GUI_ENABLE_EXEC", raising=False)

    for mod in list(sys.modules.keys()):
        if mod.startswith("api") or mod == "server":
            sys.modules.pop(mod, None)

    from api import config as config_mod  # noqa: WPS433
    from server import build_router, make_handler  # noqa: WPS433

    cfg = config_mod.load()
    router = build_router(cfg)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(router))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        root = urllib.request.urlopen(base + "/")
        assert root.status == 200
        assert root.headers["Cache-Control"] == "no-store"
        assert "SPA" in root.read().decode("utf-8")

        route = urllib.request.urlopen(base + "/chat")
        assert route.status == 200
        assert "SPA" in route.read().decode("utf-8")

        asset = urllib.request.urlopen(base + "/assets/app.js")
        assert asset.status == 200
        assert "immutable" in asset.headers["Cache-Control"]

        health = urllib.request.urlopen(base + "/api/health")
        assert health.status == 200
        assert "application/json" in health.headers["Content-Type"]
    finally:
        httpd.shutdown()
        httpd.server_close()
