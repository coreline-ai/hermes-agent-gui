"""Real PTY backend — P1#5.

stdlib HTTP doesn't speak WebSocket, so this uses a hybrid scheme:

  POST   /api/pty                       -> create PTY session, returns id
  GET    /api/pty/{sid}/stream          -> SSE stream of base64-encoded chunks
  POST   /api/pty/{sid}/input           -> {"data": "..."} forwards bytes to the PTY
  POST   /api/pty/{sid}/resize          -> {"cols": int, "rows": int}
  DELETE /api/pty/{sid}                 -> kill + close

Output is base64-encoded so xterm.js can feed it raw to ``term.write()`` after
``atob()`` — this matches the wire format A's terminal-panel uses.
"""

from __future__ import annotations

import base64
import logging
import os
import pty
import select
import signal
import struct
import termios
import threading
import time
import uuid
from dataclasses import dataclass, field
from fcntl import ioctl
from http import HTTPStatus

from . import auth as auth_module
from . import exec_policy
from . import streaming
from .config import Config
from .router import Request, Response, Router
from .workspace import _safe_path

logger = logging.getLogger(__name__)

DEFAULT_SHELL = os.environ.get("SHELL") or "/bin/sh"
PTY_MAX_OUTPUT_BUFFER = 256 * 1024
PTY_IDLE_TIMEOUT_SECONDS = 60 * 30  # auto-kill after 30 min idle


@dataclass
class PtySession:
    id: str
    pid: int
    fd: int
    cwd: str
    cmd: list[str]
    created_at: float
    last_activity: float
    buffer: bytearray = field(default_factory=bytearray)
    cond: threading.Condition = field(default_factory=threading.Condition)
    closed: bool = False


_sessions: dict[str, PtySession] = {}
_sessions_lock = threading.RLock()


def _spawn(cmd: list[str], cwd: str | None) -> PtySession:
    pid, fd = pty.fork()
    if pid == 0:
        # child
        try:
            if cwd:
                os.chdir(cwd)
        except OSError:
            pass
        env = os.environ.copy()
        env.setdefault("TERM", "xterm-256color")
        os.execvpe(cmd[0], cmd, env)
        os._exit(127)
    sess = PtySession(
        id=uuid.uuid4().hex[:12],
        pid=pid,
        fd=fd,
        cwd=cwd or os.getcwd(),
        cmd=cmd,
        created_at=time.time(),
        last_activity=time.time(),
    )
    with _sessions_lock:
        _sessions[sess.id] = sess
    threading.Thread(target=_pump, args=(sess,), daemon=True, name=f"pty-{sess.id}").start()
    return sess


def _pump(sess: PtySession) -> None:
    """Read from the PTY into the session buffer; wake waiters on each chunk."""
    try:
        while not sess.closed:
            try:
                ready, _, _ = select.select([sess.fd], [], [], 0.5)
            except (OSError, ValueError):
                break
            if not ready:
                # idle-timeout reaper
                if time.time() - sess.last_activity > PTY_IDLE_TIMEOUT_SECONDS:
                    logger.info("pty %s idle timeout — closing", sess.id)
                    _close(sess.id)
                    return
                continue
            try:
                data = os.read(sess.fd, 4096)
            except OSError:
                break
            if not data:
                break
            with sess.cond:
                sess.last_activity = time.time()
                sess.buffer.extend(data)
                # Hard cap to prevent runaway memory if no readers.
                if len(sess.buffer) > PTY_MAX_OUTPUT_BUFFER:
                    del sess.buffer[: len(sess.buffer) - PTY_MAX_OUTPUT_BUFFER]
                sess.cond.notify_all()
    finally:
        _close(sess.id)


