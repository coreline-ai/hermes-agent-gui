"""Conductor + Swarm — Phase 6 (Python port of A's TypeScript src/server/swarm-*).

Modules mirror A's split:
- foundation  → tmux session manager (worker spawn/attach/kill)
- lifecycle   → worker state machine (idle/running/blocked/done)
- missions    → mission decomposition + dispatch
- conductor   → mission sanitize + entry point
- routes      → HTTP endpoints

Phase 6 stays conservative: tmux is *detected* and used when available. If
tmux isn't installed, workers fall back to plain subprocesses with output
captured to ``~/.hermes-agent-gui/swarm/<worker>.log``. This matches A's
"native-swarm fallback" pattern.
"""

from .foundation import SwarmFoundation, Worker
from .lifecycle import WorkerState, WorkerLifecycle
from .missions import Mission, decompose_mission
from .conductor import sanitize_mission
from .dispatch import DispatchedMission, dispatch
from .routes import register_routes

__all__ = [
    "SwarmFoundation",
    "Worker",
    "WorkerState",
    "WorkerLifecycle",
    "Mission",
    "decompose_mission",
    "sanitize_mission",
    "DispatchedMission",
    "dispatch",
    "register_routes",
]
