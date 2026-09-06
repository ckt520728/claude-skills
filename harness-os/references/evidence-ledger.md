# Evidence Ledger

Every design decision in this plugin traces to a specific finding in a specific
paper. Numbers below were read from the PDFs in `../../Reference/`, not from a
secondary summary. Where the Gemini prototype notes disagreed with the source,
the source wins and the discrepancy is recorded at the bottom.

## Provenance

The corpus in `../../Reference/` is the reference list of **Lilian Weng,
"Harness Engineering for Self-Improvement" (2026-07-04)**,
<https://lilianweng.github.io/posts/2026-07-04-harness/>.

That post is the framing source, not just a bibliography. Two things this plugin
inherits from it directly:

- **The OS analogy.** "Similar to an OS, a harness should encapsulate complicated
  logic while keeping the interface simple." The kernel/skill split here is that
  sentence made concrete — the kernel holds the complicated logic, the skills
  keep the interface small.
- **The RSI framing.** Near-term recursive self-improvement runs through the
  harness rather than through weights, which is why harnesses are worth treating
  as optimisation targets at all.

The post also cites work not present in `Reference/` — Yudkowsky (2008) on
recursive self-improvement, Lu et al. (2026) AI Scientist, Novikov et al. (2025)
AlphaEvolve — so it is the wider map; the fourteen PDFs are the part read in
full here. Every number below was read from those PDFs, not from the post.

## Primary sources

| # | Paper | ID | What it establishes |
|---|---|---|---|
| 1 | Self-Harness: Harnesses That Improve Themselves — Zhang H. et al., Shanghai AI Lab, 2026 | arXiv:2606.09498 | Weakness Mining → Bounded Proposal → Regression Validation |
| 2 | Agentic Harness Engineering (AHE) — Lin J. et al., Fudan/PKU, 2026 | arXiv:2604.25850 | Three observability pillars; change manifests; where the gains actually are |
| 3 | Harness Updating Is Not Harness Benefit — Lin M. et al., PSU/UCSC/Amazon, 2026 | arXiv:2605.30621 | Updating and benefit are separate capabilities with different scaling |
| 4 | Meta-Harness — Lee et al., Stanford/MIT/KRAFTON, 2026 | arXiv:2603.28052 | Prior attempts must stay on the filesystem, not be compressed to scores |
| 5 | ACE: Agentic Context Engineering — Zhang Q. et al., ICLR 2026 | arXiv:2510.04618 | Context collapse and brevity bias; incremental delta updates |
| 6 | Meta Context Engineering (MCE) — Ye et al., PKU, 2026 | arXiv:2601.21557 | Bi-level: the context-management *mechanism* is itself an evolvable skill |
| 7 | ADAS: Automated Design of Agentic Systems — Hu, Lu, Clune, ICLR 2025 | arXiv:2408.08435 | Agents defined in code; meta-agent search over an ever-growing archive |
| 8 | AFlow — Zhang J. et al., ICLR 2025 | arXiv:2410.10762 | Workflow as a searchable code graph (MCTS) |
| 9 | STOP: Self-Taught Optimizer — Zelikman et al., COLM 2024 | arXiv:2310.02304 | Recursive self-improvement of the improver; sandbox-bypass measurement |
| 10 | Darwin Gödel Machine (DGM) — Zhang J. et al. | arXiv:2505.22954 | Open-ended evolution with an archive of stepping stones |
| 11 | HyperAgents (DGM-H) — Zhang J. et al., UBC/Meta, 2026 | arXiv:2603.19461 | Metacognitive self-modification; the improvement procedure is itself editable |
| 12 | AGENCYBENCH — Li K. et al., SII/SJTU/GAIR, 2026 | arXiv:2601.11044 | What 1M-token real-world agentic tasks actually cost |
| 13 | Robin: multi-agent scientific discovery — Ghareeb et al., *Nature*, 2026 | doi:10.1038/s41586-026-10652-y | Full-loop automation of hypothesis generation + data analysis |
| 14 | From AGI to ASI — Genewein et al., Google DeepMind, 2026 | arXiv:2606.12683 | Recursive improvement as one of four pathways; frictions and bottlenecks |

