#!/usr/bin/env python3
"""Phase 11 — single-file deploy mode (C's pyrate-llama/hermes-ui pattern).

Serves both the API (delegated to server.py) and the single HTML produced by
``pnpm --filter @hermes-agent-gui/web build:singlefile``. By default this
serves the emitted ``apps/web/dist/index.html``::

    python3 serve_singlefile.py --port 8800
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from api import config as config_mod              # noqa: E402
from api.router import make_request               # noqa: E402

from server import build_router, make_handler, _enforce_fail_closed  # noqa: E402

logger = logging.getLogger("hermes-agent-gui")

ROOT = HERE.parents[1]
DEFAULT_HTML = Path(
    os.environ.get("HERMES_GUI_SINGLEFILE_HTML", str(ROOT / "apps" / "web" / "dist" / "index.html"))
).expanduser()


def _wrap_handler(router, html_path: Path, cfg=None):
    base = make_handler(router, cfg=cfg, allow_inline_assets=True)

    class SingleFileHandler(base):  # type: ignore[misc]
        def do_GET(self):  # noqa: N802
            path = urlsplit(self.path).path
            if path in ("/", "/index.html") or not path.startswith("/api/"):
                if html_path.is_file():
                    body = html_path.read_bytes()
                    self.send_response(HTTPStatus.OK.value)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self._write_security_headers()
                    self.end_headers()
                    self.wfile.write(body)
                    return
                payload = json.dumps(
                    {
                        "error": "singlefile_html_missing",
                        "path": str(html_path),
                        "hint": "Run pnpm --filter @hermes-agent-gui/web build:singlefile",
                    },
                    separators=(",", ":"),
                ).encode("utf-8")
                self.send_response(HTTPStatus.SERVICE_UNAVAILABLE.value)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self._write_security_headers()
                self.end_headers()
                self.wfile.write(payload)
                return
            return base.do_GET(self)  # type: ignore[misc]

    return SingleFileHandler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hermes-agent-gui-singlefile")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8800)
    parser.add_argument("--html", default=str(DEFAULT_HTML))
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    cfg = config_mod.load()
    _enforce_fail_closed(cfg, args.host)
    router = build_router(cfg)
    handler = _wrap_handler(router, Path(args.html), cfg)
    srv = ThreadingHTTPServer((args.host, args.port), handler)
    logger.info("[hermes-agent-gui · singlefile] http://%s:%s · html=%s", args.host, args.port, args.html)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

# silence vulture on `make_request` re-export
_ = make_request
