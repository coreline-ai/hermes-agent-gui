"""MCP server registry — Phase 4 minimal.

Reads ``~/.hermes/mcp.json`` (B's pattern) or proxies the gateway's
``/v1/mcp/servers``. Writes go to the local JSON so the UI can register/
unregister servers without leaving the GUI.
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

LOCAL_MCP_FILE = Path.home() / ".hermes" / "mcp.json"


def _read_local() -> dict:
    if not LOCAL_MCP_FILE.exists():
        return {"servers": []}
    try:
        data = json.loads(LOCAL_MCP_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"servers": [], "error": "local_mcp_json_invalid"}
    return data if isinstance(data, dict) else {"servers": []}


def _write_local(data: dict) -> None:
    LOCAL_MCP_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_MCP_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _fetch_gateway(cfg: Config) -> dict | None:
    if not cfg.hermes_api_url:
        return None
    url = f"{cfg.hermes_api_url.rstrip('/')}/v1/mcp/servers"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    if cfg.hermes_api_token:
        req.add_header("Authorization", f"Bearer {cfg.hermes_api_token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        logger.debug("mcp gateway probe failed: %s", exc)
        return None


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("GET", "/api/mcp/servers")
    def _list(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        gw = _fetch_gateway(cfg)
        if gw is not None:
            return Response(HTTPStatus.OK, {"source": "gateway", **gw})
        return Response(HTTPStatus.OK, {"source": "local", **_read_local()})

    @router.route("POST", "/api/mcp/servers")
    def _add(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        try:
            body = req.json()
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
        name = str(body.get("name") or "").strip()
        command = body.get("command")
        if not name or not isinstance(command, list):
            return Response(HTTPStatus.BAD_REQUEST, {"error": "name_and_command_required"})
        data = _read_local()
        servers = data.setdefault("servers", [])
        servers = [s for s in servers if s.get("name") != name]
        servers.append({"name": name, "command": command, "env": body.get("env") or {}})
        data["servers"] = servers
        _write_local(data)
        return Response(HTTPStatus.CREATED, {"ok": True, "server": {"name": name}})

    @router.route("DELETE", "/api/mcp/servers/{name}")
    def _remove(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        name = req.params["name"]
        data = _read_local()
        before = len(data.get("servers", []))
        data["servers"] = [s for s in data.get("servers", []) if s.get("name") != name]
        if len(data["servers"]) == before:
            return Response(HTTPStatus.NOT_FOUND, {"error": "server_not_found"})
        _write_local(data)
        return Response(HTTPStatus.OK, {"ok": True})

    return router
