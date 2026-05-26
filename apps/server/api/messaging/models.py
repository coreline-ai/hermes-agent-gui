"""Messaging platform data models — Phase 15a."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PlatformId = Literal[
    "telegram", "discord", "slack", "whatsapp", "signal", "matrix",
    "mattermost", "email", "sms", "imessage", "dingtalk", "feishu",
    "wecom", "wechat", "webhook", "home_assistant",
]
PlatformMode = Literal["delegated", "direct"]
CredentialType = Literal["text", "password", "url", "select", "qr"]


@dataclass(frozen=True)
class CredentialField:
    name: str
    label: str
    type: CredentialType
    required: bool = True
    placeholder: str = ""
    pattern: str | None = None
    options: list[str] | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "type": self.type,
            "required": self.required,
            "placeholder": self.placeholder,
            "pattern": self.pattern,
            "options": self.options,
        }


@dataclass(frozen=True)
class PlatformMeta:
    id: PlatformId
    label: str
    mode: PlatformMode
    description: str
    credential_fields: list[CredentialField]
    behavior_schema: dict
    docs_url: str
    requires_hermes_running: bool

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "mode": self.mode,
            "description": self.description,
            "credential_fields": [f.to_dict() for f in self.credential_fields],
            "behavior_schema": self.behavior_schema,
            "docs_url": self.docs_url,
            "requires_hermes_running": self.requires_hermes_running,
        }


@dataclass(frozen=True)
class PlatformStatus:
    id: str
    configured: bool
    connected: bool
    last_event_at: int | None
    last_error: str | None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "configured": self.configured,
            "connected": self.connected,
            "last_event_at": self.last_event_at,
            "last_error": self.last_error,
        }
