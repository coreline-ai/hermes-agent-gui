"""Provider SQLite CRUD + API key env storage — Phase 16."""

from __future__ import annotations

import json
import re
import sqlite3
import threading
import time
import uuid
from pathlib import Path

from ..messaging.credentials import _read_env, _write_env  # reuse Phase 15 atomic env writer
from ..sessions.lifecycle import SESSIONS_DB
from .catalog import get_preset
from .models import Provider

_lock = threading.RLock()
_schema_ready = False

_LOCAL_KINDS = {"lm_studio", "ollama", "vllm", "llama_cpp"}
_GENERIC_KEY_RE = re.compile(r"^[A-Za-z0-9._:/+=\-]{8,}$")


class ProviderStoreError(ValueError):
    def __init__(self, code: str, detail: str | None = None) -> None:
        super().__init__(detail or code)
        self.code = code
        self.detail = detail or code


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
            CREATE TABLE IF NOT EXISTS providers (
              id TEXT PRIMARY KEY,
              kind TEXT NOT NULL,
              label TEXT NOT NULL,
              base_url TEXT NOT NULL,
              api_key_env TEXT NOT NULL,
              auth_type TEXT NOT NULL,
              enabled INTEGER NOT NULL DEFAULT 1,
              extra_json TEXT NOT NULL DEFAULT '{}',
              test_status TEXT,
              last_tested_at INTEGER,
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL
            )
            """
        )
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_providers_label_lower ON providers(lower(label))")
        c.execute("CREATE INDEX IF NOT EXISTS idx_providers_kind ON providers(kind)")
    _schema_ready = True


def _row_to_provider(row: tuple) -> Provider:
    return Provider(
        id=str(row[0]), kind=str(row[1]), label=str(row[2]), base_url=str(row[3]),
        api_key_env=str(row[4]), auth_type=str(row[5]), enabled=bool(row[6]),
        extra=json.loads(row[7] or "{}"), test_status=row[8], last_tested_at=row[9],
    )


def list_providers(*, include_disabled: bool = True) -> list[Provider]:
    ensure_schema()
    with _lock, _conn() as c:
        if include_disabled:
            rows = c.execute(
                "SELECT id,kind,label,base_url,api_key_env,auth_type,enabled,extra_json,test_status,last_tested_at FROM providers ORDER BY label COLLATE NOCASE"
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT id,kind,label,base_url,api_key_env,auth_type,enabled,extra_json,test_status,last_tested_at FROM providers WHERE enabled=1 ORDER BY label COLLATE NOCASE"
            ).fetchall()
    return [_row_to_provider(r) for r in rows]


def get_provider(provider_id: str) -> Provider | None:
    ensure_schema()
    with _lock, _conn() as c:
        row = c.execute(
            "SELECT id,kind,label,base_url,api_key_env,auth_type,enabled,extra_json,test_status,last_tested_at FROM providers WHERE id=?",
            (provider_id,),
        ).fetchone()
    return _row_to_provider(row) if row else None


def _validate_api_key(kind: str, auth_type: str, api_key: str) -> None:
    key = api_key.strip()
    if auth_type == "none" or kind in _LOCAL_KINDS:
        return
    if not key:
        raise ProviderStoreError("invalid_api_key_format", "api_key is required")
    if kind == "openai" and not re.match(r"^sk-[A-Za-z0-9_-]{8,}$", key):
        raise ProviderStoreError("invalid_api_key_format", "OpenAI API key must start with sk-")
    if kind == "anthropic" and not re.match(r"^sk-ant-[A-Za-z0-9_-]{8,}$", key):
        raise ProviderStoreError("invalid_api_key_format", "Anthropic API key must start with sk-ant-")
    if kind not in {"openai", "anthropic"} and not _GENERIC_KEY_RE.match(key):
        raise ProviderStoreError("invalid_api_key_format", "API key has an unsupported format")


def _write_api_key(env_key: str, api_key: str) -> None:
    if not api_key:
        return
    data = _read_env()
    data[env_key] = api_key
    _write_env(data)


def _delete_api_key(env_key: str) -> None:
    data = _read_env()
    if env_key in data:
        data.pop(env_key, None)
        _write_env(data)


def _provider_api_key_env(provider_id: str) -> str:
    return f"HERMES_PROVIDER_{provider_id.upper()}_API_KEY"


def read_api_key(provider: Provider) -> str:
    return _read_env().get(provider.api_key_env, "")


def create_provider(
    *,
    kind: str,
    label: str,
    base_url: str | None = None,
    api_key: str = "",
    enabled: bool = True,
    extra: dict | None = None,
) -> Provider:
    ensure_schema()
    preset = get_preset(kind)
    if preset is None:
        raise ProviderStoreError("provider_kind_unknown", f"unknown provider kind: {kind}")
    clean_label = label.strip() or preset.label
    clean_base_url = (base_url or preset.base_url).strip().rstrip("/")
    _validate_api_key(kind, preset.auth_type, api_key)
    provider_id = uuid.uuid4().hex[:12]
    api_key_env = _provider_api_key_env(provider_id) if preset.auth_type != "none" else preset.api_key_env
    now = int(time.time())
    try:
        with _lock, _conn() as c:
            c.execute(
                "INSERT INTO providers(id,kind,label,base_url,api_key_env,auth_type,enabled,extra_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    provider_id, kind, clean_label, clean_base_url, api_key_env,
                    preset.auth_type, 1 if enabled else 0, json.dumps(extra or preset.extra), now, now,
                ),
            )
    except sqlite3.IntegrityError as exc:
        raise ProviderStoreError("provider_label_taken", "provider label already exists") from exc
    _write_api_key(api_key_env, api_key.strip())
    provider = get_provider(provider_id)
    if provider is None:  # pragma: no cover
        raise ProviderStoreError("provider_create_failed")
    return provider


def update_test_status(provider_id: str, status: str) -> None:
    ensure_schema()
    with _lock, _conn() as c:
        c.execute(
            "UPDATE providers SET test_status=?, last_tested_at=?, updated_at=? WHERE id=?",
            (status, int(time.time()), int(time.time()), provider_id),
        )


def delete_provider(provider_id: str) -> bool:
    ensure_schema()
    provider = get_provider(provider_id)
    with _lock, _conn() as c:
        cur = c.execute("DELETE FROM providers WHERE id=?", (provider_id,))
    deleted = cur.rowcount > 0
    if deleted and provider is not None and provider.api_key_env.startswith("HERMES_PROVIDER_"):
        _delete_api_key(provider.api_key_env)
    return deleted
