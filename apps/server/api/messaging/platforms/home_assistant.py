"""Direct Home Assistant notify runtime — Phase 15b."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from http import HTTPStatus
from urllib.parse import urlsplit

from .. import credentials, status
from ..registry import REGISTRY
from .base import CredentialError, DelegatedPlatform, validate_credentials

platform = DelegatedPlatform(REGISTRY["home_assistant"])


@dataclass(frozen=True)
class NotifyResult:
    status: HTTPStatus
    body: dict


def _service_path(notify_service: str) -> str:
    if "." in notify_service:
        domain, service = notify_service.split(".", 1)
    else:
        domain, service = "notify", notify_service
    return f"/api/services/{domain}/{service}"


def _validate_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise CredentialError("ha_url", "ha_url must be an http(s) URL")


def notify(creds: dict[str, str], *, title: str, message: str) -> NotifyResult:
    validate_credentials(REGISTRY["home_assistant"], creds)
    ha_url = creds["ha_url"].rstrip("/")
    _validate_url(ha_url)
    token = creds["long_lived_token"]
    notify_service = creds["notify_service"]
    path = _service_path(notify_service)
    body = json.dumps({"title": title, "message": message}).encode("utf-8")
    req = urllib.request.Request(
        ha_url + path,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw) if raw else {}
            status.record_event("home_assistant", connected=True, error=None)
            return NotifyResult(
                HTTPStatus.OK,
                {"ok": True, "platform": "home_assistant", "status_code": resp.status, "response": parsed},
            )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        status.record_status("home_assistant", configured=True, connected=False, last_error=detail or str(exc))
        return NotifyResult(
            HTTPStatus.BAD_GATEWAY,
            {"error": "platform_unreachable", "status_code": exc.code, "detail": detail or str(exc)},
        )
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        status.record_status("home_assistant", configured=True, connected=False, last_error=str(exc))
        return NotifyResult(HTTPStatus.BAD_GATEWAY, {"error": "platform_unreachable", "detail": str(exc)})
    except json.JSONDecodeError as exc:
        status.record_status("home_assistant", configured=True, connected=False, last_error=str(exc))
        return NotifyResult(HTTPStatus.BAD_GATEWAY, {"error": "platform_unreachable", "detail": f"invalid JSON: {exc}"})


def test_connection() -> NotifyResult:
    creds = credentials.read_platform_credentials("home_assistant")
    return notify(creds, title="Hermes Agent GUI", message="Home Assistant notification test")
