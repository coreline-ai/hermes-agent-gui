"""Small PKCE OAuth state manager for provider OAuth flows."""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from dataclasses import dataclass

STATE_TTL_SECONDS = 600
_STATES: dict[str, "OAuthState"] = {}


@dataclass(frozen=True)
class OAuthState:
    provider: str
    state: str
    code_verifier: str
    code_challenge: str
    created_at: float
    expires_at: float

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "state": self.state,
            "code_challenge": self.code_challenge,
            "code_challenge_method": "S256",
            "expires_at": int(self.expires_at),
        }


class OAuthStateError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def start_state(provider: str, *, now: float | None = None) -> OAuthState:
    ts = time.time() if now is None else now
    verifier = _b64url(secrets.token_bytes(32))
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    state = _b64url(secrets.token_bytes(24))
    item = OAuthState(provider, state, verifier, challenge, ts, ts + STATE_TTL_SECONDS)
    _STATES[state] = item
    return item


def consume_state(state: str, *, now: float | None = None) -> OAuthState:
    ts = time.time() if now is None else now
    item = _STATES.pop(state, None)
    if item is None:
        raise OAuthStateError("oauth_state_not_found")
    if ts > item.expires_at:
        raise OAuthStateError("oauth_state_expired")
    return item


def clear_states() -> None:
    _STATES.clear()
