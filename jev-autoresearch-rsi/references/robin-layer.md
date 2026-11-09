# Robin layer

Adapted from Robin (Ghareeb et al., 2026, *Nature*, "A multi-agent system for automating scientific discovery") and the `multi_agent_research_skill` v2.7 protocol (ckt520728/2026-Hermes). The code is in `knowledge_agent/robin.py`, wired into `jev.py`.

It is on by default. Set `robin: false` (dashboard checkbox or `--no-robin`) to reproduce the plain Jev graph exactly; a test checks this.

## Graph with Robin on

```
plan ─► collect (code) ─► Crow swarm (medium: screen relevance + wiki notes) ─► falcon{loop} (high × K, guarded)
                                                                                   │ loop 1 only
                                                                                   ├─► hypotheses1 (planner) ─► tournament1 (auditor = judge)
                                                                                   ▼
                                                                                 draft ─► audit ─► … ─► deliver ─► cite ─► robinqc ─► kb
```

Falcon re-runs every loop, because it must see new evidence. The hypotheses and the tournament run once, in loop 1, to bound the cost.

## What maps to what

| Robin | Here | Decided by code |
|---|---|---|
| Crow: broad retrieval → `citation_library.json` | The real API collection plus the medium-tier notes swarm, which flags `off_topic`. Code writes the library. | `verified` = the API returned a registry identifier (DOI, PMID, arXiv or NCT) with a title. It is never a model's recollection. |
| Falcon: synthesis with no retrieval → `evidence_report.json` | One high-tier call per trajectory. It sees only the on-topic library entries. | The guard keeps a claim only if it cites ≥ 1 on-topic entry and ≥ 1 verified entry, its figures are grounded (NumericGrounding), and it is not a duplicate. |
| Hallucination rate ≤ 2 % (scoreboard metric 10) | Rate = rejected / total, logged per attempt to `hallucination_rate_log.jsonl` | Above 2 %, Falcon is respawned **once**, with the rejected list. Rejected claims never reach the writer. |
| Phase 2 ideas + BTL tournament | `hypotheses1` proposes N candidates (default 6). Code drops any without an on-topic key or with ungrounded figures. With fewer than 3 left there is no tournament (pitfall 51). | ≥ 4 seeded pairings per candidate, **each judged in both orders** and averaged. Ties count half. The Bradley–Terry–Luce fit uses MM (Hunter, 2004) with a weak prior. Output: `ranked_candidates.json` (rank, btl_score, win_rate, games). |
| No 1–10 scores (pitfall 54) | The judge prompt asks A, B or tie | The template is linted for `score`, `rate`/`rating`, `1–10` and `out of 10` before the first match. Candidate text is not linted, because it may mention scores. |
| Parallel trajectories + consensus (opt-in) | K ∈ {1, 3, 5, 8}; default 1 = off | Two claims are the same finding when they share an evidence key **and** their content-token Jaccard is ≥ 0.4. A finding is kept if its agreement ≥ the threshold, which must be in [0.5, 0.75] (pitfall 52: 1.0 keeps nothing). Output: `consensus_findings.json` and `trajectory_agreement_matrix.json`. |
| ReAct self-healing + cascade guard | Every Robin JSON step | The parse or validation error goes back into the same conversation, up to 4 iterations. 3 consecutive identical errors (compared after stripping numbers and quotes) stop the step, with a diagnosis in `react_cascade_log.jsonl`. |
| Claim ledger | `claim_ledger.csv` holds literature, unsupported and hypothesis claims | `observed`, `derived` and `simulated` are forbidden, because nothing is measured. Every literature key must be collected, and every row has an artifact path. |
| Agent 5 preserves or downgrades | The writer gets the verified findings and the top 3 hypotheses, to go under `### Hypotheses for future work`, "never as findings". | QC checks that the heading exists. The auditor must raise a high finding if a hypothesis is stated as an established result. |
| Final status | `robin_status`:<br>• `PROPOSAL_ONLY`<br>• `FAILED_REPRODUCIBILITY` (rate > 2 % after repair)<br>• `DATA_UNAVAILABLE` (no verified claim) | `AI_SCIENTIST_PASS` needs executed analysis, so it is unreachable here. |
| Finch (Docker, `edit_cell` / `submit_answer`) | **Not implemented**: there is no dataset input | Shown as `N/A`, never PASS. No setting exists for it (every setting must change something). If you add a dataset upload, run the analysis in Docker only, and refuse `sandbox: none` outside dev (pitfall 50). |
| Agent 7 monitor | Not a separate LLM | Graph gates plus `robin_qc.md` |

