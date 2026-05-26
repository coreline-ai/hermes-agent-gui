from __future__ import annotations

import base64
import hmac
import json
import tarfile
import urllib.error
import urllib.request
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from api.providers import discovery
from api.providers.models import Provider
from api.slash_commands import parse_slash_command


class _FakeResponse(BytesIO):
    def __init__(self, payload: dict) -> None:
        super().__init__(json.dumps(payload).encode("utf-8"))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _login_cookie(base: str) -> str:
    req = urllib.request.Request(
        base + "/api/auth/login",
        data=b'{"password":"test-pass"}',
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.headers["Set-Cookie"].split(";", 1)[0]


def _json(base: str, method: str, path: str, *, cookie: str, body: dict | None = None, extra_headers: dict | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json", "Cookie": cookie, **(extra_headers or {})}
    data = json.dumps(body or {}).encode("utf-8") if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw or "{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return exc.code, json.loads(raw or "{}")


def _binary(base: str, method: str, path: str, *, cookie: str, body: dict | None = None) -> tuple[int, bytes, dict]:
    headers = {"Cookie": cookie}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, resp.read(), dict(resp.headers)


def _sse_events(base: str, *, cookie: str, body: dict) -> list[tuple[str, dict]]:
    req = urllib.request.Request(
        base + "/api/chat/stream",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Cookie": cookie},
    )
    events: list[tuple[str, dict]] = []
    with urllib.request.urlopen(req, timeout=10) as resp:
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


def _signed_headers(secret: str, body: dict) -> dict:
    raw = json.dumps(body).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), raw, sha256).hexdigest()
    return {"X-Hermes-Signature": f"sha256={sig}"}


def _tar_manifest(blob: bytes) -> dict:
    with tarfile.open(fileobj=BytesIO(blob), mode="r:gz") as tf:
        mf = tf.extractfile("MANIFEST.json")
        assert mf is not None
        return json.loads(mf.read().decode("utf-8"))


def test_internal_mvp_login_echo_refresh_restore(server):
    _, _, base = server
    cookie = _login_cookie(base)

    status, sess = _json(base, "POST", "/api/sessions", cookie=cookie, body={"title": "MVP internal smoke"})
    assert status == 201
    sid = sess["id"]

    events = _sse_events(
        base,
        cookie=cookie,
        body={
            "session_id": sid,
            "save": True,
            "messages": [{"role": "user", "content": "hello internal mvp"}],
        },
    )
    assert "".join(data.get("text", "") for event, data in events if event == "token") == "hello internal mvp"
    assert any(event == "done" and data.get("adapter") == "echo" for event, data in events)

    status, restored = _json(base, "GET", f"/api/sessions/{sid}", cookie=cookie)
    assert status == 200
    assert [m["role"] for m in restored["messages"][-2:]] == ["user", "assistant"]
    assert restored["messages"][-2]["content"] == "hello internal mvp"
    assert restored["messages"][-1]["content"] == "hello internal mvp"

    # Refresh/restore is equivalent to a second read from the persisted store.
    status, restored_again = _json(base, "GET", f"/api/sessions/{sid}", cookie=cookie)
    assert status == 200
    assert restored_again["messages"] == restored["messages"]


def test_internal_phase15_messaging_webhook_and_profile_archive(server):
    _, _, base = server
    cookie = _login_cookie(base)

    status, telegram = _json(
        base,
        "POST",
        "/api/messaging/telegram/configure",
        cookie=cookie,
        body={
            "credentials": {"bot_token": "12345:abc_DEF-ghi"},
            "behavior": {"mention_required": True, "allowed_chat_ids": ["123"]},
        },
    )
    assert status == 200
    assert telegram == {"ok": True, "platform": "telegram", "configured": True}
    status, telegram_test = _json(base, "POST", "/api/messaging/telegram/test", cookie=cookie, body={})
    assert status == 503
    assert telegram_test["error"] == "hermes_agent_not_running"

    status, reg = _json(base, "POST", "/api/messaging/webhook/configure", cookie=cookie, body={})
    assert status == 200
    payload = {"text": "webhook internal echo"}
    status, inbound = _json(
        base,
        "POST",
        f"/api/messaging/webhook/{reg['token']}/inbound",
        cookie=cookie,
        body=payload,
        extra_headers=_signed_headers(reg["signing_secret"], payload),
    )
    assert status == 200
    assert inbound["response"] == "webhook internal echo"
    assert inbound["done"]["adapter"] == "echo"

    _json(base, "POST", "/api/sessions", cookie=cookie, body={"title": "archive source"})
    status, blob, headers = _binary(base, "GET", "/api/profiles/default/export", cookie=cookie)
    assert status == 200
    assert headers["Content-Type"] == "application/gzip"
    assert _tar_manifest(blob)["profile_name"] == "default"

    status, imported = _json(
        base,
        "POST",
        "/api/profiles/import",
        cookie=cookie,
        body={"archive_b64": base64.b64encode(blob).decode("ascii")},
    )
    assert status == 201
    assert imported["relogin_required"] is True
    assert imported["imported_profile"].startswith("default-imported")

    # Route-level import cannot restart the running server, so we assert the
    # explicit relogin flag and the conflict-safe imported profile instead.
    status, profiles = _json(base, "GET", "/api/profiles", cookie=cookie)
    assert status == 200
    assert any(p["name"].startswith("default-imported") for p in profiles["profiles"])


def test_internal_phase16_openai_mock_discovery_and_model_slash(monkeypatch):
    calls = {"count": 0}

    def fake_urlopen(req, timeout=0):
        calls["count"] += 1
        return _FakeResponse({"data": [{"id": "gpt-mock", "context_length": 128000, "supports_tools": True}]})

    monkeypatch.setattr(discovery.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(discovery.socket, "getaddrinfo", lambda *args, **kwargs: [])
    discovery.clear_cache()

    provider = Provider(
        id="openai-mock",
        kind="openai",
        label="OpenAI Mock",
        base_url="https://mock.openai.local/v1",
        api_key_env="OPENAI_API_KEY",
        auth_type="bearer",
    )
    models, _, cache_hit = discovery.discover_models(provider, "sk-abcdefghij", now=100, use_cache=True)
    assert cache_hit is False
    assert calls["count"] == 1
    assert models[0].id == "gpt-mock"
    assert "tools" in models[0].capabilities

    parsed = parse_slash_command("/model gpt-mock --temp 0.7")
    assert parsed.command == "model"
    assert parsed.args == ["gpt-mock"]
    assert parsed.options == {"temp": "0.7"}
