from __future__ import annotations

from .base import MemoryHit
from ..compression.vss_store import add_chunk, list_chunks, search_chunks


class LocalVssProvider:
    name = "local_vss"

    def query(self, text: str, *, k: int = 5) -> list[MemoryHit]:
        return [MemoryHit(chunk.id, chunk.summary, score, self.name) for chunk, score in search_chunks(text, k=k)]

    def write(self, text: str, *, session_id: str | None = None) -> MemoryHit:
        chunk = add_chunk(session_id or "global", 0, 0, text)
        return MemoryHit(chunk.id, chunk.summary, 1.0, self.name)

    def purge(self) -> int:
        return 0

    def test_connection(self) -> dict:
        return {"ok": True, "chunks": len(list_chunks())}
