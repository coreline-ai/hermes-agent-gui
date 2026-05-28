"""SSE helper (Phase 1).

Pattern adapted from nesquena/hermes-webui's api/streaming.py:
- Treats stalled/closed clients as normal disconnects.
- Disables intermediate buffering (X-Accel-Buffering / Cache-Control).
- Emits ``event: ...\\ndata: ...\\n\\n`` framed records.
"""

from __future__ import annotations

import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Any, Iterable

logger = logging.getLogger(__name__)

CLIENT_DISCONNECT_ERRORS = (
    BrokenPipeError,
    ConnectionResetError,
    ConnectionAbortedError,
    TimeoutError,
    OSError,
)


def begin_sse(raw: BaseHTTPRequestHandler, *, status: HTTPStatus = HTTPStatus.OK) -> None:
    raw.send_response(status.value)
    raw.send_header("Content-Type", "text/event-stream; charset=utf-8")
    raw.send_header("Cache-Control", "no-store")
    raw.send_header("X-Accel-Buffering", "no")
    raw.send_header("Connection", "keep-alive")
    raw.send_header("X-Content-Type-Options", "nosniff")
    raw.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
    raw.send_header("X-Frame-Options", "DENY")
    raw.end_headers()


def write_event(raw: BaseHTTPRequestHandler, event: str, data: Any) -> bool:
    """Write one SSE record. Returns False if the client has disconnected."""
    payload = data if isinstance(data, str) else json.dumps(data, separators=(",", ":"))
    chunk = f"event: {event}\ndata: {payload}\n\n".encode("utf-8")
    try:
        raw.wfile.write(chunk)
        raw.wfile.flush()
        return True
    except CLIENT_DISCONNECT_ERRORS as exc:
        logger.debug("sse client disconnected during %s: %s", event, exc)
        return False


def stream_events(
    raw: BaseHTTPRequestHandler,
    events: Iterable[tuple[str, Any]],
    *,
    status: HTTPStatus = HTTPStatus.OK,
) -> None:
    """Iterate ``events`` and write each one. Aborts gracefully on disconnect."""
    begin_sse(raw, status=status)
    for event, data in events:
        if not write_event(raw, event, data):
            return
