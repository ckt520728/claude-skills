# Profile verifiers

Deterministic checks for the deliverables the domain profiles describe. Each is a
standalone CLI that exits **0 = pass / 1 = fail**, so it drops straight into a
contract:

```bash
$K contract --name consistency --target draft/proposal.md --split held_in \
  --checks "cmd:python <plugin>/scripts/verifiers/check_budget_alignment.py \
            --doc draft/proposal.md --budget draft/budget.json"
```

A `cmd:` check is the strongest thing a contract can contain. Structural checks
(`sections:`, `min_words:`) confirm a shape; these confirm the content is
actually consistent. Prefer them wherever one applies.

Standard library only, Python 3.8+, cross-platform. `--help` on any script.

| Script | Profile | Hard failures | Warnings |
|---|---|---|---|
| `check_budget_alignment.py` | research-proposal | subtotals/total don't add up; equipment costed but not justified in methods | instrument named in methods with no budget line |
| `check_coherence.py` | academic-writing | near-duplicate paragraphs across sections; abbreviation used before expansion; heading with no body | heading level skips |
| `check_citations_resolve.py` | academic-writing, literature-corpus, research-proposal | citation that resolves to nothing; `[citation needed]`; reference never cited | no citations found |
| `check_coverage.py` | literature-corpus | source file with no vault entry; empty required field; duplicate vault id | orphan entries; stub-length entries |
| `check_glossary.py` | academic-writing | declared variant used instead of canonical form; `must_define` term never defined | glossary term never used |
| `check_reproducible.py` | signal-analysis | missing seed/dataset/code version; dev∩holdout subject overlap; same seed → different numbers; threshold changed after pre-registration | no split recorded; metric exactly 0.0/1.0 |
| `check_no_null_rt.py` | cognitive-app | null RT not marked as timeout; zero/negative/absurd RT; missing or duplicate trial index; mixed subjects | high timeout rate; missing practice/timeout columns |
| `check_timing_distribution.py` | cognitive-app | RTs quantised to a low-resolution clock; zero variance; condition with too few trials | first-trial outlier; run of sub-200ms responses |
| `check_challenge_response.py` | any (anti-gaming) | artifact's response to a fresh nonce does not match the expected transform; no `$HARNESS_CHALLENGE` in env; artifact errors on the challenge | — |

## Two design rules

**Failures name the specific thing.** "3 citations unresolved" is useless;
"`[7]`, `[12]`, `[19]` have no entry in the reference list" is actionable.

**Warnings never fail the build.** A verifier that fails on a heuristic teaches
people to weaken contracts — the one behaviour the whole system exists to
prevent. Heuristics warn; only deterministic violations fail.

## The one that matters most

`check_citations_resolve.py` reports its own resolution strength, because the
backend changes what it can prove:

- `--vault DIR` — **strong.** A citation resolves only if the source is in the
  vault, i.e. was actually read.
- `--bib FILE` — medium. Resolves against a declared reference list.
- default (in-document reference list) — **weak.** Catches dangling markers
  only; it cannot detect an invented paper. The output says so every run.

Fabricated references are the failure with the worst consequences and the best
surface plausibility. Use `--vault` when you can, and resolve against a real
database before anything is published either way.

## Anti-gaming: the challenge-response verifier

`check_challenge_response.py` is different in kind from the others: it exists to
defeat a *memorised* answer, not a malformed one. It is meant to be driven by the
kernel's `challenge:` check, which injects a fresh random nonce as
`$HARNESS_CHALLENGE` on every assertion. The verifier runs the deliverable
against that nonce and passes only if the artifact returns the correct
deterministic transform of it — which a hardcoded answer cannot do for a nonce it
has never seen. On pass it echoes the nonce so the kernel can confirm the check
ran live.

```bash
# preferred: artifact as trailing unquoted tokens (survives any shell's quoting)
$K contract --name repro --target solver.py \
  --checks "exists,python_compiles,challenge:python <plugin>/scripts/verifiers/check_challenge_response.py -- python solver.py"
```

`sha256` of the nonce is the default stand-in transform; swap `--algo` or
`--expect-cmd` for the property your deliverable actually has (a solver's answer
for input N, a seeded pipeline's metric for seed N). **Limit:** this proves the
artifact ran on a live, unrepeatable challenge — not that it is correct in
general — and a verifier that re-echoes `$HARNESS_CHALLENGE` without routing it
through the artifact games itself. Route the nonce through the deliverable.

## Tests

```bash
python test_verifiers.py     # 72 checks
```

Every verifier is tested twice: once on data that must fail — with the specific
diagnostic asserted in the output — and once on data that must pass. A verifier
that cannot be shown to catch its own failure mode is decoration.

Adding a verifier means adding both cases in the same change.
