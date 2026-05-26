"""Telemetry endpoints + global rate limit — P3#15.

Pattern ported from B's routes.py:

- POST /api/csp-report         (open, no auth — but rate-limited per-IP)
- POST /api/client-event       (auth required; rate-limited per-IP)
- Global rate limit middleware that all requests pass through

Limits intentionally small. Each endpoint validates body shape + caps field
sizes so a malicious or buggy client can't fill the log with junk.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from http import HTTPStatus

from . import auth as auth_module
from .config import Config
from .router import Request, Response, Router

logger = logging.getLogger(__name__)
_csp_logger = logging.getLogger("csp_report")
_client_event_logger = logging.getLogger("client_event")


# ── per-IP sliding window rate limit ────────────────────────────────────────


class RateLimiter:
    """O(N) sliding window where N = max requests per window — fine for our limits."""

    def __init__(self, *, max_requests: int, window_seconds: float) -> None:
        self.max = max_requests
        self.window = window_seconds
        self._lock = threading.Lock()
        self._buckets: dict[str, list[float]] = {}

    def check(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            bucket = [t for t in self._buckets.get(key, []) if now - t < self.window]
            if len(bucket) >= self.max:
                self._buckets[key] = bucket
                return False
            bucket.append(now)
            self._buckets[key] = bucket
            return True


# ── instances ───────────────────────────────────────────────────────────────

CSP_LIMIT = RateLimiter(max_requests=100, window_seconds=60.0)
CLIENT_EVENT_LIMIT = RateLimiter(max_requests=30, window_seconds=60.0)

# Global limit — only applies to non-auth, non-streaming POST endpoints.
GLOBAL_POST_LIMIT = RateLimiter(max_requests=300, window_seconds=60.0)

# Limits adapted from B's _CLIENT_EVENT_ALLOWED_FIELDS map.
_CLIENT_EVENT_FIELDS = {
    "event": 64,
    "source": 80,
    "session_id": 128,
    "stream_id": 128,
    "visibility_state": 32,
    "url_path": 256,
    "reason": 160,
}
_CLIENT_EVENT_MAX_BODY = 4 * 1024
_CSP_MAX_BODY = 64 * 1024


def _truncate(value: object, max_len: int) -> str:
    if not isinstance(value, str):
        return ""
    return value[:max_len]


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("POST", "/api/csp-report")
    def _csp(req: Request) -> Response:
        if not CSP_LIMIT.check(req.client_ip()):
            return Response(HTTPStatus.TOO_MANY_REQUESTS, {"error": "rate_limited"})
        try:
            raw = req.body_bytes(max_bytes=_CSP_MAX_BODY)
        except ValueError:
            return Response(HTTPStatus.PAYLOAD_TOO_LARGE, {"error": "csp_body_too_large"})
        if not raw:
            return Response(HTTPStatus.NO_CONTENT, None)
        try:
            report = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_csp_json"})
        _csp_logger.warning(
            "csp_violation ip=%s body=%.500s",
            req.client_ip(),
            json.dumps(report, separators=(",", ":")),
        )
        return Response(HTTPStatus.NO_CONTENT, None)

    @router.route("POST", "/api/client-event")
    def _client_event(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        if not CLIENT_EVENT_LIMIT.check(req.client_ip()):
            return Response(HTTPStatus.TOO_MANY_REQUESTS, {"error": "rate_limited"})
        try:
            raw = req.body_bytes(max_bytes=_CLIENT_EVENT_MAX_BODY)
        except ValueError:
            return Response(HTTPStatus.PAYLOAD_TOO_LARGE, {"error": "event_body_too_large"})
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_event_json"})
        # Whitelist + truncate.
        sanitised = {k: _truncate(body.get(k), n) for k, n in _CLIENT_EVENT_FIELDS.items() if body.get(k)}
        if not sanitised:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "empty_event"})
        _client_event_logger.info(
            "client_event ip=%s data=%s", req.client_ip(), json.dumps(sanitised, separators=(",", ":")),
        )
        return Response(HTTPStatus.OK, {"ok": True})

    return router


def global_rate_limit(req: Request) -> Response | None:
    """Apply to POST/PUT/DELETE on non-auth endpoints. Returns 429 Response or None."""
    if req.method not in {"POST", "PUT", "DELETE"}:
        return None
    if req.path in {"/api/auth/login", "/api/auth/logout"}:
        return None  # login flow already has its own limit
    if req.path.startswith("/api/chat/stream"):
        return None  # streaming endpoints handle their own throttling
    if not GLOBAL_POST_LIMIT.check(req.client_ip()):
        return Response(HTTPStatus.TOO_MANY_REQUESTS, {"error": "rate_limited"})
    return None
