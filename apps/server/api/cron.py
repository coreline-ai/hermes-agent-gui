"""Cron scheduler — Phase 5.

Background thread evaluates a crontab-style schedule every minute. Each fired
job is recorded so the UI can show the run history. Cron rows live in the same
SQLite store as sessions/tasks.

Schedule format: 5 fields ``minute hour dom month dow``. ``*`` and ``*/N``
supported (Phase 5 minimal — comma lists / ranges are a future-phase nicety).
"""

from __future__ import annotations

import logging
import sqlite3
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus

from . import auth as auth_module
from . import exec_policy
from .config import Config
from .router import Request, Response, Router
from .sessions.lifecycle import SESSIONS_DB

logger = logging.getLogger(__name__)
_lock = threading.RLock()
_scheduler_started = False
_CFG: Config | None = None


def _conn() -> sqlite3.Connection:
    SESSIONS_DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(SESSIONS_DB, isolation_level=None)
    c.execute("PRAGMA journal_mode=WAL")
    return c


_schema_ready = False


def _ensure_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return
    with _lock, _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS cron_jobs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                schedule TEXT NOT NULL,
                command TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                last_run_at INTEGER,
                last_exit_code INTEGER,
                last_output TEXT
            )
            """
        )
    _schema_ready = True


# ── Cron expression evaluation (5-field) ────────────────────────────────────


@dataclass(frozen=True)
class CronFields:
    minute: str
    hour: str
    dom: str
    month: str
    dow: str

    @staticmethod
    def parse(expr: str) -> "CronFields | None":
        parts = expr.split()
        if len(parts) != 5:
            return None
        return CronFields(*parts)


def _match_field(value: int, field: str) -> bool:
    if field == "*":
        return True
    if field.startswith("*/"):
        try:
            step = int(field[2:])
            return step > 0 and value % step == 0
        except ValueError:
            return False
    try:
        return int(field) == value
    except ValueError:
        return False


def _should_fire(cron: CronFields, dt: datetime) -> bool:
    return (
        _match_field(dt.minute, cron.minute)
        and _match_field(dt.hour, cron.hour)
        and _match_field(dt.day, cron.dom)
        and _match_field(dt.month, cron.month)
        and _match_field(dt.weekday(), cron.dow)
    )


# ── Run + scheduler loop ─────────────────────────────────────────────────────


def _run_job(job_id: str, command: str, cfg: Config | None = None) -> None:
    if not exec_policy.is_exec_enabled(cfg or _CFG):
        with _lock, _conn() as c:
            c.execute(
                "UPDATE cron_jobs SET last_run_at=?, last_exit_code=?, last_output=? WHERE id=?",
                (int(time.time()), -1, "exec_disabled", job_id),
            )
        return

    logger.info("cron fire: %s -> %s", job_id, command)
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=300, check=False,
        )
        out = (result.stdout or "")[:8000] + ((result.stderr or "")[:8000])
        with _lock, _conn() as c:
            c.execute(
                "UPDATE cron_jobs SET last_run_at=?, last_exit_code=?, last_output=? WHERE id=?",
                (int(time.time()), result.returncode, out, job_id),
            )
    except Exception as exc:  # noqa: BLE001
        with _lock, _conn() as c:
            c.execute(
                "UPDATE cron_jobs SET last_run_at=?, last_exit_code=?, last_output=? WHERE id=?",
                (int(time.time()), -1, f"runner_error: {exc}", job_id),
            )


def _scheduler_loop() -> None:
    last_minute = -1
    while True:
        now = datetime.now()
        if now.minute != last_minute:
            last_minute = now.minute
            with _lock, _conn() as c:
                rows = c.execute(
                    "SELECT id,schedule,command FROM cron_jobs WHERE enabled=1"
                ).fetchall()
            for jid, sched, cmd in rows:
                cron = CronFields.parse(sched)
                if cron and _should_fire(cron, now):
                    threading.Thread(target=_run_job, args=(jid, cmd, _CFG), daemon=True).start()
        # Sleep until next minute boundary
        time.sleep(max(1, 60 - datetime.now().second))


def _start_scheduler_once() -> None:
    global _scheduler_started
    with _lock:
        if _scheduler_started:
            return
        _scheduler_started = True
        threading.Thread(target=_scheduler_loop, daemon=True, name="cron-scheduler").start()


def register_routes(cfg: Config) -> Router:
    global _CFG
    _CFG = cfg
    _ensure_schema()
    _start_scheduler_once()
    router = Router()

    @router.route("GET", "/api/cron")
    def _list(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        with _lock, _conn() as c:
            rows = c.execute(
                "SELECT id,name,schedule,command,enabled,last_run_at,last_exit_code,last_output "
                "FROM cron_jobs ORDER BY name"
            ).fetchall()
        jobs = [
            {
                "id": r[0], "name": r[1], "schedule": r[2], "command": r[3],
                "enabled": bool(r[4]),
                "last_run_at": r[5], "last_exit_code": r[6], "last_output": r[7],
            }
            for r in rows
        ]
        return Response(HTTPStatus.OK, {"jobs": jobs})

    @router.route("POST", "/api/cron")
    def _create(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        if (blocked := exec_policy.require_exec(req, cfg)) is not None:
            return blocked
        try:
            body = req.json()
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
        name = str(body.get("name") or "").strip()
        schedule = str(body.get("schedule") or "").strip()
        command = str(body.get("command") or "").strip()
        if not (name and schedule and command):
            return Response(HTTPStatus.BAD_REQUEST, {"error": "name_schedule_command_required"})
        if CronFields.parse(schedule) is None:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_schedule"})
        jid = uuid.uuid4().hex[:16]
        with _lock, _conn() as c:
            c.execute(
                "INSERT INTO cron_jobs(id,name,schedule,command,enabled) VALUES (?,?,?,?,1)",
                (jid, name, schedule, command),
            )
        return Response(HTTPStatus.CREATED, {"id": jid})

    @router.route("POST", "/api/cron/{jid}/run")
    def _run_now(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        if (blocked := exec_policy.require_exec(req, cfg)) is not None:
            return blocked
        jid = req.params["jid"]
        with _lock, _conn() as c:
            row = c.execute("SELECT command FROM cron_jobs WHERE id=?", (jid,)).fetchone()
        if not row:
            return Response(HTTPStatus.NOT_FOUND, {"error": "job_not_found"})
        threading.Thread(target=_run_job, args=(jid, row[0], cfg), daemon=True).start()
        return Response(HTTPStatus.ACCEPTED, {"ok": True})

    @router.route("DELETE", "/api/cron/{jid}")
    def _delete(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        with _lock, _conn() as c:
            cur = c.execute("DELETE FROM cron_jobs WHERE id=?", (req.params["jid"],))
        if cur.rowcount == 0:
            return Response(HTTPStatus.NOT_FOUND, {"error": "job_not_found"})
        return Response(HTTPStatus.OK, {"ok": True})

    return router
