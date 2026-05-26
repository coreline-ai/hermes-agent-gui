from __future__ import annotations

from http import HTTPStatus

from .. import auth as auth_module
from ..config import Config
from ..router import Request, Response, Router
from .registry import activate, build_provider, list_states


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("GET", "/api/memory/providers")
    def _providers(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        return Response(HTTPStatus.OK, {"providers": [s.to_dict() for s in list_states()]})

    @router.route("POST", "/api/memory/providers/{name}/activate")
    def _activate(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            body = req.json()
            state = activate(req.params["name"], dict(body.get("config") or {}))
        except ValueError as exc:
            return Response(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        return Response(HTTPStatus.OK, state.to_dict())

    @router.route("POST", "/api/memory/providers/{name}/test")
    def _test(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        provider = build_provider(req.params["name"])
        status = provider.test_connection()
        code = HTTPStatus.OK if status.get("ok") else HTTPStatus.BAD_REQUEST
        return Response(code, status)

    return router
