from api.messaging.registry import DELEGATED_PLATFORM_IDS, DIRECT_PLATFORM_IDS, REGISTRY, list_platforms


def test_messaging_registry_has_16_platforms_and_modes():
    platforms = list_platforms()
    assert len(platforms) == 16
    assert len(DELEGATED_PLATFORM_IDS) == 14
    assert len(DIRECT_PLATFORM_IDS) == 2
    assert set(DIRECT_PLATFORM_IDS) == {"webhook", "home_assistant"}
    assert all(p.mode in {"delegated", "direct"} for p in platforms)
    assert all(p.requires_hermes_running is (p.mode == "delegated") for p in platforms)


def test_telegram_metadata_shape():
    telegram = REGISTRY["telegram"]
    assert telegram.label == "Telegram"
    assert telegram.mode == "delegated"
    field = telegram.credential_fields[0]
    assert field.name == "bot_token"
    assert field.pattern == r"^[0-9]+:[A-Za-z0-9_-]+$"


def test_messaging_platforms_endpoint(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client("GET", "/api/messaging/platforms")
    assert status == 200
    platforms = body["platforms"]
    assert len(platforms) == 16
    assert sum(1 for p in platforms if p["mode"] == "delegated") == 14
    assert sum(1 for p in platforms if p["mode"] == "direct") == 2
    assert next(p for p in platforms if p["id"] == "telegram")["configured"] is False
