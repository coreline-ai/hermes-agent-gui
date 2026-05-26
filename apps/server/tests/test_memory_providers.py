from __future__ import annotations

import importlib

from api.memory_providers.registry import PROVIDER_NAMES, build_provider


def test_all_providers_implement_base_interface():
    for name in PROVIDER_NAMES:
        provider = build_provider(name)
        for method in ("query", "write", "purge", "test_connection"):
            assert callable(getattr(provider, method))


def test_external_provider_modules_make():
    for module_name in ["honcho", "mem0", "hindsight", "retaindb", "supermemory", "byterover"]:
        module = importlib.import_module(f"api.memory_providers.{module_name}")
        provider = module.make(configured=True)
        assert provider.query("hello", k=1)


def test_provider_activation_requires_config(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client("GET", "/api/memory/providers")
    assert status == 200
    assert any(p["name"] == "local_vss" and p["active"] for p in body["providers"])

    status, body = client("POST", "/api/memory/providers/honcho/activate", body={"config": {}})
    assert status == 400
    assert body["error"] == "provider_config_missing"

    status, body = client("POST", "/api/memory/providers/honcho/activate", body={"config": {"api_key": "x"}})
    assert status == 200
    assert body["name"] == "honcho"
    assert body["configured"] is True
