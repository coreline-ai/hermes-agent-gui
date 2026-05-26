from __future__ import annotations

from pathlib import Path

from api.sessions.lifecycle import Message, SessionStore
from api.sessions.search import backfill_fts, search_messages


def test_fts5_search_ranks_redis_caching_result(tmp_path: Path):
    store = SessionStore(tmp_path / "sessions.db")
    s1 = store.create(title="Phase 18 design")
    s2 = store.create(title="Unrelated")
    store.append_messages(s1.id, [Message("user", "We decided redis caching should hold hot session state.")])
    store.append_messages(s2.id, [Message("user", "The UI theme should use bronze colors.")])

    out = search_messages(store, "redis caching", limit=10)

    assert out["total"] >= 1
    assert out["results"][0]["session_id"] == s1.id
    assert "<em>redis</em>" in out["results"][0]["snippet"].lower()


def test_incremental_indexing_after_append(tmp_path: Path):
    store = SessionStore(tmp_path / "sessions.db")
    sess = store.create(title="Append")
    store.append_messages(sess.id, [Message("user", "new append searchable immediately")])

    out = search_messages(store, "searchable immediately")

    assert out["total"] == 1
    assert out["results"][0]["message_index"] == 0


def test_backfill_idempotent(tmp_path: Path):
    store = SessionStore(tmp_path / "sessions.db")
    sess = store.create(title="Backfill")
    store.append_messages(sess.id, [Message("user", "idempotent redis caching backfill")])

    first = backfill_fts(store)
    second = backfill_fts(store)
    out = search_messages(store, "idempotent redis", limit=10)

    assert first == 0
    assert second == 0
    assert out["total"] == 1
