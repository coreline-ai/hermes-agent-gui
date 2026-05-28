from __future__ import annotations

import json
import time
import urllib.error
from io import BytesIO

import pytest

from api.providers import discovery, store
from api.providers.models import Provider


class FakeResponse(BytesIO):
    def __init__(self, payload: dict, status: int = 200) -> None:
        super().__init__(json.dumps(payload).encode("utf-8"))
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeOpener:
    def __init__(self, fn) -> None:
        self.fn = fn

    def open(self, req, timeout=0):
        return self.fn(req, timeout=timeout)


def test_provider_store_rejects_invalid_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_GUI_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes"))
    from importlib import reload
    import api.config as config_mod
    import api.sessions.lifecycle as lifecycle
    import api.providers.store as store_mod

    reload(config_mod)
    reload(lifecycle)
    reload(store_mod)
    with pytest.raises(store_mod.ProviderStoreError) as exc:
        store_mod.create_provider(kind="openai", label="Bad", api_key="nope")
    assert exc.value.code == "invalid_api_key_format"


def test_provider_store_rejects_duplicate_label(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_GUI_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes"))
    from importlib import reload
    import api.config as config_mod
    import api.sessions.lifecycle as lifecycle
    import api.providers.store as store_mod

    reload(config_mod)
    reload(lifecycle)
    reload(store_mod)
    store_mod.create_provider(kind="openai", label="Main", api_key="sk-abcdefghij")
    with pytest.raises(store_mod.ProviderStoreError) as exc:
        store_mod.create_provider(kind="anthropic", label="main", api_key="sk-ant-abcdefghij")
    assert exc.value.code == "provider_label_taken"


def test_anthropic_discovery_static_models():
    provider = Provider(
        id="anthropic1",
        kind="anthropic",
        label="Anthropic",
        base_url="https://api.anthropic.com/v1",
        api_key_env="ANTHROPIC_API_KEY",
        auth_type="bearer",
    )
    models, _, cache_hit = discovery.discover_models(provider, "sk-ant-abcdefghij", now=10, use_cache=False)
    assert not cache_hit
    assert any(m.id == "claude-opus-4" for m in models)


def test_model_discovery_cache_hit_under_10ms(monkeypatch):
    provider = Provider(
        id="openai-cache",
        kind="openai",
        label="OpenAI",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        auth_type="bearer",
    )

    calls = {"count": 0}

    def fake_urlopen(req, timeout=0):
        calls["count"] += 1
        return FakeResponse({"data": [{"id": "gpt-test", "context_length": 128000}]})

    monkeypatch.setattr(discovery.urllib.request, "build_opener", lambda *_args, **_kwargs: FakeOpener(fake_urlopen))
    monkeypatch.setattr(discovery.socket, "getaddrinfo", lambda *args, **kwargs: [])
    discovery.clear_cache()
    models, _, hit1 = discovery.discover_models(provider, "sk-abcdefghij", now=100)
    start = time.perf_counter()
    models2, _, hit2 = discovery.discover_models(provider, "sk-abcdefghij", now=101)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert [m.id for m in models] == ["gpt-test"]
    assert [m.id for m in models2] == ["gpt-test"]
    assert hit1 is False and hit2 is True
    assert calls["count"] == 1
    assert elapsed_ms < 10


def test_provider_auth_failure_maps_error(monkeypatch):
    provider = Provider(
        id="openai-401",
        kind="openai",
        label="OpenAI",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        auth_type="bearer",
    )

    def fake_urlopen(req, timeout=0):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", hdrs=None, fp=None)

    monkeypatch.setattr(discovery.urllib.request, "build_opener", lambda *_args, **_kwargs: FakeOpener(fake_urlopen))
    monkeypatch.setattr(discovery.socket, "getaddrinfo", lambda *args, **kwargs: [])
    discovery.clear_cache()
    with pytest.raises(discovery.DiscoveryError) as exc:
        discovery.discover_models(provider, "sk-abcdefghij", now=200, use_cache=False)
    assert exc.value.code == "provider_auth_failed"


def test_provider_redirect_to_private_ip_is_blocked():
    provider = Provider(
        id="openai-redirect",
        kind="openai",
        label="OpenAI",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        auth_type="bearer",
    )
    handler = discovery._ProviderRedirectHandler(provider)  # noqa: SLF001
    req = discovery.urllib.request.Request(
        "https://api.openai.com/v1/models",
        headers={"Authorization": "Bearer sk-abcdefghij"},
    )

    with pytest.raises(discovery.DiscoveryError) as exc:
        handler.redirect_request(req, None, 302, "Found", {}, "http://10.0.0.1/models")

    assert exc.value.code == "provider_private_ip_blocked"


def test_provider_cross_host_redirect_is_blocked(monkeypatch):
    provider = Provider(
        id="openai-cross-host",
        kind="openai",
        label="OpenAI",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        auth_type="bearer",
    )
    monkeypatch.setattr(discovery.socket, "getaddrinfo", lambda *args, **kwargs: [])
    handler = discovery._ProviderRedirectHandler(provider)  # noqa: SLF001
    req = discovery.urllib.request.Request(
        "https://api.openai.com/v1/models",
        headers={"Authorization": "Bearer sk-abcdefghij"},
    )

    with pytest.raises(discovery.DiscoveryError) as exc:
        handler.redirect_request(req, None, 302, "Found", {}, "https://models.openai.com/v1/models")

    assert exc.value.code == "provider_redirect_blocked"
