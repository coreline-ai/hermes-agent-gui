from __future__ import annotations

import sqlite3
import time

from ..sessions.lifecycle import SESSIONS_DB
from .parsers import Symbol


def _conn() -> sqlite3.Connection:
    SESSIONS_DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(SESSIONS_DB, isolation_level=None)
    c.execute("PRAGMA journal_mode=WAL")
    return c


def ensure_schema() -> None:
    with _conn() as c:
        c.execute("CREATE TABLE IF NOT EXISTS code_symbols(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,kind TEXT NOT NULL,file TEXT NOT NULL,line INTEGER NOT NULL,column INTEGER NOT NULL,updated_at INTEGER NOT NULL, UNIQUE(name,kind,file,line))")
        c.execute("CREATE INDEX IF NOT EXISTS idx_code_symbols_name ON code_symbols(name)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_code_symbols_file ON code_symbols(file)")


def replace_file_symbols(file: str, symbols: list[Symbol]) -> None:
    ensure_schema()
    now = int(time.time())
    with _conn() as c:
        c.execute("DELETE FROM code_symbols WHERE file=?", (file,))
        for sym in symbols:
            c.execute("INSERT OR IGNORE INTO code_symbols(name,kind,file,line,column,updated_at) VALUES (?,?,?,?,?,?)", (sym.name, sym.kind, sym.file, sym.line, sym.column, now))


def find_symbols(q: str = "", *, limit: int = 100) -> list[dict]:
    ensure_schema()
    with _conn() as c:
        if q:
            rows = c.execute("SELECT name,kind,file,line,column FROM code_symbols WHERE name LIKE ? ORDER BY name LIMIT ?", (f"%{q}%", limit)).fetchall()
        else:
            rows = c.execute("SELECT name,kind,file,line,column FROM code_symbols ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
    return [{"name": r[0], "kind": r[1], "file": r[2], "line": r[3], "column": r[4]} for r in rows]


def file_outline(file: str) -> list[dict]:
    ensure_schema()
    with _conn() as c:
        rows = c.execute("SELECT name,kind,file,line,column FROM code_symbols WHERE file=? ORDER BY line", (file,)).fetchall()
    return [{"name": r[0], "kind": r[1], "file": r[2], "line": r[3], "column": r[4]} for r in rows]
