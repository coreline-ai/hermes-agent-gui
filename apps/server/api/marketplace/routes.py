from __future__ import annotations

from http import HTTPStatus

from .. import auth as auth_module
from ..config import Config
from ..router import Request, Response, Router
from .store import favorite, install, installed_map, load_catalog, uninstall


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("GET", "/api/marketplace/catalog")
    def _catalog(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        q = ((req.query.get("q") or [""])[0]).lower()
        installed = installed_map()
        items = [{**item, "installed": item["id"] in installed, "install": installed.get(item["id"])} for item in load_catalog()]
        if q:
            items = [item for item in items if q in item["label"].lower() or q in " ".join(item["tags"]).lower()]
        return Response(HTTPStatus.OK, {"items": items, "total": len(items)})

    @router.route("POST", "/api/marketplace/{preset_id}/install")
    def _install(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            return Response(HTTPStatus.CREATED, install(req.params["preset_id"]))
        except ValueError as exc:
            code = HTTPStatus.CONFLICT if str(exc) == "already_installed" else HTTPStatus.NOT_FOUND
            return Response(code, {"error": str(exc)})

    @router.route("DELETE", "/api/marketplace/{preset_id}")
    def _uninstall(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        return Response(HTTPStatus.OK, {"ok": uninstall(req.params["preset_id"])})

    @router.route("POST", "/api/marketplace/{preset_id}/favorite")
    def _favorite(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        body = req.json()
        return Response(HTTPStatus.OK, favorite(req.params["preset_id"], bool(body.get("favorite", True))))

    return router
