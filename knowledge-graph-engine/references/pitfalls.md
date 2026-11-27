# Pitfalls (measured in the first build and its widening, Windows 11, 2026-11-27)

Each entry gives the symptom, the cause, and the fix that ships in `scripts/kgengine/`.

## LLM backend

1. **No API key, but Claude Code is logged in.** Use headless Claude Code as the provider:
   `claude -p --model haiku --output-format json --json-schema '<schema>' --tools "" --strict-mcp-config --no-session-persistence --system-prompt "..."`, with the prompt sent on stdin.
   The parsed object is in `structured_output`, and `result` holds the same JSON as a string.
   `--tools ""` stops the model from trying to read files. `--strict-mcp-config` skips loading the user's MCP servers, which cuts start-up time. `--no-session-persistence` keeps thousands of sessions out of `/resume`.
2. **Throughput through `claude -p` is lower than the per-call latency suggests.** A single call takes about 12 s, but 6 workers gave only about 2.5 chunks/min, because process start-up and long JSON output dominate. 286 chunks took about 100 min and cost $1.54 (Haiku). Use the API provider for anything over a few hundred chunks.
3. **Pydantic `$defs`/`$ref` break some structured-output backends.** Inline the refs (`providers.inline_schema`) and strip `title` before sending the schema to the Claude CLI, Ollama or OpenAI.
4. **Make the ontology a `Literal` enum in the schema, not prose in the prompt.** With enums, Haiku never produced an off-list predicate. Without them, the reference document warns of `written_by` vs `author_of` drift.

## Ingestion

5. **PyMuPDF prints MuPDF warnings to stdout,** which breaks JSON piped from the CLI. Call `fitz.TOOLS.mupdf_display_errors(False)`.
6. **Cut the bibliography before chunking.** Otherwise every cited title becomes an entity and doubles the cost. Find the last `References` heading in the second half of the text.
7. **`.gdoc` / `.gsheet` on Google Drive are shortcuts with no content.** Read them through the Google Docs connector and push the text with `kg_add_text`.
8. **The library holds many copies of the same paper:** 168 of 1,010 documents, either the same PDF in several folders or renamed copies such as `Gutmann_2015_…` vs `Gutmann 等 - 2015 - …`. Without dedup, one paper counts as "2 supporting documents", and the evidence matrix looks twice as strong as it is. Fix: word 8-gram shingles of the first chunk, an inverted index, and Jaccard ≥ 0.5. Keep the copy with the most extracted chunks, then the longest.
9. **Dedup false positive from shared boilerplate.** Two Elsevier book "Copyright" pages matched each other. Fix: also require overlap on a second sample (chunk 1, Jaccard ≥ 0.3), and require near-identity (≥ 0.85) for one-chunk documents.
10. **The user's own draft revisions (r1 … r8) are near-duplicates.** Ingest only the latest. Dedup also catches them, but decide this explicitly with the user.

## Entity resolution

11. **Acronym collision over-merge.** The first version linked any two names that shared an acronym, so "Exhaustive exercise (EE)" absorbed "Enriched environment (EE)". Fix: a shared acronym never joins two different full forms. A bare acronym ("IAPF") links only when exactly one full form uses it in that type. Regression test: `test_shared_acronym_does_not_merge_different_entities`.
12. **Sibling concepts get merged despite the prompt rule.** The LLM folded "Physical activity", "Physical exercise" and "Exercise" into one hub with 380 connections. That is a domain decision (habitual behaviour vs structured intervention), not a bug. Put it in `CONTEXT.md` as an open question and ask the user. If they choose to keep them apart, override with alias rows or add the distinction to the prompt.
13. **Resolution cannot be a single prompt per type at corpus scale** (2,668 names). Block first: rapidfuzz token-set ≥ 82 or an acronym match, then batches of ≤ 120 names. Names the model omits stay singletons. 2,668 names → 1,950 entities took about 7 min through `claude -p`. Cache the resolver responses so reruns are free.
14. **Pick the type by majority vote before resolution.** The same name is sometimes typed BIOMARKER and sometimes CONCEPT. Resolving per (name, type) creates duplicate nodes.

## Engineering on Windows / Google Drive

15. **Keep the venv off Google Drive** (`~/.venvs/kgengine`). Drive would sync thousands of files. SQLite on Drive is fine for one writer.
16. **cp950 console:** `UnicodeEncodeError` for "ä" / "等". Set `PYTHONIOENCODING=utf-8` and call `sys.stdout.reconfigure(encoding="utf-8")` in the CLI. Git Bash has no `iconv`.
17. **mcp 2.x renamed `FastMCP` to `MCPServer`.** v1 code fails with `ModuleNotFoundError: mcp.server.fastmcp`. Pin `mcp[cli]>=1.9,<2`, or port the code. Test the server with a real stdio client (`ClientSession.list_tools`), not just an import.
18. **Bug in the CLI filter shortcut:** `doc_ids=ids or [-1]` meant "no filter" turned into "match nothing". Distinguish `None` (no filter) from `[]` (the filter matched nothing).
19. **Python 3.9 is the system default here** (Anaconda), and the code uses `X | None` and `list[...]`. Create the venv with `uv venv --python 3.11`.

