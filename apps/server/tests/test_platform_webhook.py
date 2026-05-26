import hmac
import json
from hashlib import sha256


def _signed_headers(secret: str, body: dict) -> dict:
    raw = json.dumps(body).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), raw, sha256).hexdigest()
    return {"X-Hermes-Signature": f"sha256={sig}"}


def _configure_webhook(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, body = client("POST", "/api/messaging/webhook/configure", body={})
    assert status == 200
    assert body["platform"] == "webhook"
    assert body["token"]
    assert body["signing_secret"]
    assert f"/api/messaging/webhook/{body['token']}/inbound" in body["inbound_url"]
    return body


def test_webhook_registration_issues_secret_url(client):
    reg = _configure_webhook(client)
    status, body = client("POST", "/api/messaging/webhook/test", body={})
    assert status == 200
    assert body["token"] == reg["token"]
    assert body["signing_secret"] == reg["signing_secret"]


def test_webhook_valid_signature_invokes_chat(client):
    reg = _configure_webhook(client)
    payload = {"text": "hello webhook"}
    status, body = client(
        "POST",
        f"/api/messaging/webhook/{reg['token']}/inbound",
        body=payload,
        headers=_signed_headers(reg["signing_secret"], payload),
    )
    assert status == 200
    assert body["ok"] is True
    assert body["platform"] == "webhook"
    assert body["response"] == "hello webhook"
    assert body["done"]["adapter"] == "echo"


def test_webhook_bad_signature_rejected(client):
    reg = _configure_webhook(client)
    status, body = client(
        "POST",
        f"/api/messaging/webhook/{reg['token']}/inbound",
        body={"text": "hello"},
        headers={"X-Hermes-Signature": "sha256:bad"},
    )
    assert status == 401
    assert body["error"] == "webhook_signature_invalid"


def test_webhook_payload_too_large(client):
    reg = _configure_webhook(client)
    payload = {"text": "x" * (256 * 1024)}
    status, body = client(
        "POST",
        f"/api/messaging/webhook/{reg['token']}/inbound",
        body=payload,
        headers=_signed_headers(reg["signing_secret"], payload),
    )
    assert status == 413
    assert body["error"] == "payload_too_large"


def test_webhook_rate_limit(client):
    reg = _configure_webhook(client)
    payload = {"text": "x"}
    headers = _signed_headers(reg["signing_secret"], payload)
    last_status = 200
    last_body = {}
    for _ in range(61):
        last_status, last_body = client(
            "POST",
            f"/api/messaging/webhook/{reg['token']}/inbound",
            body=payload,
            headers=headers,
        )
    assert last_status == 429
    assert last_body["error"] == "rate_limited"
