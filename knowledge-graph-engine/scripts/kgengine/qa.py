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


# Question words -> entity types the answer is probably about (used to rank context edges).
_TYPE_CUES = {
    "BIOMARKER": r"eeg|meg|erp|p300|p3\b|n2\b|alpha|theta|beta|gamma|iapf|paf|oscillat|power|biomarker|bdnf|"
                 r"volume|thickness|white matter|fa\b|connectivity|bold|fmri|mri|pet|amyloid|tau|brain age",
    "COGNITIVE_DOMAIN": r"cogniti|memory|executive|attention|inhibit|processing speed|mmse|moca",
    "BRAIN_REGION": r"hippocamp|prefrontal|cortex|cortical|region|lobe|network",
    "MECHANISM": r"mechanism|pathway|why|how does|mediat|neurotroph|plasticity|angiogen",
    "POPULATION": r"older adult|elderly|aging|ageing|mci|dementia|alzheimer|young",
    "INTERVENTION": r"exercise|training|activity|aerobic|resistance|tai chi|intervention|fitness",
}


def wanted_types(question: str) -> set[str]:
    q = question.lower()
    return {t for t, rx in _TYPE_CUES.items() if re.search(rx, q)}


def rank_edges(G, seeds: list[str], dist: dict[str, int], question: str, per_node_cap: int = 30):
    """Seed-aware context ranking (pitfall 24): closer to the seeds first, then edges whose endpoints
    are of the types the question asks about, then specific (non-hub) edges, then n_docs.
    A per-node cap keeps one hub from filling the whole budget."""
    want = wanted_types(question)
    seedset = set(seeds)
    sub = G.subgraph(dist.keys())

    def key(e):
        a, b, _, d = e
        dsum = dist[a] + dist[b]
        tmatch = len({G.nodes[a]["type"], G.nodes[b]["type"]} & want)  # bridging two asked-about types wins
        hub = max(G.degree(n) for n in (a, b) if n not in seedset) if not {a, b} <= seedset else 0
        return (dsum, -tmatch, -d["weight"], hub)

    used: dict[str, int] = {}
    out = []
    for e in sorted(sub.edges(keys=True, data=True), key=key):
        a, b = e[0], e[1]
        caps = [n for n in (a, b) if n not in seedset]
        if any(used.get(n, 0) >= per_node_cap for n in caps):
            continue
        for n in caps:
            used[n] = used.get(n, 0) + 1
        out.append(e)
    return out


def ask(kg: KnowledgeGraph, provider: Provider, question: str, hops: int = 2,
        max_edges: int = 250, seeds: list[str] | None = None) -> dict:
    seeds = [s for s in (kg.resolve_name(x) for x in seeds) if s] if seeds else find_seeds(kg, question)
    dist = {s: 0 for s in seeds}
    frontier = set(seeds)
    for h in range(1, hops + 1):
        nxt = set()
        for n in frontier:
            nxt |= set(kg.G.successors(n)) | set(kg.G.predecessors(n))
        frontier = nxt - dist.keys()
        for n in frontier:
            dist[n] = h
    nodes = set(dist)
    context = edge_lines(kg.G, edges=rank_edges(kg.G, seeds, dist, question), with_evidence=True,
                         limit=max_edges)
    ans = provider.structured(QA_PROMPT.format(topic=RESEARCH_TOPIC, graph=context, question=question),
                              Answer, role="smart")
    return {"question": question, "seeds": seeds, "subgraph_nodes": len(nodes), **ans.model_dump()}
