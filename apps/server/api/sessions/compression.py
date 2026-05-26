"""Compression-session alias map (C's v3.3.1 fix).

When the agent rotates a session id after context compression, requests for the
old id must still resolve to the new canonical id — *across process restarts*.
Aliases are persisted to a small JSON file beside the SQLite store.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from ..config import STATE_DIR

ALIAS_FILE = STATE_DIR / "session-aliases.json"
_lock = threading.Lock()
_cache: dict[str, str] | None = None


def _load() -> dict[str, str]:
    global _cache
    if _cache is not None:
        return _cache
    if ALIAS_FILE.exists():
        try:
            _cache = json.loads(ALIAS_FILE.read_text() or "{}")
        except json.JSONDecodeError:
            _cache = {}
    else:
        _cache = {}
    return _cache


def _save() -> None:
    assert _cache is not None
    ALIAS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ALIAS_FILE.write_text(json.dumps(_cache, separators=(",", ":")))


def register_alias(old_id: str, new_id: str) -> None:
    if old_id == new_id:
        return
    with _lock:
        cache = _load()
        cache[old_id] = new_id
        _save()


def alias_resolve(sess_id: str) -> str:
    """Walk the alias chain; bounded so cycles don't hang."""
    with _lock:
        cache = _load()
        seen: set[str] = set()
        cur = sess_id
        while cur in cache and cur not in seen and len(seen) < 32:
            seen.add(cur)
            cur = cache[cur]
        return cur
