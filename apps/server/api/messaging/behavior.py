"""Messaging behavior YAML helpers."""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore

from .credentials import hermes_home


def config_path() -> Path:
    return hermes_home() / "config.yaml"


def read_config(path: Path | None = None) -> dict:
    path = path or config_path()
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def write_config(data: dict, path: Path | None = None) -> None:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=True, allow_unicode=True), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def read_platform_behavior(platform: str, path: Path | None = None) -> dict:
    data = read_config(path)
    behavior = data.get("messaging", {}).get("platforms", {}).get(platform, {})
    return behavior if isinstance(behavior, dict) else {}


def write_platform_behavior(platform: str, behavior: dict, path: Path | None = None) -> None:
    data = read_config(path)
    messaging = data.setdefault("messaging", {})
    if not isinstance(messaging, dict):
        messaging = {}
        data["messaging"] = messaging
    platforms = messaging.setdefault("platforms", {})
    if not isinstance(platforms, dict):
        platforms = {}
        messaging["platforms"] = platforms
    platforms[platform] = behavior
    write_config(data, path)


def delete_platform_behavior(platform: str, path: Path | None = None) -> bool:
    data = read_config(path)
    platforms = data.get("messaging", {}).get("platforms", {})
    if not isinstance(platforms, dict) or platform not in platforms:
        return False
    platforms.pop(platform, None)
    write_config(data, path)
    return True
