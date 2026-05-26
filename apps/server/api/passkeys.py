"""WebAuthn passkey authentication — P1#4.

Minimal but standards-shaped implementation:
- Register: server emits challenge → client returns ``credential.create()`` ↑
  result → server stores credential id + COSE public key (CBOR).
- Authenticate: server emits challenge → client returns ``credential.get()``
  result → server verifies the signature against the stored public key.

Credentials are stored as JSON at ``~/.hermes-agent-gui/passkeys.json``.

Only ES256 (alg=-7) and RS256 (alg=-257) are accepted — these cover virtually
all platform / hardware authenticators in the field.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from http import HTTPStatus

from . import auth as auth_module
from .config import Config, STATE_DIR
from .router import Request, Response, Router

PASSKEY_FILE = STATE_DIR / "passkeys.json"
CHALLENGE_TTL = 5 * 60
_lock = threading.RLock()
_challenges: dict[str, dict] = {}


# ── storage ──────────────────────────────────────────────────────────────────


def _read_store() -> dict:
    if not PASSKEY_FILE.exists():
        return {"credentials": []}
    try:
        return json.loads(PASSKEY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"credentials": []}


def _write_store(data: dict) -> None:
    PASSKEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    PASSKEY_FILE.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    try:
        PASSKEY_FILE.chmod(0o600)
    except OSError:
        pass


# ── base64url ────────────────────────────────────────────────────────────────


def _b64u_enc(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def _b64u_dec(s: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
    except (binascii.Error, ValueError) as exc:
        raise ValueError("invalid_base64url") from exc


# ── helpers ──────────────────────────────────────────────────────────────────


def _rp_id(req: Request) -> str:
    return (req.headers.get("host") or "127.0.0.1:8800").split(":")[0]


def _origin(req: Request) -> str:
    proto = req.headers.get("x-forwarded-proto") or "http"
    host = req.headers.get("host") or "127.0.0.1:8800"
    return f"{proto}://{host}"


def _gc_challenges() -> None:
    now = time.time()
    with _lock:
        for k, v in list(_challenges.items()):
            if now - v["created_at"] > CHALLENGE_TTL:
                _challenges.pop(k, None)


# ── COSE key parsing (CBOR) ─────────────────────────────────────────────────


def _read_cbor_arg(buf: bytes, pos: int, minor: int) -> tuple[int, int]:
    """Read a CBOR additional-information integer and return ``(value, pos)``."""
    if minor < 24:
        return minor, pos
    widths = {24: 1, 25: 2, 26: 4, 27: 8}
    width = widths.get(minor)
    if width is None:
        raise ValueError("unsupported or indefinite CBOR length")
    if pos + width > len(buf):
        raise ValueError("truncated CBOR length")
    return int.from_bytes(buf[pos : pos + width], "big"), pos + width


def _parse_cose_key(cbor: bytes) -> dict:
    """Tiny bounded CBOR map decoder — enough for WebAuthn COSE public keys."""

    if not cbor:
        raise ValueError("empty CBOR")

    def _read_item(pos: int, depth: int = 0) -> tuple[object, int]:
        if depth > 8:
            raise ValueError("CBOR nesting too deep")
        if pos >= len(cbor):
            raise ValueError("truncated CBOR item")

        head = cbor[pos]
        pos += 1
        major = head >> 5
        minor = head & 0x1F
        arg, pos = _read_cbor_arg(cbor, pos, minor)

        if major == 0:  # unsigned int
            return arg, pos
        if major == 1:  # negative int: -1 - n
            return -1 - arg, pos
        if major == 2:  # bytes
            end = pos + arg
            if end > len(cbor):
                raise ValueError("truncated CBOR byte string")
            return cbor[pos:end], end
        if major == 3:  # text
            end = pos + arg
            if end > len(cbor):
                raise ValueError("truncated CBOR text string")
            return cbor[pos:end].decode("utf-8"), end
        if major == 5:  # map
            out: dict[object, object] = {}
            for _ in range(arg):
                key, pos = _read_item(pos, depth + 1)
                if not isinstance(key, (int, str)):
                    raise ValueError("unsupported CBOR map key type")
                value, pos = _read_item(pos, depth + 1)
                out[key] = value
            return out, pos

        raise ValueError(f"unsupported COSE CBOR major {major}")

    parsed, final_pos = _read_item(0)
    if final_pos != len(cbor):
        raise ValueError("trailing CBOR data")
    if not isinstance(parsed, dict):
        raise ValueError("expected CBOR map")
    return parsed


# ── verification ────────────────────────────────────────────────────────────


def _verify_signature(cose_key: dict, signed: bytes, signature: bytes) -> bool:
    """Verify ECDSA (ES256) or RSA (RS256) signature."""
    alg = cose_key.get(3)
    try:
        from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa  # type: ignore
        from cryptography.hazmat.primitives import hashes  # type: ignore
        from cryptography.hazmat.backends import default_backend  # type: ignore
    except ImportError:  # pragma: no cover
        return False

    try:
        if alg == -7:  # ES256 — P-256 + SHA-256
            x = int.from_bytes(cose_key[-2], "big")
            y = int.from_bytes(cose_key[-3], "big")
            pub_numbers = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1())
            pubkey = pub_numbers.public_key(default_backend())
            # WebAuthn ECDSA signatures are DER-encoded.
            pubkey.verify(signature, signed, ec.ECDSA(hashes.SHA256()))
            return True
        if alg == -257:  # RS256
            n = int.from_bytes(cose_key[-1], "big")
            e = int.from_bytes(cose_key[-2], "big")
            pub = rsa.RSAPublicNumbers(e, n).public_key(default_backend())
            pub.verify(signature, signed, padding.PKCS1v15(), hashes.SHA256())
            return True
    except Exception:
        return False
    return False


# ── routes ──────────────────────────────────────────────────────────────────


router = Router()
_CFG: Config | None = None


@router.route("POST", "/api/auth/passkey/register/begin")
def _register_begin(req: Request) -> Response:
    cfg = _CFG
    if cfg is None or auth_module.authenticate(req, cfg) is None:
        return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
    _gc_challenges()
    challenge = secrets.token_bytes(32)
    cid = _b64u_enc(challenge)
    with _lock:
        _challenges[cid] = {"kind": "register", "challenge": challenge, "created_at": time.time()}
    rp_id = _rp_id(req)
    return Response(
        HTTPStatus.OK,
        {
            "publicKey": {
                "challenge": cid,
                "rp": {"id": rp_id, "name": "Hermes Agent GUI"},
                "user": {
                    "id": _b64u_enc(b"local-user"),
                    "name": "local",
                    "displayName": "local",
                },
                "pubKeyCredParams": [
                    {"type": "public-key", "alg": -7},
                    {"type": "public-key", "alg": -257},
                ],
                "timeout": 60_000,
                "attestation": "none",
                "authenticatorSelection": {
                    "residentKey": "preferred",
                    "userVerification": "preferred",
                },
            }
        },
    )


@router.route("POST", "/api/auth/passkey/register/finish")
def _register_finish(req: Request) -> Response:
    cfg = _CFG
    if cfg is None or auth_module.authenticate(req, cfg) is None:
        return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
    try:
        body = req.json()
    except ValueError:
        return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})

    raw_id = str(body.get("rawId") or "")
    att = body.get("response") or {}
    client_data_b64 = str(att.get("clientDataJSON") or "")
    att_object_b64 = str(att.get("attestationObject") or "")
    if not (raw_id and client_data_b64 and att_object_b64):
        return Response(HTTPStatus.BAD_REQUEST, {"error": "missing_fields"})

    try:
        client_data = json.loads(_b64u_dec(client_data_b64))
    except (ValueError, json.JSONDecodeError):
        return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_clientData"})

    challenge_b64 = client_data.get("challenge")
    with _lock:
        pending = _challenges.pop(challenge_b64 or "", None)
    if not pending or pending["kind"] != "register":
        return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_challenge"})
    if client_data.get("type") != "webauthn.create":
        return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_type"})
    if client_data.get("origin") != _origin(req):
        return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_origin"})

    try:
        # attestationObject is CBOR — we want authData.cred public key.
        att_obj = _b64u_dec(att_object_b64)
    except ValueError:
        return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_attestation_object"})
    # The first map key is usually "fmt" or "authData"; we locate authData and parse it.
    # A robust CBOR parser is over-engineered for Phase 1; we use a heuristic search.
    needle = b"authData"
    idx = att_obj.find(needle)
    if idx < 0:
        return Response(HTTPStatus.BAD_REQUEST, {"error": "no_authData"})
    if idx + len(needle) >= len(att_obj):
        return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_attestation_object"})
    # Next bytes should be a CBOR byte string header (major 2). Find the length.
    head = att_obj[idx + len(needle)]
    if head >> 5 != 2:
        return Response(HTTPStatus.BAD_REQUEST, {"error": "authData_not_bytes"})
    try:
        length, pos = _read_cbor_arg(att_obj, idx + len(needle) + 1, head & 0x1F)
    except ValueError as exc:
        return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_authData_length", "detail": str(exc)})
    if pos + length > len(att_obj):
        return Response(HTTPStatus.BAD_REQUEST, {"error": "authData_truncated"})

    auth_data = att_obj[pos : pos + length]
    # authData layout: rpIdHash(32) | flags(1) | counter(4) | (attestedCredData?)
    # attestedCredData: aaguid(16) | credIdLen(2) | credId | COSE pub key (CBOR)
    if len(auth_data) < 55:
        return Response(HTTPStatus.BAD_REQUEST, {"error": "authData_too_short"})
    rp_hash = hashlib.sha256(_rp_id(req).encode()).digest()
    if not hmac.compare_digest(auth_data[:32], rp_hash):
        return Response(HTTPStatus.BAD_REQUEST, {"error": "rpIdHash_mismatch"})
    cred_id_len = int.from_bytes(auth_data[53:55], "big")
    if 55 + cred_id_len > len(auth_data):
        return Response(HTTPStatus.BAD_REQUEST, {"error": "credential_data_truncated"})
    cred_id = auth_data[55 : 55 + cred_id_len]
    cose_cbor = auth_data[55 + cred_id_len :]
    if not cose_cbor:
        return Response(HTTPStatus.BAD_REQUEST, {"error": "missing_cose_key"})
    try:
        cose_key = _parse_cose_key(cose_cbor)
    except ValueError as exc:
        return Response(HTTPStatus.BAD_REQUEST, {"error": "cose_parse_failed", "detail": str(exc)})
    alg = cose_key.get(3)
    if alg not in (-7, -257):
        return Response(HTTPStatus.BAD_REQUEST, {"error": "unsupported_alg", "alg": alg})

    store = _read_store()
    store["credentials"].append(
        {
            "id": _b64u_enc(cred_id),
            "raw_id_b64": raw_id,
            "cose_key_b64": _b64u_enc(cose_cbor),
            "alg": alg,
            "created_at": int(time.time()),
        }
    )
    _write_store(store)
    return Response(HTTPStatus.CREATED, {"ok": True, "id": _b64u_enc(cred_id)})


@router.route("POST", "/api/auth/passkey/authenticate/begin")
def _auth_begin(req: Request) -> Response:
    del req
    cfg = _CFG
    if cfg is None:
        return Response(HTTPStatus.NOT_IMPLEMENTED, {"error": "passkey_not_configured"})
    _gc_challenges()
    store = _read_store()
    if not store.get("credentials"):
        return Response(HTTPStatus.NOT_FOUND, {"error": "no_passkeys_registered"})
    challenge = secrets.token_bytes(32)
    cid = _b64u_enc(challenge)
    with _lock:
        _challenges[cid] = {"kind": "auth", "challenge": challenge, "created_at": time.time()}
    return Response(
        HTTPStatus.OK,
        {
            "publicKey": {
                "challenge": cid,
                "timeout": 60_000,
                "userVerification": "preferred",
                "allowCredentials": [
                    {"type": "public-key", "id": c["id"]} for c in store["credentials"]
                ],
            }
        },
    )


@router.route("POST", "/api/auth/passkey/authenticate/finish")
def _auth_finish(req: Request) -> Response:
    cfg = _CFG
    if cfg is None:
        return Response(HTTPStatus.NOT_IMPLEMENTED, {"error": "passkey_not_configured"})
    try:
        body = req.json()
    except ValueError:
        return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})

    raw_id = str(body.get("rawId") or "")
    resp = body.get("response") or {}
    client_data_b64 = str(resp.get("clientDataJSON") or "")
    auth_data_b64 = str(resp.get("authenticatorData") or "")
    signature_b64 = str(resp.get("signature") or "")
    if not all([raw_id, client_data_b64, auth_data_b64, signature_b64]):
        return Response(HTTPStatus.BAD_REQUEST, {"error": "missing_fields"})

    try:
        client_data_bytes = _b64u_dec(client_data_b64)
        client_data = json.loads(client_data_bytes)
    except (ValueError, json.JSONDecodeError):
        return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_clientData"})

    challenge_b64 = client_data.get("challenge")
    with _lock:
        pending = _challenges.pop(challenge_b64 or "", None)
    if not pending or pending["kind"] != "auth":
        return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_challenge"})
    if client_data.get("type") != "webauthn.get":
        return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_type"})
    if client_data.get("origin") != _origin(req):
        return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_origin"})

    store = _read_store()
    cred = next((c for c in store.get("credentials", []) if c["id"] == raw_id), None)
    if cred is None:
        return Response(HTTPStatus.NOT_FOUND, {"error": "unknown_credential"})

    try:
        auth_data_bytes = _b64u_dec(auth_data_b64)
    except ValueError:
        return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_authenticatorData"})
    signed = auth_data_bytes + hashlib.sha256(client_data_bytes).digest()
    try:
        cose_key = _parse_cose_key(_b64u_dec(cred["cose_key_b64"]))
    except ValueError as exc:
        return Response(HTTPStatus.BAD_REQUEST, {"error": "cose_parse_failed", "detail": str(exc)})
    try:
        signature = _b64u_dec(signature_b64)
    except ValueError:
        return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_signature"})
    if not _verify_signature(cose_key, signed, signature):
        return Response(HTTPStatus.UNAUTHORIZED, {"error": "signature_invalid"})

    cookie = auth_module.issue_cookie(cfg.secret, user="passkey:local")
    resp_obj = Response(HTTPStatus.OK, {"ok": True})
    resp_obj.add_header(
        "Set-Cookie",
        f"{auth_module.COOKIE_NAME}={cookie}; Path=/; HttpOnly; SameSite=Lax; "
        f"Max-Age={auth_module.SESSION_TTL_SECONDS}",
    )
    return resp_obj


def register_routes(cfg: Config) -> Router:
    global _CFG
    _CFG = cfg
    return router


# ``os`` is intentionally imported for future PASSKEY_RP_ID env override.
_ = os
