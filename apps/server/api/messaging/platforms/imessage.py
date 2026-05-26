"""imessage delegated messaging wrapper."""

from __future__ import annotations

from ..registry import REGISTRY
from .base import DelegatedPlatform

platform = DelegatedPlatform(REGISTRY["imessage"])
