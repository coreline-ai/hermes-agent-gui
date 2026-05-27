"""Terminal — Phase 3 minimal.

stdlib HTTP doesn't speak WebSocket easily, so Phase 3 ships a single
``POST /api/terminal/exec`` that runs a one-shot command and returns stdout +
stderr. A future phase (likely with ``websockets`` lib) will lift this into a
real PTY with xterm.js. For now this is sufficient to verify the wiring and
plug a basic "shell exec" component into the UI.

A safety check rejects obviously dangerous commands when no explicit allow-list
flag is set; the user-facing message tells them how to opt-in for full power.
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
from http import HTTPStatus

from . import auth as auth_module
from . import exec_policy
from .config import Config
from .router import Request, Response, Router
from .workspace import _safe_path  # reuse workspace path guard

logger = logging.getLogger(__name__)

EXEC_TIMEOUT_SECONDS = 30
EXEC_MAX_OUTPUT = 256 * 1024  # 256 KB
EXEC_ALLOWED_BINS = {
    "ls", "pwd", "cat", "head", "tail", "wc", "grep", "find", "echo", "stat",
    "git", "python3", "node", "pnpm", "npm",
}


def _is_safe(argv: list[str]) -> bool:
    if not argv:
        return False
    binname = os.path.basename(argv[0])
    return binname in EXEC_ALLOWED_BINS


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("GET", "/api/terminal/status")
    def _status(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        blocked = exec_policy.require_exec(req, cfg)
        blocked_body = blocked.body if blocked is not None and isinstance(blocked.body, dict) else {}
        exec_available = blocked is None
        return Response(
            HTTPStatus.OK,
            {
                "exec_enabled": cfg.exec_enabled,
                "exec_available": exec_available,
                "exec_allow_remote": cfg.exec_allow_remote,
                "blocked_reason": None if exec_available else blocked_body.get("error"),
                "bind_host": blocked_body.get("bind_host"),
                "allowlist": sorted(EXEC_ALLOWED_BINS),
                "detail": (
                    "Terminal execution is enabled for allowlisted commands."
                    if exec_available
                    else blocked_body.get("detail")
                    or "Terminal execution is disabled. Restart with HERMES_GUI_ENABLE_EXEC=1."
                ),
            },
        )

    @router.route("POST", "/api/terminal/exec")
    def _exec(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        if (blocked := exec_policy.require_exec(req, cfg)) is not None:
            return blocked
        try:
            body = req.json()
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
        cmd = str(body.get("cmd") or "").strip()
        cwd_rel = str(body.get("cwd") or ".")
        allow_unsafe = bool(body.get("allow_unsafe"))
        if not cmd:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "cmd_required"})
        try:
            argv = shlex.split(cmd)
        except ValueError as exc:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "shlex", "detail": str(exc)})
        if not allow_unsafe and not _is_safe(argv):
            return Response(
                HTTPStatus.FORBIDDEN,
                {
                    "error": "command_not_in_allowlist",
                    "detail": "Pass {\"allow_unsafe\": true} to bypass (Phase 3 dev only).",
                    "allowlist": sorted(EXEC_ALLOWED_BINS),
                },
            )
        try:
            cwd = _safe_path(cwd_rel)
        except ValueError as exc:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_cwd", "detail": str(exc)})
        try:
            result = subprocess.run(
                argv,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=EXEC_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return Response(HTTPStatus.GATEWAY_TIMEOUT, {"error": "timeout"})
        except FileNotFoundError as exc:
            return Response(HTTPStatus.NOT_FOUND, {"error": "binary_not_found", "detail": str(exc)})
        out = (result.stdout or "")[:EXEC_MAX_OUTPUT]
        err = (result.stderr or "")[:EXEC_MAX_OUTPUT]
        return Response(
            HTTPStatus.OK,
            {
                "exit_code": result.returncode,
                "stdout": out,
                "stderr": err,
                "truncated": (
                    len(result.stdout or "") > EXEC_MAX_OUTPUT
                    or len(result.stderr or "") > EXEC_MAX_OUTPUT
                ),
                "cwd": str(cwd),
            },
        )

    return router
