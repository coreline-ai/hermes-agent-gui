"""Worker state machine — Phase 6 minimal."""

from __future__ import annotations

import enum
from dataclasses import dataclass

from .foundation import SwarmFoundation, Worker


class WorkerState(str, enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    BLOCKED = "blocked"
    REVIEW = "review"
    DONE = "done"
    KILLED = "killed"


@dataclass
class WorkerLifecycle:
    foundation: SwarmFoundation

    def transition(self, wid: str, new_state: WorkerState) -> Worker | None:
        worker = self.foundation.get(wid)
        if worker is None:
            return None
        worker.state = new_state.value
        return worker
