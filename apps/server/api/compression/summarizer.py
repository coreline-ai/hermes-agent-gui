"""Deterministic local summarizer fallback — Phase 18.

Provider-backed summarization can replace this later. The current implementation
is intentionally dependency-free and deterministic for tests.
"""

from __future__ import annotations


def summarize_messages(messages: list, *, max_chars: int = 1200) -> str:
    parts: list[str] = []
    for m in messages:
        role = getattr(m, "role", None) if not isinstance(m, dict) else m.get("role")
        content = getattr(m, "content", None) if not isinstance(m, dict) else m.get("content")
        text = " ".join(str(content or "").split())
        if text:
            parts.append(f"{role or 'message'}: {text}")
    joined = "\n".join(parts)
    if not joined:
        return "No prior content to summarize."
    if len(joined) <= max_chars:
        return joined
    return joined[: max_chars - 1].rstrip() + "…"
