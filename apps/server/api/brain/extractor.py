from __future__ import annotations

import re

_COMPANY_RE = re.compile(r"\b([A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*)*\s+(?:Inc|Labs|Corp|LLC|Ltd|Company))\b")
_MENTION_RE = re.compile(r"@([A-Za-z][A-Za-z0-9_.-]{1,39})")
_WORKS_AT_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+works\s+at\s+([A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*)*)", re.I)
_FOUNDED_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+founded\s+([A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*)*)", re.I)
_DECISION_RE = re.compile(r"\bDecision\s*:\s*([^\.\n]+)", re.I)


def _node(label: str, kind: str, source: str) -> dict:
    return {"label": " ".join(label.split()), "kind": kind, "source": source}


def extract(text: str, *, source: str = "manual") -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []
    for mention in _MENTION_RE.findall(text):
        nodes.append(_node(mention, "person", source))
    for company in _COMPANY_RE.findall(text):
        nodes.append(_node(company, "org", source))
    for person, org in _WORKS_AT_RE.findall(text):
        nodes.extend([_node(person, "person", source), _node(org, "org", source)])
        edges.append({"src": person, "dst": org, "kind": "works_at", "source": source})
    for person, org in _FOUNDED_RE.findall(text):
        nodes.extend([_node(person, "person", source), _node(org, "org", source)])
        edges.append({"src": person, "dst": org, "kind": "founded", "source": source})
    for decision in _DECISION_RE.findall(text):
        nodes.append(_node(decision, "decision", source))
    dedup: dict[tuple[str, str], dict] = {}
    for item in nodes:
        dedup[(item["label"].lower(), item["kind"])] = item
    return {"nodes": list(dedup.values()), "edges": edges}
