# Jev Autoresearch RSI: lessons and pitfalls (2026-11-08)

**Project:** a custom autoresearch agent using the Jev planner, executors and auditor; a knowledge-base dashboard with RSI; an Obsidian Second Brain wiki
**Skill produced:** `jev-autoresearch-rsi/`
**Environment:** Windows 11, PowerShell 5.1 and Git Bash, uv, Python 3.12, Claude Agent SDK, OpenAI and Gemini (OpenAI-compatible), `nlm` 0.16.1, Edge + Playwright

> Methods and lessons only. No keys, no patient data, no private paths beyond placeholders.

## One-line summary

**The model writes. Code decides what counts as verified. The page only shows what actually happened.** Reading the outputs by hand still found four defects that every automated check had passed.

## What was built

| Item | Result | Evidence |
|---|---|---|
| Jev graph engine | plan → collect → notes swarm → draft/checks/repair → audit → replan → deliverables → citation lookup → KB merge → KB RSI | 167 offline tests; mutation-checked budget split |
| Providers and tiers | Claude, OpenAI and Gemini; `@effort` suffix; priced tiers; auditor on another provider | live ping of 4 of 5 models, US$0.0006 in total; Argon got HTTP 429 (quota) |
| Gemini Notebook source | LIVE through the `nlm` CLI | 207 notebooks visible; engine query returned clean UTF-8 |
| Second Brain wiki | topic, concept, source and gap pages in managed blocks; vault index and log appended | 67 pages after two runs; 0 broken links, orphans or unsourced claims |
| Full demo run | COMPLETED, US$1.46, 544 s | audit FAIL → replan → PASS (0.86); 18 sources; 66/66 numbers grounded; 0 citation problems |
| Blog | staged in a fresh clone, committed locally, **not pushed** | rendered in Edge, 0 page errors |

## Top lessons

1. **Listed is not usable.** A model can appear in `/models` and still return 429. Ping each model before a paid run.
2. **"Connected" in the coding agent is not "connected" in the engine.** The notebook MCP worked in the agent, but the engine calls a CLI, and an older copy of that CLI came first on PATH.
3. **The auditor earns its cost on another provider.** gpt-6-astra failed loop 1 with one high finding, and the replan fixed it.
4. **Reading the outputs is a step, not a courtesy.** It found a wrong zh-TW term, a slug cut mid-word, a truncated English chart label and an English notice in a Chinese post. Each became a test.
5. **Fitness built on absolute counts punishes growth.** The score fell from 0.906 to 0.879 while quality held. Read the components before reading the trend.
6. **Secrets go where tooling expects them.** Keys pasted into the tracked `.env.example` were invisible to the engine and one commit away from a public repo.

The full pitfall table is in `jev-autoresearch-rsi/references/pitfalls.md`.

## Open items

- Blog push awaiting the owner's approval.
- Possible normalisation of the KB fitness score by concept count.
- No per-call token cap on OpenAI-compatible calls.
- The blog check does not detect Simplified Chinese characters.
- `gemini-4-argon` still needs billing enabled.
- macOS and Linux runs not yet done.
