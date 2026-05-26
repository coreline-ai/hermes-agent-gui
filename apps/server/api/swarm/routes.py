"""Swarm + Conductor HTTP routes — Phase 6 + P1#6 dispatch."""

from __future__ import annotations

from http import HTTPStatus

from .. import auth as auth_module
from .. import exec_policy
from ..config import Config
from ..router import Request, Response, Router
from .conductor import sanitize_mission
from .dispatch import (
    dispatch as do_dispatch,
    get as get_dispatched,
    list_recent as list_dispatched,
)
from .foundation import SwarmFoundation
from .missions import decompose_mission

_foundation = SwarmFoundation()


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("GET", "/api/swarm/workers")
    def _list_workers(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        return Response(
            HTTPStatus.OK,
            {
                "tmux": _foundation.has_tmux,
                "workers": [w.to_dict() for w in _foundation.list()],
            },
        )

    @router.route("POST", "/api/swarm/workers")
    def _spawn(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        if (blocked := exec_policy.require_exec(req, cfg)) is not None:
            return blocked
        try:
            body = req.json()
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
        role = str(body.get("role") or "builder")
        cmd = body.get("cmd")
        if not isinstance(cmd, list) or not cmd:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "cmd_array_required"})
        worker = _foundation.spawn(role, [str(x) for x in cmd], meta=body.get("meta") or {})
        return Response(HTTPStatus.CREATED, worker.to_dict())

    @router.route("DELETE", "/api/swarm/workers/{wid}")
    def _kill(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        ok = _foundation.kill(req.params["wid"])
        return Response(HTTPStatus.OK if ok else HTTPStatus.NOT_FOUND, {"ok": ok})

    @router.route("POST", "/api/conductor/missions")
    def _new_mission(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            body = req.json()
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
        prompt = sanitize_mission(str(body.get("prompt") or ""))
        if not prompt:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "prompt_required"})
        mission = decompose_mission(prompt)

        dispatched = None
        if body.get("dispatch", False):
            if (blocked := exec_policy.require_exec(req, cfg)) is not None:
                return blocked
            dispatched = do_dispatch(_foundation, mission)

        return Response(
            HTTPStatus.CREATED,
            {**mission.to_dict(), "dispatched": dispatched.to_dict() if dispatched else None},
        )

    @router.route("POST", "/api/conductor/missions/{mid}/dispatch")
    def _dispatch_existing(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        if (blocked := exec_policy.require_exec(req, cfg)) is not None:
            return blocked
        try:
            body = req.json()
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
        # Caller may resubmit the prompt to rebuild the decomposition deterministically.
        prompt = sanitize_mission(str(body.get("prompt") or ""))
        if not prompt:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "prompt_required"})
        mission = decompose_mission(prompt)
        mission.id = req.params["mid"]   # preserve UI's mission id
        dispatched = do_dispatch(_foundation, mission)
        return Response(HTTPStatus.OK, dispatched.to_dict())

    @router.route("GET", "/api/conductor/missions/{mid}")
    def _mission_status(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        rec = get_dispatched(req.params["mid"])
        if rec is None:
            return Response(HTTPStatus.NOT_FOUND, {"error": "mission_not_dispatched"})
        workers = [
            (_foundation.get(wid).to_dict() if _foundation.get(wid) else {"id": wid, "state": "gone"})
            for wid in rec.workers
        ]
        return Response(HTTPStatus.OK, {**rec.to_dict(), "workers_state": workers})

    @router.route("GET", "/api/conductor/missions")
    def _missions(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        return Response(HTTPStatus.OK, {"missions": [m.to_dict() for m in list_dispatched()]})

    return router
