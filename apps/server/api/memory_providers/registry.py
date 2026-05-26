"""Memory provider registry and SQLite activation state — Phase 19."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from ..sessions.lifecycle import SESSIONS_DB
from .base import AbstractMemoryProvider
from .local_vss import LocalVssProvider
from .stub import ExternalMemoryProvider

PROVIDER_NAMES = ["local_vss", "honcho", "mem0", "hindsight", "retaindb", "supermemory", "byterover"]


@dataclass(frozen=True)
class ProviderState:
    name: str
    active: bool
    configured: bool
    label: str

    def to_dict(self) -> dict:
        return {"name": self.name, "label": self.label, "active": self.active, "configured": self.configured}


def _conn() -> sqlite3.Connection:
    SESSIONS_DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(SESSIONS_DB, isolation_level=None)
    c.execute("PRAGMA journal_mode=WAL")
    return c


def ensure_schema() -> None:
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_provider_settings (
              name TEXT PRIMARY KEY,
              active INTEGER NOT NULL DEFAULT 0,
              config_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        c.execute("INSERT OR IGNORE INTO memory_provider_settings(name,active,config_json) VALUES ('local_vss',1,'{}')")


def list_states() -> list[ProviderState]:
    ensure_schema()
    with _conn() as c:
        rows = {r[0]: (bool(r[1]), json.loads(r[2] or '{}')) for r in c.execute("SELECT name,active,config_json FROM memory_provider_settings").fetchall()}
    states: list[ProviderState] = []
    for name in PROVIDER_NAMES:
        active, cfg = rows.get(name, (False, {}))
        configured = name == "local_vss" or bool(cfg.get("api_key") or cfg.get("base_url"))
        states.append(ProviderState(name, active, configured, name.replace("_", " ").title()))
    return states


def activate(name: str, config: dict | None = None) -> ProviderState:
    if name not in PROVIDER_NAMES:
        raise ValueError("provider_unknown")
    if name != "local_vss" and not (config or {}).get("api_key"):
        raise ValueError("provider_config_missing")
    ensure_schema()
    with _conn() as c:
        c.execute(
            "INSERT INTO memory_provider_settings(name,active,config_json) VALUES (?,?,?) ON CONFLICT(name) DO UPDATE SET active=excluded.active, config_json=excluded.config_json",
            (name, 1, json.dumps(config or {})),
        )
    return next(s for s in list_states() if s.name == name)


def build_provider(name: str) -> AbstractMemoryProvider:
    state = next((s for s in list_states() if s.name == name), None)
    configured = bool(state and state.configured)
    if name == "local_vss":
        return LocalVssProvider()
    return ExternalMemoryProvider(name, configured=configured)
