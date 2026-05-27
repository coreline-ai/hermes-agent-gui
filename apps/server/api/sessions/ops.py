"""Session HTTP routes — Phase 2."""

from __future__ import annotations

from http import HTTPStatus
from typing import Callable

from .. import auth as auth_module
from .. import streaming
from ..config import Config
from ..router import Request, Response, Router
from .compression import alias_resolve
from .events import events
from .lifecycle import Message, SessionStore
from .recovery import repair_transcript_drift, session_health


def _require_auth(req: Request, cfg: Config):
    return auth_module.authenticate(req, cfg)


def register_routes(cfg: Config, store: SessionStore) -> Router:
    router = Router()

    @router.route("GET", "/api/sessions")
    def _list(req: Request) -> Response:
        if _require_auth(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        all_profiles = (req.query.get("all_profiles") or ["0"])[0] in {"1", "true"}
        profile = (req.query.get("profile") or ["default"])[0]
        items = [s.to_summary() for s in store.list(profile=profile, all_profiles=all_profiles)]
        return Response(HTTPStatus.OK, {"sessions": items})

    @router.route("POST", "/api/sessions")
    def _create(req: Request) -> Response:
        if _require_auth(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            body = req.json()
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
        sess = store.create(
            title=str(body.get("title") or "New chat"),
            profile=str(body.get("profile") or "default"),
        )
        events.publish("session_list_changed", {"session_id": sess.id})
        return Response(HTTPStatus.CREATED, sess.to_dict())

    @router.route("GET", "/api/sessions/_stream")
    def _events_stream(req: Request):
        if _require_auth(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        q = events.subscribe()
        try:
            streaming.begin_sse(req.raw)
            if not streaming.write_event(req.raw, "ready", {"ok": True}):
                return None
            while True:
                got_any = False
                for evt in events.drain(q, timeout=20.0):
                    got_any = True
                    if not streaming.write_event(req.raw, evt.kind, evt.payload):
                        return None
                if not got_any:
                    if not streaming.write_event(req.raw, "ping", {"ts": int(__import__("time").time())}):
                        return None
        finally:
            events.unsubscribe(q)
        return None

    @router.route("GET", "/api/sessions/{sid}")
    def _get(req: Request) -> Response:
        if _require_auth(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        sid = alias_resolve(req.params["sid"])
        sess = store.get(sid)
        if sess is None:
            return Response(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
        return Response(HTTPStatus.OK, sess.to_dict())

    @router.route("PUT", "/api/sessions/{sid}")
    def _rename(req: Request) -> Response:
        if _require_auth(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            body = req.json()
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
        title = str(body.get("title") or "").strip()
        if not title:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "title_required"})
        sid = alias_resolve(req.params["sid"])
        sess = store.rename(sid, title)
        if sess is None:
            return Response(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
        events.publish("session_updated", {"session_id": sess.id})
        return Response(HTTPStatus.OK, sess.to_summary())

    @router.route("DELETE", "/api/sessions/{sid}")
    def _delete(req: Request) -> Response:
        if _require_auth(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        sid = alias_resolve(req.params["sid"])
        ok = store.delete(sid)
        if ok:
            events.publish("session_deleted", {"session_id": sid})
            return Response(HTTPStatus.OK, {"ok": True})
        return Response(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})

    @router.route("POST", "/api/sessions/{sid}/health")
    def _health(req: Request) -> Response:
        if _require_auth(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            body = req.json()
        except ValueError:
            body = {}
        sid = alias_resolve(req.params["sid"])
        sess = store.get(sid)
        if sess is None:
            return Response(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})

        browser_messages_raw = body.get("browser_messages")
        browser_messages = (
            [Message.from_dict(m) for m in browser_messages_raw]
            if isinstance(browser_messages_raw, list)
            else None
        )
        compact = body.get("compact_context_messages")
        if not isinstance(compact, int):
            compact = None
        report = session_health(sess, browser_messages, compact)

        repaired = False
        if report.drift and report.drift_kind in {"browser_ahead"} and browser_messages:
            sess = repair_transcript_drift(store, sess, browser_messages)
            repaired = True

        return Response(
            HTTPStatus.OK,
            {**report.to_dict(), "repaired": repaired, "messages": [m.to_dict() for m in sess.messages]},
        )

    return router


__all__ = ["register_routes"]
