from __future__ import annotations

from .base import AbstractCliBridge


class Bridge(AbstractCliBridge):
    name = "openclaw"
    binary = "openclaw"
    install_url = "https://github.com"