A QC FAIL makes the run `NEEDS_REVIEW`. All artifacts go in `outputs/runs/<id>/robin/`.

## Settings

| Setting | Default | Range | Effect |
|---|---|---|---|
| `robin.enabled` | true | bool | Adds the falcon, hypotheses, tournament and robinqc nodes |
| `robin.candidates` | 6 | 3–10 | Hypotheses entering the tournament. Matches = 2 × ⌈N/2⌉ × 4. |
| `robin.trajectories` | 1 | 1, 3, 5, 8 | Parallel Falcon runs. The dashboard disables the threshold when this is 1. |
| `robin.consensus` | 0.5 | 0.5–0.75 | Agreement needed to keep a finding |

The API refuses out-of-range values; it never clamps them. CLI: `--no-robin --candidates N --trajectories K --consensus T`.

## Cost

The layer adds:
- K high-tier syntheses per loop
- 1 generator call
- 2 × 4 × ⌈N/2⌉ short judge calls (24 for N = 6), split across ≤ 4 at a time

Budget shares, taken from what remains: Falcon 0.12, hypotheses 0.06, tournament 0.10. A Haiku-only, 1-loop run with N = 4 cost about US$0.08–0.09.

## Lessons from the first live runs (2026-11-09)

- **Position bias is real.** A Haiku judge picked the first-shown candidate in 7 of 8 matches. Randomising sides only spreads that bias around; it does not remove it. Judging both orders cancels it: a verdict that flips with the order becomes a tie. With both orders, the next run's first-shown share was 38 %. `position_a_share` is reported on the dashboard. Regression test: an always-"A" judge leaves every candidate level.
- **Full run with strong models** (Opus planner and Falcon, Sonnet executor, gpt-6-astra as auditor and judge; 2 loops; US$2.94):
  - Every Robin stage ran.
  - Falcon's respawn worked: 46 % → 7.1 % in loop 1, 29 % → 14 % in loop 2.
  - gpt-6-astra chose the first-shown candidate in 71 % of decisive games, so counterbalancing matters for strong judges too.
- **Reading the rejected claims turned up a guard bug.** Two-sentence claims whose figures matched the abstract word for word were rejected. `check_numbers` needs a citation in the *same sentence* as each figure, and the guard had appended the keys once, at the end of the claim. Fixed with `checks.check_claim_numbers`, which attaches the keys to every sentence, and used for Falcon claims, hypotheses, notes and gap answers. Regression tests use the live claims, and a mutation check confirms the tests catch a revert. The reported 7–14 % rates were therefore inflated by false positives.
- **The writer copied an internal label.** The paper said "Falcon-verified findings", copied from the prompt heading, and the auditor flagged it as unsupported provenance. The brief no longer names internal steps, and CleanText now fails on engine-only labels ("Falcon-verified", "Crow swarm", "VERIFIED FINDINGS", "RANKED HYPOTHESES"). Topic words such as "pairwise tournament" stay allowed.
- A 0 % hallucination rate on a live run means the guard was not exercised. The offline tests (a hallucinating Falcon is respawned once, then FAILED_REPRODUCIBILITY) are what prove it works.
- An audit FAIL that has nothing to do with Robin (for example, a term the paper never defines) still makes a 1-loop run NEEDS_REVIEW. Use 2 loops so the replan can fix it.