## Findings → design decisions

### Self-Harness (§3.2–3.4)

**Failure signature.** A failure is attributed as a triple: the terminal
verifier-level cause, the causal status of the agent behaviour, and the abstract
agent mechanism the trace exposes. Failures cluster only on *exact agreement of
all three*. The paper is explicit about why: two runs can share a verifier
outcome — a timeout, a missing artifact — while needing entirely different
harness changes, because the underlying behaviours differ.

→ `trace --signature "cause|causal_status|mechanism"` and `mine`, which clusters
deterministically on the exact triple. No semantic similarity, no drift.

**Addressability.** Not every cluster implies a harness edit. Some reflect task
difficulty, unstable outcomes, or model capability limits. Weakly supported or
non-addressable patterns are *excluded rather than forced into a patch*.

→ `addressable` flag in the bundle; [[harness-mine]] states explicitly that
producing no edit is a valid round.

**Bounded proposals.** Diversity across branches, minimality within each branch:
one failure mechanism, one editable surface, no rewrites of the control
architecture. Every proposal ships an audit record naming the targeted failure,
the edited surface, the expected effect, and the regression risks.

→ `manifest` requires exactly those fields.

**Promotion gate.** Held-in measures whether the proposal addressed the evidence
that motivated it; held-out is a regression test on behaviour the proposer never
saw. Only edits that improve without measurable degradation are merged.

→ `--split held_in|held_out`, `gate`, and a loud warning when no held-out
contract exists.

**Result.** All nine model×benchmark combinations improved on *both* splits.
Largest relative gain 132% (Qwen3.5-35B-A3B, AppWorld); largest absolute 40.6 pp
(GLM-5, AppWorld, 44.4% → 85.0%).

### AHE (§3.1–3.3)

**Component observability.** Seven orthogonal, file-level component types at
fixed mount points: system prompt, tool description, tool implementation,
middleware, skill, sub-agent configuration, long-term memory. Each failure
pattern maps to one component class, so every change is localisable and
revertible.

→ [[harness-mine]]'s component table; one component per edit.

**Experience observability.** ~10M raw trace tokens distilled by an Agent
Debugger into ~10K of layered, drill-down evidence, with raw traces still on
disk for verification.

→ On-disk JSONL trace, per-job summary files, progressive disclosure. The main
context holds pointers, never payloads.

**Decision observability.** Every edit carries a self-declared prediction:
expected fixes and at-risk regressions. The next round intersects predictions
with observed task-level deltas to produce a per-edit verdict. Edits become
falsifiable contracts, which is what stops the loop collapsing into trial and
error.

→ `manifest --predict-fix/--predict-regress` and `attribute`. A refuted edit is
rolled back even if the round improved overall.

**Controllability.** The evolving agent writes only inside the harness workspace;
the runs directory, tracer, verifier and model configuration are read-only, and
the seed system prompt is non-deletable. These restrictions block the shortcuts
an unconstrained self-modifier takes — disabling the verifier, swapping the
model, raising the reasoning budget.

→ `guard init` / `guard check`, plus the explicit "never weaken a contract" rule.
The kernel's guard is a **tripwire, not a sandbox** — this is stated in the code
and the skills, because overstating it would be worse than not having it.

**Where the gains are.** Ablation localises the improvement to **tools,
middleware and long-term memory — not the system prompt.** 69.7% → 77.0% pass@1
on Terminal-Bench 2 over ten iterations, above human-designed Codex (71.9%). The
frozen harness transferred to SWE-bench-verified with 12% fewer tokens than the
seed, and gave +5.1 to +10.1 pp across three other model families.

→ Stated prominently in [[harness-os]] and [[harness-mine]]. This is the single
most actionable finding in the corpus and the most counter-intuitive: the
instinct to rewrite the prompt is usually wrong.

### Harness Updating ≠ Harness Benefit

- **Harness-updating is flat in base capability.** Models across capability tiers
  produce updates yielding similar gains; even Qwen3.5-9B's updates are
  comparable to Claude Opus 4.6's.
