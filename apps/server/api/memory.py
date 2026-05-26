"""Hermes Agent memory viewer — Phase 4.

The default Hermes Agent memory layout is ``~/.hermes/memory/MEMORY.md`` plus
individual ``.md`` shards next to it. We expose a thin browse/read/write API;
path safety reuses the workspace guard.
"""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from . import auth as auth_module
from .config import Config
from .router import Request, Response, Router

MEMORY_ROOT = Path.home() / ".hermes" / "memory"
MAX_BYTES = 1 * 1024 * 1024


def _safe_memory(rel: str) -> Path:
    if rel.startswith("/") or ".." in Path(rel).parts:
        raise ValueError("bad path")
    p = (MEMORY_ROOT / rel).resolve()
    p.relative_to(MEMORY_ROOT.resolve())  # raises ValueError if outside
    return p


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("GET", "/api/memory")
    def _list(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        if not MEMORY_ROOT.exists():
            return Response(HTTPStatus.OK, {"root": str(MEMORY_ROOT), "entries": [], "exists": False})
        entries = []
        for child in sorted(MEMORY_ROOT.rglob("*.md")):
            try:
                rel = child.relative_to(MEMORY_ROOT).as_posix()
                entries.append({"path": rel, "size": child.stat().st_size, "modified": child.stat().st_mtime})
            except (OSError, ValueError):
                continue
        return Response(HTTPStatus.OK, {"root": str(MEMORY_ROOT), "entries": entries, "exists": True})

    @router.route("GET", "/api/memory/read")
    def _read(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        rel = (req.query.get("path") or [""])[0]
        try:
            p = _safe_memory(rel)
        except ValueError as exc:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_path", "detail": str(exc)})
        if not p.is_file():
            return Response(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        if p.stat().st_size > MAX_BYTES:
            return Response(HTTPStatus.PAYLOAD_TOO_LARGE, {"error": "too_large"})
        return Response(HTTPStatus.OK, {"path": rel, "content": p.read_text(encoding="utf-8")})

    @router.route("PUT", "/api/memory/write")
    def _write(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            body = req.json()
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
        rel = str(body.get("path") or "")
        content = body.get("content")
        if not isinstance(content, str):
            return Response(HTTPStatus.BAD_REQUEST, {"error": "content_required"})
        try:
            p = _safe_memory(rel)
        except ValueError as exc:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_path", "detail": str(exc)})
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return Response(HTTPStatus.OK, {"ok": True, "path": rel})

    return router
