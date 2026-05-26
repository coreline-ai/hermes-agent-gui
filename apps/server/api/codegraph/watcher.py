from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class Debouncer:
    delay_ms: int = 500
    last_at: float = 0.0
    pending: int = 0

    def touch(self) -> bool:
        now = time.time() * 1000
        self.pending += 1
        if now - self.last_at >= self.delay_ms:
            self.last_at = now
            self.pending = 0
            return True
        return False
