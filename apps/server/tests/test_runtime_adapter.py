from __future__ import annotations

import urllib.error

from api.runtime_adapter import ChatTurn, GatewayAdapter


def test_gateway_payload_carries_explicit_provider_for_all_flavors():
    adapter = GatewayAdapter("http://gateway.test", None)
    turn = ChatTurn(
        messages=[{"role": "user", "content": "hello"}],
        session_id="s1",
        model="claude-test",
        provider_id="anthropic-main",
    )

    assert adapter._payload(turn, "openai")["provider_id"] == "anthropic-main"  # noqa: SLF001
    assert adapter._payload(turn, "responses")["provider_id"] == "anthropic-main"  # noqa: SLF001
    assert adapter._payload(turn, "agent")["provider_id"] == "anthropic-main"  # noqa: SLF001


def test_gateway_payload_omits_auto_provider_for_openai_compat():
    adapter = GatewayAdapter("http://gateway.test", None)
    turn = ChatTurn(messages=[{"role": "user", "content": "hello"}], provider_id="auto")

    assert "provider_id" not in adapter._payload(turn, "openai")  # noqa: SLF001
    assert "provider_id" not in adapter._payload(turn, "responses")  # noqa: SLF001


def test_gateway_probe_prefers_native_agent_stream_for_explicit_provider(monkeypatch):
    adapter = GatewayAdapter("http://gateway.test", None)
    calls: list[tuple[str, str]] = []

    def fake_open(path: str, flavor: str, turn: ChatTurn):
        del turn
        calls.append((path, flavor))
        raise urllib.error.HTTPError(path, 404, "not found", hdrs={}, fp=None)

    monkeypatch.setattr(adapter, "_open", fake_open)
    picked = adapter._try_endpoint(ChatTurn(messages=[], provider_id="anthropic-main"))  # noqa: SLF001

    assert picked is None
    assert calls[0] == ("/v1/agent/stream", "agent")
    assert calls[1:] == [
        ("/v1/chat/completions", "openai"),
        ("/v1/responses", "responses"),
    ]


def test_gateway_reprobes_native_agent_after_default_cache(monkeypatch):
    adapter = GatewayAdapter("http://gateway.test", None)
    calls: list[tuple[str, str, str]] = []

    def fake_open(path: str, flavor: str, turn: ChatTurn):
        calls.append((path, flavor, turn.provider_id))
        if turn.provider_id == "auto" and path == "/v1/chat/completions":
            return object()
        if turn.provider_id == "anthropic-main" and path == "/v1/agent/stream":
            return object()
        raise urllib.error.HTTPError(path, 404, "not found", hdrs={}, fp=None)

    monkeypatch.setattr(adapter, "_open", fake_open)

    assert adapter._try_endpoint(ChatTurn(messages=[], provider_id="auto")) is not None  # noqa: SLF001
    calls.clear()

    picked = adapter._try_endpoint(ChatTurn(messages=[], provider_id="anthropic-main"))  # noqa: SLF001

    assert picked is not None
    assert picked[1] == ("/v1/agent/stream", "agent")
    assert calls[0] == ("/v1/agent/stream", "agent", "anthropic-main")
