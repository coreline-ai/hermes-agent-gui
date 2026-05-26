from __future__ import annotations

from http import HTTPStatus

from .. import auth as auth_module
from ..config import Config
from ..router import Request, Response, Router
from ..workspace import _safe_path
from .indexer import index_path
from .store import file_outline, find_symbols
from .tools import find_definition


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("POST", "/api/codegraph/index")
    def _index(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            body = req.json()
            root = _safe_path(str(body.get("root") or "."))
        except ValueError as exc:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_path", "detail": str(exc)})
        return Response(HTTPStatus.OK, index_path(str(root)))

    @router.route("GET", "/api/codegraph/symbols")
    def _symbols(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        q = (req.query.get("q") or [""])[0]
        return Response(HTTPStatus.OK, {"symbols": find_symbols(q)})

    @router.route("GET", "/api/codegraph/definition")
    def _definition(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        symbol = (req.query.get("symbol") or [""])[0]
        found = find_definition(symbol)
        if not found:
            return Response(HTTPStatus.NOT_FOUND, {"error": "symbol_not_found"})
        return Response(HTTPStatus.OK, found)

    @router.route("GET", "/api/codegraph/outline")
    def _outline(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        file = (req.query.get("file") or [""])[0]
        return Response(HTTPStatus.OK, {"symbols": file_outline(file)})

    return router