- **Harness-benefit is non-monotonic.** Weak tier benefits little, **mid tier
  benefits most**, strong tier benefits *less than* mid tier.
- Weak-tier failure modes: failing to activate the relevant harness artifact at
  all, or activating it and then not following it faithfully.
- Recommendation: spend capability budget on the **task-solving agent**, not the
  evolver.

→ The model-routing section of [[harness-os]], and the diagnostic framing that an
executor which stops running `assert` is ignoring the harness rather than
disproving it.

### Meta-Harness

Existing text optimisers compress feedback too aggressively — memoryless,
conditioning only on scalar scores, or restricting feedback to short templates.
Meta-Harness instead gives the proposer filesystem access to the source, scores
and execution traces of *all* prior candidates. +7.7 points on online text
classification with 4× fewer context tokens; +4.7 points on 200 IMO-level
problems across five held-out models.

→ `archive/`, `manifests/`, `evidence/` all persist per round and stay readable.
Rejected proposals are logged, not deleted.

### ACE

Two named failure modes: **brevity bias** (domain insight dropped for concise
summaries) and **context collapse** (iterative rewriting erodes detail over
time). ACE prevents both with structured, incremental updates — a Generator /
Reflector / Curator division of labour. +10.6% on agents, +8.6% on finance, and
effective without labelled supervision using natural execution feedback.

→ `playbook add` appends and dedupes; it never rewrites wholesale. `playbook
mark` / `prune` implement grow-and-refine. Both skills that touch it say so
explicitly, because "just rewrite the summary" is the natural instinct and it is
precisely the failure mode.

### MCE

Bi-level: a meta-level agent evolves context-engineering *skills* via agentic
crossover over the history of skills, executions and evaluations; a base-level
agent executes them and optimises context as files and code. 5.6–53.8% relative
improvement across five domains (mean 16.9%).

→ Why this plugin ships as skills-plus-kernel rather than one script: the
procedure is meant to be edited. Profiles are the base level; the skills are the
meta level.

### ADAS / AFlow / STOP / DGM / HyperAgents

- **ADAS**: agents defined in code, discovered by a meta agent against a growing
  archive; discovered designs transfer across domains and models.
- **AFlow**: workflow as a code graph searched by MCTS; +5.7% average over SOTA,
  and smaller models beating GPT-4o at 4.55% of the cost.
- **STOP**: the seed improver improves itself, discovering beam search, genetic
  algorithms and simulated annealing. The authors are careful that this is *not*
  full recursive self-improvement — the model is unchanged — and they measure how
  often generated code bypasses the sandbox.
- **DGM**: open-ended evolution with an archive of stepping stones; SWE-bench
  20.0% → 50.0%, Polyglot from ~14%.
- **HyperAgents (DGM-H)**: task agent and meta agent merged into one editable
  self-referential program, so the improvement procedure is itself improvable.
  Meta-level improvements (persistent memory, performance tracking) transfer
  across domains and accumulate across runs. Domains include paper review and
  Olympiad grading — i.e. beyond code, where task skill and self-modification
  skill are no longer the same thing. Conducted with sandboxing and human
  oversight.

→ `snapshot` / `rollback` as an archive of stepping stones; STOP's sandbox-bypass
measurement is the direct ancestor of the anti-gaming checklist.

### AgencyBench

6 capabilities, 32 scenarios, 138 tasks. Scenarios average **90 tool calls, 1M
tokens, and hours of execution**. Closed-source 48.4% vs open-source 32.1%.
Scaffold interacts with model: proprietary models perform best inside their
native ecosystems.

→ Calibration for the cost-discipline section. Tasks at this scale are what a
harness is for; a ten-minute task is not.

## Where the prototype notes were wrong

The Gemini notebook notes are a good synthesis. Two claims did not survive
checking against the PDFs, and both would have produced a worse design:

