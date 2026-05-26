"""PII redaction policy and HTTP helpers — Phase 19."""

from __future__ import annotations

import re
from dataclasses import dataclass
from http import HTTPStatus

from . import auth as auth_module
from .config import Config
from .router import Request, Response, Router


@dataclass(frozen=True)
class Redaction:
    kind: str
    count: int


@dataclass(frozen=True)
class RedactionResult:
    text: str
    redactions: list[Redaction]

    @property
    def changed(self) -> bool:
        return bool(self.redactions)

    def to_dict(self) -> dict:
        return {"text": self.text, "redactions": [{"kind": r.kind, "count": r.count} for r in self.redactions]}


_PATTERNS: list[tuple[str, re.Pattern[str], str | None]] = [
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED:ssn]"),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED:email]"),
    ("kr_rrn", re.compile(r"(?<!\d)\d{6}[ .-]?[1-4]\d{6}(?!\d)"), "[REDACTED:kr_rrn]"),
    ("phone", re.compile(r"(?<!\d)(?:\+?\d{1,3}[ .-]?)?(?:\(?\d{2,4}\)?[ .-]?)\d{3,4}[ .-]?\d{4}(?!\d)"), "[REDACTED:phone]"),
    ("iban", re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"), "[REDACTED:iban]"),
    ("ipv4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[REDACTED:ip]"),
    ("access_token", re.compile(r"\b(?:sk|pk|ghp|xoxb|xoxp)_[A-Za-z0-9_\-]{16,}\b|\bsk-[A-Za-z0-9_\-]{16,}\b"), "[REDACTED:token]"),
]
_CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
_CUSTOM: list[tuple[str, re.Pattern[str]]] = []


def _luhn_ok(digits: str) -> bool:
    total = 0
    alt = False
    for ch in reversed(digits):
        n = ord(ch) - 48
        if alt:
            n *= 2
            if n > 9:
                n -= 9
        total += n
        alt = not alt
    return total % 10 == 0


def _redact_cards(text: str) -> tuple[str, int]:
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        raw = match.group(0)
        digits = re.sub(r"\D", "", raw)
        if len(digits) < 13 or len(digits) > 19 or not _luhn_ok(digits):
            return raw
        count += 1
        return f"[REDACTED:card:****{digits[-4:]}]"

    return _CARD_RE.sub(repl, text), count


def _is_safe_regex(pattern: str) -> bool:
    if len(pattern) > 256:
        return False
    risky = ("+)+", "*)+", "{1,")
    if any(token in pattern for token in risky):
        return False
    try:
        re.compile(pattern)
    except re.error:
        return False
    return True


def add_custom_pattern(name: str, pattern: str) -> None:
    clean_name = re.sub(r"[^A-Za-z0-9_.-]", "_", name.strip() or "custom")[:40]
    if not _is_safe_regex(pattern):
        raise ValueError("redos_pattern_rejected")
    _CUSTOM.append((clean_name, re.compile(pattern)))


def redact_text(text: str) -> RedactionResult:
    out = str(text)
    redactions: list[Redaction] = []
    out, card_count = _redact_cards(out)
    if card_count:
        redactions.append(Redaction("card", card_count))
    for kind, pattern, replacement in _PATTERNS:
        out, count = pattern.subn(replacement or f"[REDACTED:{kind}]", out)
        if count:
            redactions.append(Redaction(kind, count))
    for kind, pattern in _CUSTOM:
        out, count = pattern.subn(f"[REDACTED:{kind}]", out)
        if count:
            redactions.append(Redaction(kind, count))
    return RedactionResult(out, redactions)


def redact_message(message: dict) -> tuple[dict, list[dict]]:
    content = message.get("content")
    if not isinstance(content, str):
        return dict(message), []
    result = redact_text(content)
    if not result.changed:
        return dict(message), []
    redacted = dict(message)
    redacted["content"] = result.text
    return redacted, [{"kind": r.kind, "count": r.count} for r in result.redactions]


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("POST", "/api/pii/test")
    def _test(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            body = req.json()
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
        return Response(HTTPStatus.OK, redact_text(str(body.get("text") or "")).to_dict())

    @router.route("POST", "/api/pii/patterns")
    def _pattern(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            body = req.json()
            add_custom_pattern(str(body.get("name") or "custom"), str(body.get("pattern") or ""))
        except ValueError as exc:
            return Response(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        return Response(HTTPStatus.CREATED, {"ok": True, "custom_patterns": len(_CUSTOM)})

    return router
