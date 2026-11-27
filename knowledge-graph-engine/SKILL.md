---
name: knowledge-graph-engine
description: |
  Build a knowledge-graph engine over a personal research library (PDF, DOCX, Markdown, URLs, pasted notes) that integrates with Claude and other models.
  It follows Anthropic's claude-cookbooks capabilities/knowledge_graph pipeline (structured-output NER + relation extraction → entity resolution → hub summaries → multi-hop Graph-RAG), hardened for a corpus of about 1,000 papers:
  - an ontology gate on entity types and predicates;
  - a SQLite raw store with an LLM cache;
  - duplicate-document detection;
  - two-stage entity resolution (normalization + acronyms, then LLM clustering in fuzzy blocks), plus curated merge rules for domain decisions;
  - an acute / chronic `timescale` qualifier on every claim, so contradictions are only flagged like-for-like;
  - Cypher-like pattern queries, evidence matrices, contradiction finding and seed-aware Graph-RAG context ranking;
  - an interactive vis-network HTML view and GraphML/JSON/Cypher export;
  - a FastAPI REST API and an MCP server for Claude Code / Claude Desktop.
  LLM backends are swappable: headless `claude -p --json-schema` on the user's Claude login (no API key), the Anthropic API, Ollama, or any OpenAI-compatible endpoint.
  Ships a working Python package (`scripts/kgengine/`, 9 offline tests) and the measured pitfalls of a first build on Windows (physical activity × neurocognitive aging, EEG/neuroimaging).
  Use when the user asks to "build a knowledge graph", "知識圖譜", "graph RAG over my papers", "turn my library / forgotten files into a second brain", "entity and relation extraction with Claude", "entity resolution", "connect a knowledge graph to Claude via MCP", "evidence map from my literature", "圖譜工程", or reuses the knowledge_graph cookbook on their own documents.
---

# Knowledge-graph engine (Claude-built, model-agnostic)

Turn a pile of documents into a graph of **claims**. Each edge is `(source) -[PREDICATE]-> (target)` and carries evidence quotes and source documents. Multi-hop questions then become graph traversals with citations.

Reference build: *2026 Knowledge graph with Claude*. 1,017 documents / 11.5k chunks were ingested (including Google Docs notes). A pilot of 97 physical-activity × EEG/imaging papers plus the author's own review draft was fully extracted (1,032 chunks) with Claude Haiku through `claude -p`, at about $0.007 per chunk. The resulting graph has 6.3k entities, 14.9k claims and 306 timescale-aware contradictions.

## Architecture

```
sources ─► ingest ─► dedup ─► extract (NER+RE) ─► resolve (ER) ─► summarize ─► query / ask / viz / export
PDF DOCX  chunk 6k  shingle   fast model, JSON    normalize +      smart model   CLI · REST · MCP · HTML
MD URL    cut refs  Jaccard   schema, ontology    acronym, LLM     hub profiles  GraphML · JSON · Cypher
text                          gate, cached        in fuzzy blocks
       ──────── SQLite: documents · chunks · raw_entities · raw_relations · aliases · profiles · llm_cache ────────
                       NetworkX MultiDiGraph DERIVED on load (one edge per claim, evidence aggregated)
```

Key decisions (copy them unless there is a reason not to):
1. **Raw extractions are immutable.** The canonical graph is derived from raw rows + the alias table. Fix resolution by changing aliases, never raw data. Re-resolution never needs re-extraction.
2. **The ontology is a gate.** Entity types and predicates are `Literal` enums in the Pydantic schema, so the model cannot invent `written_by` vs `author_of`. Off-list values normalize to CONCEPT / RELATED_TO.
3. **Two roles:** `fast` (extraction, high volume) and `smart` (resolution, summaries, QA), as in the cookbook's Haiku/Sonnet split.
4. **Edge weight = number of distinct supporting documents**, after duplicate-document collapse. Without dedup, weights lie (see pitfalls).
5. **Domain decisions are rules, not hand edits.** Lumping choices (e.g. PA = physical exercise = exercise) live in `curation.py` and are re-applied on every resolve. Acute and chronic effects are separate edges (`PREDICATE@timescale`).
6. **Every answer cites edges.** Graph-RAG prompts say "use only this graph" and return `cited_edges` plus `gaps`.

