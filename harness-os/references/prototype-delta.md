# What changed from the prototype

The Gemini prototype (`../../Gemini Notebook notes/`, `../../Harness OS workspace/`)
established the right architecture: filesystem as memory, process isolation,
assertion before publication, weakness mining, hot patching. That framing is kept
in full.

What follows is what did not survive contact with a real run, and why. Each item
is a defect the prototype would have hit on the first serious task.

## Blocking defects

### 1. `spawn_job` did not actually run jobs in parallel

```python
result = subprocess.run(cmd_list, ..., timeout=300)   # prototype
```

`subprocess.run` blocks until the child exits. The prototype's "parallel
sub-agent dispatch" was strictly sequential — the single feature the whole
architecture is built around did not exist.

**Now:** `Popen` with a detached process group, a per-job registry, and separate
`poll` (non-blocking, reaps and kills) and `wait` (blocking) commands. Verified
by selftest: `fork is non-blocking`, `job reaped`, `timeout kills job`.

### 2. `/workspace` was hardcoded

```python
def __init__(self, workspace_root: str = "/workspace"):
```

Does not exist on Windows, which is where this work is being done. The
accompanying `harness_run.sh` also assumed bash and `python3`.

**Now:** `HARNESS_WORKSPACE`, then `--workspace`, then cwd. `pathlib` throughout.
Windows process handling uses `tasklist` / `taskkill`; POSIX uses process groups.

### 3. The assertion verifier could be passed by garbage

The prototype checked `exists`, `not_empty`, `valid_json`, and "does the file
contain a `#` character". A one-byte file containing `#` passed `has_sections`.
The most common real failure — a plausible-looking draft full of `TODO` and
truncated mid-section — passed everything.

**Now:** twelve check kinds, including `sections:A|B|C` (named headings must be
present), `min_words:N`, `regex_present` / `regex_absent`, `python_compiles`,
`no_placeholder`, and `cmd:` for arbitrary external verifiers. `no_placeholder`
is mandatory on prose and code deliverables. Selftest asserts that a draft
containing `TODO` and a missing section fails.

### 4. Hot-patching wrote fixed strings

```python
if "does not exist" in sig:
    suggested_patches.append("CHECK_OUTPUT_PATH_REGISTRY")
```

Three hardcoded string constants written into a JSON file that nothing read.
There was no proposal, no validation, no promotion, no rollback — so nothing in
the loop could tell an improvement from a regression.

**Now:** the full Self-Harness / AHE loop — evidence bundle → bounded proposal →
change manifest with a falsifiable prediction → re-evaluation → attribution
verdict → held-in/held-out promotion gate → rollback on refutation.

### 5. Loop detection compared only action names

The prototype flagged a loop when three consecutive log lines shared an action
name, regardless of whether the output changed. A job legitimately calling
`extract` on three different PDFs tripped it.

**Now:** the key is `(action, detail)`, so genuinely different work does not trip
the breaker and genuinely repeated work does.

### 6. Failure clustering had no mechanism dimension

The prototype grouped by substring match on the error text — so an infinite retry
and a slow build both clustered as "timeout" and got the same patch.

**Now:** the Self-Harness triple `(verifier_cause, causal_status, mechanism)`,
clustered on exact agreement of all three, with `addressable: false` for clusters
that have no annotated mechanism.

### 7. There was nothing stopping the loop from cheating

The prototype's own analysis correctly identified reward hacking as the central
risk — an agent editing the verifier to return `True` — and then implemented no
countermeasure. The verifier lived in the same writable tree as everything else.

**Now:** `guard init` hashes every contract and named verifier script;
`guard check` reports `TAMPERED`; the skills state that a tamper result voids
every result since the last clean check, and that weakening a contract is never
an option. The docs also say plainly that this is a **tripwire, not a sandbox** —
a determined self-modifier can recompute hashes. Overstating it would be worse
than not having it.

## Missing mechanisms now present

| Mechanism | Source | Why it matters |
|---|---|---|
| Held-in / held-out split | Self-Harness §3.4 | Without it, "improvement" is indistinguishable from overfitting to the failures you were shown |
| Change manifest with prediction | AHE §3.3 | Turns each edit into a falsifiable claim rather than a plausible story |
| Attribution verdict + auto-rollback | AHE §3.3 | A refuted edit is removed even when the round improved — otherwise the harness accumulates cargo cult |
| Snapshot archive | DGM / Meta-Harness | Rollback is a normal move, not an emergency |
| Incremental playbook deltas | ACE | Wholesale rewrites erode exactly the detail that was worth keeping |
| Component taxonomy for edits | AHE §3.1 | One edit, one component — otherwise nothing is attributable |
| `cmd:` external verifier | — | The strongest available check; the prototype had no way to run a real test suite |
| `selftest` | — | The kernel proves it works before any real task depends on it (24 checks) |

## Kept from the prototype

- The OS analogy as the organising metaphor. It is genuinely load-bearing, not
  decoration: it makes the right questions obvious (what is persistent? what is
  isolated? what is privileged?).
- Filesystem as durable memory; context holds pointers, not payloads.
- Sandbox per job with an enforced timeout.
- Assertion before publication, with a write-only outbox.
- Weakness mining as the trigger for repair rather than blind retry.
- The five application scenarios, which became `profiles/` — expanded to six by
  splitting signal-analysis (EEG/HRV) out as its own domain.

## What was deliberately dropped

- **`harness_run.sh`'s interactive menu.** A numbered TUI menu is the wrong
  interface when the caller is an agent. The kernel is a CLI with JSON output;
  the skills are the interface for a human.
- **ASCII-art banner.** Cost tokens, conveyed nothing.
- **The claim that the daemon "runs in the background managing your tasks
  invisibly".** It does not and should not. It is a synchronous control plane the
  agent drives explicitly. Autonomy that is not observable is the thing this
  whole architecture exists to prevent.
