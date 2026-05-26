from __future__ import annotations

import re

from .common import Symbol

_PATTERNS = [
    ("function", re.compile(r"^(?:pub\s+)?fn\s+([A-Za-z_][\w]*)")),
    ("struct", re.compile(r"^(?:pub\s+)?struct\s+([A-Za-z_][\w]*)")),
    ("enum", re.compile(r"^(?:pub\s+)?enum\s+([A-Za-z_][\w]*)")),
    ("trait", re.compile(r"^(?:pub\s+)?trait\s+([A-Za-z_][\w]*)")),
]


def parse(path: str, text: str) -> list[Symbol]:
    out: list[Symbol] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for kind, pattern in _PATTERNS:
            match = pattern.search(line.strip())
            if match:
                out.append(Symbol(match.group(1), kind, path, line_no))
    return out
