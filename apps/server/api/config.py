"""Phase 1 config loader.

Resolution order:
1. Environment variables (HERMES_GUI_*)
2. ~/.hermes-agent-gui/config.yaml (if present, requires pyyaml)
3. Defaults

Phase 1 keeps the surface narrow: password, token, secret, runtime backend
selectors, and the gateway/dashboard URLs the runtime_adapter consults.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path

STATE_DIR = Path(os.environ.get("HERMES_GUI_STATE_DIR", str(Path.home() / ".hermes-agent-gui")))
SECRET_FILE = STATE_DIR / "secret"


@dataclass(frozen=True)
class Config:
    password: str | None
    bearer_token: str | None
    secret: bytes
    fake_backend: str | None              # "echo" enables EchoAdapter
    hermes_api_url: str | None            # zero-fork gateway
    hermes_api_token: str | None
    hermes_dashboard_url: str | None
    fail_open: bool                       # allow remote bind without auth (NOT recommended)
    exec_enabled: bool                    # opt-in shell/PTY/cron/swarm command execution
    exec_allow_remote: bool               # allow command execution when bound off-loopback

    @property
    def has_any_auth(self) -> bool:
        return bool(self.password) or bool(self.bearer_token)


def _load_or_create_secret() -> bytes:
    if (env := os.environ.get("HERMES_GUI_SECRET")):
        return env.encode("utf-8")
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if SECRET_FILE.exists():
        data = SECRET_FILE.read_bytes().strip()
        if data:
            return data
    fresh = secrets.token_hex(32).encode("utf-8")
    SECRET_FILE.write_bytes(fresh)
    SECRET_FILE.chmod(0o600)
    return fresh


def load() -> Config:
    return Config(
        password=os.environ.get("HERMES_GUI_PASSWORD") or None,
        bearer_token=os.environ.get("HERMES_GUI_TOKEN") or None,
        secret=_load_or_create_secret(),
        fake_backend=(os.environ.get("HERMES_GUI_FAKE_BACKEND") or "").lower() or None,
        hermes_api_url=os.environ.get("HERMES_API_URL") or None,
        hermes_api_token=os.environ.get("HERMES_API_TOKEN") or None,
        hermes_dashboard_url=os.environ.get("HERMES_DASHBOARD_URL") or None,
        fail_open=os.environ.get("HERMES_GUI_FAIL_OPEN", "").lower() in {"1", "true", "yes"},
        exec_enabled=os.environ.get("HERMES_GUI_ENABLE_EXEC", "").lower() in {"1", "true", "yes"},
        exec_allow_remote=os.environ.get("HERMES_GUI_ALLOW_REMOTE_EXEC", "").lower() in {"1", "true", "yes"},
    )
