from __future__ import annotations

from api.providers.oauth.pkce import OAuthStateError, clear_states, consume_state, start_state
from api.providers.oauth import nous_portal
from api.oauth import _safe_token_error


def test_oauth_pkce_state_expires_after_10_minutes():
    clear_states()
    state = start_state("nous_portal", now=1000)
    try:
        consume_state(state.state, now=1000 + 601)
    except OAuthStateError as exc:
        assert exc.code == "oauth_state_expired"
    else:  # pragma: no cover
        raise AssertionError("expected expiry")


def test_nous_portal_start_uses_s256_challenge():
    clear_states()
    payload = nous_portal.start(now=10)
    assert payload["code_challenge_method"] == "S256"
    assert payload["state"] in payload["authorization_url"]
    assert payload["code_challenge"] in payload["authorization_url"]


def test_oauth_token_error_redacts_token_like_fields():
    safe = _safe_token_error(
        {
            "error": "invalid_grant",
            "error_description": "bad code",
            "refresh_token": "secret-refresh-token",
            "access_token": "secret-access-token",
        }
    )

    assert safe["error"] == "token_response_invalid"
    assert safe["provider_error"] == "invalid_grant"
    assert safe["error_description"] == "bad code"
    assert "refresh_token" not in safe
    assert "access_token" not in safe
