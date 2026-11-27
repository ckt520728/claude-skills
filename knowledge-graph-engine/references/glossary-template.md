# CONTEXT — ubiquitous language

| Term | Meaning | Not to be confused with |
|---|---|---|
| **Library** | The user's files on E:\ and G:\ that the engine can ingest. | the *graph* |
| **Document** | One ingested source (PDF, DOCX, MD, URL, pasted text), identified by source path and content SHA-1. | a *chunk* |
| **Chunk** | ~6,000-character paragraph-aware slice of a document; the unit of extraction. Reference lists are cut off before chunking. | |
| **Raw entity / raw relation** | Exactly what the extractor returned for one chunk. Immutable, kept with provenance. | canonical entity |
| **Canonical entity (node)** | A real-world thing after entity resolution; has a type, aliases, documents, optional profile. | |
| **Alias** | A surface form mapped to a canonical entity (`aliases` table). Method = deterministic or llm. | |
| **Claim (edge)** | One `(source) -[PREDICATE]-> (target)` aggregated over all documents that state it. `weight` = number of supporting documents. Carries evidence quotes. | a single mention |
| **Evidence** | A short quote from a chunk supporting a claim, plus its document title and confidence (1.0 reported result, ~0.7 reviewed consensus, ~0.4 hypothesis). | |
| **Ontology gate** | The fixed entity types and predicates in `ontology.py`. Off-list values are normalized or fall back to CONCEPT / RELATED_TO. | |
| **Entity resolution (ER)** | Merging aliases into canonical entities: (1) normalization + acronym linking, (2) LLM clustering inside fuzzy candidate blocks. | deduplicating documents |
| **Hub / profile** | A high-degree node, and the LLM-written summary plus key facts derived only from its claims. | |
| **Provider / role** | LLM backend (claude-cli, anthropic, ollama, openai) and its role: fast = extraction, smart = resolution, summaries, QA. | |
| **Contradiction** | The same entity pair with opposing predicates across documents (e.g. INCREASES vs NO_EFFECT_ON). Shown to the user, never auto-resolved. | |

## Entity types
INTERVENTION · BIOMARKER · BRAIN_REGION · COGNITIVE_DOMAIN · CONDITION · POPULATION · METHOD · MECHANISM · CONCEPT
(definitions in `kgengine/ontology.py`)

## Open terminology questions
- Should "physical activity" (habitual behaviour), "exercise" (structured intervention) and "fitness"
  (VO2max, a BIOMARKER?) stay separate nodes? Currently: PA and exercise are INTERVENTION; fitness is split
  by the extractor. Decide in a grilling session.
- Do acute-bout and chronic-training effects need a predicate qualifier (edge attribute `timescale`)?