def _close(sid: str) -> bool:
    with _sessions_lock:
        sess = _sessions.pop(sid, None)
    if sess is None:
        return False
    sess.closed = True
    try:
        os.kill(sess.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        os.close(sess.fd)
    except OSError:
        pass
    with sess.cond:
        sess.cond.notify_all()
    return True


def _resize(sess: PtySession, cols: int, rows: int) -> None:
    try:
        ioctl(sess.fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    except OSError as exc:
        logger.debug("pty %s resize failed: %s", sess.id, exc)


# ── routes ──────────────────────────────────────────────────────────────────


def register_routes(cfg: Config) -> Router:
    router = Router()

    @router.route("POST", "/api/pty")
    def _create(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        if (blocked := exec_policy.require_exec(req, cfg)) is not None:
            return blocked
        try:
            body = req.json()
        except ValueError:
            body = {}
        cmd_raw = body.get("cmd") or DEFAULT_SHELL
        if isinstance(cmd_raw, str):
            argv = [cmd_raw, "-i"]
        elif isinstance(cmd_raw, list) and cmd_raw:
            argv = [str(x) for x in cmd_raw]
        else:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_cmd"})
        try:
            cwd = str(_safe_path(str(body.get("cwd") or ".")))
        except ValueError as exc:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "bad_cwd", "detail": str(exc)})
        try:
            sess = _spawn(argv, cwd)
        except FileNotFoundError as exc:
            return Response(HTTPStatus.NOT_FOUND, {"error": "binary_not_found", "detail": str(exc)})
        except OSError as exc:
            return Response(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "fork_failed", "detail": str(exc)})
        return Response(HTTPStatus.CREATED, {"id": sess.id, "pid": sess.pid, "cwd": sess.cwd})

    @router.route("GET", "/api/pty/{sid}/stream")
    def _stream(req: Request):
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        if (blocked := exec_policy.require_exec(req, cfg)) is not None:
            return blocked
        sid = req.params["sid"]
        with _sessions_lock:
            sess = _sessions.get(sid)
        if sess is None:
            return Response(HTTPStatus.NOT_FOUND, {"error": "pty_not_found"})
        streaming.begin_sse(req.raw)
        if not streaming.write_event(req.raw, "ready", {"id": sid}):
            return None
        cursor = 0
        try:
            while not sess.closed:
                with sess.cond:
                    if cursor >= len(sess.buffer):
                        sess.cond.wait(timeout=15.0)
                    chunk = bytes(sess.buffer[cursor:])
                    cursor = len(sess.buffer)
                if chunk:
                    ok = streaming.write_event(req.raw, "data", {"b64": base64.b64encode(chunk).decode("ascii")})
                    if not ok:
                        return None
                else:
                    if not streaming.write_event(req.raw, "ping", {"ts": int(time.time())}):
                        return None
            streaming.write_event(req.raw, "exit", {"id": sid})
        except (BrokenPipeError, ConnectionResetError):
            pass
        return None

    @router.route("POST", "/api/pty/{sid}/input")
    def _input(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        if (blocked := exec_policy.require_exec(req, cfg)) is not None:
            return blocked
        sid = req.params["sid"]
        with _sessions_lock:
            sess = _sessions.get(sid)
        if sess is None or sess.closed:
            return Response(HTTPStatus.NOT_FOUND, {"error": "pty_not_found"})
        try:
            body = req.json()
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
        data = body.get("data")
        b64 = body.get("b64")
        if isinstance(data, str):
            payload = data.encode("utf-8")
        elif isinstance(b64, str):
            payload = base64.b64decode(b64)
        else:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "data_or_b64_required"})
        try:
            os.write(sess.fd, payload)
            sess.last_activity = time.time()
        except OSError as exc:
            return Response(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "write_failed", "detail": str(exc)})
        return Response(HTTPStatus.OK, {"bytes": len(payload)})

    @router.route("POST", "/api/pty/{sid}/resize")
    def _do_resize(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        if (blocked := exec_policy.require_exec(req, cfg)) is not None:
            return blocked
        sid = req.params["sid"]
        with _sessions_lock:
            sess = _sessions.get(sid)
        if sess is None or sess.closed:
            return Response(HTTPStatus.NOT_FOUND, {"error": "pty_not_found"})
        try:
            body = req.json()
        except ValueError:
            return Response(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
        cols = int(body.get("cols") or 80)
        rows = int(body.get("rows") or 24)
        _resize(sess, cols, rows)
        return Response(HTTPStatus.OK, {"cols": cols, "rows": rows})

    @router.route("DELETE", "/api/pty/{sid}")
    def _close_route(req: Request) -> Response:
        if auth_module.authenticate(req, cfg) is None:
            return Response(HTTPStatus.UNAUTHORIZED, {"error": "not_authenticated"})
        if (blocked := exec_policy.require_exec(req, cfg)) is not None:
            return blocked
        ok = _close(req.params["sid"])
        return Response(HTTPStatus.OK if ok else HTTPStatus.NOT_FOUND, {"ok": ok})

    return router
