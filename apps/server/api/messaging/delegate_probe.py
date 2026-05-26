"""Hermes Agent delegated messaging test probe."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from http import HTTPStatus

from ..config import Config


@dataclass(frozen=True)
class ProbeResult:
    status: HTTPStatus
    body: dict


def test_connection(cfg: Config, platform: str) -> ProbeResult:
    if not cfg.hermes_api_url:
        return ProbeResult(
            HTTPStatus.SERVICE_UNAVAILABLE,
            {
                "error": "hermes_agent_not_running",
                "detail": "Delegated messaging platforms require HERMES_API_URL / a running Hermes Agent.",
            },
        )

    url = f"{cfg.hermes_api_url.rstrip('/')}/v1/messaging/test/{platform}"
    req = urllib.request.Request(url, data=b"{}", method="POST", headers={"Content-Type": "application/json"})
    if cfg.hermes_api_token:
        req.add_header("Authorization", f"Bearer {cfg.hermes_api_token}")
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
            payload.setdefault("ok", True)
            payload.setdefault("latency_ms", int((time.monotonic() - started) * 1000))
            payload.setdefault("test_kind", "delegated")
            return ProbeResult(HTTPStatus.OK, payload)
    except TimeoutError:
        return ProbeResult(HTTPStatus.GATEWAY_TIMEOUT, {"error": "test_timeout"})
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        return ProbeResult(
            HTTPStatus.BAD_GATEWAY,
            {"error": "platform_unreachable", "detail": detail or str(exc)},
        )
    except (urllib.error.URLError, OSError) as exc:
        return ProbeResult(
            HTTPStatus.SERVICE_UNAVAILABLE,
            {"error": "hermes_agent_not_running", "detail": str(exc)},
        )
    except json.JSONDecodeError as exc:
        return ProbeResult(HTTPStatus.BAD_GATEWAY, {"error": "platform_unreachable", "detail": f"invalid JSON: {exc}"})
