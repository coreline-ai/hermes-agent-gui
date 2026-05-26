from __future__ import annotations

from .base import AbstractCliBridge


class Bridge(AbstractCliBridge):
    name = "claude_code"
    binary = "claude"
    install_url = "https://docs.anthropic.com/claude-code"
