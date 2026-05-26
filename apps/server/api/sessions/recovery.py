"""Transcript drift / tool-evidence repair — adapted from pyrate-llama/hermes-ui v3.3.4-v3.3.11.

Key invariants (mirrored from C's patch notes):

1. If the browser-visible transcript has more user turns than the server, and
   the browser carries tool evidence (``tool_calls``) that the server is
   missing, repair the server side without replacing existing tool history.
2. Never replace richer backend ``tool_calls`` with a simplified browser
   transcript — provenance is preserved.
3. ``/api/session/health`` returns counts from server / browser / compact
   context so clients can detect drift before sending a new turn.
4. Compaction-induced ID rotation: the server keeps an alias map so requests
   for the old session ID still resolve. See :mod:`compression`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .lifecycle import Message, Session, SessionStore


@dataclass
class HealthReport:
    session_id: str
    server_messages: int
    browser_messages: int | None
    compact_context_messages: int | None
    has_tool_evidence_on_server: bool
    has_tool_evidence_on_browser: bool
    drift: bool
    drift_kind: str | None  # 'browser_ahead' | 'server_ahead' | 'compact_stale' | None

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "server_messages": self.server_messages,
            "browser_messages": self.browser_messages,
            "compact_context_messages": self.compact_context_messages,
            "has_tool_evidence_on_server": self.has_tool_evidence_on_server,
            "has_tool_evidence_on_browser": self.has_tool_evidence_on_browser,
            "drift": self.drift,
            "drift_kind": self.drift_kind,
        }


def _has_tool_evidence(messages: Iterable[Message]) -> bool:
    return any(bool(m.tool_calls) or m.role == "tool" for m in messages)


def _user_count(messages: Iterable[Message]) -> int:
    return sum(1 for m in messages if m.role == "user")


def session_health(
    session: Session,
    browser_messages: list[Message] | None,
    compact_context_count: int | None,
) -> HealthReport:
    server_user_count = _user_count(session.messages)
    browser_user_count = _user_count(browser_messages) if browser_messages is not None else None
    drift_kind: str | None = None
    drift = False
    if browser_user_count is not None:
        if browser_user_count > server_user_count:
            drift = True
            drift_kind = "browser_ahead"
        elif browser_user_count < server_user_count:
            drift = True
            drift_kind = "server_ahead"
    if compact_context_count is not None and compact_context_count < server_user_count and not drift:
        drift = True
        drift_kind = "compact_stale"
    return HealthReport(
        session_id=session.id,
        server_messages=len(session.messages),
        browser_messages=(len(browser_messages) if browser_messages is not None else None),
        compact_context_messages=compact_context_count,
        has_tool_evidence_on_server=_has_tool_evidence(session.messages),
        has_tool_evidence_on_browser=(
            _has_tool_evidence(browser_messages) if browser_messages is not None else False
        ),
        drift=drift,
        drift_kind=drift_kind,
    )


def repair_transcript_drift(
    store: SessionStore,
    session: Session,
    browser_messages: list[Message],
) -> Session:
    """Repair using the v3.3.4-v3.3.11 rules. Returns the repaired session."""
    if not browser_messages:
        return session

    server_user_count = _user_count(session.messages)
    browser_user_count = _user_count(browser_messages)

    # Rule 1: browser is ahead and carries tool evidence → merge, preserving server tool history.
    server_has_tools = _has_tool_evidence(session.messages)
    browser_has_tools = _has_tool_evidence(browser_messages)

    if browser_user_count > server_user_count:
        merged = _merge_preserving_tools(
            server=session.messages,
            browser=browser_messages,
            prefer_browser_text=True,
        )
        return store.replace_messages(session.id, merged) or session

    # Rule 2: counts equal but browser has tool evidence missing from server.
    if browser_user_count == server_user_count and browser_has_tools and not server_has_tools:
        merged = _merge_preserving_tools(
            server=session.messages,
            browser=browser_messages,
            prefer_browser_text=False,
        )
        return store.replace_messages(session.id, merged) or session

    # Otherwise: server is authoritative.
    return session


def _merge_preserving_tools(
    *,
    server: list[Message],
    browser: list[Message],
    prefer_browser_text: bool,
) -> list[Message]:
    """Merge browser + server timelines while never dropping server-side tool history."""
    by_index: dict[int, Message] = {}
    # Seed from server (authoritative for tool_calls).
    for i, m in enumerate(server):
        by_index[i] = m
    # Overlay/append from browser.
    for i, b in enumerate(browser):
        if i in by_index:
            s = by_index[i]
            # Preserve server tool_calls; let browser refresh text only if asked.
            content = b.content if prefer_browser_text and b.content else s.content
            tool_calls = s.tool_calls or b.tool_calls
            by_index[i] = Message(
                role=s.role or b.role,
                content=content,
                tool_calls=tool_calls,
                created_at=s.created_at or b.created_at,
            )
        else:
            by_index[i] = b
    return [by_index[i] for i in sorted(by_index)]