## Build order

1. **Scope first (cheap, no LLM).** Ingest everything and look at counts. Pick a pilot with a title regex (topic AND modality), with `--max-chunks 3` (abstract + intro + early results). Leave out your own draft revisions except the latest.
2. **Smoke test one paper** with the real model and read the triples before any batch run. Check that the predicates are directional, the evidence is quoted, and confidence separates results from hypotheses.
3. **Run the batch in the background** with a log file. `claude -p` manages about 1.5–2.5 chunks/min; use 3–6 workers (3 on a 16 GB laptop). Use the API provider for big runs. Only one machine may write the SQLite file at a time.
4. **Dedup → resolve → summarize → viz.** Spot-check merges, the largest hubs and the contradictions list.
5. **Wire up integrations:** `.mcp.json` for Claude Code, the same block in `claude_desktop_config.json` for Desktop, and `kg serve` for developers.

## Using the bundled package

```bash
cp -r scripts/kgengine scripts/tests scripts/pyproject.toml <project>/
uv venv --python 3.11 ~/.venvs/kgengine          # keep the venv OFF Google Drive / OneDrive
uv pip install --python ~/.venvs/kgengine/Scripts/python.exe -e "<project>[dev]"
PY=~/.venvs/kgengine/Scripts/python.exe
export PYTHONIOENCODING=utf-8 KG_LIBRARY="D:/papers;E:/more" KG_TOPIC="<one-sentence research focus>"
$PY -m pytest -q -p no:cacheprovider               # 9 offline tests (FakeProvider)
$PY -m kgengine ingest --library                    # also runs dedup
$PY -m kgengine extract --max-chunks 3 --title "REGEX" --workers 6
$PY -m kgengine resolve && $PY -m kgengine summarize --top 20 && $PY -m kgengine viz
```

To adapt the domain, edit `kgengine/ontology.py` (`ENTITY_TYPES`, `PREDICATES`, `SYNONYMS`, `RESEARCH_TOPIC`) and bump `PROMPT_VERSION` in `pipeline.py`. The extraction cache is keyed on it.

Providers: `--provider claude-cli|anthropic|ollama|openai`, plus `KG_FAST_MODEL` / `KG_SMART_MODEL`. The default is `anthropic` if `ANTHROPIC_API_KEY` is set, otherwise `claude-cli`.

## Query surface

| Query | CLI / MCP tool |
|---|---|
| fuzzy entity lookup | `search` / `kg_search` |
| entity card (aliases, profile, documents) | `entity` / `kg_entity` |
| k-hop neighborhood with predicate/type/min-docs filters | `neighbors` / `kg_neighbors` |
| multi-hop explanation between two entities | `paths` / `kg_paths` |
| pattern: `(INTERVENTION)-[INCREASES\|IMPROVES]->(BIOMARKER)-[PREDICTS]->(*)`, `[INCREASES@acute]`, `(BIOMARKER{name~alpha})<-[*]-(INTERVENTION)` | `match` / `kg_match` |
| evidence map between two types | `matrix` / `kg_matrix` |
| opposing claims (INCREASES vs DECREASES / NO_EFFECT_ON) | `contradictions` / `kg_contradictions` |
| Louvain topic clusters | `communities` |
| grounded answer with cited edges and gaps (context ranked by seed distance and asked-about types) | `ask` / `kg_ask` |
| add a note and extract it now | `kg_add_text` / `POST /ingest/text` |

## Project hygiene that paid off
- `CLAUDE.md` names the goal, the library roots, the commands, the provider rules and which thinking skills to use (grill-with-docs; the finding-unknowns series).
- `CONTEXT.md` is the glossary (Document / Chunk / Raw entity / Canonical entity / Claim / Evidence / Ontology gate), and `docs/adr/` holds the decisions.
- `handoffs.md` gets the newest entry at the top: state, decisions, open questions, the next 3 actions.

Read `references/pitfalls.md` (36 pitfalls) before the first batch run. `references/adr.md` holds ADRs 0001–0005.
