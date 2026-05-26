from __future__ import annotations

from http import HTTPStatus

from .. import auth as auth_module
from ..config import Config
from ..router import Request, Response, Router
from .registry import BRIDGES


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("GET", "/api/cli-bridges")
    def _list(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        return Response(HTTPStatus.OK, {"bridges": [b.detect().to_dict() for b in BRIDGES.values()]})

    @router.route("POST", "/api/cli-bridges/{name}/run")
    def _run(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        if not cfg.exec_enabled:
            return Response(HTTPStatus.FORBIDDEN, {"error": "exec_disabled"})
        bridge = BRIDGES.get(req.params["name"])
        if bridge is None:
            return Response(HTTPStatus.NOT_FOUND, {"error": "bridge_not_found"})
        try:
            body = req.json()
            output = bridge.send(str(body.get("prompt") or ""))
        except FileNotFoundError:
            return Response(HTTPStatus.NOT_FOUND, {"error": "binary_not_found"})
        except Exception as exc:  # noqa: BLE001
            return Response(HTTPStatus.BAD_GATEWAY, {"error": "bridge_failed", "detail": str(exc)})
        return Response(HTTPStatus.OK, {"output": output})

    return router
