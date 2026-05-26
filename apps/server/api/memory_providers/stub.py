from __future__ import annotations

from .base import MemoryHit


class ExternalMemoryProvider:
    def __init__(self, name: str, configured: bool = False) -> None:
        self.name = name
        self.configured = configured

    def query(self, text: str, *, k: int = 5) -> list[MemoryHit]:
        if not self.configured:
            return []
        return [MemoryHit(f"{self.name}-preview", text[:160], 0.5, self.name)][:k]

    def write(self, text: str, *, session_id: str | None = None) -> MemoryHit:
        if not self.configured:
            raise ValueError("provider_config_missing")
        return MemoryHit(f"{self.name}-{session_id or 'global'}", text, 1.0, self.name)

    def purge(self) -> int:
        return 0

    def test_connection(self) -> dict:
        if not self.configured:
            return {"ok": False, "error": "provider_config_missing"}
        return {"ok": True}
