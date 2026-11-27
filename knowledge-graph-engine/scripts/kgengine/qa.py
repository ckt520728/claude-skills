"""Graph-RAG question answering: seed entities -> k-hop subgraph -> grounded, cited answer."""
from __future__ import annotations

import re

from rapidfuzz import fuzz

from .graph import KnowledgeGraph, edge_lines
from .pipeline import RESEARCH_TOPIC
from .providers import Provider
from .schema import Answer

QA_PROMPT = """Answer the question using ONLY the knowledge graph below (extracted from the user's own paper library on: {topic}).
Each edge lists how many documents support it and evidence quotes with <source document>.

<graph>
{graph}
</graph>

Question: {question}

Rules: cite the specific edges you rely on; name source documents for key claims; say explicitly when
sources disagree; list in `gaps` what the graph lacks to answer fully. Do not use outside knowledge."""


def find_seeds(kg: KnowledgeGraph, question: str, k: int = 6) -> list[str]:
    q = question.lower()
    scored = []
    for n, d in kg.G.nodes(data=True):
        best = 0
        for label in [n, *d["aliases"]]:
            lab = re.sub(r"\s*\(.*?\)", "", label).lower().strip()
            if len(lab) < 3:
                continue
            if re.search(rf"\b{re.escape(lab)}\b", q):
                best = max(best, 100 + len(lab))
            else:
                s = fuzz.partial_ratio(lab, q) if len(lab) >= 5 else 0
                if s >= 90:
                    best = max(best, s)
        if best:
            scored.append((best, kg.G.degree(n), n))
    scored.sort(reverse=True)
    seeds = [n for *_, n in scored[:k]]
    if not seeds:
        seeds = [h["name"] for h in kg.search(question, limit=3)]
    return seeds


def ask(kg: KnowledgeGraph, provider: Provider, question: str, hops: int = 2,
        max_edges: int = 250, seeds: list[str] | None = None) -> dict:
    seeds = [s for s in (kg.resolve_name(x) for x in seeds) if s] if seeds else find_seeds(kg, question)
    nodes = set(seeds)
    frontier = set(seeds)
    for _ in range(hops):
        nxt = set()
        for n in frontier:
            nxt |= set(kg.G.successors(n)) | set(kg.G.predecessors(n))
        frontier = nxt - nodes
        nodes |= frontier
    context = edge_lines(kg.G, nodes=nodes, with_evidence=True, limit=max_edges)
    ans = provider.structured(QA_PROMPT.format(topic=RESEARCH_TOPIC, graph=context, question=question),
                              Answer, role="smart")
    return {"question": question, "seeds": seeds, "subgraph_nodes": len(nodes), **ans.model_dump()}
