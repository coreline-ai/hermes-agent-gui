from __future__ import annotations

from .stub import ExternalMemoryProvider


def make(configured: bool = False) -> ExternalMemoryProvider:
    return ExternalMemoryProvider("hindsight", configured=configured)
