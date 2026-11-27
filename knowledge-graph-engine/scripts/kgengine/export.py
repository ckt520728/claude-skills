"""Export to GraphML (Gephi/Cytoscape), node-link JSON, or Cypher (Neo4j import)."""
from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

from .config import OUT_DIR


def _flat(kg):
    H = nx.MultiDiGraph()
    for n, d in kg.G.nodes(data=True):
        H.add_node(n, type=d["type"], description=d.get("description", ""), aliases="|".join(d["aliases"]),
                   mentions=d["mentions"], n_docs=len(d["docs"]),
                   summary=(d.get("profile") or {}).get("summary", ""))
    for a, b, k, d in kg.G.edges(keys=True, data=True):
        H.add_edge(a, b, key=k, predicate=k, weight=d["weight"],
                   evidence=" || ".join(f"{e['text']} <{e['doc']}>" for e in d["evidence"][:5]))
    return H


def _cy(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def export(kg, fmt: str = "graphml", out: str | None = None) -> Path:
    out = Path(out or OUT_DIR / f"graph.{ {'graphml': 'graphml', 'json': 'json', 'cypher': 'cypher'}[fmt] }")
    out.parent.mkdir(parents=True, exist_ok=True)
    H = _flat(kg)
    if fmt == "graphml":
        nx.write_graphml(H, out)
    elif fmt == "json":
        out.write_text(json.dumps(nx.node_link_data(H, edges="links"), ensure_ascii=False, indent=1), encoding="utf-8")
    else:
        lines = ["CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE;"]
        for n, d in H.nodes(data=True):
            lines.append(f"MERGE (e:Entity {{name:{_cy(n)}}}) SET e:{d['type']}, e.description={_cy(d['description'])}, "
                         f"e.aliases={_cy(d['aliases'])}, e.n_docs={d['n_docs']};")
        for a, b, k, d in H.edges(keys=True, data=True):
            lines.append(f"MATCH (a:Entity {{name:{_cy(a)}}}),(b:Entity {{name:{_cy(b)}}}) "
                         f"MERGE (a)-[r:{k}]->(b) SET r.weight={d['weight']}, r.evidence={_cy(d['evidence'])};")
        out.write_text("\n".join(lines), encoding="utf-8")
    return out
