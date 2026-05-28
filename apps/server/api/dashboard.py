"""Dashboard / inspector / health aggregator — Phase 7.

Combines B's agent_health + system_health + dashboard_probe + gateway_watcher
and C's redacted-logs policy into three endpoints:

- GET /api/health/agent     -- Hermes Agent heartbeat (gateway/embedded probe)
- GET /api/health/system    -- OS-level stats (memory, load)
- GET /api/dashboard        -- session counts, model mix, recent activity
- GET /api/inspector/logs   -- last N log lines, redacted
"""

from __future__ import annotations

import os
import re
import time
import urllib.error
import urllib.request
from http import HTTPStatus
from pathlib import Path

from . import auth as auth_module
from .config import Config
from .router import Request, Response, Router
from .sessions.lifecycle import SESSIONS_DB
from .validation import ValidationError, parse_bounded_int, validation_response


# C v3.3 redaction policy — extended in P3#14.
# Each pattern is (regex, replacement_factory). The factory keeps any non-secret
# prefix the match captures so context stays readable.

_REPLACE_KEEP_PREFIX = lambda m: m.group(1) + "***"
_REPLACE_FULL = lambda _: "***"
_REPLACE_DB = lambda m: m.group(1) + "://" + m.group(2) + ":***@"

REDACT_PATTERNS: list[tuple[re.Pattern, object]] = [
    # OpenAI-style secret tokens: sk-..., sk-live-..., sk-proj-...
    (re.compile(r"(?i)\b(sk-[a-z0-9_\-]{16,})\b"), _REPLACE_FULL),
    # AWS access key id
    (re.compile(r"\b(AKIA[0-9A-Z]{16})\b"), _REPLACE_FULL),
    # AWS secret access key (40 char base64)
    (re.compile(r"(?i)(aws[_-]?secret[_-]?access[_-]?key[\"' :=]+)([A-Za-z0-9/+=]{30,})"), _REPLACE_KEEP_PREFIX),
    # JWT (header.payload.signature)
    (re.compile(r"\b(eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,})\b"), _REPLACE_FULL),
    # GitHub personal access tokens & fine-grained
    (re.compile(r"\b(ghp_|gho_|ghu_|ghs_|ghr_|github_pat_)[A-Za-z0-9_]{16,}\b"), _REPLACE_FULL),
    # Slack tokens
    (re.compile(r"\b(xox[abprso]-[A-Za-z0-9\-]{10,})\b"), _REPLACE_FULL),
    # Google API key
    (re.compile(r"\b(AIza[0-9A-Za-z_\-]{30,})\b"), _REPLACE_FULL),
    # Anthropic API key
    (re.compile(r"\b(sk-ant-[A-Za-z0-9_\-]{16,})\b"), _REPLACE_FULL),
    # api_key / token / password assignments
    (re.compile(r"(?i)((?:api[_-]?key|access[_-]?token|auth[_-]?token|password|passwd|secret)[\"' :=]+)([A-Za-z0-9._/+=\-]{8,})"), _REPLACE_KEEP_PREFIX),
    # HTTP Authorization: Bearer ...
    (re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._\-]{12,})"), _REPLACE_KEEP_PREFIX),
    (re.compile(r"(?i)(authorization[\"' :=]+)([A-Za-z0-9._\-\s]{12,})"), _REPLACE_KEEP_PREFIX),
    # PEM key blocks (entire block — multi-line)
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----"), _REPLACE_FULL),
    # SSH private keys
    (re.compile(r"-----BEGIN OPENSSH PRIVATE KEY-----[\s\S]+?-----END OPENSSH PRIVATE KEY-----"), _REPLACE_FULL),
    # Database connection strings (postgres://, mysql://, mongodb+srv://, redis://)
    (re.compile(r"\b(postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp)://([^:/@\s]+):[^@\s]+@"), _REPLACE_DB),
]


