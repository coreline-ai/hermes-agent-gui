from __future__ import annotations

from api.pii import add_custom_pattern, redact_text


def test_kr_rrn_variants_redacted():
    samples = [
        "900101-1234567",
        "900101 1234567",
        "900101.1234567",
        "9001011234567",
        "001231-4234567",
    ]
    for sample in samples:
        out = redact_text(sample).text
        assert sample not in out
        assert "[REDACTED:kr_rrn]" in out


def test_credit_card_keeps_last_four():
    out = redact_text("card 4242 4242 4242 4242 please").text
    assert "4111" not in out[: out.find("****4242")]
    assert "****4242" in out


def test_custom_regex_and_redos_rejection():
    add_custom_pattern("ticket", r"TICKET-\d+")
    assert "[REDACTED:ticket]" in redact_text("see TICKET-123").text
    try:
        add_custom_pattern("bad", r"(a+)+$")
    except ValueError as exc:
        assert str(exc) == "redos_pattern_rejected"
    else:  # pragma: no cover
        raise AssertionError("expected redos rejection")


def test_pii_routes(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client("POST", "/api/pii/test", body={"text": "me@example.com"})
    assert status == 200
    assert body["redactions"][0]["kind"] == "email"
    status, body = client("POST", "/api/pii/patterns", body={"name": "secret", "pattern": r"SECRET-\d+"})
    assert status == 201
    status, body = client("POST", "/api/pii/patterns", body={"name": "bad", "pattern": r"(a+)+$"})
    assert status == 400
    assert body["error"] == "redos_pattern_rejected"
