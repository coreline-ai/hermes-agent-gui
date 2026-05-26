"""Credential file merge/write helpers for Phase 15a messaging."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from .models import PlatformMeta

_KEY_RE = re.compile(r"[^A-Z0-9_]")


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))).expanduser().resolve()


def env_path() -> Path:
    return hermes_home() / ".env"


def _env_key(platform: str, key: str) -> str:
    safe_platform = _KEY_RE.sub("_", platform.upper())
    safe_key = _KEY_RE.sub("_", key.upper())
    return f"HERMES_{safe_platform}_{safe_key}"


def _read_env(path: Path | None = None) -> dict[str, str]:
    path = path or env_path()
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        out[key.strip()] = value.strip()
    return out


def _write_env(data: dict[str, str], path: Path | None = None) -> None:
    path = path or env_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".env.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for key in sorted(data):
                f.write(f"{key}={data[key]}\n")
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
        try:
            path.chmod(0o600)
        except OSError:
            pass
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def write_credentials(platform: str, credentials: dict[str, str], path: Path | None = None) -> None:
    data = _read_env(path)
    for key, value in credentials.items():
        data[_env_key(platform, key)] = str(value)
    _write_env(data, path)


def read_platform_credentials(platform: str, path: Path | None = None) -> dict[str, str]:
    prefix = f"HERMES_{_KEY_RE.sub('_', platform.upper())}_"
    data = _read_env(path)
    return {key[len(prefix):].lower(): value for key, value in data.items() if key.startswith(prefix)}


def delete_platform_credentials(platform: str, path: Path | None = None) -> bool:
    prefix = f"HERMES_{_KEY_RE.sub('_', platform.upper())}_"
    data = _read_env(path)
    filtered = {key: value for key, value in data.items() if not key.startswith(prefix)}
    changed = len(filtered) != len(data)
    _write_env(filtered, path)
    return changed


def is_configured(meta: PlatformMeta, path: Path | None = None) -> bool:
    creds = read_platform_credentials(meta.id, path)
    for field in meta.credential_fields:
        if field.required and not str(creds.get(field.name, "")).strip():
            return False
    return True if meta.credential_fields else False
