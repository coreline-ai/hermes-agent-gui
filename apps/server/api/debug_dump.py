"""Redacted debug dump zip — Phase 20."""

from __future__ import annotations

import io
import json
import platform
import time
import zipfile
from http import HTTPStatus

from . import auth as auth_module
from .config import Config
from .dashboard import _redact
from .router import Request, Response, Router


def build_debug_dump(cfg: Config) -> bytes:
    bio = io.BytesIO()
    payload = {
        "version": "0.1.0",
        "created_at": int(time.time()),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "capabilities": {
            "auth": cfg.has_any_auth,
            "exec_enabled": cfg.exec_enabled,
            "hermes_gateway": bool(cfg.hermes_api_url),
        },
    }
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(payload, indent=2))
        zf.writestr("redacted-env.txt", _redact("\n".join(f"{k}={v}" for k, v in sorted(__import__('os').environ.items()) if k.startswith("HERMES"))))
    return bio.getvalue()


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("GET", "/api/debug/dump")
    def _dump(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        return Response(HTTPStatus.OK, build_debug_dump(cfg), headers=[("Content-Type", "application/zip"), ("Content-Disposition", "attachment; filename=hermes-debug-dump.zip")])

    return router
