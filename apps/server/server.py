#!/usr/bin/env python3
"""hermes-agent-gui — Python stdlib HTTP server (Phase 1).

- Phase 0 routes: GET /api/health
- Phase 1 routes: auth (password + token + cookie), oauth/passkeys stubs,
                  chat SSE (echo / gateway / embedded-detect runtime adapter).

Backend is framework-free (stdlib + pyyaml + cryptography).
"""

from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from api import (
    auth,
    chat,
    codegraph,
    cli_bridges,
    compression,
    config as config_mod,
    cron,
    dashboard,
    backup,
    brain,
    browser,
    debug_dump,
    health,
    mcp,
    marketplace,
    memory,
    memory_providers,
    messaging,
    oauth,
    pii,
    passkeys,
    persona,
    profile_archive,
    providers,
    pty as pty_mod,
    runtime_adapter,
    skills,
    slash_commands,
    tasks,
    telemetry,
    terminal,
    usage,
    workspace,
)
from api.router import Router, make_request
from api.sessions import SessionStore
from api.sessions.ops import register_routes as register_session_routes
from api.groups import register_routes as register_group_routes
from api.sessions.search import backfill_fts, register_routes as register_search_routes
from api.swarm import register_routes as register_swarm_routes

logger = logging.getLogger("hermes-agent-gui")

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_WEB_DIST = ROOT_DIR / "apps" / "web" / "dist"
WEB_DIST = Path(os.environ.get("HERMES_GUI_WEB_DIST", str(DEFAULT_WEB_DIST))).expanduser().resolve()


def build_router(cfg: config_mod.Config) -> Router:
    adapter = runtime_adapter.select(cfg)
    store = SessionStore()
    try:
        backfill_fts(store)
    except Exception:  # noqa: BLE001 -- FTS5 is best-effort at startup
        logger.exception("FTS5 backfill failed")
    root = Router()
    root.extend(health.register_routes(cfg, adapter.name))
    root.extend(auth.register_routes(cfg))
    root.extend(oauth.register_routes(cfg))
    root.extend(passkeys.register_routes(cfg))
    root.extend(profile_archive.register_routes(cfg))
    root.extend(providers.register_routes(cfg))
    root.extend(slash_commands.register_routes(cfg))
    root.extend(persona.register_routes(cfg))
    root.extend(usage.register_routes(cfg))
    root.extend(register_search_routes(cfg, store))
    root.extend(register_session_routes(cfg, store))
    root.extend(workspace.register_routes(cfg))
    root.extend(terminal.register_routes(cfg))
    root.extend(pty_mod.register_routes(cfg))
    root.extend(skills.register_routes(cfg))
    root.extend(mcp.register_routes(cfg))
    root.extend(memory.register_routes(cfg))
    root.extend(memory_providers.register_routes(cfg))
    root.extend(pii.register_routes(cfg))
    root.extend(compression.register_routes(cfg, store))
    root.extend(messaging.register_routes(cfg, adapter, store))
    root.extend(tasks.register_routes(cfg))
    root.extend(cron.register_routes(cfg))
    root.extend(dashboard.register_routes(cfg))
    root.extend(backup.register_routes(cfg))
    root.extend(debug_dump.register_routes(cfg))
    root.extend(brain.register_routes(cfg))
    root.extend(codegraph.register_routes(cfg))
    root.extend(browser.register_routes(cfg))
    root.extend(cli_bridges.register_routes(cfg))
    root.extend(marketplace.register_routes(cfg))
    root.extend(register_group_routes(cfg))
    root.extend(telemetry.register_routes(cfg))
    root.extend(register_swarm_routes(cfg))
    root.extend(chat.register_routes(cfg, adapter, store))
    return root


