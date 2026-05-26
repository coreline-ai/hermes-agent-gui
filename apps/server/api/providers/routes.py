"""HTTP routes for Phase 16 providers."""

from __future__ import annotations

import time
from http import HTTPStatus

from .. import auth as auth_module
from ..config import Config
from ..router import Request, Response, Router
from . import discovery, store
from .catalog import get_preset, list_presets
from .oauth import nous_portal, openai_codex
from .oauth.pkce import OAuthStateError


def _auth(req: Request, cfg: Config) -> Response | None:
    if auth_module.authenticate(req, cfg) is None:
        return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
    return None


def register_routes(cfg: Config) -> Router:
    store.ensure_schema()
    router = Router()

    @router.route("GET", "/api/providers/presets")
    def _presets(req: Request) -> Response:
        if (err := _auth(req, cfg)) is not None:
            return err
        return Response(HTTPStatus.OK, {"presets": [p.to_dict() for p in list_presets()]})

    @router.route("GET", "/api/providers")
    def _list(req: Request) -> Response:
        if (err := _auth(req, cfg)) is not None:
            return err
        return Response(HTTPStatus.OK, {"providers": [p.to_dict() for p in store.list_providers()]})

    @router.route("POST", "/api/providers")
    def _create(req: Request) -> Response:
        if (err := _auth(req, cfg)) is not None:
            return err
        try:
            body = req.json()
            provider = store.create_provider(
                kind=str(body.get("kind") or ""),
                label=str(body.get("label") or ""),
                base_url=str(body.get("base_url") or "") or None,
                api_key=str(body.get("api_key") or ""),
                enabled=bool(body.get("enabled", True)),
                extra=body.get("extra") if isinstance(body.get("extra"), dict) else None,
            )
            return Response(HTTPStatus.CREATED, provider.to_dict())
        except store.ProviderStoreError as exc:
            status = HTTPStatus.CONFLICT if exc.code == "provider_label_taken" else HTTPStatus.BAD_REQUEST
            return Response(status, {"error": exc.code, "detail": exc.detail})
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})

    @router.route("DELETE", "/api/providers/{pid}")
    def _delete(req: Request) -> Response:
        if (err := _auth(req, cfg)) is not None:
            return err
        ok = store.delete_provider(req.params["pid"])
        return Response(HTTPStatus.OK if ok else HTTPStatus.NOT_FOUND, {"ok": ok} if ok else {"error": "provider_not_found"})

    @router.route("GET", "/api/providers/{pid}/models")
    def _models(req: Request) -> Response:
        if (err := _auth(req, cfg)) is not None:
            return err
        provider = store.get_provider(req.params["pid"])
        if provider is None:
            return Response(HTTPStatus.NOT_FOUND, {"error": "provider_not_found"})
        try:
            models, fetched_at, cache_hit = discovery.discover_models(provider, store.read_api_key(provider))
            return Response(
                HTTPStatus.OK,
                {
                    "provider_id": provider.id,
                    "models": [m.to_dict() for m in models],
                    "fetched_at": int(fetched_at),
                    "cache_hit": cache_hit,
                },
            )
        except discovery.DiscoveryError as exc:
            # Model catalog fetch failure is non-fatal for the picker, except URL policy errors.
            if exc.code == "provider_private_ip_blocked":
                return Response(HTTPStatus.BAD_REQUEST, {"error": exc.code, "detail": exc.detail})
            return Response(HTTPStatus.OK, {"provider_id": provider.id, "models": [], "fetched_at": int(time.time()), "cache_hit": False})

    @router.route("POST", "/api/providers/{pid}/test")
    def _test(req: Request) -> Response:
        if (err := _auth(req, cfg)) is not None:
            return err
        provider = store.get_provider(req.params["pid"])
        if provider is None:
            return Response(HTTPStatus.NOT_FOUND, {"error": "provider_not_found"})
        started = time.monotonic()
        try:
            models, _, _ = discovery.discover_models(provider, store.read_api_key(provider), use_cache=False)
            model_used = models[0].id if models else (get_preset(provider.kind).default_models[0] if get_preset(provider.kind) and get_preset(provider.kind).default_models else "unknown")
            store.update_test_status(provider.id, "ok")
            return Response(HTTPStatus.OK, {"ok": True, "latency_ms": int((time.monotonic() - started) * 1000), "model_used": model_used})
        except discovery.DiscoveryError as exc:
            store.update_test_status(provider.id, exc.code)
            status = HTTPStatus.BAD_REQUEST if exc.code in {"provider_private_ip_blocked", "invalid_provider_url"} else HTTPStatus.BAD_GATEWAY
            return Response(status, {"error": exc.code, "detail": exc.detail})

    @router.route("GET", "/api/providers/oauth/{provider}/start")
    def _oauth_start(req: Request) -> Response:
        if (err := _auth(req, cfg)) is not None:
            return err
        provider = req.params["provider"]
        if provider == "nous_portal":
            return Response(HTTPStatus.OK, nous_portal.start())
        if provider == "openai_codex":
            return Response(HTTPStatus.OK, openai_codex.start())
        return Response(HTTPStatus.NOT_FOUND, {"error": "oauth_provider_not_found"})

    @router.route("GET", "/api/providers/oauth/{provider}/callback")
    def _oauth_callback(req: Request) -> Response:
        if (err := _auth(req, cfg)) is not None:
            return err
        provider = req.params["provider"]
        state = (req.query.get("state") or [""])[0]
        try:
            if provider == "nous_portal":
                return Response(HTTPStatus.OK, nous_portal.complete(state))
            if provider == "openai_codex":
                return Response(HTTPStatus.OK, openai_codex.complete(state))
            return Response(HTTPStatus.NOT_FOUND, {"error": "oauth_provider_not_found"})
        except OAuthStateError as exc:
            return Response(HTTPStatus.BAD_REQUEST, {"error": exc.code})

    return router
