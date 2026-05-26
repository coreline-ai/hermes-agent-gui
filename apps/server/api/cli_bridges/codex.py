from __future__ import annotations

from .base import AbstractCliBridge


class Bridge(AbstractCliBridge):
    name = "codex"
    binary = "codex"
    install_url = "https://developers.openai.com/codex"
