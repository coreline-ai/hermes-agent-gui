"""Webhook inbound route shim — Phase 15b."""

from __future__ import annotations

from ..router import Request, Response
from ..runtime_adapter import Adapter
from .platforms.webhook import handle_inbound


def inbound(req: Request, adapter: Adapter) -> Response:
    return handle_inbound(req, adapter)
