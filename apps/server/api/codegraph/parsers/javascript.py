from __future__ import annotations

import re

from .common import Symbol

_PATTERNS = [
    ("interface", re.compile(r"^\s*export\s+interface\s+([A-Za-z_$][\w$]*)|^\s*interface\s+([A-Za-z_$][\w$]*)")),
    ("type", re.compile(r"^\s*export\s+type\s+([A-Za-z_$][\w$]*)|^\s*type\s+([A-Za-z_$][\w$]*)")),
    ("function", re.compile(r"^\s*export\s+function\s+([A-Za-z_$][\w$]*)|^\s*function\s+([A-Za-z_$][\w$]*)|^\s*const\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(")),
    ("class", re.compile(r"^\s*export\s+class\s+([A-Za-z_$][\w$]*)|^\s*class\s+([A-Za-z_$][\w$]*)")),
]


def parse(path: str, text: str) -> list[Symbol]:
    out: list[Symbol] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for kind, pattern in _PATTERNS:
            match = pattern.search(line)
            if match:
                name = next(g for g in match.groups() if g)
                out.append(Symbol(name, kind, path, line_no, max(1, line.find(name) + 1)))
    return out
