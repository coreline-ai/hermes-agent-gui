"""Swarm foundation — tmux session manager with subprocess fallback.

Port of A's src/server/swarm-foundation.ts. ``tmux`` is used when available
(persistent workers across server restarts); otherwise we run ``subprocess``
and tail logs from ``~/.hermes-agent-gui/swarm/<worker>.log``.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from ..config import STATE_DIR

logger = logging.getLogger(__name__)

SWARM_DIR = STATE_DIR / "swarm"
SWARM_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Worker:
    id: str
    role: str
    cmd: list[str]
    created_at: float
    pid: int | None = None
    tmux_session: str | None = None
    log_path: str = ""
    state: str = "idle"
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return self.__dict__ | {}


class SwarmFoundation:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._workers: dict[str, Worker] = {}
        self._tmux = bool(shutil.which("tmux"))

    @property
    def has_tmux(self) -> bool:
        return self._tmux

    def list(self) -> list[Worker]:
        with self._lock:
            return list(self._workers.values())

    def get(self, wid: str) -> Worker | None:
        with self._lock:
            return self._workers.get(wid)

    def spawn(self, role: str, cmd: list[str], *, meta: dict | None = None) -> Worker:
        wid = uuid.uuid4().hex[:12]
        log_path = SWARM_DIR / f"{role}-{wid}.log"
        worker = Worker(
            id=wid,
            role=role,
            cmd=cmd,
            created_at=time.time(),
            log_path=str(log_path),
            meta=meta or {},
        )
        if self._tmux:
            sess = f"hermes-{role}-{wid}"
            joined = " ".join(_q(part) for part in cmd)
            try:
                subprocess.run(
                    ["tmux", "new-session", "-d", "-s", sess,
                     f"({joined}) 2>&1 | tee -a {_q(str(log_path))}"],
                    check=True,
                )
                worker.tmux_session = sess
            except subprocess.CalledProcessError:
                self._tmux = False  # downgrade for the rest of this process
        if not worker.tmux_session:
            f = open(log_path, "ab")
            proc = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, env=os.environ.copy())
            worker.pid = proc.pid
        worker.state = "running"
        with self._lock:
            self._workers[wid] = worker
        return worker

    def kill(self, wid: str) -> bool:
        with self._lock:
            worker = self._workers.pop(wid, None)
        if worker is None:
            return False
        if worker.tmux_session:
            subprocess.run(["tmux", "kill-session", "-t", worker.tmux_session], check=False)
        elif worker.pid:
            try:
                os.kill(worker.pid, 15)
            except ProcessLookupError:
                pass
        worker.state = "killed"
        return True

    def tail_log(self, wid: str, *, lines: int = 200) -> str | None:
        worker = self.get(wid)
        if not worker or not worker.log_path:
            return None
        p = Path(worker.log_path)
        if not p.is_file():
            return ""
        # Read the last N lines (small bounded read).
        data = p.read_bytes()[-(lines * 200):]
        return data.decode("utf-8", errors="replace").splitlines()[-lines:].__iter__() and "\n".join(
            data.decode("utf-8", errors="replace").splitlines()[-lines:]
        )


def _q(s: str) -> str:
    """Shell-quote helper for tmux command construction."""
    if not s or any(c in s for c in " '\"$\\`;|&<>(){}[]*?#"):
        return "'" + s.replace("'", "'\\''") + "'"
    return s
