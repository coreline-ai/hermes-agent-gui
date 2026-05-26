"""Conductor mission sanitize + dispatch entry — port of A's conductor-mission-sanitize.ts.

Strips obvious prompt-injection junk, normalises whitespace, caps length.
"""

from __future__ import annotations

import re

MAX_PROMPT_BYTES = 16 * 1024
INJECTION_MARKERS = (
    "ignore previous instructions",
    "disregard the above",
    "system prompt:",
)


def sanitize_mission(prompt: str) -> str:
    p = (prompt or "").strip()
    if not p:
        return ""
    # Normalize whitespace.
    p = re.sub(r"\s+", " ", p)
    # Cheap injection guard — flag but keep so the model can still see it.
    lo = p.lower()
    if any(marker in lo for marker in INJECTION_MARKERS):
        p = "[!] suspected-instruction-override prefix removed by sanitizer.\n" + p
    # Hard cap on length.
    encoded = p.encode("utf-8")
    if len(encoded) > MAX_PROMPT_BYTES:
        p = encoded[:MAX_PROMPT_BYTES].decode("utf-8", errors="ignore") + " … [truncated]"
    return p
