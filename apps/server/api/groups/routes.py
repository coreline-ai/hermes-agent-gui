from __future__ import annotations

import time
from http import HTTPStatus

from .. import auth as auth_module
from ..config import Config
from ..router import Request, Response, Router
from .routing import route_message
from .store import add_message, create_group, get_group, list_groups, list_messages


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("GET", "/api/groups")
    def _list(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        return Response(HTTPStatus.OK, {"groups": [g.to_dict() for g in list_groups()]})

    @router.route("POST", "/api/groups")
    def _create(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            body = req.json()
            group = create_group(str(body.get("name") or "New group"), body.get("participants") if isinstance(body.get("participants"), list) else None)
        except ValueError as exc:
            return Response(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        return Response(HTTPStatus.CREATED, group.to_dict())

    @router.route("GET", "/api/groups/{gid}")
    def _get(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        group = get_group(req.params["gid"])
        if group is None:
            return Response(HTTPStatus.NOT_FOUND, {"error": "group_not_found"})
        return Response(HTTPStatus.OK, {**group.to_dict(), "messages": list_messages(group.id)})

    @router.route("POST", "/api/groups/{gid}/messages")
    def _message(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        group = get_group(req.params["gid"])
        if group is None:
            return Response(HTTPStatus.NOT_FOUND, {"error": "group_not_found"})
        if int(time.time()) > group.invite_expires_at:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invite_expired"})
        try:
            body = req.json()
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
        content = str(body.get("content") or "").strip()
        if not content:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "content_required"})
        participant = route_message(group, content)
        if participant is None:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "no_participants"})
        msg = add_message(group.id, participant.name, content)
        return Response(HTTPStatus.OK, {"message": msg, "routed_to": participant.to_dict()})

    return router
