from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from ..persona import write_persona
from ..sessions.lifecycle import SESSIONS_DB

CATALOG_PATH = Path(__file__).with_name("catalog.json")


def load_catalog() -> list[dict]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def get_preset(preset_id: str) -> dict | None:
    return next((item for item in load_catalog() if item["id"] == preset_id), None)


def _conn() -> sqlite3.Connection:
    SESSIONS_DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(SESSIONS_DB, isolation_level=None)
    c.execute("PRAGMA journal_mode=WAL")
    return c


def ensure_schema() -> None:
    with _conn() as c:
        c.execute("CREATE TABLE IF NOT EXISTS marketplace_installs(preset_id TEXT PRIMARY KEY, profile TEXT NOT NULL, favorite INTEGER NOT NULL DEFAULT 0, installed_at INTEGER NOT NULL)")


def install(preset_id: str) -> dict:
    ensure_schema()
    preset = get_preset(preset_id)
    if preset is None:
        raise ValueError("preset_not_found")
    profile = f"market-{preset_id}"
    try:
        with _conn() as c:
            c.execute("INSERT INTO marketplace_installs(preset_id,profile,favorite,installed_at) VALUES (?,?,0,?)", (preset_id, profile, int(time.time())))
    except sqlite3.IntegrityError as exc:
        raise ValueError("already_installed") from exc
    write_persona(profile, preset["soul_md"])
    return {"ok": True, "preset_id": preset_id, "profile": profile}


def uninstall(preset_id: str) -> bool:
    ensure_schema()
    with _conn() as c:
        cur = c.execute("DELETE FROM marketplace_installs WHERE preset_id=?", (preset_id,))
    return cur.rowcount > 0


def favorite(preset_id: str, enabled: bool = True) -> dict:
    ensure_schema()
    with _conn() as c:
        c.execute("UPDATE marketplace_installs SET favorite=? WHERE preset_id=?", (1 if enabled else 0, preset_id))
    return {"ok": True, "preset_id": preset_id, "favorite": enabled}


def installed_map() -> dict[str, dict]:
    ensure_schema()
    with _conn() as c:
        rows = c.execute("SELECT preset_id,profile,favorite,installed_at FROM marketplace_installs").fetchall()
    return {r[0]: {"profile": r[1], "favorite": bool(r[2]), "installed_at": r[3]} for r in rows}
