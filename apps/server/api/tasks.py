"""Kanban Tasks board — Phase 5.

Lanes from A's TaskBoard (backlog/ready/running/review/blocked/done).
Aging rules from C v3.3.3 (Done 2h, Needs-You 12h).

Storage: SQLite (reuses sessions DB connection for simplicity; tasks live in
their own table). Aging is applied lazily on list().
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from http import HTTPStatus

from . import auth as auth_module
from .config import Config
from .router import Request, Response, Router
from .sessions.lifecycle import SESSIONS_DB

LANES = ("backlog", "ready", "running", "review", "blocked", "done", "needs_you")
DONE_TTL_SECONDS = 2 * 60 * 60      # C v3.3.3 — 2 hours
NEEDS_YOU_TTL = 12 * 60 * 60        # C v3.3.3 — 12 hours

_lock = threading.RLock()


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
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                lane TEXT NOT NULL DEFAULT 'backlog',
                profile TEXT NOT NULL DEFAULT 'default',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                done_at INTEGER,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_lane ON tasks(lane)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_updated ON tasks(updated_at DESC)")
    _schema_ready = True


def _expire_aged() -> None:
    _ensure_schema()
    now = int(time.time())
    with _lock, _conn() as c:
        c.execute(
            "DELETE FROM tasks WHERE lane='done' AND done_at IS NOT NULL AND done_at < ?",
            (now - DONE_TTL_SECONDS,),
        )
        c.execute(
            "DELETE FROM tasks WHERE lane='needs_you' AND updated_at < ?",
            (now - NEEDS_YOU_TTL,),
        )


@dataclass
class Task:
    id: str
    title: str
    lane: str
    profile: str
    created_at: int
    updated_at: int
    done_at: int | None
    metadata: dict

    def to_dict(self) -> dict:
        return self.__dict__ | {}


def _row_to_task(row) -> Task:
    return Task(
        id=row[0], title=row[1], lane=row[2], profile=row[3],
        created_at=row[4], updated_at=row[5], done_at=row[6],
        metadata=json.loads(row[7] or "{}"),
    )


def register_routes(cfg: Config) -> Router:
    _ensure_schema()
    router = Router()

    @router.route("GET", "/api/tasks")
    def _list(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        _expire_aged()
        profile = (req.query.get("profile") or ["default"])[0]
        all_p = (req.query.get("all_profiles") or ["0"])[0] in {"1", "true"}
        with _lock, _conn() as c:
            if all_p:
                rows = c.execute(
                    "SELECT id,title,lane,profile,created_at,updated_at,done_at,metadata_json "
                    "FROM tasks ORDER BY updated_at DESC"
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT id,title,lane,profile,created_at,updated_at,done_at,metadata_json "
                    "FROM tasks WHERE profile=? ORDER BY updated_at DESC",
                    (profile,),
                ).fetchall()
        tasks = [_row_to_task(r).to_dict() for r in rows]
        by_lane = {lane: [t for t in tasks if t["lane"] == lane] for lane in LANES}
        return Response(HTTPStatus.OK, {"lanes": LANES, "tasks": tasks, "by_lane": by_lane})

    @router.route("POST", "/api/tasks")
    def _create(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            body = req.json()
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
        title = str(body.get("title") or "").strip()
        if not title:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "title_required"})
        lane = str(body.get("lane") or "backlog")
        if lane not in LANES:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_lane", "lanes": LANES})
        now = int(time.time())
        tid = uuid.uuid4().hex[:16]
        with _lock, _conn() as c:
            c.execute(
                "INSERT INTO tasks(id,title,lane,profile,created_at,updated_at,metadata_json) "
                "VALUES (?,?,?,?,?,?,?)",
                (tid, title, lane, str(body.get("profile") or "default"), now, now,
                 json.dumps(body.get("metadata") or {})),
            )
        return Response(HTTPStatus.CREATED, {"id": tid})

    @router.route("PUT", "/api/tasks/{tid}")
    def _update(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            body = req.json()
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
        tid = req.params["tid"]
        now = int(time.time())
        fields: list[str] = []
        args: list = []
        if (lane := body.get("lane")):
            if lane not in LANES:
                return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_lane"})
            fields.append("lane=?"); args.append(lane)
            if lane == "done":
                fields.append("done_at=?"); args.append(now)
        if (title := body.get("title")):
            fields.append("title=?"); args.append(title)
        if not fields:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "nothing_to_update"})
        fields.append("updated_at=?"); args.append(now)
        args.append(tid)
        with _lock, _conn() as c:
            cur = c.execute(f"UPDATE tasks SET {','.join(fields)} WHERE id=?", args)
            if cur.rowcount == 0:
                return Response(HTTPStatus.NOT_FOUND, {"error": "task_not_found"})
        return Response(HTTPStatus.OK, {"ok": True})

    @router.route("DELETE", "/api/tasks/{tid}")
    def _delete(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        with _lock, _conn() as c:
            cur = c.execute("DELETE FROM tasks WHERE id=?", (req.params["tid"],))
        if cur.rowcount == 0:
            return Response(HTTPStatus.NOT_FOUND, {"error": "task_not_found"})
        return Response(HTTPStatus.OK, {"ok": True})

    return router
