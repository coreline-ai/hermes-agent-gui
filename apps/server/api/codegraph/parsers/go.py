from __future__ import annotations

import re

from .common import Symbol

_PATTERNS = [
    ("function", re.compile(r"^func\s+(?:\([^)]*\)\s*)?([A-Za-z_][\w]*)")),
    ("type", re.compile(r"^type\s+([A-Za-z_][\w]*)\s+(?:struct|interface|func|map|\w+)")),
    ("const", re.compile(r"^const\s+([A-Za-z_][\w]*)")),
]


def parse(path: str, text: str) -> list[Symbol]:
    out: list[Symbol] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for kind, pattern in _PATTERNS:
            match = pattern.search(line.strip())
            if match:
                out.append(Symbol(match.group(1), kind, path, line_no))
    return out
