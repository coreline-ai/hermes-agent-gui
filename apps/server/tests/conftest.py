"""Pytest fixtures — spin up the full server on an ephemeral port per test."""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))


def _start_server(
    tmp_path,
    monkeypatch,
    *,
    enable_exec: bool = False,
    web_dist: Path | None = None,
    fake_backend: str | None = "echo",
    hermes_api_url: str | None = None,
):
    """Yield a running ``(host, port, base_url)`` triple."""
    monkeypatch.setenv("HERMES_GUI_PASSWORD", "test-pass")
    if fake_backend is None:
        monkeypatch.delenv("HERMES_GUI_FAKE_BACKEND", raising=False)
    else:
        monkeypatch.setenv("HERMES_GUI_FAKE_BACKEND", fake_backend)
    if hermes_api_url is None:
        monkeypatch.delenv("HERMES_API_URL", raising=False)
    else:
        monkeypatch.setenv("HERMES_API_URL", hermes_api_url)
    monkeypatch.setenv("HERMES_GUI_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("HERMES_GUI_WORKSPACES", str(tmp_path / "ws"))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes"))
    if enable_exec:
        monkeypatch.setenv("HERMES_GUI_ENABLE_EXEC", "1")
    else:
        monkeypatch.delenv("HERMES_GUI_ENABLE_EXEC", raising=False)
    monkeypatch.delenv("HERMES_GUI_ALLOW_REMOTE_EXEC", raising=False)
    if web_dist is not None:
        monkeypatch.setenv("HERMES_GUI_WEB_DIST", str(web_dist))
    else:
        monkeypatch.delenv("HERMES_GUI_WEB_DIST", raising=False)
    (tmp_path / "ws").mkdir(parents=True, exist_ok=True)

    # Force reload of config-dependent modules with the fresh env.
    for mod in list(sys.modules.keys()):
        if mod.startswith("api") or mod == "server":
            sys.modules.pop(mod, None)

    from server import build_router, make_handler  # noqa: WPS433
    from api import config as config_mod  # noqa: WPS433
    from http.server import ThreadingHTTPServer

    cfg = config_mod.load()
    router = build_router(cfg)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(router))
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)
    try:
        yield ("127.0.0.1", port, f"http://127.0.0.1:{port}")
    finally:
        httpd.shutdown()
        httpd.server_close()


@pytest.fixture
def server(tmp_path, monkeypatch):
    yield from _start_server(tmp_path, monkeypatch, enable_exec=False)


@pytest.fixture
def server_exec(tmp_path, monkeypatch):
    yield from _start_server(tmp_path, monkeypatch, enable_exec=True)


@pytest.fixture
def server_gateway_down(tmp_path, monkeypatch):
    yield from _start_server(
        tmp_path,
        monkeypatch,
        fake_backend=None,
        hermes_api_url="http://127.0.0.1:9",
    )


def _client_for(server_info):
    """Return a tiny urllib-based client for tests."""
    import json as _json
    import urllib.request

    _, _, base = server_info
    jar: dict[str, str] = {}

    def call(method, path, *, body=None, headers=None):
        h = {"Content-Type": "application/json", **(headers or {})}
        if jar:
            h["Cookie"] = "; ".join(f"{k}={v}" for k, v in jar.items())
        data = _json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(base + path, data=data, method=method, headers=h)
        try:
            resp = urllib.request.urlopen(req, timeout=5)
            raw = resp.read().decode("utf-8")
            sc = resp.getcode()
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            sc = exc.code
            resp = exc
        for cookie in resp.headers.get_all("Set-Cookie") or []:
            name, _, rest = cookie.partition("=")
            jar[name.strip()] = rest.split(";")[0].strip()
        try:
            return sc, _json.loads(raw)
        except _json.JSONDecodeError:
            return sc, raw

    return call


@pytest.fixture
def client(server):
    return _client_for(server)


@pytest.fixture
def client_exec(server_exec):
    return _client_for(server_exec)