## Process

20. **Smoke-test one paper before the batch.** Read 20 triples. Directional predicates with p-values in the evidence (`EE -[INCREASES]-> iAPF, P=0.012`; `SSE -[NO_EFFECT_ON]-> iAPF`) are the quality bar.
21. **Spot-check the largest alias clusters after every resolve.** That is where over-merges show up (pitfall 11 was found this way in under a minute).
22. **Scope the extraction with the user before a full run:** 11.5k chunks ≈ $45 and many hours on `claude -p`. A title-regex pilot (topic AND modality, `--max-chunks 3`) gave a usable graph for $1.6.

## Found at evaluation time (Graph-RAG check)

23. **`--max-chunks 3` misses the results sections.** The first three 6k chunks hold the abstract, intro and methods. The Graph-RAG answer correctly reported that the P300 results of several trials (Khan 2023, Tsai 2018) were never extracted. Fix for the next pass: extract the remaining chunks of the pilot papers only, or find the "Results" heading and always extract that chunk.
24. **Hub edges crowd out specific evidence in Graph-RAG context.** A 2-hop expansion from "Aerobic exercise" reached 1,002 nodes. Ranking edges by `n_docs` and cutting at 250 filled the budget with generic hub claims (PA → cognition), so the specific EEG edges were dropped. Fix: rank edges by distance to the seeds and by type relevance (e.g. keep BIOMARKER edges first for a biomarker question), or use `kg_match` patterns as the retrieval step.
25. **LLM resolution in separate batches gives inconsistent merges.** "Physical activity and physical exercise (PA/PE)" (324 connections) and "Physical Exercise (PE)" (105) stayed apart because the variants landed in different candidate blocks. Run a second, hub-level resolution pass over the top-N nodes per type.
26. **About 10% of edges fall back to RELATED_TO** (377 of 3,853). Watch the predicate distribution in `kg stats`. When the fallback rate is high, add a predicate to the ontology (e.g. `MODULATES`) rather than accepting vague edges.
27. **Keep "low confidence + explicit gaps" as the expected output.** On a private corpus, a grounded answer that says "the graph has no edge linking VO2max to any EEG measure" is the useful result. Do not tune the prompt to sound more confident.

## Found while widening the pilot (sessions 2–3)

28. **Calling `claude` through npm's `claude.CMD` shim mangles long arguments** (the `--json-schema` JSON and the system prompt), because `cmd.exe` re-parses them. Resolve the native `claude.exe` (`providers._claude_exe`, override with `KG_CLAUDE_EXE`).
29. **A Claude Code self-update during a batch run** left `bin/claude.exe` as a 500-byte stub ("native binary not installed"). About 870 calls then failed with `[WinError 216]` / `[WinError 2]`. Skip binaries that are too small to be real. The extraction only marks a chunk done after a successful save, so rerunning picks up exactly the failed chunks (`pending_chunks`).
30. **Decode `claude -p` stderr with `errors="replace"`.** On a cp950 machine the Windows error text is not UTF-8, and a strict decode hides the real error behind a `UnicodeDecodeError`.
31. **Long `claude -p` batches were killed for low system memory,** with each worker spawning a full CLI process. Run 3 workers on a 16 GB laptop. Because the extraction cache is keyed per chunk, a resume costs nothing for finished chunks.
32. **Two machines writing one SQLite file through Google Drive.** The same project was resumed from a second Windows account. Only one writer may run at a time. Check the log's last-write time and `tasklist` before resuming, and use `${USERPROFILE}` in `.mcp.json` instead of a hard-coded account path.
33. **Acute vs chronic effects contradict each other falsely.** "Exhaustive exercise INCREASES iAPF" (acute) and a chronic-training null result are different claims. Add a `timescale` qualifier to every relation (ADR 0004), key edges as `PREDICATE@timescale`, and only flag contradictions at a compatible timescale. Bump `PROMPT_VERSION`, because old extractions lack the field.
34. **The domain's own lumping decision must win over the LLM's batch-to-batch merges** (pitfall 25). Encode it as a curated merge rule (`curation.py`, ADR 0005) that is re-applied on every resolve, rather than patching aliases by hand. Result: PA / physical exercise / exercise became one hub (degree 1,108, 19 aliases), and sub-types (aerobic, acute, training) stayed separate.
35. **Seed-aware Graph-RAG context fixed the "hub crowding" of pitfall 24.** `qa.rank_edges` ranks edges by distance to the seeds, then by edges that bridge two entity types the question asks about (keyword cues), then n_docs, with a 30-edge cap per non-seed node. Together with the results chunks (pitfall 23), the reference question went from *low* confidence with 41 cited edges to *medium* with 81. The answer now uses the P300/ERP, resting-EEG and SEP results, and it still reports the real gap: no edge shows an EEG measure *predicting* cognition. The two changes were not measured separately.
36. **A grounded answer is also an extraction audit.** The re-asked answer pointed out likely direction errors (a theta value that rose, extracted as DECREASES), an "IMPROVES" edge whose quote was only the study aim, and duplicate EEG band nodes. Feed these back into prompt and resolution fixes, and verify them with a context-isolated rubric check before trusting the counts.
