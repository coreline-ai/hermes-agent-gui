"""RAG injection helper — Phase 18."""

from __future__ import annotations

from .vss_store import search_chunks


def maybe_inject(messages: list[dict], *, session_id: str | None = None, k: int = 3) -> list[dict]:
    last_user = next((m for m in reversed(messages) if m.get("role") == "user"), None)
    if not last_user or not session_id:
        return messages
    results = search_chunks(str(last_user.get("content") or ""), k=k, session_id_filter=session_id)
    if not results:
        return messages
    context = "\n".join(f"- {chunk.summary}" for chunk, _score in results)
    system = {"role": "system", "content": "Relevant prior compressed context:\n" + context}
    return [system, *messages]
