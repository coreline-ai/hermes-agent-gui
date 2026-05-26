import sqlite3

import pytest

from api.messaging.platforms.base import CredentialError, validate_credentials
from api.messaging.registry import REGISTRY
from api.messaging.status import ensure_schema
from api.sessions.lifecycle import SESSIONS_DB


@pytest.mark.parametrize(
    "token",
    [
        "1:a",
        "123456:ABCDEF",
        "123456:ABC_def-ghi",
        "987654321:token_WITH-123",
        "42:abcdefghijklmnopqrstuvwxyz0123456789_-",
    ],
)
def test_telegram_credential_regex_ok(token):
    validate_credentials(REGISTRY["telegram"], {"bot_token": token})


@pytest.mark.parametrize("token", ["", "abc:def", "123", "123:bad token", "123:bad.token"])
def test_telegram_credential_regex_ng(token):
    with pytest.raises(CredentialError):
        validate_credentials(REGISTRY["telegram"], {"bot_token": token})


def test_configure_rejects_bad_telegram_credential(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client(
        "POST",
        "/api/messaging/telegram/configure",
        body={"credentials": {"bot_token": "bad-token"}},
    )
    assert status == 400
    assert body["error"] == "invalid_credential"
    assert body["field"] == "bot_token"


def test_configure_then_test_delegated_without_hermes_returns_503(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client(
        "POST",
        "/api/messaging/telegram/configure",
        body={
            "credentials": {"bot_token": "12345:abc_DEF-ghi"},
            "behavior": {"mention_required": True, "allowed_chat_ids": ["123"]},
        },
    )
    assert status == 200
    assert body == {"ok": True, "platform": "telegram", "configured": True}

    status, body = client("GET", "/api/messaging/platforms")
    telegram = next(p for p in body["platforms"] if p["id"] == "telegram")
    assert status == 200
    assert telegram["configured"] is True
    assert telegram["behavior"]["mention_required"] is True

    status, body = client("POST", "/api/messaging/telegram/test")
    assert status == 503
    assert body["error"] == "hermes_agent_not_running"


def test_messaging_status_schema_created(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, _ = client("GET", "/api/messaging/platforms")
    assert status == 200
    ensure_schema()
    with sqlite3.connect(SESSIONS_DB) as c:
        table = c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='messaging_status'"
        ).fetchone()
        index = c.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_messaging_status_updated'"
        ).fetchone()
    assert table is not None
    assert index is not None
