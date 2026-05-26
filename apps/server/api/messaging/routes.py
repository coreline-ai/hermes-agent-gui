"""HTTP routes for Phase 15 messaging."""

from __future__ import annotations

from http import HTTPStatus

from .. import auth as auth_module
from ..config import Config
from ..router import Request, Response, Router
from ..runtime_adapter import Adapter
from ..sessions import SessionStore
from . import behavior, credentials, status
from .platforms.base import CredentialError, validate_credentials
from .platforms import home_assistant, webhook
from .registry import get_platform, list_platforms
from .delegate_probe import test_connection as delegated_test_connection
from .webhook_inbound import inbound as webhook_inbound


def _platform_payload(meta) -> dict:
    st = status.get_status(meta.id)
    configured = credentials.is_configured(meta) or st.configured
    return {
        **meta.to_dict(),
        "configured": configured,
        "connected": st.connected,
        "last_event_at": st.last_event_at,
        "last_error": st.last_error,
        "behavior": behavior.read_platform_behavior(meta.id),
    }


def _require_platform(platform_id: str) -> tuple[object | None, Response | None]:
    meta = get_platform(platform_id)
    if meta is None:
        return None, Response(HTTPStatus.NOT_FOUND, {"error": "platform_not_found", "platform": platform_id})
    return meta, None


def register_routes(cfg: Config, adapter: Adapter, store: SessionStore | None = None) -> Router:
    del store  # Phase 15b inbound is stateless; profile/session archive lands later.
    status.ensure_schema()
    router = Router()

    @router.route("GET", "/api/messaging/platforms")
    def _list(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        platforms = [_platform_payload(meta) for meta in list_platforms()]
        return Response(HTTPStatus.OK, {"platforms": platforms})

    @router.route("POST", "/api/messaging/{platform}/configure")
    def _configure(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        meta, error = _require_platform(req.params["platform"])
        if error is not None:
            return error
        try:
            body = req.json()
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
        creds = body.get("credentials") or {}
        beh = body.get("behavior")
        if not isinstance(creds, dict):
            return Response(HTTPStatus.BAD_REQUEST, {"error": "credentials_object_required"})
        if beh is not None and not isinstance(beh, dict):
            return Response(HTTPStatus.BAD_REQUEST, {"error": "behavior_object_required"})
        if meta.id == "webhook":  # type: ignore[union-attr]
            if beh is not None:
                behavior.write_platform_behavior("webhook", beh)
            reg = webhook.ensure_registration(req, rotate=bool(body.get("rotate")))
            return Response(HTTPStatus.OK, {"ok": True, "platform": "webhook", "configured": True, **reg.to_dict()})
        try:
            validate_credentials(meta, creds)  # type: ignore[arg-type]
        except CredentialError as exc:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_credential", "field": exc.field, "detail": exc.detail})
        credentials.write_credentials(meta.id, {str(k): str(v) for k, v in creds.items()})  # type: ignore[union-attr]
        if beh is not None:
            behavior.write_platform_behavior(meta.id, beh)  # type: ignore[union-attr]
        status.record_status(meta.id, configured=True, connected=False, last_error=None)  # type: ignore[union-attr]
        return Response(HTTPStatus.OK, {"ok": True, "platform": meta.id, "configured": True})  # type: ignore[union-attr]

    @router.route("POST", "/api/messaging/{platform}/test")
    def _test(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        meta, error = _require_platform(req.params["platform"])
        if error is not None:
            return error
        stored = credentials.read_platform_credentials(meta.id)  # type: ignore[union-attr]
        try:
            validate_credentials(meta, stored)  # type: ignore[arg-type]
        except CredentialError as exc:
            status.record_status(meta.id, configured=False, connected=False, last_error=exc.detail)  # type: ignore[union-attr]
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_credential", "field": exc.field, "detail": exc.detail})
        if meta.id == "webhook":  # type: ignore[union-attr]
            reg = webhook.get_registration(req)
            if reg is None:
                return Response(HTTPStatus.BAD_REQUEST, {"error": "webhook_not_configured"})
            return Response(HTTPStatus.OK, {"ok": True, "platform": "webhook", **reg.to_dict()})
        if meta.id == "home_assistant":  # type: ignore[union-attr]
            result = home_assistant.test_connection()
            return Response(result.status, result.body)
        if meta.mode == "direct":  # type: ignore[union-attr]
            return Response(HTTPStatus.NOT_IMPLEMENTED, {"error": "direct_platform_not_implemented"})
        result = delegated_test_connection(cfg, meta.id)  # type: ignore[union-attr]
        ok = result.status == HTTPStatus.OK and bool(result.body.get("ok", True))
        status.record_status(
            meta.id,  # type: ignore[union-attr]
            configured=True,
            connected=ok,
            last_error=None if ok else str(result.body.get("error") or result.body.get("detail") or "test_failed"),
        )
        return Response(result.status, result.body)

    @router.route("DELETE", "/api/messaging/{platform}")
    def _delete(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        meta, error = _require_platform(req.params["platform"])
        if error is not None:
            return error
        purged = credentials.delete_platform_credentials(meta.id)  # type: ignore[union-attr]
        behavior.delete_platform_behavior(meta.id)  # type: ignore[union-attr]
        status.record_status(meta.id, configured=False, connected=False, last_error=None)  # type: ignore[union-attr]
        return Response(HTTPStatus.OK, {"ok": True, "platform": meta.id, "purged_credential": purged})  # type: ignore[union-attr]

    @router.route("POST", "/api/messaging/webhook/{token}/inbound")
    def _webhook_inbound(req: Request) -> Response:
        return webhook_inbound(req, adapter)

    return router
