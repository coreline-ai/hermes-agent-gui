"""Group chat domain models — Phase 20."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
MAX_PARTICIPANTS = 10
INVITE_TTL_SECONDS = 24 * 60 * 60


def invite_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(8))


@dataclass(frozen=True)
class GroupParticipant:
    name: str
    profile: str = "default"
    model: str = "auto"

    def to_dict(self) -> dict:
        return {"name": self.name, "profile": self.profile, "model": self.model}


@dataclass(frozen=True)
class Group:
    id: str
    name: str
    invite_code: str
    invite_expires_at: int
    created_at: int
    participants: list[GroupParticipant] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "invite_code": self.invite_code,
            "invite_expires_at": self.invite_expires_at,
            "invite_expired": int(time.time()) > self.invite_expires_at,
            "created_at": self.created_at,
            "participants": [p.to_dict() for p in self.participants],
        }
