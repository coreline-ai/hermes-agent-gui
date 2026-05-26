"""SQLite-backed summary store with lexical search fallback — Phase 18."""

from __future__ import annotations

import sqlite3
import time
import uuid
from dataclasses import dataclass

from ..sessions.lifecycle import SESSIONS_DB
from .embedder import similarity


@dataclass(frozen=True)
class MemoryChunk:
    id: str
    session_id: str
    range_start: int
    range_end: int
    summary: str
    embedding_model: str
    created_at: int

    def to_dict(self, score: float | None = None) -> dict:
        out = {
            "id": self.id,
            "session_id": self.session_id,
            "range_start": self.range_start,
            "range_end": self.range_end,
            "summary": self.summary,
            "embedding_model": self.embedding_model,
            "created_at": self.created_at,
        }
        if score is not None:
            out["score"] = score
        return out


def _conn() -> sqlite3.Connection:
    SESSIONS_DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(SESSIONS_DB, isolation_level=None)
    c.execute("PRAGMA journal_mode=WAL")
    return c


def ensure_schema() -> None:
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_chunks (
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL,
              range_start INTEGER NOT NULL,
              range_end INTEGER NOT NULL,
              summary TEXT NOT NULL,
              embedding_model TEXT NOT NULL,
              created_at INTEGER NOT NULL,
              UNIQUE(session_id, range_start, range_end)
            )
            """
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_memory_chunks_session ON memory_chunks(session_id)")


def add_chunk(session_id: str, range_start: int, range_end: int, summary: str, *, embedding_model: str = "lexical-v1") -> MemoryChunk:
    ensure_schema()
    chunk = MemoryChunk(uuid.uuid4().hex[:12], session_id, range_start, range_end, summary, embedding_model, int(time.time()))
    with _conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO memory_chunks(id,session_id,range_start,range_end,summary,embedding_model,created_at) VALUES (?,?,?,?,?,?,?)",
            (chunk.id, chunk.session_id, chunk.range_start, chunk.range_end, chunk.summary, chunk.embedding_model, chunk.created_at),
        )
        row = c.execute(
            "SELECT id,session_id,range_start,range_end,summary,embedding_model,created_at FROM memory_chunks WHERE session_id=? AND range_start=? AND range_end=?",
            (session_id, range_start, range_end),
        ).fetchone()
    return _row(row)


def list_chunks(session_id: str | None = None) -> list[MemoryChunk]:
    ensure_schema()
    with _conn() as c:
        if session_id:
            rows = c.execute("SELECT id,session_id,range_start,range_end,summary,embedding_model,created_at FROM memory_chunks WHERE session_id=? ORDER BY range_start", (session_id,)).fetchall()
        else:
            rows = c.execute("SELECT id,session_id,range_start,range_end,summary,embedding_model,created_at FROM memory_chunks ORDER BY created_at DESC").fetchall()
    return [_row(r) for r in rows]


def search_chunks(query: str, *, k: int = 5, session_id_filter: str | None = None) -> list[tuple[MemoryChunk, float]]:
    chunks = list_chunks(session_id_filter)
    scored = [(chunk, similarity(query, chunk.summary)) for chunk in chunks]
    scored.sort(key=lambda item: item[1], reverse=True)
    return [item for item in scored[:k] if item[1] > 0]


def _row(row: tuple) -> MemoryChunk:
    return MemoryChunk(str(row[0]), str(row[1]), int(row[2]), int(row[3]), str(row[4]), str(row[5]), int(row[6]))
