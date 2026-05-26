from __future__ import annotations

from collections import deque

from .graph import list_edges, list_nodes, node_by_id


def query_graph(query: str, *, depth: int = 3) -> dict:
    depth = max(1, min(depth, 3))
    seeds = list_nodes(query)[:5]
    edge_map: dict[str, list[str]] = {}
    edge_by_pair: dict[tuple[str, str], str] = {}
    for edge in list_edges():
        edge_map.setdefault(edge.src, []).append(edge.dst)
        edge_map.setdefault(edge.dst, []).append(edge.src)
        edge_by_pair[(edge.src, edge.dst)] = edge.kind
        edge_by_pair[(edge.dst, edge.src)] = edge.kind
    seen = {seed.id for seed in seeds}
    q = deque((seed.id, 0) for seed in seeds)
    paths: list[dict] = []
    while q:
        node_id, d = q.popleft()
        if d >= depth:
            continue
        for nxt in edge_map.get(node_id, []):
            src = node_by_id(node_id)
            dst = node_by_id(nxt)
            if src and dst:
                paths.append({"src": src.to_dict(), "dst": dst.to_dict(), "kind": edge_by_pair.get((node_id, nxt), "related"), "score": 1 / (d + 1)})
            if nxt not in seen:
                seen.add(nxt)
                q.append((nxt, d + 1))
    return {"seeds": [s.to_dict() for s in seeds], "paths": paths[:50]}
