from __future__ import annotations

import json
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer

from api import auth, chat, config as config_mod
from api.router import Router
from api.runtime_adapter import Adapter, ChatTurn
from api.sessions import SessionStore
from server import make_handler


class CaptureAdapter(Adapter):
    name = "capture"

    def __init__(self) -> None:
        self.turns: list[ChatTurn] = []

    def stream(self, turn: ChatTurn):
        self.turns.append(turn)
        yield "token", {"text": "ok"}
        yield "done", {"session_id": turn.session_id, "adapter": self.name}


def _login_cookie(base: str) -> str:
    req = urllib.request.Request(
        base + "/api/auth/login",
        data=json.dumps({"password": "test-pass"}).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.headers["Set-Cookie"].split(";", 1)[0]


def _read_sse_until_done(base: str, cookie: str, body: dict) -> list[tuple[str, dict]]:
    req = urllib.request.Request(
        base + "/api/chat/stream",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Cookie": cookie},
    )
    events: list[tuple[str, dict]] = []
    with urllib.request.urlopen(req, timeout=5) as resp:
        event = "message"
        data_lines: list[str] = []
        while True:
            line = resp.readline().decode("utf-8")
            if line == "":
                break
            line = line.rstrip("\n")
            if not line:
                if data_lines:
                    payload = json.loads("\n".join(data_lines))
                    events.append((event, payload))
                    if event in {"done", "error"}:
                        break
                event = "message"
                data_lines = []
                continue
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].strip())
    return events


def test_chat_route_passes_model_provider_and_created_session_to_adapter(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_GUI_PASSWORD", "test-pass")
    monkeypatch.setenv("HERMES_GUI_STATE_DIR", str(tmp_path / "state"))
    cfg = config_mod.load()
    store = SessionStore(tmp_path / "sessions.db")
    adapter = CaptureAdapter()
    router = Router()
    router.extend(auth.register_routes(cfg))
    router.extend(chat.register_routes(cfg, adapter, store))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(router, web_dist=tmp_path / "missing-web"))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        cookie = _login_cookie(base)
        events = _read_sse_until_done(
            base,
            cookie,
            {
                "auto_create_session": True,
                "model": "model-xyz",
                "provider_id": "provider-123",
                "messages": [{"role": "user", "content": "route capture"}],
            },
        )
    finally:
        httpd.shutdown()
        httpd.server_close()

    assert any(event == "done" for event, _ in events)
    assert len(adapter.turns) == 1
    turn = adapter.turns[0]
    assert turn.model == "model-xyz"
    assert turn.provider_id == "provider-123"
    assert turn.session_id
    assert store.get(turn.session_id) is not None
