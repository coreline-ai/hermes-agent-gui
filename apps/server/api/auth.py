"""Password + Bearer-token + HMAC-cookie auth (Phase 1).

Pattern adapted from nesquena/hermes-webui's api/auth.py — but trimmed to
the password + token + cookie path. OAuth and Passkey live in their own
modules as 501 stubs for Phase 1 (see docs/review/08-phase-1.md).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from http import HTTPStatus
from typing import Final

from .config import Config
from .router import Request, Response, Router

COOKIE_NAME: Final = "hermes_gui_auth"
SESSION_TTL_SECONDS: Final = 30 * 24 * 60 * 60  # 30 days

router = Router()


@dataclass(frozen=True)
class Session:
    user: str
    issued_at: int
    expires_at: int


# ── HMAC-signed cookie ───────────────────────────────────────────────────────


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def issue_cookie(secret: bytes, user: str, *, ttl: int = SESSION_TTL_SECONDS) -> str:
    now = int(time.time())
    payload = {"u": user, "iat": now, "exp": now + ttl}
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = _b64url(hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{sig}"


def verify_cookie(secret: bytes, token: str | None) -> Session | None:
    if not token or "." not in token:
        return None
    body, sig = token.split(".", 1)
    expected = _b64url(hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        data = json.loads(_b64url_decode(body))
        return Session(user=data["u"], issued_at=int(data["iat"]), expires_at=int(data["exp"]))
    except (KeyError, ValueError):
        return None


def _is_expired(s: Session) -> bool:
    return time.time() >= s.expires_at


# ── Middleware entry point ───────────────────────────────────────────────────


def authenticate(req: Request, cfg: Config) -> Session | None:
    """Return Session if request is authenticated; None otherwise.

    Order: Bearer token → cookie. Constant-time comparison throughout.
    """
    if cfg.bearer_token and (presented := req.bearer()):
        if hmac.compare_digest(presented, cfg.bearer_token):
            now = int(time.time())
            return Session(user="api-token", issued_at=now, expires_at=now + SESSION_TTL_SECONDS)
    if (raw := req.cookie(COOKIE_NAME)):
        if (sess := verify_cookie(cfg.secret, raw)):
            if not _is_expired(sess):
                return sess
    return None


# ── Login rate limiting (per IP, sliding 60s) ────────────────────────────────

_LOGIN_ATTEMPTS: dict[str, list[float]] = {}
_LOGIN_RATE_WINDOW = 60.0
_LOGIN_RATE_MAX = 5


def _login_rate_ok(ip: str) -> bool:
    now = time.time()
    bucket = [t for t in _LOGIN_ATTEMPTS.get(ip, []) if now - t < _LOGIN_RATE_WINDOW]
    if len(bucket) >= _LOGIN_RATE_MAX:
        _LOGIN_ATTEMPTS[ip] = bucket
        return False
    bucket.append(now)
    _LOGIN_ATTEMPTS[ip] = bucket
    return True



def login_lock_snapshot() -> list[dict]:
    now = time.time()
    return [
        {"ip": ip, "attempts": len([t for t in attempts if now - t < _LOGIN_RATE_WINDOW]), "window_seconds": int(_LOGIN_RATE_WINDOW)}
        for ip, attempts in sorted(_LOGIN_ATTEMPTS.items())
        if len([t for t in attempts if now - t < _LOGIN_RATE_WINDOW]) >= _LOGIN_RATE_MAX
    ]


def clear_login_locks(ip: str | None = None) -> int:
    if ip:
        return 1 if _LOGIN_ATTEMPTS.pop(ip, None) is not None else 0
    count = len(_LOGIN_ATTEMPTS)
    _LOGIN_ATTEMPTS.clear()
    return count

# ── Routes ───────────────────────────────────────────────────────────────────


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("POST", "/api/auth/login")
    def _login(req: Request) -> Response:
        if not _login_rate_ok(req.client_ip()):
            return Response(HTTPStatus.TOO_MANY_REQUESTS, {"error": "rate_limited"})
        try:
            body = req.json()
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
        password = str(body.get("password") or "")
        if not cfg.password:
            return Response(HTTPStatus.NOT_IMPLEMENTED, {"error": "password_auth_disabled"})
        if not password or not hmac.compare_digest(password, cfg.password):
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "invalid_credentials"})
        cookie = issue_cookie(cfg.secret, user="local")
        resp = Response(
            HTTPStatus.OK,
            {"user": {"name": "local"}, "expires_at": int(time.time()) + SESSION_TTL_SECONDS},
        )
        secure = "Secure; " if req.headers.get("x-forwarded-proto") == "https" else ""
        resp.add_header(
            "Set-Cookie",
            f"{COOKIE_NAME}={cookie}; Path=/; HttpOnly; SameSite=Lax; "
            f"Max-Age={SESSION_TTL_SECONDS}; {secure}",
        )
        return resp

    @router.route("POST", "/api/auth/logout")
    def _logout(_req: Request) -> Response:
        resp = Response(HTTPStatus.OK, {"ok": True})
        resp.add_header(
            "Set-Cookie",
            f"{COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0",
        )
        return resp

    @router.route("GET", "/api/auth/me")
    def _me(req: Request) -> Response:
        if (sess := authenticate(req, cfg)) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        return Response(HTTPStatus.OK, {"user": {"name": sess.user}, "expires_at": sess.expires_at})

    @router.route("GET", "/api/auth/login-locks")
    def _locks(req: Request) -> Response:
        if authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        return Response(HTTPStatus.OK, {"locks": login_lock_snapshot()})

    @router.route("DELETE", "/api/auth/login-locks")
    def _clear_locks(req: Request) -> Response:
        if authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        ip = (req.query.get("ip") or [None])[0]
        return Response(HTTPStatus.OK, {"cleared": clear_login_locks(ip)})

    return router