def _redact(text: str) -> str:
    out = text
    for pat, repl in REDACT_PATTERNS:
        out = pat.sub(repl, out)
    return out


def _probe_gateway(cfg: Config) -> dict:
    if not cfg.hermes_api_url:
        return {"configured": False}
    url = f"{cfg.hermes_api_url.rstrip('/')}/health"
    started = time.monotonic()
    try:
        req = urllib.request.Request(url)
        if cfg.hermes_api_token:
            req.add_header("Authorization", f"Bearer {cfg.hermes_api_token}")
        with urllib.request.urlopen(req, timeout=3) as resp:
            body = resp.read().decode("utf-8", errors="replace")[:512]
        return {
            "configured": True,
            "reachable": True,
            "latency_ms": round((time.monotonic() - started) * 1000, 1),
            "body_preview": body,
        }
    except urllib.error.URLError as exc:
        return {
            "configured": True,
            "reachable": False,
            "latency_ms": round((time.monotonic() - started) * 1000, 1),
            "error": str(exc),
        }


def _system_stats() -> dict:
    try:
        load1, load5, load15 = os.getloadavg()
    except OSError:
        load1 = load5 = load15 = 0.0
    return {
        "platform": os.uname().sysname if hasattr(os, "uname") else os.name,
        "loadavg_1": round(load1, 2),
        "loadavg_5": round(load5, 2),
        "loadavg_15": round(load15, 2),
    }


def _dashboard_summary() -> dict:
    import sqlite3
    SESSIONS_DB.parent.mkdir(parents=True, exist_ok=True)
    if not SESSIONS_DB.exists():
        return {"sessions": 0, "tasks": 0, "cron_jobs": 0, "recent_sessions": []}
    with sqlite3.connect(SESSIONS_DB) as c:
        def _safe(query: str, default=0):
            try:
                return c.execute(query).fetchone()[0]
            except sqlite3.OperationalError:
                return default

        sessions_total = _safe("SELECT COUNT(*) FROM sessions")
        tasks_total = _safe("SELECT COUNT(*) FROM tasks")
        cron_total = _safe("SELECT COUNT(*) FROM cron_jobs")
        recent: list[dict] = []
        try:
            for row in c.execute(
                "SELECT id,title,updated_at FROM sessions ORDER BY updated_at DESC LIMIT 6"
            ):
                recent.append({"id": row[0], "title": row[1], "updated_at": row[2]})
        except sqlite3.OperationalError:
            pass
    return {
        "sessions": sessions_total,
        "tasks": tasks_total,
        "cron_jobs": cron_total,
        "recent_sessions": recent,
    }


def _tail_log(path: Path, *, lines: int = 100) -> list[str]:
    if not path.is_file():
        return []
    data = path.read_bytes()[-(lines * 400):]
    return [_redact(ln) for ln in data.decode("utf-8", errors="replace").splitlines()[-lines:]]


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("GET", "/api/health/agent")
    def _agent_health(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        return Response(HTTPStatus.OK, _probe_gateway(cfg))

    @router.route("GET", "/api/health/system")
    def _system_health(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        return Response(HTTPStatus.OK, _system_stats())

    @router.route("GET", "/api/dashboard")
    def _dashboard(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        return Response(
            HTTPStatus.OK,
            {
                "summary": _dashboard_summary(),
                "agent": _probe_gateway(cfg),
                "system": _system_stats(),
            },
        )

    @router.route("GET", "/api/inspector/logs")
    def _logs(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            lines = parse_bounded_int(
                (req.query.get("lines") or ["100"])[0],
                field="lines",
                default=100,
                min_value=1,
                max_value=1000,
            )
        except ValidationError as exc:
            return validation_response(exc)
        path = Path.home() / ".hermes-agent-gui" / "gui.log"
        return Response(HTTPStatus.OK, {"path": str(path), "lines": _tail_log(path, lines=lines)})

    return router


__all__ = ["register_routes", "_redact"]
