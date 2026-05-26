"""Mission decomposition + dispatch — Phase 6 minimal port of A's swarm-missions.ts.

Decomposition heuristic: split a multi-sentence mission into role-tagged
sub-tasks based on simple cues (``review``, ``test``, ``research``, ``deploy``,
``docs``...). This is intentionally crude — A's TS version queries the model
for decomposition; that wiring lands in a future phase once embedded chat
roundtrips are robust.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field

ROLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "builder":   ("build", "implement", "code", "write code", "scaffold", "create"),
    "reviewer":  ("review", "lint", "audit", "check"),
    "qa":        ("test", "verify", "qa", "spec"),
    "researcher":("research", "investigate", "explore", "find"),
    "docs":      ("doc", "readme", "comment", "tutorial"),
    "ops":       ("deploy", "release", "rollout", "infra"),
    "triage":    ("triage", "categorize", "label"),
}
DEFAULT_ROLE = "builder"


@dataclass
class SubTask:
    text: str
    role: str
    order: int


@dataclass
class Mission:
    id: str
    prompt: str
    sub_tasks: list[SubTask] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "sub_tasks": [
                {"text": t.text, "role": t.role, "order": t.order} for t in self.sub_tasks
            ],
        }


def _pick_role(text: str) -> str:
    lo = text.lower()
    for role, hints in ROLE_KEYWORDS.items():
        if any(h in lo for h in hints):
            return role
    return DEFAULT_ROLE


def decompose_mission(prompt: str) -> Mission:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", prompt) if s.strip()]
    if not sentences:
        sentences = [prompt.strip() or "(empty mission)"]
    sub_tasks = [
        SubTask(text=s, role=_pick_role(s), order=i)
        for i, s in enumerate(sentences)
    ]
    return Mission(id=uuid.uuid4().hex[:12], prompt=prompt, sub_tasks=sub_tasks)
