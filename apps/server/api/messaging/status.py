"""SQLite status cache for messaging platforms."""

from __future__ import annotations

import sqlite3
import threading
import time

from ..sessions.lifecycle import SESSIONS_DB
from .models import PlatformStatus

_lock = threading.RLock()
_schema_ready = False


def _conn() -> sqlite3.Connection:
    SESSIONS_DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(SESSIONS_DB, isolation_level=None)
    c.execute("PRAGMA journal_mode=WAL")
    return c


def ensure_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return
    with _lock, _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS messaging_status (
              platform TEXT PRIMARY KEY,
              configured INTEGER NOT NULL DEFAULT 0,
              connected INTEGER NOT NULL DEFAULT 0,
              last_event_at INTEGER,
              last_error TEXT,
              updated_at INTEGER NOT NULL
            )
            """
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_messaging_status_updated ON messaging_status(updated_at DESC)")
    _schema_ready = True


def get_status(platform: str) -> PlatformStatus:
    ensure_schema()
    with _lock, _conn() as c:
        row = c.execute(
            "SELECT configured,connected,last_event_at,last_error FROM messaging_status WHERE platform=?",
            (platform,),
        ).fetchone()
    if not row:
        return PlatformStatus(platform, False, False, None, None)
    return PlatformStatus(platform, bool(row[0]), bool(row[1]), row[2], row[3])


def record_status(
    platform: str,
    *,
    configured: bool | None = None,
    connected: bool | None = None,
    last_event_at: int | None = None,
    last_error: str | None = None,
) -> PlatformStatus:
    ensure_schema()
    current = get_status(platform)
    new = PlatformStatus(
        platform,
        current.configured if configured is None else configured,
        current.connected if connected is None else connected,
        current.last_event_at if last_event_at is None else last_event_at,
        current.last_error if last_error is None else last_error,
    )
    with _lock, _conn() as c:
        c.execute(
            """
            INSERT INTO messaging_status(platform,configured,connected,last_event_at,last_error,updated_at)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(platform) DO UPDATE SET
              configured=excluded.configured,
              connected=excluded.connected,
              last_event_at=excluded.last_event_at,
              last_error=excluded.last_error,
              updated_at=excluded.updated_at
            """,
            (
                platform,
                1 if new.configured else 0,
                1 if new.connected else 0,
                new.last_event_at,
                new.last_error,
                int(time.time()),
            ),
        )
    return new


def record_event(platform: str, *, connected: bool = True, error: str | None = None) -> PlatformStatus:
    return record_status(platform, connected=connected, last_event_at=int(time.time()), last_error=error)
