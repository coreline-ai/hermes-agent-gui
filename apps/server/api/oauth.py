"""OAuth 2.1 + OIDC with PKCE — P1#4.

Provider config comes from env, one block per provider, e.g.::

    HERMES_GUI_OAUTH_GITHUB_CLIENT_ID=...
    HERMES_GUI_OAUTH_GITHUB_CLIENT_SECRET=...
    HERMES_GUI_OAUTH_GITHUB_AUTH_URL=https://github.com/login/oauth/authorize
    HERMES_GUI_OAUTH_GITHUB_TOKEN_URL=https://github.com/login/oauth/access_token
    HERMES_GUI_OAUTH_GITHUB_USERINFO_URL=https://api.github.com/user
    HERMES_GUI_OAUTH_GITHUB_SCOPES=read:user user:email

On a successful callback the GUI issues its own HMAC session cookie (same
``hermes_gui_auth`` cookie used by the password flow), so downstream code
doesn't need to know which auth method was used.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http import HTTPStatus

from . import auth as auth_module
from .config import Config
from .router import Request, Response, Router

logger = logging.getLogger(__name__)

# ── in-memory pending-state store (TTL 10 min) ──────────────────────────────

_PENDING: dict[str, dict] = {}
_TTL_SECONDS = 600


def _gc_pending() -> None:
    now = time.time()
    for k, v in list(_PENDING.items()):
        if now - v["created_at"] > _TTL_SECONDS:
            _PENDING.pop(k, None)


# ── provider config ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Provider:
    name: str
    client_id: str
    client_secret: str
    auth_url: str
    token_url: str
    userinfo_url: str
    scopes: list[str]


def _provider(name: str) -> Provider | None:
    upper = name.upper()
    prefix = f"HERMES_GUI_OAUTH_{upper}_"
    cid = os.environ.get(prefix + "CLIENT_ID")
    secret = os.environ.get(prefix + "CLIENT_SECRET")
    auth_url = os.environ.get(prefix + "AUTH_URL")
    token_url = os.environ.get(prefix + "TOKEN_URL")
    userinfo_url = os.environ.get(prefix + "USERINFO_URL")
    if not (cid and secret and auth_url and token_url and userinfo_url):
        return None
    return Provider(
        name=name.lower(),
        client_id=cid,
        client_secret=secret,
        auth_url=auth_url,
        token_url=token_url,
        userinfo_url=userinfo_url,
        scopes=(os.environ.get(prefix + "SCOPES") or "openid email profile").split(),
    )


# ── PKCE helpers ────────────────────────────────────────────────────────────


def _pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode("ascii")
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    return verifier, challenge


def _redirect_uri(req: Request, provider: str) -> str:
    fwd_proto = req.headers.get("x-forwarded-proto") or "http"
    host = req.headers.get("host") or "127.0.0.1:8800"
    return f"{fwd_proto}://{host}/api/auth/oauth/{provider}/callback"


def _safe_token_error(token_resp: object) -> dict:
    """Return provider error details without echoing token-like fields."""

    out = {"error": "token_response_invalid"}
    if not isinstance(token_resp, dict):
        return out
    if isinstance(token_resp.get("error"), str):
        out["provider_error"] = token_resp["error"][:200]
    for key in ("error_description", "error_uri"):
        val = token_resp.get(key)
        if isinstance(val, str):
            out[key] = val[:500]
    return out


# ── HTTP routes ─────────────────────────────────────────────────────────────


router = Router()


@router.route("GET", "/api/auth/oauth/{provider}/start")
def _start(req: Request) -> Response:
    _gc_pending()
    name = req.params["provider"]
    p = _provider(name)
    if p is None:
        return Response(HTTPStatus.NOT_IMPLEMENTED, {"error": "oauth_not_configured", "provider": name})

    state = secrets.token_urlsafe(32)
    verifier, challenge = _pkce_pair()
    _PENDING[state] = {
        "provider": name,
        "verifier": verifier,
        "created_at": time.time(),
        "redirect": _redirect_uri(req, name),
    }
    params = {
        "response_type": "code",
        "client_id": p.client_id,
        "redirect_uri": _PENDING[state]["redirect"],
        "scope": " ".join(p.scopes),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    url = p.auth_url + ("&" if "?" in p.auth_url else "?") + urllib.parse.urlencode(params)
    resp = Response(HTTPStatus.FOUND, {"redirect": url})
    resp.add_header("Location", url)
    return resp


@router.route("GET", "/api/auth/oauth/{provider}/callback")
def _callback(req: Request) -> Response:
    _gc_pending()
    name = req.params["provider"]
    code = (req.query.get("code") or [""])[0]
    state = (req.query.get("state") or [""])[0]
    if not (code and state):
        return Response(HTTPStatus.BAD_REQUEST, {"error": "missing_code_or_state"})
    pending = _PENDING.pop(state, None)
    if not pending or pending["provider"] != name:
        return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_state"})
    p = _provider(name)
    if p is None:
        return Response(HTTPStatus.NOT_IMPLEMENTED, {"error": "oauth_not_configured"})

    # Exchange code → access_token
    token_body = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": pending["redirect"],
            "client_id": p.client_id,
            "client_secret": p.client_secret,
            "code_verifier": pending["verifier"],
        }
    ).encode("ascii")
    treq = urllib.request.Request(
        p.token_url,
        data=token_body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(treq, timeout=10) as r:
            raw = r.read().decode("utf-8")
    except urllib.error.URLError as exc:
        return Response(HTTPStatus.BAD_GATEWAY, {"error": "token_exchange_failed", "detail": str(exc)})

    try:
        token_resp = json.loads(raw)
    except json.JSONDecodeError:
        token_resp = dict(urllib.parse.parse_qsl(raw))
    if not isinstance(token_resp, dict):
        return Response(HTTPStatus.BAD_GATEWAY, _safe_token_error(token_resp))
    access = token_resp.get("access_token")
    if not access:
        return Response(HTTPStatus.BAD_GATEWAY, _safe_token_error(token_resp))

    # Pull a stable identifier from the user-info endpoint
    ureq = urllib.request.Request(
        p.userinfo_url,
        headers={"Authorization": f"Bearer {access}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(ureq, timeout=10) as r:
            userinfo = json.loads(r.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        return Response(HTTPStatus.BAD_GATEWAY, {"error": "userinfo_failed", "detail": str(exc)})

    user = str(userinfo.get("login") or userinfo.get("email") or userinfo.get("sub") or "oauth-user")

    # Issue our own HMAC session cookie so the rest of the app is provider-agnostic.
    cfg: Config = _CFG  # set by register_routes()
    cookie = auth_module.issue_cookie(cfg.secret, user=f"oauth:{name}:{user}")
    resp = Response(HTTPStatus.FOUND, {"ok": True, "user": user, "provider": name})
    resp.add_header(
        "Set-Cookie",
        auth_module.session_cookie_header(req, cookie),
    )
    resp.add_header("Location", "/")
    return resp


_CFG: Config | None = None  # populated by register_routes()


def register_routes(cfg: Config) -> Router:
    global _CFG
    _CFG = cfg
    fresh = Router()
    fresh.add("GET", "/api/auth/oauth/{provider}/start", _start)
    fresh.add("GET", "/api/auth/oauth/{provider}/callback", _callback)
    return fresh
