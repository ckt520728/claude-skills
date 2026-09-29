# HANDOFFS

One entry per working session, newest first. Keep entries short and point at artifacts
rather than restating them — `CLAUDE.md` holds the standing brief, `UNKNOWNS.md` holds the
open questions, the playbooks hold the substance.

---

## 2026-09-29 (v1.1) — Routing across platforms, self-switching, economics

**Goal.** Extend the skill with model self-routing/switching across agent platforms on three
named tiers, deeper tool-call gating, richer real-time control, composite decision processes,
and economics that judge on cost per completed task.

**Tier assignment, taken as given from the user's platform inventory.**

| Tier | Anthropic | OpenAI | Google |
|---|---|---|---|
| high | Claude Opus 5.5 | GPT-6 Astra · Sol-high | — |
| medium | Claude Sonnet 5.5 | GPT-5 Terra-high | Gemini 3.6 Flash-high |
| low | Claude Haiku 4.5 | GPT-5 Luna-high | Gemini 3.6 Flash-medium |

**Built.**
- `assets/jev/models.json` — the registry, as **data**. A tier is a `(model, effort)` pair,
  which is why Gemini 3.6 Flash appears in two tiers. Prices and ids mostly `null` by design.
- `assets/jev/routing.py` — `Registry`, `route_task()`, `switch_cost()`, `worth_switching()`,
  `self_route()`, `PolicyStop`.
- `assets/jev/economics.py` — `compare_policies()`, `expected_task_cost()`, `BreakEven`,
  `cascade_economics()`, `loop_overhead()`, `tier_cost_table()`.
- `assets/jev/toolgate.py` — `ToolGate`: 8 capability classes, per-capability thresholds,
  batched gating, normalised verdict cache, health stats, audit log.
- `assets/jev/control.py` — `ControlLoop` (null action, tick deadline, observation cache,
  stuck detection, independent done-verification), `RiskLimits`, `classify_regime()`.
- `assets/jev/compose.py` — `run_plan()` (DAG), `speculative()`, `two_stage_choice()`,
  `shortlist_then_choose()`, `ensemble()`, `debiased_pairwise()`.
- `references/15-model-registry.md`, `16-self-switching.md`, `17-composite-decisions.md`;
  substantial extensions to `01`, `03`, `08`, `11`.
- `examples/route_models.py`; `eval/test_smoke.py` (**108 behavioural checks**, stub backend,
  wired into `checks.sh`).

**Three findings worth carrying forward.**
1. **The "borrow a cheaper model for one step" rule is conditional, not absolute.** A round
   trip pays iff `Y*(A_out - B_out - A_in) > B_in*(X + Z)`. At a 1.7x output gap (5/25 → 3/15)
   the re-read dominates and it never pays; at 12x (10/50 → 0.8/4) it does. The first draft of
   `16-self-switching.md` asserted the absolute rule and the demo contradicted it — the formula
   is now derived in the doc and checked against the implementation on five price pairs.
2. **A router must beat "start cheap and climb on failure", not "always use the high tier".**
   On a shallow capability gradient it does not, at any accuracy. `router_breakeven_accuracy`
   answers this directly and `references/01` now says so.
3. **Completion rate must sit beside cost.** With retries modelled as independent, "always low"
   priced cheapest; it completes 62% of tasks. `TierProfile.retry_recovery` (0.25) makes retries
   decay, and `PolicyCost` carries completion as a column.

**Bugs found and fixed while testing.**
- `router_breakeven_accuracy` returned `None` for both "wins always" and "never wins" —
  indistinguishable, and it reported a win the sweep contradicted. Now returns `BreakEven`
  with an explicit status.
- `route_task` on data class `secrets` raised a generic "no model available". Now `PolicyStop`,
  with the reason and an instruction not to retry without the filter.
- `worth_switching` reported "break-even below 0.000 Mtok" where the truth is "no context size
  makes it pay".
- `checks.sh` assumed `python` on PATH; a shell launched from the Stop hook inherits a PATH
  that often lacks it. Resolves `$PYTHON` / `python3` / `python` / `py` now.

**State.** `bash .claude/checks.sh` passes: 18 playbooks, registry integrity, 108 behavioural
checks, every hook and example compiling.

**Not done, and deliberately.** Still no live API call and no measured success rate or
threshold. Seven of nine models have no price and six have no `api_id`, so the economics layer
runs on synthetic inputs — labelled `SYNTHETIC` wherever it appears. See `UNKNOWNS.md` #11-#20.

