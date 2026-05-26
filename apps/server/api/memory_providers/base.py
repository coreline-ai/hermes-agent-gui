"""Memory provider plugin contract — Phase 19."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class MemoryHit:
    id: str
    text: str
    score: float = 1.0
    source: str = "local"

    def to_dict(self) -> dict:
        return {"id": self.id, "text": self.text, "score": self.score, "source": self.source}


class AbstractMemoryProvider(Protocol):
    name: str

    def query(self, text: str, *, k: int = 5) -> list[MemoryHit]: ...
    def write(self, text: str, *, session_id: str | None = None) -> MemoryHit: ...
    def purge(self) -> int: ...
    def test_connection(self) -> dict: ...
