"""Session 5-module set — Phase 2.

Adapted from nesquena/hermes-webui's api/agent_sessions / session_events /
session_lifecycle / session_ops / session_recovery split, with C's
transcript-drift / tool-evidence repair algorithm bolted on.
"""

from .lifecycle import Session, Message, SessionStore
from .recovery import HealthReport, repair_transcript_drift, session_health
from .events import SessionEvents
from .ops import register_routes
from .compression import alias_resolve, register_alias

__all__ = [
    "Session",
    "Message",
    "SessionStore",
    "HealthReport",
    "repair_transcript_drift",
    "session_health",
    "SessionEvents",
    "register_routes",
    "alias_resolve",
    "register_alias",
]
