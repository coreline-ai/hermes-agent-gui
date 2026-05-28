"""Input validation helpers for small stdlib HTTP routes."""

from __future__ import annotations

import base64
import binascii
from http import HTTPStatus
from typing import Any

from .router import Response


class ValidationError(ValueError):
    """User-correctable request validation error."""

    def __init__(self, code: str, *, field: str, detail: str | None = None, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        super().__init__(detail or code)
        self.code = code
        self.field = field
        self.detail = detail or code
        self.status = status


def validation_response(exc: ValidationError) -> Response:
    return Response(exc.status, {"error": exc.code, "field": exc.field, "detail": exc.detail})


def parse_bounded_int(
    value: Any,
    *,
    field: str,
    default: int,
    min_value: int,
    max_value: int,
) -> int:
    """Parse an integer field and clamp only by rejecting out-of-range values."""

    raw = default if value in (None, "") else value
    try:
        parsed = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError("invalid_int", field=field, detail=f"{field} must be an integer") from exc
    if parsed < min_value or parsed > max_value:
        raise ValidationError(
            "int_out_of_range",
            field=field,
            detail=f"{field} must be between {min_value} and {max_value}",
        )
    return parsed


def decode_base64_field(value: str, *, field: str = "b64", max_bytes: int | None = None) -> bytes:
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValidationError("invalid_base64", field=field, detail=f"{field} must be valid base64") from exc
    if max_bytes is not None and len(decoded) > max_bytes:
        raise ValidationError(
            "payload_too_large",
            field=field,
            detail=f"{field} decoded payload exceeds {max_bytes} bytes",
            status=HTTPStatus.PAYLOAD_TOO_LARGE,
        )
    return decoded
