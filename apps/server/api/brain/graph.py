from __future__ import annotations

import hashlib
import sqlite3
from typing import Iterable

from ..sessions.lifecycle import SESSIONS_DB
from .models import BrainEdge, BrainNode


def _id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).lower().encode("utf-8")).hexdigest()[:16]


def _conn() -> sqlite3.Connection:
    SESSIONS_DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(SESSIONS_DB, isolation_level=None)
    c.execute("PRAGMA journal_mode=WAL")
    return c


def ensure_schema() -> None:
    with _conn() as c:
        c.execute("CREATE TABLE IF NOT EXISTS brain_nodes(id TEXT PRIMARY KEY,label TEXT NOT NULL,kind TEXT NOT NULL,source TEXT NOT NULL, UNIQUE(label,kind))")
        c.execute("CREATE TABLE IF NOT EXISTS brain_edges(id TEXT PRIMARY KEY,src TEXT NOT NULL,dst TEXT NOT NULL,kind TEXT NOT NULL,source TEXT NOT NULL, UNIQUE(src,dst,kind,source))")
        c.execute("CREATE INDEX IF NOT EXISTS idx_brain_nodes_label ON brain_nodes(label)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_brain_edges_src ON brain_edges(src)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_brain_edges_dst ON brain_edges(dst)")


def upsert(nodes: Iterable[dict], edges: Iterable[dict]) -> dict:
    ensure_schema()
    node_map: dict[str, str] = {}
    with _conn() as c:
        for n in nodes:
            label = str(n["label"])
            kind = str(n.get("kind") or "entity")
            nid = _id(label, kind)
            node_map[label.lower()] = nid
            c.execute("INSERT OR IGNORE INTO brain_nodes(id,label,kind,source) VALUES (?,?,?,?)", (nid, label, kind, str(n.get("source") or "manual")))
        edge_count = 0
        for e in edges:
            src_label = str(e["src"])
            dst_label = str(e["dst"])
            src = node_map.get(src_label.lower()) or _id(src_label, "person")
            dst = node_map.get(dst_label.lower()) or _id(dst_label, "org")
            kind = str(e.get("kind") or "related")
            eid = _id(src, dst, kind, str(e.get("source") or "manual"))
            c.execute("INSERT OR IGNORE INTO brain_edges(id,src,dst,kind,source) VALUES (?,?,?,?,?)", (eid, src, dst, kind, str(e.get("source") or "manual")))
            edge_count += 1
    return {"nodes": len(list_nodes()), "edges_inserted": edge_count}


def list_nodes(q: str | None = None) -> list[BrainNode]:
    ensure_schema()
    with _conn() as c:
        if q:
            rows = c.execute("SELECT id,label,kind,source FROM brain_nodes WHERE lower(label) LIKE ? ORDER BY label LIMIT 100", (f"%{q.lower()}%",)).fetchall()
        else:
            rows = c.execute("SELECT id,label,kind,source FROM brain_nodes ORDER BY label LIMIT 500").fetchall()
    return [BrainNode(str(r[0]), str(r[1]), str(r[2]), str(r[3])) for r in rows]


def list_edges() -> list[BrainEdge]:
    ensure_schema()
    with _conn() as c:
        rows = c.execute("SELECT id,src,dst,kind,source FROM brain_edges LIMIT 1000").fetchall()
    return [BrainEdge(str(r[0]), str(r[1]), str(r[2]), str(r[3]), str(r[4])) for r in rows]


def node_by_id(node_id: str) -> BrainNode | None:
    ensure_schema()
    with _conn() as c:
        r = c.execute("SELECT id,label,kind,source FROM brain_nodes WHERE id=?", (node_id,)).fetchone()
    return BrainNode(str(r[0]), str(r[1]), str(r[2]), str(r[3])) if r else None