**Next session, in order.**
1. **Fill `models.json`** — nine ids and nine price pairs, dates in `price_source`. Half an
   hour, and it converts the economics layer from arithmetic to measurement.
2. Set `TYPESAFE_API_KEY`, run `examples/router.py`, confirm the price page.
3. Label 100 real requests with the tier that actually completed them; derive `success_rate`
   per tier; re-run `examples/route_models.py --economics` and see whether a router is worth
   building at all on this traffic.

---

## 2026-09-29 — Project initialised, skill built

**Goal.** Build an embedded JEV-engineering skill usable by Claude Opus 5.5+, GPT-6 Astra+,
and other agents, covering nine decision use cases; initialise the project with a
CLAUDE.md/AGENTS.md and a handoffs file.

**Sources read.** Two reference archives from
`E:\USB_2019_2020_ADATA\Artificial intelligence\Agent Loop Engineering\` — the
*JEV-as-a-Judge* paper (Li et al., CMU, 2026), the *Jev in the Agent Loop* guide (@N01ennn),
the 10-step roadmap (@0xCodila), the Loop-Engineering-meets-Jev article (@polydao), and two
prior analysis notes. Then verified the API against `docs.typesafe.ai` directly, because the
articles disagree with each other.

**Decisions taken (put to the user, all three recommendations accepted).**
Portable skill pack plus plugin manifest · pluggable `decide()` with Jev as default ·
one skill plus nine reference playbooks. Rationale and the alternatives in `UNKNOWNS.md`
quadrant 2.

**Built.**
- `skills/jev-engineering/SKILL.md` — the portable skill: tri-part split, KV-cache-tax
  argument, three primitives, seven rules, confidence gate, fork inventory, playbook index.
- `references/00-14` — primitives and wire format; nine use-case playbooks; threshold-tuning
  protocol; economics; failure modes; portability; audit protocol.
- `assets/jev/` — stdlib-only package: `decide()` over a pluggable provider, `gate()` with
  four exits, `cascade()`, per-action thresholds, `aligned_pairwise()`, resumable bulk labeller.
- `assets/examples/` — `router.py`, `triage_inbox.py`, `rerank.py`, `tune_threshold.py`.
- `.claude/hooks/jev_gate.py`, `jev_done.py`, `checks.sh`, `settings.json.example`.
- `CLAUDE.md`, `AGENTS.md`, `UNKNOWNS.md`, `.claude-plugin/`.

**Verified by running, not by reading.**
- All three primitives round-trip; validation rejects 1-option `Choice`, numeric `Score`
  levels, blank criteria, empty instructions; warns on a missing `other`.
- Gate decision matrix, 6/6 cases — including `external` at confidence 0.99 still asking,
  and `other` at 0.99 never auto-approving.
- Gate fail-safe paths: missing key, malformed event, hard-rule block, empty command.
- Bulk labeller: checkpoint resume made exactly 1 new call for 1 new row over 12 cached;
  exit-option rows excluded from the confident set; probabilities survive the round-trip.
- Threshold sweep on synthetic data: AUROC 0.837, gate between random and oracle, held out
  on the test split.

**Two things learned the hard way, both now encoded.**
1. Writing `.claude/settings.json` with a hooks block activated it mid-session, and the gate
   failed on a relative path once the working directory changed. Hooks now ship inert in
   `settings.json.example` using `$CLAUDE_PROJECT_DIR`, with the reason written down in
   `CLAUDE.md`.
2. Python here is 3.9, so runtime `X | Y` unions break at import. `assets/jev/` is 3.9-safe
   and that is now an invariant.

**State.** Complete and self-consistent. `bash .claude/checks.sh` passes.

**Not done, and deliberately.** The live API has never been called — every test used a stub
provider, so no real request has been made and no threshold has been tuned against real
traffic. The `$0.042/M` price, which every cost figure inherits, could not be confirmed by
direct fetch. See `UNKNOWNS.md` quadrant 4.

**Next session, in order.**
1. Set `TYPESAFE_API_KEY`, run `examples/router.py`. Closes the largest unknown and confirms
   the price page in the same pass.
2. Enable `PreToolUse` only, from `settings.json.example`. Measure for a week before adding
   the Stop hook.
3. Label 150 items from a real workload; run `examples/tune_threshold.py`; record the chosen
   `tau` beside the constant with its date and label set.

**Suggested skills.** `map-vs-territory` or `blindspot-pass` before restructuring the skill ·
`writing-great-skills` before editing `SKILL.md` (watch for duplication between it and the
playbooks) · `grilling` for an unresolved design decision · `handoff` to append the next entry.
