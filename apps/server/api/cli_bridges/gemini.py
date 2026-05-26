from __future__ import annotations

from .base import AbstractCliBridge


class Bridge(AbstractCliBridge):
    name = "gemini"
    binary = "gemini"
    install_url = "https://ai.google.dev/gemini-api/docs/cli"
