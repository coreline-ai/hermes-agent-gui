"""FTS5 session search — Phase 17."""

from __future__ import annotations

import re
import sqlite3
import time
from http import HTTPStatus

from .. import auth as auth_module
from ..config import Config
from ..dashboard import _redact
from ..router import Request, Response, Router
from ..validation import ValidationError, parse_bounded_int, validation_response
from .lifecycle import Message, Session, SessionStore


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
          session_id UNINDEXED,
          message_index UNINDEXED,
          role UNINDEXED,
          ts UNINDEXED,
          content,
          tokenize = 'porter unicode61 remove_diacritics 2'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages_fts_meta (
          session_id TEXT NOT NULL,
          message_index INTEGER NOT NULL,
          PRIMARY KEY(session_id, message_index)
        )
        """
    )


def _index_messages(conn: sqlite3.Connection, session_id: str, messages: list[Message], start_index: int = 0) -> None:
    ensure_schema(conn)
    rows = []
    for i, m in enumerate(messages):
        idx = start_index + i
        rows.append((session_id, idx, m.role, int(m.created_at or time.time()), m.content))
    for row in rows:
        cur = conn.execute(
            "INSERT OR IGNORE INTO messages_fts_meta(session_id,message_index) VALUES (?,?)",
            (row[0], row[1]),
        )
        if cur.rowcount > 0:
            conn.execute(
                "INSERT INTO messages_fts(session_id,message_index,role,ts,content) VALUES (?,?,?,?,?)",
                row,
            )


def delete_session_index(conn: sqlite3.Connection, session_id: str) -> None:
    ensure_schema(conn)
    conn.execute("DELETE FROM messages_fts WHERE session_id=?", (session_id,))
    conn.execute("DELETE FROM messages_fts_meta WHERE session_id=?", (session_id,))


def reindex_session(conn: sqlite3.Connection, session: Session) -> None:
    delete_session_index(conn, session.id)
    _index_messages(conn, session.id, session.messages, 0)


def backfill_fts(store: SessionStore) -> int:
    total = 0
    with store._lock, store._conn() as conn:  # noqa: SLF001 - internal hook for same DB
        ensure_schema(conn)
        rows = conn.execute("SELECT id,title,profile,created_at,updated_at,messages_json,metadata_json FROM sessions").fetchall()
        for row in rows:
            sess = SessionStore._row_to_session(row)
            before = conn.execute("SELECT COUNT(*) FROM messages_fts_meta WHERE session_id=?", (sess.id,)).fetchone()[0]
            _index_messages(conn, sess.id, sess.messages, 0)
            after = conn.execute("SELECT COUNT(*) FROM messages_fts_meta WHERE session_id=?", (sess.id,)).fetchone()[0]
            total += max(0, int(after or 0) - int(before or 0))
    return total


def _escape_query(q: str) -> str:
    terms = re.findall(r"[\w가-힣]+", q, flags=re.UNICODE)
    return " ".join(f'"{term}"' for term in terms[:8]) or '""'


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _snippet_parts(content: str, query: str) -> list[dict[str, object]]:
    redacted = _redact(content)
    terms = re.findall(r"[\w가-힣]+", query, flags=re.UNICODE)[:8]
    lower = redacted.lower()
    pos = min([lower.find(t.lower()) for t in terms if lower.find(t.lower()) >= 0] or [0])
    start = max(0, pos - 60)
    end = min(len(redacted), pos + 180)
    window = redacted[start:end]
    matches: list[tuple[int, int]] = []
    for term in terms:
        for match in re.finditer(re.escape(term), window, flags=re.IGNORECASE):
            matches.append(match.span())
    merged: list[tuple[int, int]] = []
    for m_start, m_end in sorted(matches):
        if not merged or m_start >= merged[-1][1]:
            merged.append((m_start, m_end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], m_end))

    parts: list[dict[str, object]] = []
    if start:
        parts.append({"text": "…", "highlight": False})
    cursor = 0
    for m_start, m_end in merged:
        if cursor < m_start:
            parts.append({"text": window[cursor:m_start], "highlight": False})
        parts.append({"text": window[m_start:m_end], "highlight": True})
        cursor = m_end
    if cursor < len(window):
        parts.append({"text": window[cursor:], "highlight": False})
    if end < len(redacted):
        parts.append({"text": "…", "highlight": False})
    return parts or [{"text": "", "highlight": False}]


def _snippet(content: str, query: str) -> str:
    out = []
    for part in _snippet_parts(content, query):
        text = _escape_html(str(part["text"]))
        out.append(f"<em>{text}</em>" if part.get("highlight") else text)
    return "".join(out)


def search_messages(store: SessionStore, query: str, *, limit: int = 50) -> dict:
    q = _escape_query(query)
    with store._lock, store._conn() as conn:  # noqa: SLF001
        ensure_schema(conn)
        try:
            rows = conn.execute(
                """
                SELECT f.session_id, s.title, f.message_index, f.role, f.ts, f.content, bm25(messages_fts) AS score
                FROM messages_fts f
                JOIN sessions s ON s.id = f.session_id
                WHERE messages_fts MATCH ?
                ORDER BY score ASC
                LIMIT ?
                """,
                (q, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []
    results = [
        {
            "session_id": row[0],
            "session_title": row[1],
            "message_index": int(row[2]),
            "role": row[3],
            "ts": int(row[4] or 0),
            "snippet": _snippet(str(row[5] or ""), query),
            "snippet_parts": _snippet_parts(str(row[5] or ""), query),
            "score": float(row[6] or 0.0),
        }
        for row in rows
    ]
    return {"query": query, "results": results, "total": len(results)}


def register_routes(cfg: Config, store: SessionStore) -> Router:
    router = Router()

    @router.route("GET", "/api/sessions/search")
    def _search(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        q = (req.query.get("q") or [""])[0]
        try:
            limit = parse_bounded_int(
                (req.query.get("limit") or ["50"])[0],
                field="limit",
                default=50,
                min_value=1,
                max_value=100,
            )
        except ValidationError as exc:
            return validation_response(exc)
        return Response(HTTPStatus.OK, search_messages(store, q, limit=limit))

    @router.route("POST", "/api/sessions/search/backfill")
    def _backfill(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        return Response(HTTPStatus.OK, {"indexed": backfill_fts(store)})

    return router
