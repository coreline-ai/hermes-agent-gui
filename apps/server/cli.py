"""Maintenance CLI — Phase 24."""

from __future__ import annotations

import argparse
import json
import platform
import sqlite3
from pathlib import Path

try:  # direct server-tree execution under apps/server/tests
    from api.config import SECRET_FILE, STATE_DIR, load
    from api.sessions.lifecycle import SESSIONS_DB
except ModuleNotFoundError:  # package entry point: apps.server.cli
    from .api.config import SECRET_FILE, STATE_DIR, load
    from .api.sessions.lifecycle import SESSIONS_DB


def clear_login_locks(_args: argparse.Namespace) -> int:
    lock_file = STATE_DIR / ".login-lock.json"
    if lock_file.exists():
        lock_file.unlink()
    print(json.dumps({"ok": True, "cleared": str(lock_file)}))
    return 0


def reset_login(_args: argparse.Namespace) -> int:
    if SECRET_FILE.exists():
        SECRET_FILE.unlink()
    load()
    print(json.dumps({"ok": True, "secret": str(SECRET_FILE)}))
    return 0


def purge_sessions(args: argparse.Namespace) -> int:
    db = Path(args.db or SESSIONS_DB)
    if not db.exists():
        print(json.dumps({"ok": True, "purged": 0}))
        return 0
    with sqlite3.connect(db) as conn:
        cur = conn.execute("DELETE FROM sessions")
        conn.commit()
    print(json.dumps({"ok": True, "purged": cur.rowcount}))
    return 0


def doctor(_args: argparse.Namespace) -> int:
    cfg = load()
    report = {
        "ok": True,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "state_dir": str(STATE_DIR),
        "sessions_db_exists": SESSIONS_DB.exists(),
        "auth_configured": cfg.has_any_auth,
        "exec_enabled": cfg.exec_enabled,
        "hermes_api_url": bool(cfg.hermes_api_url),
    }
    print(json.dumps(report, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hermes-agent-gui")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("clear-login-locks").set_defaults(func=clear_login_locks)
    sub.add_parser("reset-login").set_defaults(func=reset_login)
    purge = sub.add_parser("purge-sessions")
    purge.add_argument("--db")
    purge.set_defaults(func=purge_sessions)
    sub.add_parser("doctor").set_defaults(func=doctor)
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
