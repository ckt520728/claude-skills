# Autonomous Discovery Lab dashboard: lessons and pitfalls (2026-11-12)

**Project:** upgrade a preliminary "autonomous scientific discovery" page into an interactive dashboard with a simulation, grounded in browser research (lean-lang.org, metr.org) and local papers
**Skill updated:** `jev-autoresearch-rsi/`
- template `discovery_lab.html`
- `/discovery-lab` route
- honesty test
- `references/discovery-lab-manual.md`

**Environment:** Windows 11, PowerShell 5.1 and Git Bash, uv, Python 3.12, Claude in Chrome, Playwright with system Chrome

> Methods and lessons only. No keys, no private data.

## One-line summary

**A simulation that "looks right" can still teach the wrong lesson.** The first model made the AI agent lose to a random planner. Only a multi-seed sweep showed this, and fixing it meant finding the mechanism, not tuning until it won.

## What was built

| Item | Result | Evidence |
|---|---|---|
| Dashboard | KPIs, control rail, search map (belief / ground truth), discovery curve with a live 20-seed batch, agent graph, event log, test-time-scaling chart, METR chart, BTL tournament, claim ledger, Lean-inspired proof gate, source cards | 0 console errors; every control clicked; 375 px has no horizontal scroll |
| Real data | METR Time Horizon 1.1, 18 frontier models (minutes); doubling 128.7 d since 2023 | read from the page's own data object in the browser |
| Measured lesson (materials, 20 seeds) | agent 3.0 targets / 0.5 false promotions vs random 1.3 / 3.4. Without the literature prior the agent drops to 1.9 targets | the in-page batch reproduces the external sweep exactly |
| Skill sync | fresh scaffold passes 214 tests (213 + the discovery-lab test) | `pytest -q` |
| User manual | controls, panels, guided exercises, what is real vs simulated, troubleshooting | `references/discovery-lab-manual.md` |

## Pitfalls and fixes

1. **The page text did not hold the numbers.** METR's page shows a chart, but per-model horizons live in an inline JS object (`benchmarkDataV1_1`). Read it with the browser's JavaScript tool, then check the units against visible text: 1044.8 matches the page's "17 hr", so the values are minutes.
2. **Benchmark versions disagree.** METR's FAQ gives GPT-5 about 2 h 17 min (TH 1.0); TH 1.1 data gives 203 min. Always name the version.
3. **Extraction can be blocked.** `document.body.innerText` on lean-lang.org was refused by the extension ("cookie/query string data"). Selecting `h1, h2, h3, p, li` worked.
4. **Quote the PDF you have, not the figure you remember.** The local A-Lab PDF's abstract says 36 of 57 targets in 17 days. Other versions circulate different numbers.
5. **A blog is a concept source, not a data source.** The test-time-scaling series was used for ideas only; none of its benchmark figures were reused.
6. **The first simulation inverted the lesson.** Three separate causes, each found by measuring:
   - The UCB uncertainty bonus outweighed every observed value, so the agent only spread samples out. Fixed by rescaling κ.
   - The agent kept re-confirming one peak. Fixed with a novelty penalty near promoted or refuted claims.
   - Replicates required ≥ 0.80, so true targets near the threshold failed by regression to the mean. Now they confirm at 0.80 − σ.
7. **Do not tune until the agent wins.** After the fixes the agent still only tied random on targets, while cutting false discoveries 3–5×. The honest next step was the mechanism the A-Lab paper credits: literature-proposed recipes. It went in as a toggle, so users can see that prior knowledge drives target gains and verification drives fewer false discoveries.
8. **Put the batch in the page.** A static sentence like "the agent wins 16 of 20" breaks the moment settings change. A live 20-seed batch button measures it with the user's settings.
9. **A rewrite silently broke an existing test.** The old page carried honesty labels ("SIMULATED EDUCATIONAL MODEL", "not a real Lean runtime") that `test_agent.py` asserts. The browser smoke test passed. Only the full pytest run caught it. The labels were restored, not the test weakened.
10. **Screenshots catch what code checks miss:** two SVG label collisions (curve end labels; METR last point against the band text). An end-label de-collision helper fixed them.
11. **Playwright's bundled browser was missing** after a version bump. `launch(channel="chrome")` used the installed Chrome without a download.
12. **`sed` with a Windows path containing backslashes and CJK failed** ("Invalid back reference"). Use Python string replacement for path edits.
13. **The start script opens the root page.** To land on a sub-page, start the server in the background, poll until it returns HTTP 200, then open the URL.
14. **The local clone was behind.** Fetch before pushing: the remote had 5 newer commits from other sessions.

## Reusable rules

- Before trusting a simulation's headline, run it across ≥ 20 seeds against a baseline that shares the same noise and budget.
- When a model gives the wrong answer, look for the missing mechanism in the sources before touching parameters.
- Label every number as real (with fetch date and version), quoted (with file), or simulated.
- After rewriting any served page, run the full test suite, not just the browser smoke test.
