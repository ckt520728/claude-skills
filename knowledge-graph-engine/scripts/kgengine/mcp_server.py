"""MCP server: exposes the knowledge graph as tools to Claude Code / Claude Desktop /
any MCP client.  Registered for this project in .mcp.json as server "kg".

Run manually:  python -m kgengine.mcp_server   (stdio transport)
"""
from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from . import pipeline, qa
from .config import open_kg, provider

mcp = FastMCP("kg", instructions=(
    "Knowledge graph built from the user's research library on physical activity and neurocognitive "
    "aging (EEG/MEG biomarkers, neuroimaging). Use kg_search to find entity names, then kg_entity / "
    "kg_neighbors / kg_paths / kg_match to traverse. Every edge carries evidence quotes and source "
    "document titles - cite them. kg_ask runs a grounded Graph-RAG answer with a separate model call."))
_s: dict = {}


def _kg():
    if "kg" not in _s:
        _s["store"], _s["kg"] = open_kg()
    return _s["kg"]


def _j(x) -> str:
    return json.dumps(x, ensure_ascii=False, indent=1, default=list)


@mcp.tool()
def kg_stats() -> str:
    """Graph size, node-type and predicate distribution, top hub entities."""
    return _j(_kg().stats())


@mcp.tool()
def kg_search(query: str, limit: int = 10, type: str | None = None) -> str:
    """Fuzzy-search entity names/aliases. type: INTERVENTION, BIOMARKER, BRAIN_REGION, COGNITIVE_DOMAIN,
    CONDITION, POPULATION, METHOD, MECHANISM, CONCEPT."""
    return _j(_kg().search(query, limit, type))


@mcp.tool()
def kg_entity(name: str) -> str:
    """Entity card: type, description/profile, aliases, degree, source documents."""
    return _j(_kg().entity(name) or {"error": "not found", "suggestions": _kg().search(name, 5)})


@mcp.tool()
def kg_neighbors(name: str, depth: int = 1, predicates: list[str] | None = None,
                 types: list[str] | None = None, min_weight: int = 1) -> str:
    """k-hop neighbourhood with optional predicate/type filters. min_weight = min # supporting documents."""
    return _j(_kg().neighbors(name, depth, predicates, types, min_weight))


@mcp.tool()
def kg_paths(source: str, target: str, max_len: int = 4) -> str:
    """Simple paths linking two entities (multi-hop explanations)."""
    return _j(_kg().paths(source, target, max_len))


@mcp.tool()
def kg_match(pattern: str, limit: int = 50, min_weight: int = 1) -> str:
    """Cypher-like path pattern. Nodes: (TYPE) (*) (TYPE{name~substring}) (*{name=exact}).
    Edges: -[PRED|PRED2]-> , <-[PRED]- , -[*]- . Example:
    (INTERVENTION)-[INCREASES|IMPROVES]->(BIOMARKER)-[PREDICTS|BIOMARKER_OF|ASSOCIATED_WITH]->(COGNITIVE_DOMAIN)"""
    return _j(_kg().match(pattern, limit, min_weight))


@mcp.tool()
def kg_matrix(src_type: str = "INTERVENTION", tgt_type: str = "BIOMARKER", top: int = 40) -> str:
    """Evidence map: claims between two entity types ranked by number of supporting documents."""
    return _j(_kg().evidence_matrix(src_type, tgt_type, top))


@mcp.tool()
def kg_contradictions() -> str:
    """Entity pairs with opposing claims across documents (e.g. INCREASES vs NO_EFFECT_ON)."""
    return _j(_kg().contradictions())


@mcp.tool()
def kg_ask(question: str, hops: int = 2) -> str:
    """Grounded Graph-RAG answer (separate LLM call) with cited edges and stated gaps."""
    return _j(qa.ask(_kg(), provider(), question, hops))


@mcp.tool()
def kg_add_text(title: str, text: str, extract_now: bool = True) -> str:
    """Add a note/abstract/web text to the library; optionally extract and resolve immediately."""
    k = _kg()
    doc_id, new = pipeline.ingest_text(k.store, title, text)
    rep = {"doc_id": doc_id, "new": new}
    if extract_now:
        p = provider()
        rep["extract"] = pipeline.extract(k.store, p, doc_ids=[doc_id], progress=lambda *_: None)
        rep["resolve"] = pipeline.resolve(k.store, p, progress=lambda *_: None)
        k.reload()
    return _j(rep)


if __name__ == "__main__":
    mcp.run()
