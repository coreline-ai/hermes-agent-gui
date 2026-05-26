"""Compression trigger policy — Phase 18."""

from __future__ import annotations


def should_compact(session, tokens: int, context_window: int = 128_000) -> bool:
    turns = len(getattr(session, "messages", []) or [])
    return turns >= 40 or tokens >= int(context_window * 0.75)


def estimate_message_tokens(messages: list) -> int:
    total = 0
    for m in messages:
        content = getattr(m, "content", None) if not isinstance(m, dict) else m.get("content")
        total += max(1, len(str(content or "")) // 4)
    return total
