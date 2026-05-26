"""Simple lexical embedding helpers — Phase 18."""

from __future__ import annotations

import re
from collections import Counter

TOKEN_RE = re.compile(r"[A-Za-z0-9_가-힣]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def embed_text(text: str) -> dict[str, float]:
    counts = Counter(tokenize(text))
    total = sum(counts.values()) or 1
    return {k: v / total for k, v in counts.items()}


def similarity(a: str, b: str) -> float:
    va = embed_text(a)
    vb = embed_text(b)
    if not va or not vb:
        return 0.0
    keys = set(va) | set(vb)
    dot = sum(va.get(k, 0.0) * vb.get(k, 0.0) for k in keys)
    na = sum(v * v for v in va.values()) ** 0.5
    nb = sum(v * v for v in vb.values()) ** 0.5
    return dot / (na * nb) if na and nb else 0.0
