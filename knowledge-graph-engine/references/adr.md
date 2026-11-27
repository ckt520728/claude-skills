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

# 0004 — Acute vs chronic effects are separate edges (`timescale` qualifier)

**Status:** accepted (2026-11-27, user decision)

**Context.** One exercise can have opposite-looking results depending on the time frame. A single bout raises
iAPF or P300 amplitude for minutes to hours, while months of training may or may not change the resting value.
With one edge per `(source, predicate, target)`, these results were pooled. The graph reported false
contradictions (acute INCREASES vs chronic NO_EFFECT_ON) and hid real ones.

**Decision.**
- Every extracted relation carries `timescale ∈ {acute, chronic, unspecified}` (`ontology.TIMESCALES`):
  - **acute**: a single bout or session, measured during it or shortly after.
  - **chronic**: repeated training over weeks or longer, or long-term habitual activity / fitness.
  - **unspecified**: not an intervention effect (MEASURED_BY, IS_A, …), or the text does not say.
- The JSON schema makes the field required for the LLM. The pydantic default (`unspecified`) keeps old rows
  and fixtures valid. `PROMPT_VERSION` is bumped to `extract-v2`.
- The canonical graph has one edge per `(source, predicate, timescale, target)`. The edge key is
  `PREDICATE` or `PREDICATE@acute|chronic`. Code reads the predicate from the `predicate` attribute,
  never from the key. Labels show `INCREASES|acute`.
- **Contradictions** are flagged only at a compatible timescale: the same timescale, or one side `unspecified`.
  An acute effect next to a chronic null is reported as two claims, not as a contradiction.
- Patterns accept qualified predicates: `(INTERVENTION)-[INCREASES@acute]->(BIOMARKER)`. A bare `INCREASES`
  matches every timescale.
- The 97 pilot documents were fully re-extracted with v2, so older claims also carry a timescale.

**Consequences.** More edges, each with lower `n_docs`. Evidence for one claim is no longer pooled across
timescales. That is the intended trade-off. Habitual activity and structured training share `chronic`. If the
two need to be told apart later, add a value here (and bump the prompt version) rather than adding a predicate.

# 0005 — Curated merges; "physical activity", "physical exercise" and "exercise" are one node

**Status:** accepted (2026-11-27, user decision)

**Context.** Resolution left the general exposure split in two. The LLM merged 13 surface forms into
"Physical activity and physical exercise (PA/PE)" (324 connections), but "Physical Exercise (PE)" (105) stayed
separate. The prompt rule against sub-type → super-type merges keeps the resolver from fixing this by itself.
Any manual alias edit would be wiped by the next `resolve`, which rewrites the alias table.

**Decision.**
- The user decided that the general terms *physical activity*, *physical exercise* and *exercise* are **one
  node**: `Physical activity / exercise (PA)` (INTERVENTION).
- User decisions live as rules in `kgengine/curation.py` (`CURATED_MERGES`). They run after the deterministic
  and LLM stages on every `resolve`. Their aliases are written with `method = 'curated'`. Raw extractions are
  untouched. Deleting a rule undoes it.
- The match rule: a name merges if all its word tokens come from {physical, activity, exercise, PA, PE, and, or}.
  A cluster whose canonical name matches moves whole. Otherwise only the matching members move.
- Sub-types stay separate: aerobic exercise, exercise training, exercise intervention, acute exercise,
  physical activity level, and so on.

**Consequences.** This hub absorbs every general-exposure claim, and acute versus chronic is carried by the
edge `timescale` (ADR 0004). Habitual PA and structured exercise are not told apart at this node. Studies that
need that distinction should use the sub-type nodes.
