from __future__ import annotations


def synthesize(question: str, graph_result: dict) -> dict:
    citations = []
    for path in graph_result.get("paths", [])[:5]:
        citations.append({"node_id": path["src"]["id"], "label": path["src"]["label"], "edge": path["kind"]})
    if citations:
        answer = f"Based on the local graph, {question} relates to " + ", ".join(c["label"] for c in citations[:3]) + "."
        gaps: list[str] = []
    else:
        answer = "No strong local graph evidence yet. Add notes or chat history first."
        gaps = ["insufficient_graph_context"]
    return {"answer": answer, "citations": citations, "gap_analysis": gaps}
