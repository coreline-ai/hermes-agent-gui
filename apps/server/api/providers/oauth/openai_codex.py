from __future__ import annotations

from .pkce import consume_state, start_state

PROVIDER = "openai_codex"
AUTH_URL = "https://auth.openai.com/oauth/authorize"


def start(now: float | None = None) -> dict:
    state = start_state(PROVIDER, now=now)
    return {**state.to_dict(), "authorization_url": f"{AUTH_URL}?response_type=code&state={state.state}&code_challenge={state.code_challenge}&code_challenge_method=S256"}


def complete(state: str, now: float | None = None) -> dict:
    item = consume_state(state, now=now)
    return {"provider": item.provider, "ok": True}
