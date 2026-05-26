from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Symbol:
    name: str
    kind: str
    file: str
    line: int
    column: int = 1

    def to_dict(self) -> dict:
        return {"name": self.name, "kind": self.kind, "file": self.file, "line": self.line, "column": self.column}
