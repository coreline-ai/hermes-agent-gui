"""GET /api/health — Phase 0 liveness probe (extended for Phase 1)."""

from __future__ import annotations

import time
from http import HTTPStatus

from . import __version__
from .config import Config
from .router import Request, Response, Router

_STARTED_AT = time.monotonic()

router = Router()


def get_health(adapter_name: str = "unknown") -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "phase": "1",
        "uptime_seconds": round(time.monotonic() - _STARTED_AT, 1),
        "adapter": adapter_name,
    }


def register_routes(cfg: Config, adapter_name: str) -> Router:
    del cfg  # health is intentionally open in Phase 1
    router = Router()

    @router.route("GET", "/api/health")
    def _health(_req: Request) -> Response:
        return Response(HTTPStatus.OK, get_health(adapter_name))

    return router
