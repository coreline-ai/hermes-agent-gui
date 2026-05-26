from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

IDLE_SECONDS = 5 * 60
MAX_SESSIONS = 4


@dataclass
class BrowserSession:
    id: str
    url: str = "about:blank"
    html: str = ""
    updated_at: float = field(default_factory=time.time)


class BrowserPool:
    def __init__(self) -> None:
        self.sessions: dict[str, BrowserSession] = {}

    def sweep(self) -> None:
        now = time.time()
        for sid in list(self.sessions):
            if now - self.sessions[sid].updated_at > IDLE_SECONDS:
                self.sessions.pop(sid, None)

    def get(self, sid: str | None = None) -> BrowserSession:
        self.sweep()
        if sid and sid in self.sessions:
            sess = self.sessions[sid]
            sess.updated_at = time.time()
            return sess
        if len(self.sessions) >= MAX_SESSIONS:
            oldest = min(self.sessions.values(), key=lambda s: s.updated_at)
            self.sessions.pop(oldest.id, None)
        sess = BrowserSession(uuid.uuid4().hex[:12])
        self.sessions[sess.id] = sess
        return sess


pool = BrowserPool()
