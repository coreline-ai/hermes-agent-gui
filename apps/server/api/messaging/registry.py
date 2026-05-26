"""Messaging platform registry — Phase 15a."""

from __future__ import annotations

from .models import CredentialField, PlatformMeta

DOCS_BASE = "https://hermes-agent.nousresearch.com/docs/integrations"

DEFAULT_BEHAVIOR = {
    "enabled": {"type": "boolean", "default": True},
    "mention_required": {"type": "boolean", "default": False},
    "allowed_chat_ids": {"type": "array", "items": "string", "default": []},
}


def _field(
    name: str,
    label: str,
    type_: str = "password",
    *,
    required: bool = True,
    placeholder: str = "",
    pattern: str | None = None,
    options: list[str] | None = None,
) -> CredentialField:
    return CredentialField(
        name=name,
        label=label,
        type=type_,  # type: ignore[arg-type]
        required=required,
        placeholder=placeholder,
        pattern=pattern,
        options=options,
    )


def _delegated(pid: str, label: str, description: str, fields: list[CredentialField]) -> PlatformMeta:
    return PlatformMeta(
        id=pid,  # type: ignore[arg-type]
        label=label,
        mode="delegated",
        description=description,
        credential_fields=fields,
        behavior_schema=DEFAULT_BEHAVIOR,
        docs_url=f"{DOCS_BASE}/{pid}",
        requires_hermes_running=True,
    )


def _direct(pid: str, label: str, description: str, fields: list[CredentialField], behavior: dict | None = None) -> PlatformMeta:
    return PlatformMeta(
        id=pid,  # type: ignore[arg-type]
        label=label,
        mode="direct",
        description=description,
        credential_fields=fields,
        behavior_schema=behavior or DEFAULT_BEHAVIOR,
        docs_url=f"{DOCS_BASE}/{pid.replace('_', '-')}",
        requires_hermes_running=False,
    )


REGISTRY: dict[str, PlatformMeta] = {
    "telegram": _delegated(
        "telegram",
        "Telegram",
        "Bot token + mention control. Actual bot runtime is delegated to Hermes Agent.",
        [_field("bot_token", "Bot Token", placeholder="123456:ABC-DEF...", pattern=r"^[0-9]+:[A-Za-z0-9_-]+$")],
    ),
    "discord": _delegated(
        "discord",
        "Discord",
        "Discord bot token and channel behavior delegated to Hermes Agent.",
        [_field("bot_token", "Bot Token", pattern=r"^[A-Za-z0-9._-]{20,}$")],
    ),
    "slack": _delegated(
        "slack",
        "Slack",
        "Slack app/bot token delegated to Hermes Agent.",
        [_field("bot_token", "Bot Token", placeholder="xoxb-...", pattern=r"^xox[abprso]-[A-Za-z0-9-]+$")],
    ),
    "whatsapp": _delegated(
        "whatsapp",
        "WhatsApp",
        "WhatsApp Cloud API credentials delegated to Hermes Agent.",
        [_field("access_token", "Access Token"), _field("phone_number_id", "Phone Number ID", "text")],
    ),
    "signal": _delegated(
        "signal",
        "Signal",
        "Signal bridge account delegated to Hermes Agent.",
        [_field("account", "Signal Account", "text"), _field("bridge_token", "Bridge Token")],
    ),
    "matrix": _delegated(
        "matrix",
        "Matrix",
        "Matrix homeserver and token delegated to Hermes Agent.",
        [_field("homeserver_url", "Homeserver URL", "url", placeholder="https://matrix.org"), _field("access_token", "Access Token")],
    ),
    "mattermost": _delegated(
        "mattermost",
        "Mattermost",
        "Mattermost server and token delegated to Hermes Agent.",
        [_field("server_url", "Server URL", "url"), _field("token", "Token")],
    ),
    "email": _delegated(
        "email",
        "Email",
        "IMAP/SMTP credentials delegated to Hermes Agent.",
        [
            _field("imap_host", "IMAP Host", "text"),
            _field("smtp_host", "SMTP Host", "text"),
            _field("username", "Username", "text"),
            _field("app_password", "App Password"),
        ],
    ),
    "sms": _delegated(
        "sms",
        "SMS",
        "SMS provider credentials delegated to Hermes Agent.",
        [
            _field("provider", "Provider", "select", options=["twilio", "vonage"]),
            _field("account_id", "Account ID", "text"),
            _field("auth_token", "Auth Token"),
        ],
    ),
    "imessage": _delegated(
        "imessage",
        "iMessage",
        "BlueBubbles bridge credentials delegated to Hermes Agent.",
        [_field("bridge_url", "Bridge URL", "url"), _field("api_key", "API Key")],
    ),
    "dingtalk": _delegated(
        "dingtalk",
        "DingTalk",
        "DingTalk bot credentials delegated to Hermes Agent.",
        [_field("app_key", "App Key", "text"), _field("app_secret", "App Secret")],
    ),
    "feishu": _delegated(
        "feishu",
        "Feishu / Lark",
        "Feishu/Lark app credentials delegated to Hermes Agent.",
        [_field("app_id", "App ID", "text"), _field("app_secret", "App Secret")],
    ),
    "wecom": _delegated(
        "wecom",
        "WeCom",
        "WeCom app credentials delegated to Hermes Agent.",
        [_field("corp_id", "Corp ID", "text"), _field("agent_id", "Agent ID", "text"), _field("secret", "Secret")],
    ),
    "wechat": _delegated(
        "wechat",
        "WeChat",
        "WeChat QR login/session is delegated to Hermes Agent.",
        [_field("session_hint", "Session Hint", "qr", required=False, placeholder="Hermes Agent manages QR login")],
    ),
    "webhook": _direct(
        "webhook",
        "Webhook",
        "Direct inbound webhook endpoint handled by hermes-agent-gui.",
        [],
        {"enabled": {"type": "boolean", "default": True}, "response_mode": {"type": "string", "default": "sync"}},
    ),
    "home_assistant": _direct(
        "home_assistant",
        "Home Assistant",
        "Direct Home Assistant notify integration handled by hermes-agent-gui.",
        [_field("ha_url", "Home Assistant URL", "url"), _field("long_lived_token", "Long-lived Token"), _field("notify_service", "Notify Service", "text", placeholder="notify.mobile_app_phone")],
    ),
}

DELEGATED_PLATFORM_IDS = tuple(pid for pid, meta in REGISTRY.items() if meta.mode == "delegated")
DIRECT_PLATFORM_IDS = tuple(pid for pid, meta in REGISTRY.items() if meta.mode == "direct")


def get_platform(platform_id: str) -> PlatformMeta | None:
    return REGISTRY.get(platform_id)


def list_platforms() -> list[PlatformMeta]:
    return list(REGISTRY.values())
