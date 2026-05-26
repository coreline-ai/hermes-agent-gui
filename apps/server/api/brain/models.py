"""Knowledge graph models — Phase 21."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrainNode:
    id: str
    label: str
    kind: str
    source: str

    def to_dict(self) -> dict:
        return {"id": self.id, "label": self.label, "kind": self.kind, "source": self.source}


@dataclass(frozen=True)
class BrainEdge:
    id: str
    src: str
    dst: str
    kind: str
    source: str

    def to_dict(self) -> dict:
        return {"id": self.id, "src": self.src, "dst": self.dst, "kind": self.kind, "source": self.source}
