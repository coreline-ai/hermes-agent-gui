import stat

from api.messaging.credentials import (
    delete_platform_credentials,
    env_path,
    is_configured,
    read_platform_credentials,
    write_credentials,
)
from api.messaging.registry import REGISTRY


def test_credential_write_is_atomic_0600_and_merges(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes"))
    path = env_path()
    path.parent.mkdir(parents=True)
    path.write_text("HERMES_EXISTING_TOKEN=keep\n", encoding="utf-8")
    path.chmod(0o600)

    write_credentials("telegram", {"bot_token": "12345:abc_DEF-ghi"})
    write_credentials("slack", {"bot_token": "xoxb-abc-123"})

    raw = path.read_text(encoding="utf-8")
    assert "HERMES_EXISTING_TOKEN=keep" in raw
    assert "HERMES_TELEGRAM_BOT_TOKEN=12345:abc_DEF-ghi" in raw
    assert "HERMES_SLACK_BOT_TOKEN=xoxb-abc-123" in raw
    assert stat.S_IMODE(path.stat().st_mode) == 0o600

    assert read_platform_credentials("telegram") == {"bot_token": "12345:abc_DEF-ghi"}
    assert is_configured(REGISTRY["telegram"]) is True


def test_credential_delete_only_platform_prefix(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes"))
    write_credentials("telegram", {"bot_token": "12345:abc"})
    write_credentials("slack", {"bot_token": "xoxb-abc-123"})

    assert delete_platform_credentials("telegram") is True

    raw = env_path().read_text(encoding="utf-8")
    assert "HERMES_TELEGRAM_BOT_TOKEN" not in raw
    assert "HERMES_SLACK_BOT_TOKEN=xoxb-abc-123" in raw
    assert is_configured(REGISTRY["telegram"]) is False
