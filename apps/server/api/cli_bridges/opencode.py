from __future__ import annotations

from .base import AbstractCliBridge


class Bridge(AbstractCliBridge):
    name = "opencode"
    binary = "opencode"
    install_url = "https://opencode.ai"
