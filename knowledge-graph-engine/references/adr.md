# 0001 — SQLite raw store, NetworkX graph derived on load

**Status:** accepted (2026-11-27)

**Context.** The cookbook keeps everything in memory. Our library is about 1,000 papers and 11.5k chunks.
Extraction is the expensive step. Resolution and the ontology will keep changing.

**Decision.** Store raw per-chunk extractions, aliases, profiles and an LLM response cache in SQLite
(`data/kg.sqlite`). Rebuild the canonical NetworkX `MultiDiGraph` from these tables on load: one edge per
(source, predicate, target), with evidence aggregated across documents.

**Consequences.** Re-running resolution never needs re-extraction and never loses information. Unchanged
chunks are free to re-extract because of the cache. NetworkX works up to roughly 10^5 edges. Past that, export
Cypher (`kg export --format cypher`) to Neo4j. The query API stays the same, but it would need a Neo4j backend.
# 0002 — Model-agnostic providers; headless Claude Code CLI as the default backend

**Status:** accepted (2026-11-27)

**Context.** The goal requires integration with "Claude and other AI models". No `ANTHROPIC_API_KEY` is set on
this machine, but Claude Code is logged in. Ollama is installed locally with gemma4 and llama3.2.

**Decision.** Every LLM call goes through `Provider.structured(prompt, PydanticModel, role)` /
`Provider.text(...)`. There are four implementations: `claude-cli` (`claude -p --json-schema`, default when no
API key), `anthropic` (tool-forced structured output), `ollama` (`format=<schema>`), `openai`
(OpenAI-compatible `response_format=json_schema`). Pydantic schemas are inlined (no `$defs`) for portability.
Claude *consumes* the graph through the MCP server `kg`, and other clients use the REST API.

**Consequences.** Switching models is one flag. Calls through `claude-cli` count against the user's Claude
plan and take about 12 s each (process start-up). Use the API provider for bulk runs once a key exists.
The extraction cache key includes provider and model, so switching models triggers new extraction.
# 0003 — Two-stage entity resolution with fuzzy blocking

**Status:** accepted (2026-11-27)

**Context.** The cookbook sends every entity of a type to the model in one prompt. With thousands of names
that overflows context. It also has two known failure modes: names the model omits disappear, and sub-types
get over-merged into super-types.

**Decision.** (1) Each name gets the majority-vote type of its mentions. (2) Deterministic merge inside a type:
normalized form (case, punctuation, articles, trailing plural) plus acronym linking (`Full Name (ACR)` ↔ `ACR`).
(3) LLM clustering runs only inside candidate blocks (rapidfuzz token-set ≥ 82 or an acronym match), batched
at ≤ 120 names per call. The prompt forbids sub-type → super-type merges. Omitted names stay singletons.

**Consequences.** This scales roughly linearly, apart from the O(n²) fuzzy blocking per type (fine up to about
10^4 names per type). Synonyms with no lexical overlap (e.g. "Edwin" vs "Buzz" Aldrin) are only caught when
the extractor writes the acronym form. Embedding-based blocking is the planned upgrade.
