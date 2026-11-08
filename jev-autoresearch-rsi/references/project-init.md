# Project init (the "/init" step)

Create these in the new project root before the first run.

| File | Contents |
|---|---|
| `CLAUDE.md` | goal, layout table, commands, hard rules (from `SKILL.md`), Second Brain rules, which skill to use at which stage, verification ladder, environment notes |
| `AGENTS.md` | one line: "Read CLAUDE.md; it applies to every agent." It is read by Codex, Gemini CLI, Antigravity and OpenCode |
| `CONTEXT.md` | glossary: Run, Loop, Node, Evidence key, Managed block, Fitness, Promotion, Tier, Role |
| `docs/adr/0001-architecture.md` | why the graph lives in the engine, which providers, what is out of scope |
| `handoffs.md` | newest first. Each entry has state, evidence (commands and numbers), next step, open risks, and deviations from the plan |
| `.gitignore` | `.env`, `.phi_blocklist.txt`, `.rsi/`, `outputs/`, `references/`, `.venv/` |

## Skills by stage (where available)

| Stage | Skill |
|---|---|
| Domain decisions and naming | `grill-with-docs` (user-invoked), which updates `CONTEXT.md` and `docs/adr/` |
| Before work | `map-vs-territory`, `blindspot-pass`, `reference-anchor`, `decision-first-plan` |
| During work | `deviation-log`: record every departure in `handoffs.md` |
| Before accepting | `verify-with-rubric`, `comprehension-quiz` |
| Decks | `soil-deck-pipeline`, `soil-html-deck` |
| Blog | `publish-lab-blog` |
| Planner / executor / auditor | `jev-engineering` |

## Building the engine with the engine's own roles

Building the project itself can use the same roles:
1. The planner writes TaskSpecs per module (KB writer, KB RSI, renderers, dashboard).
2. Executors build the modules in parallel, each with its own tests.
3. An auditor reviews each wave before integration.

In the original build, the wave-1 audit found 4 high findings, and all were fixed with regression tests:
- a cancel was recorded as a failure
- the parallel budget could overspend
- an audit PASS was accepted even with a high finding
- a sanitizer could be bypassed with HTML entities
