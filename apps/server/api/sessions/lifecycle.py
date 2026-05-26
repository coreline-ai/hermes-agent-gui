"""Session lifecycle — create / list / get / append / rename / delete.

Storage: SQLite at ``~/.hermes-agent-gui/sessions.db`` (stdlib sqlite3).
Schema kept minimal for Phase 2; metadata + per-message tool_calls are JSON
blobs so future phases can grow without migrations.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from ..config import STATE_DIR

SESSIONS_DB = STATE_DIR / "sessions.db"


@dataclass
class Message:
    role: str  # 'system' | 'user' | 'assistant' | 'tool'
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    created_at: int = 0

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(d: dict) -> "Message":
        return Message(
            role=str(d.get("role") or "user"),
            content=str(d.get("content") or ""),
            tool_calls=list(d.get("tool_calls") or []),
            created_at=int(d.get("created_at") or 0),
        )


@dataclass
class Session:
    id: str
    title: str
    profile: str
    created_at: int
    updated_at: int
    messages: list[Message]
    metadata: dict = field(default_factory=dict)

    def to_summary(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "profile": self.profile,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message_count": len(self.messages),
        }

    def to_dict(self) -> dict:
        return {
            **self.to_summary(),
            "messages": [m.to_dict() for m in self.messages],
            "metadata": self.metadata,
        }


class SessionStore:
    """Thread-safe SQLite-backed session store."""

    def __init__(self, path: Path = SESSIONS_DB) -> None:
        self.path = path
        self._lock = threading.RLock()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _ensure_schema(self) -> None:
        with self._lock, self._conn() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    profile TEXT NOT NULL DEFAULT 'default',
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    messages_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at DESC)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_profile ON sessions(profile)")

    # ── CRUD ────────────────────────────────────────────────────────────────

    def create(self, *, title: str | None = None, profile: str = "default") -> Session:
        now = int(time.time())
        sess = Session(
            id=uuid.uuid4().hex[:16],
            title=title or "New chat",
            profile=profile,
            created_at=now,
            updated_at=now,
            messages=[],
        )
        with self._lock, self._conn() as c:
            c.execute(
                "INSERT INTO sessions(id,title,profile,created_at,updated_at,messages_json,metadata_json)"
                " VALUES (?,?,?,?,?,?,?)",
                (
                    sess.id,
                    sess.title,
                    sess.profile,
                    sess.created_at,
                    sess.updated_at,
                    json.dumps([]),
                    json.dumps({}),
                ),
            )
        return sess

    def list(self, *, profile: str | None = None, all_profiles: bool = False) -> list[Session]:
        with self._lock, self._conn() as c:
            if all_profiles or profile is None:
                rows = c.execute(
                    "SELECT id,title,profile,created_at,updated_at,messages_json,metadata_json"
                    " FROM sessions ORDER BY updated_at DESC"
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT id,title,profile,created_at,updated_at,messages_json,metadata_json"
                    " FROM sessions WHERE profile=? ORDER BY updated_at DESC",
                    (profile,),
                ).fetchall()
        return [self._row_to_session(r) for r in rows]

    def get(self, sess_id: str) -> Session | None:
        with self._lock, self._conn() as c:
            row = c.execute(
                "SELECT id,title,profile,created_at,updated_at,messages_json,metadata_json"
                " FROM sessions WHERE id=?",
                (sess_id,),
            ).fetchone()
        return self._row_to_session(row) if row else None

    def append_messages(self, sess_id: str, new_messages: Iterable[Message]) -> Session | None:
        pending = list(new_messages)
        with self._lock, self._conn() as c:
            row = c.execute(
                "SELECT messages_json FROM sessions WHERE id=?", (sess_id,)
            ).fetchone()
            if not row:
                return None
            existing: list[dict] = json.loads(row[0])
            start_index = len(existing)
            for m in pending:
                if not m.created_at:
                    m.created_at = int(time.time())
                existing.append(m.to_dict())
            now = int(time.time())
            c.execute(
                "UPDATE sessions SET messages_json=?, updated_at=? WHERE id=?",
                (json.dumps(existing), now, sess_id),
            )
            if pending:
                try:
                    from .search import _index_messages
                    _index_messages(c, sess_id, pending, start_index=start_index)
                except sqlite3.Error:
                    pass
        return self.get(sess_id)

    def replace_messages(self, sess_id: str, messages: list[Message]) -> Session | None:
        with self._lock, self._conn() as c:
            row = c.execute("SELECT id FROM sessions WHERE id=?", (sess_id,)).fetchone()
            if not row:
                return None
            now = int(time.time())
            c.execute(
                "UPDATE sessions SET messages_json=?, updated_at=? WHERE id=?",
                (json.dumps([m.to_dict() for m in messages]), now, sess_id),
            )
            try:
                from .search import delete_session_index, _index_messages
                delete_session_index(c, sess_id)
                _index_messages(c, sess_id, messages, start_index=0)
            except sqlite3.Error:
                pass
        return self.get(sess_id)

    def rename(self, sess_id: str, title: str) -> Session | None:
        with self._lock, self._conn() as c:
            cur = c.execute(
                "UPDATE sessions SET title=?, updated_at=? WHERE id=?",
                (title, int(time.time()), sess_id),
            )
            if cur.rowcount == 0:
                return None
        return self.get(sess_id)

    def delete(self, sess_id: str) -> bool:
        with self._lock, self._conn() as c:
            cur = c.execute("DELETE FROM sessions WHERE id=?", (sess_id,))
            try:
                from .search import delete_session_index
                delete_session_index(c, sess_id)
            except sqlite3.Error:
                pass
        return cur.rowcount > 0

    # ── helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_session(row: tuple) -> Session:
        id_, title, profile, created_at, updated_at, messages_json, metadata_json = row
        return Session(
            id=id_,
            title=title,
            profile=profile,
            created_at=created_at,
            updated_at=updated_at,
            messages=[Message.from_dict(m) for m in json.loads(messages_json)],
            metadata=json.loads(metadata_json or "{}"),
        )
