from __future__ import annotations

import re

from .models import Group, GroupParticipant

MENTION_RE = re.compile(r"@([A-Za-z0-9_.-]+)")


def route_message(group: Group, content: str) -> GroupParticipant | None:
    if not group.participants:
        return None
    mentions = {m.group(1).lower() for m in MENTION_RE.finditer(content)}
    if mentions:
        for participant in group.participants:
            if participant.name.lower() in mentions:
                return participant
    return group.participants[0]
