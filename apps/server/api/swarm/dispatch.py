"""Mission → workers dispatcher — P1#6.

Takes a decomposed mission (from ``missions.decompose_mission``) and spawns
one worker per sub-task using ``SwarmFoundation``. Tracks mission→worker
mapping so callers can fetch status.

Worker command template (env-driven):
    HERMES_SWARM_WORKER_CMD="echo {role}: {text}"

If ``HERMES_SWARM_WORKER_CMD`` is unset we default to running ``hermes`` if
available, otherwise a plain ``echo`` so the wiring is still exercisable in
dev.
"""

from __future__ import annotations

import os
import shlex
import shutil
import threading
import time
from dataclasses import dataclass, field

from .foundation import SwarmFoundation, Worker
from .missions import Mission


def _default_worker_cmd() -> str:
    if (env := os.environ.get("HERMES_SWARM_WORKER_CMD")):
        return env
    if shutil.which("hermes"):
        return "hermes prompt {role!q} -m {text!q}"
    return "echo {role}: {text}"


def _render_cmd(template: str, role: str, text: str) -> list[str]:
    """Render ``{role}`` and ``{text}`` placeholders, with optional ``!q`` shell-quoting."""
    out = template
    out = out.replace("{role!q}", shlex.quote(role)).replace("{role}", role)
    out = out.replace("{text!q}", shlex.quote(text)).replace("{text}", text)
    return shlex.split(out)


@dataclass
class DispatchedMission:
    mission_id: str
    workers: list[str] = field(default_factory=list)   # worker ids
    sub_task_to_worker: dict[int, str] = field(default_factory=dict)
    started_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "workers": list(self.workers),
            "sub_task_to_worker": dict(self.sub_task_to_worker),
            "started_at": self.started_at,
        }


_lock = threading.RLock()
_dispatched: dict[str, DispatchedMission] = {}


def dispatch(foundation: SwarmFoundation, mission: Mission) -> DispatchedMission:
    template = _default_worker_cmd()
    rec = DispatchedMission(mission_id=mission.id, started_at=time.time())
    for sub in mission.sub_tasks:
        try:
            argv = _render_cmd(template, sub.role, sub.text)
        except ValueError:
            argv = ["echo", f"{sub.role}: {sub.text}"]
        worker: Worker = foundation.spawn(
            sub.role, argv,
            meta={"mission_id": mission.id, "sub_task_order": sub.order, "sub_task_text": sub.text},
        )
        rec.workers.append(worker.id)
        rec.sub_task_to_worker[sub.order] = worker.id
    with _lock:
        _dispatched[mission.id] = rec
    return rec


def get(mission_id: str) -> DispatchedMission | None:
    with _lock:
        return _dispatched.get(mission_id)


def list_recent(limit: int = 50) -> list[DispatchedMission]:
    with _lock:
        items = sorted(_dispatched.values(), key=lambda m: m.started_at, reverse=True)
        return items[:limit]
