"""Messaging platform wrappers."""

from __future__ import annotations

from ..registry import REGISTRY
from .base import DelegatedPlatform


def get_platform_impl(platform_id: str) -> DelegatedPlatform | None:
    meta = REGISTRY.get(platform_id)
    return DelegatedPlatform(meta) if meta else None
