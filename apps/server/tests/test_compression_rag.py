from __future__ import annotations

from api.compression.summarizer import summarize_messages
from api.compression.trigger import should_compact
from api.sessions.lifecycle import Message, Session


def test_trigger_thresholds():
    small = Session("s", "t", "default", 0, 0, [Message("user", "x") for _ in range(39)])
    large = Session("s", "t", "default", 0, 0, [Message("user", "x") for _ in range(40)])
    assert should_compact(small, tokens=100, context_window=1000) is False
    assert should_compact(small, tokens=750, context_window=1000) is True
    assert should_compact(large, tokens=1, context_window=1000) is True


def test_summary_preserves_decisions():
    messages = [
        {"role": "user", "content": "Decision: use Redis for cache."},
        {"role": "assistant", "content": "Decision: keep Postgres as source of truth."},
    ]
    out = summarize_messages(messages)
    assert "Redis" in out
    assert "Postgres" in out
    assert out.count("Decision") == 2


def test_compact_and_rag_inject_visible_messages_unchanged(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    _, sess = client("POST", "/api/sessions", body={"title": "rag"})
    sid = sess["id"]
    for i in range(3):
        client("POST", f"/api/sessions/{sid}/health", body={"browser_messages": [{"role": "user", "content": f"Decision {i}: keep redis cluster"}]})
    # health repair above replaced messages; compact visible transcript into hidden chunk store.
    status, body = client("POST", f"/api/sessions/{sid}/compact", body={"trigger": "manual"})
    assert status == 200
    assert body["compacted_chunks"]

    before_status, before = client("GET", f"/api/sessions/{sid}")
    assert before_status == 200
    before_messages = before["messages"]

    # Compaction stores hidden chunks only; visible transcript remains unchanged.
    after_status, after = client("GET", f"/api/sessions/{sid}")
    assert after_status == 200
    assert after["messages"] == before_messages


def test_memory_search_top_k(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    _, sess = client("POST", "/api/sessions", body={"title": "search"})
    sid = sess["id"]
    client(
        "POST",
        f"/api/sessions/{sid}/health",
        body={"browser_messages": [{"role": "user", "content": "Decision: choose qdrant vector search for embeddings."}]},
    )
    client("POST", f"/api/sessions/{sid}/compact", body={"trigger": "manual"})
    status, body = client("POST", "/api/memory/search", body={"q": "qdrant embeddings", "k": 1})
    assert status == 200
    assert body["results"]
    assert "qdrant" in body["results"][0]["summary"].lower()
