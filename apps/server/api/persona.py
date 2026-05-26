"""Persona SOUL.md routes — Phase 17."""

from __future__ import annotations

import time
from http import HTTPStatus
from pathlib import Path

from . import auth as auth_module
from .config import Config
from .messaging.credentials import hermes_home
from .presets.personas import list_presets
from .router import Request, Response, Router

MAX_SOUL_BYTES = 100 * 1024


def _profile_name(req: Request) -> str:
    raw = (req.query.get("profile") or ["default"])[0]
    clean = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in raw.strip())
    return clean.strip(".-_") or "default"


def soul_path(profile: str = "default") -> Path:
    return hermes_home() / "profiles" / profile / "SOUL.md"


def read_persona(profile: str = "default") -> dict:
    path = soul_path(profile)
    if path.exists():
        soul = path.read_text(encoding="utf-8")
        updated = int(path.stat().st_mtime)
    else:
        soul = "# Hermes Agent\n\nYou are helpful, concise, and grounded in the user's local context."
        updated = 0
    return {"profile_name": profile, "soul_md": soul, "updated_at": updated}


def write_persona(profile: str, soul_md: str) -> dict:
    payload = soul_md.encode("utf-8")
    if len(payload) > MAX_SOUL_BYTES:
        raise ValueError("payload_too_large")
    path = soul_path(profile)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{int(time.time() * 1000)}.tmp")
    tmp.write_bytes(payload)
    tmp.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return {"ok": True, "profile_name": profile, "updated_at": int(path.stat().st_mtime)}


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("GET", "/api/persona/presets")
    def _presets(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        return Response(HTTPStatus.OK, {"presets": list_presets()})

    @router.route("GET", "/api/persona")
    def _get(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        return Response(HTTPStatus.OK, read_persona(_profile_name(req)))

    @router.route("PUT", "/api/persona")
    def _put(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            body = req.json()
            soul = str(body.get("soul_md") or "")
            return Response(HTTPStatus.OK, write_persona(_profile_name(req), soul))
        except ValueError as exc:
            if str(exc) == "payload_too_large":
                return Response(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "payload_too_large", "max": MAX_SOUL_BYTES})
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})

    return router
