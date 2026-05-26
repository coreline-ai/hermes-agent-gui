"""Base platform validation helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ...config import Config
from .. import delegate_probe
from ..models import PlatformMeta


@dataclass(frozen=True)
class CredentialError(Exception):
    field: str
    detail: str


def validate_credentials(meta: PlatformMeta, credentials: dict[str, object]) -> None:
    for field in meta.credential_fields:
        raw = credentials.get(field.name)
        value = "" if raw is None else str(raw).strip()
        if field.required and not value:
            raise CredentialError(field.name, f"{field.name} is required")
        if not value:
            continue
        if field.pattern and not re.match(field.pattern, value):
            raise CredentialError(field.name, f"{field.name} does not match pattern")
        if field.type == "url" and not (value.startswith("http://") or value.startswith("https://")):
            raise CredentialError(field.name, f"{field.name} must be an http(s) URL")
        if field.options and value not in field.options:
            raise CredentialError(field.name, f"{field.name} must be one of: {', '.join(field.options)}")


class DelegatedPlatform:
    def __init__(self, meta: PlatformMeta) -> None:
        self.meta = meta

    def validate(self, credentials: dict[str, object]) -> None:
        validate_credentials(self.meta, credentials)

    def test_connection(self, cfg: Config):
        return delegate_probe.test_connection(cfg, self.meta.id)
