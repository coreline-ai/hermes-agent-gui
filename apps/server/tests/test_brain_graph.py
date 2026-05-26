from __future__ import annotations

from api.brain.extractor import extract
from api.brain.graph import list_nodes, upsert
from api.brain.synthesizer import synthesize
from api.brain.traversal import query_graph


def test_extractor_mentions_company_and_edges(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_GUI_STATE_DIR", str(tmp_path / "state"))
    out = extract("@Alice works at Acme Labs. Bob founded Beta Inc. Decision: use citations.")
    labels = {n["label"] for n in out["nodes"]}
    assert "Alice" in labels
    assert "Acme Labs" in labels
    assert any(e["kind"] == "works_at" for e in out["edges"])
    assert any(e["kind"] == "founded" for e in out["edges"])


def test_graph_query_depth_and_citations(client):
    client("POST", "/api/auth/login", body={"password": "test-pass"})
    status, _ = client("POST", "/api/brain/ingest", body={"text": "Alice works at Acme Labs. Alice founded Beta Inc."})
    assert status == 200
    status, body = client("POST", "/api/brain/query", body={"q": "Alice", "depth": 3})
    assert status == 200
    assert body["synthesis"]["citations"]
    assert len(body["graph"]["paths"]) <= 50
