"""Workspace file operations — Phase 3.

Adapted from B's workspace.py + C's path whitelist guard:
- Roots come from ``HERMES_GUI_WORKSPACES`` (':' separated) or default to $HOME.
- Every read/write resolves through ``_safe_path`` so symlinks and ``..`` traversal
  cannot escape the chosen root.
- Files larger than ``MAX_READ_BYTES`` are not returned inline (Phase 3 minimal —
  Phase 11 will add range reads).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path

from . import auth as auth_module
from .config import Config
from .router import Request, Response, Router

logger = logging.getLogger(__name__)

MAX_READ_BYTES = 2 * 1024 * 1024     # 2 MB inline read
MAX_WRITE_BYTES = 5 * 1024 * 1024    # 5 MB inline write


def _roots() -> list[Path]:
    raw = os.environ.get("HERMES_GUI_WORKSPACES")
    if raw:
        return [Path(p).expanduser().resolve() for p in raw.split(":") if p.strip()]
    return [Path.home().resolve()]


def _safe_path(rel: str) -> Path:
    """Return absolute path within an allowed root, or raise ValueError."""
    if not rel or rel.startswith("/"):
        raise ValueError("absolute path not allowed; use root-relative")
    p = Path(rel).expanduser()
    for root in _roots():
        candidate = (root / p).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        return candidate
    # rel may itself be absolute-ish (already resolved); accept if within roots.
    candidate = Path(rel).expanduser().resolve()
    for root in _roots():
        try:
            candidate.relative_to(root)
            return candidate
        except ValueError:
            continue
    raise ValueError(f"path outside allowed roots: {rel}")


@dataclass
class Entry:
    name: str
    path: str
    kind: str  # 'file' | 'dir' | 'symlink' | 'other'
    size: int
    modified: float

    def to_dict(self) -> dict:
        return self.__dict__


def _list_dir(p: Path) -> list[Entry]:
    out: list[Entry] = []
    for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        try:
            st = child.lstat()
            if child.is_symlink():
                kind = "symlink"
            elif child.is_dir():
                kind = "dir"
            elif child.is_file():
                kind = "file"
            else:
                kind = "other"
            out.append(
                Entry(
                    name=child.name,
                    path=str(child),
                    kind=kind,
                    size=st.st_size if kind == "file" else 0,
                    modified=st.st_mtime,
                )
            )
        except OSError:
            continue
    return out


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("GET", "/api/workspace/roots")
    def _roots_ep(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        return Response(HTTPStatus.OK, {"roots": [str(r) for r in _roots()]})

    @router.route("GET", "/api/workspace/list")
    def _list(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        rel = (req.query.get("path") or ["."])[0]
        try:
            p = _safe_path(rel)
        except ValueError as exc:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_path", "detail": str(exc)})
        if not p.exists():
            return Response(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        if not p.is_dir():
            return Response(HTTPStatus.BAD_REQUEST, {"error": "not_a_directory"})
        return Response(HTTPStatus.OK, {"path": str(p), "entries": [e.to_dict() for e in _list_dir(p)]})

    @router.route("GET", "/api/workspace/read")
    def _read(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        rel = (req.query.get("path") or [""])[0]
        try:
            p = _safe_path(rel)
        except ValueError as exc:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_path", "detail": str(exc)})
        if not p.is_file():
            return Response(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        if p.stat().st_size > MAX_READ_BYTES:
            return Response(HTTPStatus.PAYLOAD_TOO_LARGE, {"error": "too_large", "max": MAX_READ_BYTES})
        try:
            content = p.read_text(encoding="utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            content = p.read_bytes().hex()
            encoding = "hex"
        return Response(HTTPStatus.OK, {"path": str(p), "encoding": encoding, "content": content})

    @router.route("PUT", "/api/workspace/write")
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
            return Response(HTTPStatus.BAD_REQUEST, {"error": "content_string_required"})
        if len(content.encode("utf-8")) > MAX_WRITE_BYTES:
            return Response(HTTPStatus.PAYLOAD_TOO_LARGE, {"error": "too_large"})
        try:
            p = _safe_path(rel)
        except ValueError as exc:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_path", "detail": str(exc)})
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return Response(HTTPStatus.OK, {"path": str(p), "bytes": len(content.encode("utf-8"))})

    @router.route("DELETE", "/api/workspace/delete")
    def _delete(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        rel = (req.query.get("path") or [""])[0]
        try:
            p = _safe_path(rel)
        except ValueError as exc:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_path", "detail": str(exc)})
        if not p.exists():
            return Response(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        if p.is_dir():
            try:
                p.rmdir()
            except OSError:
                return Response(HTTPStatus.CONFLICT, {"error": "directory_not_empty"})
        else:
            p.unlink()
        return Response(HTTPStatus.OK, {"ok": True})

    return router
