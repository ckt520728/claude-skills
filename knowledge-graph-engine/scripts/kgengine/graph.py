"""Canonical graph view + query layer.

The graph is rebuilt from SQLite (raw rows + alias table) into a NetworkX MultiDiGraph
with ONE edge per (source, predicate, timescale, target) aggregating all supporting evidence.
Edge key = "PREDICATE" or "PREDICATE@acute" / "PREDICATE@chronic" (ADR 0004); always read the
predicate from the edge's `predicate` attribute, never from the key.

Query surface:
    search(text)                    fuzzy entity lookup
    entity(name)                    node card (aliases, profile, degree, documents)
    neighbors(name, depth, ...)     k-hop ego subgraph with predicate/type filters
    paths(a, b, max_len)            all simple paths (undirected reachability, directed labels)
    match(pattern)                  Cypher-like path patterns, e.g.
        (INTERVENTION)-[INCREASES|IMPROVES]->(BIOMARKER)-[PREDICTS|BIOMARKER_OF]->(*)
        (INTERVENTION{name~aerobic})-[*]->(BRAIN_REGION)
        (BIOMARKER)<-[DECREASES]-(*)
        (INTERVENTION)-[INCREASES@acute]->(BIOMARKER)      timescale-qualified predicate
    evidence_matrix(src_type, tgt_type)   claim counts by pair (e.g. INTERVENTION x BIOMARKER)
    contradictions()                pairs with opposing predicates (INCREASES vs DECREASES/NO_EFFECT_ON)
    communities() / stats()
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from itertools import islice

import networkx as nx
from rapidfuzz import fuzz, process

from .ontology import normalize_timescale
from .store import Store

OPPOSITES = {("INCREASES", "DECREASES"), ("IMPROVES", "NO_EFFECT_ON"), ("INCREASES", "NO_EFFECT_ON"),
             ("DECREASES", "NO_EFFECT_ON"), ("PROTECTS_AGAINST", "RISK_FACTOR_FOR")}


def ekey(predicate: str, timescale: str = "unspecified") -> str:
    return predicate if timescale == "unspecified" else f"{predicate}@{timescale}"


def elabel(d: dict) -> str:
    """Human label of an edge, e.g. 'INCREASES' or 'INCREASES|chronic'."""
    ts = d.get("timescale", "unspecified")
    return d["predicate"] if ts == "unspecified" else f"{d['predicate']}|{ts}"


class KnowledgeGraph:
    def __init__(self, store: Store, min_confidence: float = 0.0):
        self.store = store
        self.min_confidence = min_confidence
        self.reload()

    # ------------------------------------------------------------------ build
    def reload(self) -> None:
        s = self.store
        amap = {r["alias"]: (r["canonical"], r["type"]) for r in s.q("SELECT * FROM aliases")}
        drows = s.q("SELECT id, title, dup_of FROM documents")
        docs = {r["id"]: r["title"] for r in drows}
        # duplicate copies of one paper count as ONE supporting document
        canon_doc = {r["id"]: (r["dup_of"] or r["id"]) for r in drows}
        G = nx.MultiDiGraph()
        for r in s.q("SELECT name, type, description, doc_id FROM raw_entities"):
            canon, t = amap.get(r["name"], (r["name"], r["type"]))
            if canon not in G:
                G.add_node(canon, type=t, description=r["description"], aliases=set(), docs=set(), mentions=0)
            n = G.nodes[canon]
            n["mentions"] += 1
            n["docs"].add(canon_doc.get(r["doc_id"], r["doc_id"]))
            if r["name"] != canon:
                n["aliases"].add(r["name"])
        for r in s.q("SELECT * FROM raw_relations WHERE confidence >= ?", (self.min_confidence,)):
            a = amap.get(r["source"], (r["source"],))[0]
            b = amap.get(r["target"], (r["target"],))[0]
            if a == b or a not in G or b not in G:
                continue
            p = r["predicate"]
            ts = normalize_timescale(r["timescale"])
            k = ekey(p, ts)
            if not G.has_edge(a, b, key=k):
                G.add_edge(a, b, key=k, predicate=p, timescale=ts, evidence=[], docs=set(), weight=0)
            e = G.edges[a, b, k]
            e["evidence"].append({"doc": docs.get(r["doc_id"], "?"), "doc_id": r["doc_id"],
                                  "text": r["evidence"], "confidence": r["confidence"]})
            e["docs"].add(canon_doc.get(r["doc_id"], r["doc_id"]))
            e["weight"] = len(e["docs"])
        for r in s.q("SELECT * FROM profiles"):
            if r["canonical"] in G:
                G.nodes[r["canonical"]]["profile"] = {"summary": r["summary"], "key_facts": json.loads(r["key_facts"])}
        for _, d in G.nodes(data=True):
            d["aliases"] = sorted(d["aliases"])
            d["docs"] = sorted(d["docs"])
        for *_, d in G.edges(keys=True, data=True):
            d["docs"] = sorted(d["docs"])
        self.G = G
        self.doc_titles = docs

    # ----------------------------------------------------------------- lookup
    def resolve_name(self, name: str) -> str | None:
        if name in self.G:
            return name
        low = name.lower().strip()
        for n, d in self.G.nodes(data=True):
            if n.lower() == low or low in (a.lower() for a in d["aliases"]):
                return n
        hit = self.search(name, limit=1)
        return hit[0]["name"] if hit and hit[0]["score"] >= 85 else None

    def search(self, text: str, limit: int = 10, type: str | None = None) -> list[dict]:
        choices = {}
        for n, d in self.G.nodes(data=True):
            if type and d["type"] != type:
                continue
            for label in [n, *d["aliases"]]:
                choices[label] = n
        hits = process.extract(text, list(choices), scorer=fuzz.WRatio, limit=limit * 3)
        out, seen = [], set()
        for label, score, _ in hits:
            n = choices[label]
            if n in seen:
                continue
            seen.add(n)
            out.append({"name": n, "type": self.G.nodes[n]["type"], "score": round(score, 1),
                        "matched": label, "degree": self.G.degree(n)})
            if len(out) >= limit:
                break
        return out

    def entity(self, name: str) -> dict | None:
        n = self.resolve_name(name)
        if n is None:
            return None
        d = self.G.nodes[n]
        return {"name": n, **{k: v for k, v in d.items() if k != "docs"},
                "documents": [self.doc_titles.get(i, "?") for i in d["docs"]],
                "degree": self.G.degree(n), "out": self.G.out_degree(n), "in": self.G.in_degree(n)}

    # ------------------------------------------------------------- traversal
    def neighbors(self, name: str, depth: int = 1, predicates: list[str] | None = None,
                  types: list[str] | None = None, min_weight: int = 1, max_edges: int = 300) -> dict:
        start = self.resolve_name(name)
        if start is None:
            return {"error": f"entity '{name}' not found", "suggestions": self.search(name, 5)}
        preds = {p.upper() for p in predicates} if predicates else None
        nodes, frontier, edges = {start}, {start}, []
        for _ in range(depth):
            nxt = set()
            for n in frontier:
                for a, b, k, d in list(self.G.out_edges(n, keys=True, data=True)) + list(self.G.in_edges(n, keys=True, data=True)):
                    other = b if a == n else a
                    if preds and d["predicate"] not in preds and k not in preds:
                        continue
                    if d["weight"] < min_weight:
                        continue
                    if types and self.G.nodes[other]["type"] not in types and other != start:
                        continue
                    edges.append((a, k, b))
                    if other not in nodes:
                        nxt.add(other)
            nodes |= nxt
            frontier = nxt
        edges = list(dict.fromkeys(edges))[:max_edges]
        return {"center": start, "nodes": sorted({x for e in edges for x in (e[0], e[2])} | {start}),
                "edges": [self.edge_dict(a, k, b) for a, k, b in edges]}

    def edge_dict(self, a, k, b, evidence: int = 3) -> dict:
        d = self.G.edges[a, b, k]
        return {"source": a, "predicate": d["predicate"], "timescale": d["timescale"], "target": b,
                "weight": d["weight"], "evidence": d["evidence"][:evidence]}

    def paths(self, a: str, b: str, max_len: int = 4, limit: int = 20) -> dict:
        s, t = self.resolve_name(a), self.resolve_name(b)
        if s is None or t is None:
            return {"error": "entity not found", "source": s, "target": t}
        U = nx.Graph(self.G)
        out = []
        for p in islice(nx.all_simple_paths(U, s, t, cutoff=max_len), limit * 5):
            steps = []
            for x, y in zip(p, p[1:]):
                if self.G.has_edge(x, y):
                    steps.append(f"({x}) -[{', '.join(map(elabel, self.G[x][y].values()))}]-> ({y})")
                else:
                    steps.append(f"({y}) -[{', '.join(map(elabel, self.G[y][x].values()))}]-> ({x})")
            out.append({"nodes": p, "steps": steps})
        out.sort(key=lambda x: len(x["nodes"]))
        return {"source": s, "target": t, "paths": out[:limit]}

    # ---------------------------------------------------------- pattern match
    _NODE = re.compile(r"\(\s*([A-Z_*]+)?\s*(?:\{\s*name\s*([~=])\s*([^}]+?)\s*\})?\s*\)")
    _EDGE = re.compile(r"\s*(<)?-\[\s*([A-Za-z_|@*]+)?\s*\]-(>)?\s*")

    def _parse(self, pattern: str):
        pos, nodes, edges = 0, [], []
        pattern = pattern.strip()
        while True:
            m = self._NODE.match(pattern, pos)
            if not m:
                raise ValueError(f"bad node pattern at: {pattern[pos:]!r}")
            nodes.append((m.group(1) or "*", m.group(2), (m.group(3) or "").strip("'\" ")))
            pos = m.end()
            if pos >= len(pattern):
                break
            e = self._EDGE.match(pattern, pos)
            if not e:
                raise ValueError(f"bad edge pattern at: {pattern[pos:]!r}")
            preds = None if not e.group(2) or e.group(2) == "*" else set(e.group(2).split("|"))
            direction = "in" if e.group(1) else ("out" if e.group(3) else "any")
            edges.append((preds, direction))
            pos = e.end()
        return nodes, edges

    def _node_ok(self, n, spec) -> bool:
        t, op, val = spec
        d = self.G.nodes[n]
        if t != "*" and d["type"] != t:
            return False
        if op == "=":
            return n.lower() == val.lower()
        if op == "~":
            v = val.lower()
            return v in n.lower() or any(v in a.lower() for a in d["aliases"])
        return True

    def match(self, pattern: str, limit: int = 100, min_weight: int = 1) -> dict:
        nodes, edges = self._parse(pattern)
        results: list[tuple[list, list]] = []

        def step(bound: list, triples: list):
            if len(results) >= limit:
                return
            i = len(triples)
            if i == len(edges):
                results.append((bound, triples))
                return
            cur = bound[-1]
            preds, direction = edges[i]
            cands = []
            if direction in ("out", "any"):
                cands += [(cur, k, b, b) for _, b, k in self.G.out_edges(cur, keys=True)]
            if direction in ("in", "any"):
                cands += [(a, k, cur, a) for a, _, k in self.G.in_edges(cur, keys=True)]
            for a, k, b, other in cands:
                if preds and self.G.edges[a, b, k]["predicate"] not in preds and k not in preds:
                    continue
                if other in bound or self.G.edges[a, b, k]["weight"] < min_weight:
                    continue
                if self._node_ok(other, nodes[i + 1]):
                    step(bound + [other], triples + [(a, k, b)])

        for n in self.G.nodes:
            if self._node_ok(n, nodes[0]):
                step([n], [])
        rows = [{"bindings": b, "edges": [self.edge_dict(a, k, c, evidence=2) for a, k, c in t]} for b, t in results]
        rows.sort(key=lambda r: -sum(e["weight"] for e in r["edges"]))
        return {"pattern": pattern, "count": len(rows), "truncated": len(rows) >= limit, "results": rows}

    # ------------------------------------------------------------- analytics
    def evidence_matrix(self, src_type: str = "INTERVENTION", tgt_type: str = "BIOMARKER", top: int = 40) -> list[dict]:
        rows = []
        for a, b, k, d in self.G.edges(keys=True, data=True):
            if self.G.nodes[a]["type"] == src_type and self.G.nodes[b]["type"] == tgt_type:
                rows.append({"source": a, "predicate": d["predicate"], "timescale": d["timescale"],
                             "target": b, "n_docs": d["weight"],
                             "docs": [self.doc_titles.get(i, "?") for i in d["docs"]]})
        rows.sort(key=lambda r: -r["n_docs"])
        return rows[:top]

    def contradictions(self) -> list[dict]:
        """Opposing predicates on the same pair *at a compatible timescale*. An acute effect and a
        chronic null are different claims, not a contradiction; 'unspecified' is compatible with both."""
        out = []
        for a, b in {(a, b) for a, b, _ in self.G.edges(keys=True)}:
            es = self.G[a][b]
            for k1, d1 in es.items():
                for k2, d2 in es.items():
                    if (d1["predicate"], d2["predicate"]) not in OPPOSITES:
                        continue
                    t1, t2 = d1["timescale"], d2["timescale"]
                    if t1 != t2 and "unspecified" not in (t1, t2):
                        continue
                    out.append({"source": a, "target": b, "timescale": t1 if t1 != "unspecified" else t2,
                                "claims": [self.edge_dict(a, k1, b), self.edge_dict(a, k2, b)]})
        return out

    def communities(self, top: int = 12) -> list[dict]:
        U = nx.Graph(self.G)
        if U.number_of_edges() == 0:
            return []
        comms = nx.community.louvain_communities(U, seed=42)
        out = []
        for c in sorted(comms, key=len, reverse=True)[:top]:
            hubs = sorted(c, key=lambda n: -self.G.degree(n))[:6]
            out.append({"size": len(c), "hubs": hubs,
                        "types": dict(Counter(self.G.nodes[n]["type"] for n in c).most_common())})
        return out

    def stats(self) -> dict:
        G = self.G
        return {**self.store.stats(), "nodes": G.number_of_nodes(), "edges": G.number_of_edges(),
                "components": nx.number_weakly_connected_components(G) if len(G) else 0,
                "node_types": dict(Counter(d["type"] for _, d in G.nodes(data=True)).most_common()),
                "predicates": dict(Counter(d["predicate"] for *_, d in G.edges(data=True)).most_common()),
                "timescales": dict(Counter(d["timescale"] for *_, d in G.edges(data=True)).most_common()),
                "top_hubs": [(n, d) for n, d in sorted(G.degree(), key=lambda x: -x[1])[:15]]}


def edge_lines(G, center: str | None = None, with_evidence: bool = False, limit: int = 400, nodes=None,
               edges=None) -> str:
    """Serialize (a sub)graph as triples for prompting — the cookbook's subgraph serialization,
    plus provenance so answers can cite source documents. Pass `edges` (already ranked) to keep their order."""
    if edges is not None:
        edges = list(edges)
    elif center is not None:
        edges = list(G.out_edges(center, keys=True, data=True)) + list(G.in_edges(center, keys=True, data=True))
        edges.sort(key=lambda e: -e[3]["weight"])
    else:
        sub = G.subgraph(nodes) if nodes is not None else G
        edges = list(sub.edges(keys=True, data=True))
        edges.sort(key=lambda e: -e[3]["weight"])
    lines = []
    for a, b, k, d in edges[:limit]:
        line = f"({a}) -[{elabel(d)}]-> ({b})  [n_docs={d['weight']}]"
        if with_evidence:
            ev = "; ".join(f"\"{x['text']}\" <{x['doc']}>" for x in d["evidence"][:2])
            line += f"\n    evidence: {ev}"
        lines.append(line)
    return "\n".join(lines) or "(no relations)"
