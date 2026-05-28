"""Shared execution feature gate for shell/PTY/cron/swarm routes.

Command execution is intentionally disabled by default. Local desktop users may
enable it explicitly with ``HERMES_GUI_ENABLE_EXEC=1``. If the server is bound
to a non-loopback interface, a second opt-in is required to avoid accidentally
turning Docker/LAN exposure into RCE.
"""

from __future__ import annotations

import ipaddress
from http import HTTPStatus

from .config import Config
from .router import Request, Response


def is_exec_enabled(cfg: Config | None) -> bool:
    return bool(cfg and cfg.exec_enabled)


def _bind_host(req: Request) -> str:
    server = getattr(req.raw, "server", None)
    addr = getattr(server, "server_address", ("?", 0))
    return str(addr[0]) if addr else "?"


def _is_loopback(host: str) -> bool:
    if host in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _exec_block_body(cfg: Config | None, host: str) -> dict | None:
    if cfg is None or not cfg.exec_enabled:
        return {
            "error": "exec_disabled",
            "detail": "Set HERMES_GUI_ENABLE_EXEC=1 to enable terminal/PTY/cron/swarm execution.",
        }

    if not _is_loopback(host) and not cfg.exec_allow_remote:
        return {
            "error": "exec_remote_bind_disabled",
            "detail": (
                "Execution is disabled on non-loopback binds unless "
                "HERMES_GUI_ALLOW_REMOTE_EXEC=1 is set."
            ),
            "bind_host": host,
        }
    return None


def _block_response(body: dict | None) -> Response | None:
    return Response(HTTPStatus.FORBIDDEN, body) if body is not None else None


def require_exec_for_host(cfg: Config | None, host: str | None = None) -> Response | None:
    if cfg is None:
        return _block_response(
            {
                "error": "exec_disabled",
                "detail": "Execution config is unavailable.",
            }
        )
    return _block_response(_exec_block_body(cfg, host or cfg.bind_host))


def require_exec(req: Request, cfg: Config) -> Response | None:
    blocked = require_exec_for_host(cfg, _bind_host(req))
    if blocked is not None:
        return blocked
    return None