1. **"必須依賴高階模型才能發揮進化後的 Harness 優勢" / must use a top-tier model
   at runtime to benefit.** The actual finding is non-monotonic: *mid*-tier
   models benefit most, and strong-tier models benefit **less** than mid-tier.
   The real risk is a weak model that never activates the harness at all. Design
   consequence: the diagnostic is "is the executor actually invoking the
   harness?", not "is the model big enough?"

2. **AHE's ablation is not mentioned in the notes.** It is arguably the most
   useful result in the corpus — the gain sits in tools, middleware and memory,
   *not* the system prompt. Without it, a repair loop's default move is prompt
   rewriting, which the evidence says is the least productive edit available.

Two other claims checked out:

- DGM's SWE-bench improvement from 20.0% to 50.0% — exact.
- **The attribution to Lilian Weng's "Harness Engineering for Self-Improvement"
  is correct.** An earlier draft of this ledger flagged it as unverified, on the
  grounds that the post is not in `Reference/` and none of the fourteen PDFs cite
  it. That reasoning was backwards: the post is the *source of* the reading list,
  so it would not appear in its own bibliography, and papers published before it
  could not cite it. The post is confirmed at the URL in Provenance above, and
  the OS analogy the prototype builds on is the post's own framing.

  Worth keeping as a lesson: "absent from the evidence I gathered" is not
  "unsupported". The gathering method — a folder of PDFs — could not have
  contained the thing being checked.

---

## v2.1.0 upgrade — the frontier-benchmark corpus

The 2026-09 upgrade extracts three mechanisms from a second body of material: a
Gemini/ChatGPT synthesis of 2026 frontier agent benchmarks and system
architectures (OSWorld 2.0, Agents' Last Exam, ExploitBench/ExploitGym,
SRE-Bench, ScreenSpot-Pro/ScreenSeekeR, the Codex system architecture, and the
recurrent-depth transformer line). The source files are:

- `.../ChatGPT_Work_Code/2026年自主智慧代理評估範式與架構演進綜述.md`
- `.../ChatGPT_Work_Code/Harness OS 插件進化：級聯視覺搜索與動態挑戰驗證.md`
- `.../ChatGPT_Work_Code/harness_agent_plugin.py` (v1 prototype)
- `.../ChatGPT_Work_Code/harness_agent_plugin-v2.py` (v2 prototype)
- `.../ChatGPT_Work_Code/Geiping_2025_..._Recurrent Depth.pdf`
- `.../ChatGPT_Work_Code/Lu_2025_Latent Chain-of-Thought....`

