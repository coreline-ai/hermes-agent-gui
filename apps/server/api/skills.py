"""Skills catalog — Phase 4.

Talks to Hermes Agent gateway for the real list when ``HERMES_API_URL`` is set;
otherwise returns the local on-disk index at ``~/.hermes/skills`` (B's pattern).
Either way, the response shape is stable so the UI doesn't care.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from http import HTTPStatus
from pathlib import Path

from . import auth as auth_module
from .config import Config
from .router import Request, Response, Router

logger = logging.getLogger(__name__)


def _read_local_skills() -> list[dict]:
    root = Path.home() / ".hermes" / "skills"
    if not root.exists():
        return []
    items: list[dict] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        meta = {
            "id": child.name,
            "name": child.name,
            "origin": "local",
            "path": str(child),
        }
        readme = child / "SKILL.md"
        if readme.is_file():
            try:
                head = readme.read_text(encoding="utf-8").splitlines()[0:8]
                meta["description"] = "\n".join(head).strip()
            except OSError:
                pass
        items.append(meta)
    return sorted(items, key=lambda m: m["name"])


def _fetch_gateway_skills(cfg: Config) -> list[dict] | None:
    if not cfg.hermes_api_url:
        return None
    url = f"{cfg.hermes_api_url.rstrip('/')}/v1/skills"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    if cfg.hermes_api_token:
        req.add_header("Authorization", f"Bearer {cfg.hermes_api_token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("skills") if isinstance(data, dict) else data
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        logger.debug("skills gateway probe failed: %s", exc)
        return None


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("GET", "/api/skills")
    def _list(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        gw = _fetch_gateway_skills(cfg)
        if gw is not None:
            return Response(HTTPStatus.OK, {"source": "gateway", "skills": gw})
        return Response(HTTPStatus.OK, {"source": "local", "skills": _read_local_skills()})

    return router
