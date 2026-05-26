from __future__ import annotations

import json
import sqlite3
import time
import uuid

from ..sessions.lifecycle import SESSIONS_DB
from .models import Group, GroupParticipant, INVITE_TTL_SECONDS, MAX_PARTICIPANTS, invite_code


def _conn() -> sqlite3.Connection:
    SESSIONS_DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(SESSIONS_DB, isolation_level=None)
    c.execute("PRAGMA journal_mode=WAL")
    return c


def ensure_schema() -> None:
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS groups (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              invite_code TEXT NOT NULL UNIQUE,
              invite_expires_at INTEGER NOT NULL,
              participants_json TEXT NOT NULL,
              created_at INTEGER NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS group_messages (
              id TEXT PRIMARY KEY,
              group_id TEXT NOT NULL,
              participant TEXT NOT NULL,
              content TEXT NOT NULL,
              created_at INTEGER NOT NULL
            )
            """
        )


def _participants(raw: list[dict] | None) -> list[GroupParticipant]:
    out = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if name:
            out.append(GroupParticipant(name=name[:40], profile=str(item.get("profile") or "default"), model=str(item.get("model") or "auto")))
    if not out:
        out.append(GroupParticipant("Hermes"))
    if len(out) > MAX_PARTICIPANTS:
        raise ValueError("too_many_participants")
    return out


def create_group(name: str, participants_raw: list[dict] | None = None) -> Group:
    ensure_schema()
    participants = _participants(participants_raw)
    now = int(time.time())
    group = Group(uuid.uuid4().hex[:12], name.strip() or "New group", invite_code(), now + INVITE_TTL_SECONDS, now, participants)
    with _conn() as c:
        c.execute(
            "INSERT INTO groups(id,name,invite_code,invite_expires_at,participants_json,created_at) VALUES (?,?,?,?,?,?)",
            (group.id, group.name, group.invite_code, group.invite_expires_at, json.dumps([p.to_dict() for p in participants]), group.created_at),
        )
    return group


def list_groups() -> list[Group]:
    ensure_schema()
    with _conn() as c:
        rows = c.execute("SELECT id,name,invite_code,invite_expires_at,participants_json,created_at FROM groups ORDER BY created_at DESC").fetchall()
    return [_row(r) for r in rows]


def get_group(gid: str) -> Group | None:
    ensure_schema()
    with _conn() as c:
        row = c.execute("SELECT id,name,invite_code,invite_expires_at,participants_json,created_at FROM groups WHERE id=?", (gid,)).fetchone()
    return _row(row) if row else None


def add_message(group_id: str, participant: str, content: str) -> dict:
    ensure_schema()
    now = int(time.time())
    mid = uuid.uuid4().hex[:12]
    with _conn() as c:
        c.execute("INSERT INTO group_messages(id,group_id,participant,content,created_at) VALUES (?,?,?,?,?)", (mid, group_id, participant, content, now))
    return {"id": mid, "group_id": group_id, "participant": participant, "content": content, "created_at": now}


def list_messages(group_id: str) -> list[dict]:
    ensure_schema()
    with _conn() as c:
        rows = c.execute("SELECT id,group_id,participant,content,created_at FROM group_messages WHERE group_id=? ORDER BY created_at", (group_id,)).fetchall()
    return [{"id": r[0], "group_id": r[1], "participant": r[2], "content": r[3], "created_at": r[4]} for r in rows]


def _row(row: tuple) -> Group:
    participants = [GroupParticipant(**p) for p in json.loads(row[4] or "[]")]
    return Group(str(row[0]), str(row[1]), str(row[2]), int(row[3]), int(row[5]), participants)