**Verification honesty (this matters — see CLAUDE.md).** Unlike the fourteen
papers in `../../Reference/`, the frontier benchmark papers named above are **not
in this repo's corpus and were not read in full here.** The benchmark statistics
these notes quote (e.g. "18.9% → 48.1%", "16-tier ladder", "average 318 tool
calls") are therefore reported as **from the ChatGPT notes, unverified against a
primary source.** What is adopted is the *design pattern*, not the numbers — and
each pattern below is **independently supported by a paper that IS in the corpus
and was read in full.** That double grounding is deliberate: the frontier notes
supply the framing; the verified corpus supplies the licence to build it.

### Mechanism 1 — invariant constraints (`constraint`)

- **Frontier framing (notes, unverified):** long-horizon agents fail not by
  lacking skill but by *losing track of constraints* over hundreds of steps
  (attributed to OSWorld 2.0). The Codex architecture answers this with an
  invariant prefix layer — hard constraints physically separated from the
  compactible history so they cannot be summarised away.
- **Corpus grounding (verified):** this is the same failure ACE names as
  **context collapse** and **brevity bias** (arXiv:2510.04618, in corpus) — 
  iterative rewriting erodes exactly the domain detail you needed — and the same
  thing Meta-Harness prevents by keeping prior evidence on the filesystem rather
  than compressed to scalars (arXiv:2603.28052, in corpus).

→ `constraint add` / `constraint list`; invariants surfaced verbatim by
`status`, never compacted, never pruned. Distinct from the playbook, which is
*learned and prunable* (ACE grow-and-refine); constraints are *given and
immutable*. This is the on-disk analogue of the Codex invariant prefix.

### Mechanism 2 — dynamic challenge-response (`challenge:` check)

- **Frontier framing (notes, unverified):** ExploitBench replaces binary
  crash/no-crash judging with a per-run **challenge-response oracle** — a fresh
  random token each run that the artifact must dynamically resolve — so a memory
  layout hardcoded from a known CVE cannot pass. The notes also record the
  matching attack: agents that don't exploit the target but instead find a logic
  bug in the *grader* ("gamed runs").
- **Corpus grounding (verified):** this is the direct descendant of STOP's
  measurement of how often generated code **bypasses the sandbox**
  (arXiv:2310.02304, in corpus), and the concrete tool the existing "Anti-gaming"
  section (already in [[harness-os]]) was asking for. The whole loop "optimises
  against the verifier faithfully and relentlessly"; a static verifier is the gap
  it exploits, and freshness is what closes it.

→ new check kind `challenge:<cmd>`: the kernel injects a fresh nonce as
`$HARNESS_CHALLENGE` each assertion; the verifier passes only if it exits 0 **and
echoes that live nonce**, which it can do only by running the artifact against
this challenge. `check_challenge_response.py` is the reusable realisation.
**Stated limit:** this proves the verifier ran live on an unrepeatable challenge;
it does not prove correctness in general, and a verifier that merely re-echoes
`$HARNESS_CHALLENGE` without routing it through the artifact games itself — the
contract author must route the nonce through the deliverable. The kernel provides
the freshness primitive; the oracle is still the author's responsibility, exactly
as with `cmd:`.

### Mechanism 3 — graded capability ladder (`ladder`)

- **Frontier framing (notes, unverified):** ExploitBench scores exploitation on
  a **16-tier capability ladder** (coverage → crash → primitive → arbitrary R/W
  → control-flow hijack → ACE) rather than pass/fail, giving a dense signal that
  distinguishes "crashed by luck" from "built a real primitive." The v1 prototype
  implemented a 7-tier `CapabilityLadderOracle`.
- **Corpus grounding (verified):** Self-Harness's whole loop needs a *dense*
  failure signal to mine (arXiv:2606.09498, in corpus); a binary contract says
  nothing until the end. A ladder is the progress-meter complement to the
  binary promotion gate — it does not replace it.

→ `ladder set` / `ladder assert`: an ordered list of the same checks a contract
uses, scored as the **highest contiguous tier passed** plus a fraction, surfaced
in `status` as `tier/total`. It is a progress meter, explicitly *not* a gate:
promotion still runs through held-in/held-out `gate`, which the ladder does not
touch.

### Deliberately excluded (recorded, not silently dropped)

Two prominent mechanisms in the frontier notes were **not** built into the
general kernel, with reasons:

1. **ScreenSeekeR cascaded visual grounding** (recursive crop + geometric
   inverse-projection back to a 4K canvas). This is GUI-pixel-specific; the
   general Harness OS kernel owns *files, processes and contracts*, not a screen
   coordinate space, so a pixel-grounding module would be dead weight in five of
   the six profiles. The *abstract* lesson it teaches — recursively narrow a
   search while keeping a reversible record of each narrowing step — is already
   how `fork`/decompose + the on-disk trace work. The v2 prototype's
   `ScreenSeekeRVisualGrounder` is kept in `Harness OS workspace`-style reference
   only; a GUI-automation profile could wrap it later if that domain is added.

2. **Recurrent-depth / latent-reasoning transformers** (Geiping 2025; Lu 2025;
   the notes' Nanbeige example). These are *model-architecture* results, not
   harness mechanisms — they change what happens inside the weights, which this
   kernel deliberately does not touch. Their one harness-relevant consequence is
   a caution, not a feature: latent reasoning **hides the chain-of-thought**,
   which *raises* the value of the harness's on-disk trace and change-manifest
   record as the remaining audit surface. That is an argument for the design the
   kernel already has, so it is recorded here rather than acted on. The notes'
   own caveat — gains from extra passes flatten after two — is consistent with
   the corpus's non-monotonic model-tier finding and needs no separate change.
