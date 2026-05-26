from __future__ import annotations

from http import HTTPStatus

from .. import auth as auth_module
from ..config import Config
from ..router import Request, Response, Router
from . import actions
from .session import pool


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("POST", "/api/browser/navigate")
    def _navigate(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            body = req.json()
            sess = pool.get(str(body.get("session_id") or "") or None)
            return Response(HTTPStatus.OK, actions.navigate(sess, str(body.get("url") or "")))
        except PermissionError as exc:
            return Response(HTTPStatus.FORBIDDEN, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001 -- browser backend fallback surface
            return Response(HTTPStatus.BAD_GATEWAY, {"error": "browser_action_failed", "detail": str(exc)})

    @router.route("POST", "/api/browser/extract")
    def _extract(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            body = req.json()
            sess = pool.get(str(body.get("session_id") or "") or None)
            return Response(HTTPStatus.OK, actions.extract(sess, str(body.get("selector") or "title")))
        except LookupError as exc:
            return Response(HTTPStatus.NOT_FOUND, {"error": str(exc)})

    @router.route("POST", "/api/browser/screenshot")
    def _screenshot(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        body = req.json()
        sess = pool.get(str(body.get("session_id") or "") or None)
        return Response(HTTPStatus.OK, actions.screenshot(sess))

    return router