def make_handler(router: Router, web_dist: Path | None = None) -> type[BaseHTTPRequestHandler]:
    resolved_web_dist = (web_dist or WEB_DIST).expanduser().resolve()

    class Handler(BaseHTTPRequestHandler):
        server_version = "hermes-agent-gui/0.1.0-phase-1"
        web_dist = resolved_web_dist

        def _dispatch(self) -> None:
            req = make_request(self)

            # P3#15 global rate limit (before route resolution)
            throttled = telemetry.global_rate_limit(req)
            if throttled is not None:
                self._write_response(throttled)
                return

            resolved = router.resolve(req.method, req.path)
            if resolved is None:
                self._write_json(HTTPStatus.NOT_FOUND, {"error": "not_found", "path": req.path})
                return
            handler_fn, params = resolved
            req.params = params
            try:
                response = handler_fn(req)
            except Exception:  # noqa: BLE001 -- safety net at boundary
                logger.exception("handler error for %s %s", req.method, req.path)
                self._write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "internal_error"})
                return
            if response is None:
                # Streaming handler — it has already written the response.
                return
            self._write_response(response)

        def do_GET(self) -> None:  # noqa: N802
            path = urlsplit(self.path).path
            if not (path == "/api" or path.startswith("/api/")) and self._try_write_static(path):
                return
            self._dispatch()

        def do_HEAD(self) -> None:  # noqa: N802
            path = urlsplit(self.path).path
            if not (path == "/api" or path.startswith("/api/")) and self._try_write_static(path, head_only=True):
                return
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "not_found", "path": path}, head_only=True)

        do_POST = _dispatch    # noqa: N815
        do_DELETE = _dispatch  # noqa: N815
        do_PUT = _dispatch     # noqa: N815

        def _try_write_static(self, path: str, *, head_only: bool = False) -> bool:
            if not self.web_dist.is_dir():
                return False

            index = self.web_dist / "index.html"
            if path in ("/", "/index.html"):
                target = index
            else:
                rel = unquote(path).lstrip("/")
                if not rel:
                    target = index
                elif ".." in Path(rel).parts:
                    return False
                else:
                    target = (self.web_dist / rel).resolve()
                    try:
                        target.relative_to(self.web_dist)
                    except ValueError:
                        return False
                    if not target.is_file():
                        # SPA history fallback: /chat, /workspace, etc. serve index.html.
                        target = index

            if not target.is_file():
                return False
            self._write_static_file(target, head_only=head_only)
            return True

        def _write_static_file(self, path: Path, *, head_only: bool = False) -> None:
            payload = path.read_bytes()
            ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            rel_name = path.name
            if rel_name == "index.html":
                cache_control = "no-store"
            elif rel_name in {"sw.js", "registerSW.js", "manifest.webmanifest"} or path.suffix == ".html":
                cache_control = "no-cache"
            else:
                cache_control = "public, max-age=31536000, immutable"

            self.send_response(HTTPStatus.OK.value)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", cache_control)
            self._write_security_headers()
            self.end_headers()
            if payload and not head_only:
                self.wfile.write(payload)

        def _write_security_headers(self) -> None:
            # P3#15 security headers
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; "
                "connect-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "frame-ancestors 'none'; "
                "report-uri /api/csp-report",
            )
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
            self.send_header("X-Frame-Options", "DENY")

        def _write_response(self, response) -> None:
            body = response.body
            header_names = {k.lower() for k, _ in response.headers}
            if body is None:
                payload = b""
                ctype = None
            elif isinstance(body, (dict, list)):
                payload = json.dumps(body, separators=(",", ":")).encode("utf-8")
                ctype = "application/json; charset=utf-8"
            elif isinstance(body, str):
                payload = body.encode("utf-8")
                ctype = "text/plain; charset=utf-8"
            else:
                payload = bytes(body)
                ctype = "application/octet-stream"

            self.send_response(response.status.value)
            if ctype and "content-type" not in header_names:
                self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self._write_security_headers()
            for k, v in response.headers:
                self.send_header(k, v)
            self.end_headers()
            if payload:
                self.wfile.write(payload)

        def _write_json(self, status: HTTPStatus, body: dict, *, head_only: bool = False) -> None:
            payload = json.dumps(body, separators=(",", ":")).encode("utf-8")
            self.send_response(status.value)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self._write_security_headers()
            self.end_headers()
            if not head_only:
                self.wfile.write(payload)

        def log_message(self, fmt: str, *args) -> None:
            logger.info("%s - %s", self.address_string(), fmt % args)

    return Handler


def _enforce_fail_closed(cfg: config_mod.Config, host: str) -> None:
    is_remote_bind = host not in {"127.0.0.1", "localhost", "::1"}
    if is_remote_bind and not cfg.has_any_auth and not cfg.fail_open:
        logger.error(
            "Refusing to bind on %s without auth. Set HERMES_GUI_PASSWORD or "
            "HERMES_GUI_TOKEN, or pass HERMES_GUI_FAIL_OPEN=1 to override "
            "(NOT recommended for public exposure).",
            host,
        )
        sys.exit(2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hermes-agent-gui-server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8800)
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    cfg = config_mod.load()
    _enforce_fail_closed(cfg, args.host)

    router = build_router(cfg)
    handler_cls = make_handler(router)

    server = ThreadingHTTPServer((args.host, args.port), handler_cls)
    logger.info(
        "[hermes-agent-gui] listening on http://%s:%s (Phase 1) — auth=%s",
        args.host,
        args.port,
        "on" if cfg.has_any_auth else "OFF",
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("shutdown requested")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
