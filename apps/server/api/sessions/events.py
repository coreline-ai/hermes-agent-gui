"""Per-process pub/sub for session list changes — Phase 2.

Adapted from B's session_events.py. Listeners use blocking queue.get() with a
timeout so disconnect detection is cheap. SSE endpoint in ops.py publishes to
this.
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class Event:
    kind: str  # 'session_list_changed' | 'session_updated' | 'session_deleted'
    payload: dict


class SessionEvents:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: list[queue.Queue[Event]] = []

    def publish(self, kind: str, payload: dict) -> None:
        evt = Event(kind=kind, payload=payload)
        with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait(evt)
            except queue.Full:
                pass  # subscriber's loop will catch up

    def subscribe(self, maxsize: int = 256) -> queue.Queue[Event]:
        q: queue.Queue[Event] = queue.Queue(maxsize=maxsize)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue[Event]) -> None:
        with self._lock:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass

    def drain(self, q: queue.Queue[Event], timeout: float = 15.0) -> Iterator[Event]:
        try:
            evt = q.get(timeout=timeout)
        except queue.Empty:
            return
        yield evt
        while True:
            try:
                yield q.get_nowait()
            except queue.Empty:
                return


events = SessionEvents()
