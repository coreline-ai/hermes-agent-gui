"""Direct Webhook platform runtime — Phase 15b.

The webhook endpoint is intentionally unauthenticated because third-party
systems call it directly. The endpoint is protected by a random URL token plus
an HMAC-SHA256 signature over the raw request body.
"""

from __future__ import annotations

import hmac
import json
import secrets
import threading
import time
from dataclasses import dataclass
from hashlib import sha256
from http import HTTPStatus

from ...router import Request, Response
from ...runtime_adapter import Adapter, ChatTurn
from .. import credentials, status
from ..registry import REGISTRY
from .base import DelegatedPlatform

platform = DelegatedPlatform(REGISTRY["webhook"])

MAX_PAYLOAD_BYTES = 256 * 1024
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 60

_rate_lock = threading.RLock()
_rate_buckets: dict[str, list[float]] = {}


@dataclass(frozen=True)
class WebhookRegistration:
    token: str
    signing_secret: str
    inbound_url: str

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "signing_secret": self.signing_secret,
            "inbound_url": self.inbound_url,
            "signature_header": "X-Hermes-Signature",
            "signature_format": "sha256=<hex_hmac_sha256_raw_body>",
        }


def _origin(req: Request) -> str:
    proto = req.headers.get("x-forwarded-proto") or "http"
    host = req.headers.get("host") or "127.0.0.1:8800"
    return f"{proto}://{host}"


def _inbound_url(req: Request, token: str) -> str:
    return f"{_origin(req)}/api/messaging/webhook/{token}/inbound"


def get_registration(req: Request | None = None) -> WebhookRegistration | None:
    creds = credentials.read_platform_credentials("webhook")
    token = creds.get("token")
    secret = creds.get("signing_secret")
    if not token or not secret:
        return None
    inbound = _inbound_url(req, token) if req is not None else f"/api/messaging/webhook/{token}/inbound"
    return WebhookRegistration(token=token, signing_secret=secret, inbound_url=inbound)


def ensure_registration(req: Request, *, rotate: bool = False) -> WebhookRegistration:
    current = None if rotate else get_registration(req)
    if current is not None:
        return current
    token = secrets.token_urlsafe(24)
    signing_secret = secrets.token_urlsafe(32)
    credentials.write_credentials("webhook", {"token": token, "signing_secret": signing_secret})
    status.record_status("webhook", configured=True, connected=True, last_error=None)
    return WebhookRegistration(token=token, signing_secret=signing_secret, inbound_url=_inbound_url(req, token))


def _signature_header(req: Request) -> str:
    return (
        req.headers.get("x-hermes-signature")
        or req.headers.get("x-hub-signature-256")
        or ""
    ).strip()


def verify_signature(secret: str, body: bytes, header: str) -> bool:
    if not header:
        return False
    provided = header.removeprefix("sha256=").strip()
    expected = hmac.new(secret.encode("utf-8"), body, sha256).hexdigest()
    return hmac.compare_digest(provided, expected)


def _check_rate_limit(token: str) -> bool:
    now = time.monotonic()
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS
    with _rate_lock:
        bucket = [ts for ts in _rate_buckets.get(token, []) if ts >= cutoff]
        if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
            _rate_buckets[token] = bucket
            return False
        bucket.append(now)
        _rate_buckets[token] = bucket
        return True


def _extract_text(payload: dict) -> str:
    for key in ("text", "message", "prompt"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    nested = payload.get("message")
    if isinstance(nested, dict):
        value = nested.get("text") or nested.get("content")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _collect_chat(adapter: Adapter, text: str, session_id: str | None = None) -> tuple[bool, dict]:
    tokens: list[str] = []
    final: dict = {}
    turn = ChatTurn(messages=[{"role": "user", "content": text}], session_id=session_id)
    for event, data in adapter.stream(turn):
        if event == "token":
            tokens.append(str(data.get("text") or ""))
        elif event == "error":
            return False, {"error": data.get("error") or "chat_error", "detail": data.get("detail")}
        elif event == "done":
            final = data
            break
    return True, {"response": "".join(tokens), "done": final}


def handle_inbound(req: Request, adapter: Adapter) -> Response:
    token = req.params.get("token", "")
    reg = get_registration(req)
    if reg is None or not token or not hmac.compare_digest(token, reg.token):
        return Response(HTTPStatus.NOT_FOUND, {"error": "webhook_not_found"})

    try:
        raw = req.body_bytes(MAX_PAYLOAD_BYTES)
    except ValueError:
        return Response(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "payload_too_large", "max": MAX_PAYLOAD_BYTES})

    if not verify_signature(reg.signing_secret, raw, _signature_header(req)):
        status.record_status("webhook", configured=True, connected=False, last_error="webhook_signature_invalid")
        return Response(HTTPStatus.UNAUTHORIZED, {"error": "webhook_signature_invalid"})

    if not _check_rate_limit(token):
        return Response(HTTPStatus.TOO_MANY_REQUESTS, {"error": "rate_limited", "limit": RATE_LIMIT_MAX_REQUESTS})

    try:
        payload = json.loads(raw.decode("utf-8")) if raw else {}
    except (UnicodeDecodeError, json.JSONDecodeError):
        return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})

    if not isinstance(payload, dict):
        return Response(HTTPStatus.BAD_REQUEST, {"error": "payload_object_required"})
    text = _extract_text(payload)
    if not text:
        return Response(HTTPStatus.BAD_REQUEST, {"error": "text_required"})

    ok, chat = _collect_chat(adapter, text, session_id=str(payload.get("session_id") or "") or None)
    if not ok:
        status.record_status("webhook", configured=True, connected=False, last_error=str(chat.get("error")))
        return Response(HTTPStatus.BAD_GATEWAY, chat)

    status.record_event("webhook", connected=True, error=None)
    return Response(
        HTTPStatus.OK,
        {
            "ok": True,
            "platform": "webhook",
            "received": text,
            **chat,
        },
    )
