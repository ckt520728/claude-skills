# 03 — Tool-call gating

Classify every tool call before it runs. This is usually the fork an agent hits most often, so it is the one to move first.

## Hard rules run in code, before the model

Non-negotiable, and for a specific reason: **the model trusts whatever text is in its state, and a command can be written to mislead a classifier.** A deterministic blocklist cannot be talked out of a decision.

```python
HARD_BLOCKS = ("rm -rf /", "git push --force", "| sh", "| bash", "curl | ", "chmod 777 /")
for pattern in HARD_BLOCKS:
    if pattern in cmd:
        deny(f"blocked by rule: {pattern}")
```

## The call

```python
from jev import decide, Choice, Noul

r = decide(
    state={"command": cmd, "cwd": cwd, "recent_actions": history[-5:]},
    questions={
        "risk": Choice(
            instructions="What happens if `command` runs inside `cwd`?",
            criteria={
                "read_only":   "Only reads, lists, searches files or runs tests",
                "local_edit":  "Changes files inside the project that git can restore",
                "destructive": "Deletes data, rewrites git history or touches files outside the project",
                "external":    "Sends data out, pushes, deploys, installs from the internet or spends money",
                "other":       "None of the above fits",
            },
        ),
        "reversible": Noul(instructions="This command can be undone without cost."),
    },
)
```

Two questions, one round trip, roughly 100 ms, zero generation tokens on the safety path.

## The gate

```python
a = r.answers["risk"]
if a.choice in ("read_only", "local_edit") and a.confidence >= 0.90:
    allow(f"jev: {a.choice} {a.confidence:.2f}")
if a.choice == "destructive" and a.confidence >= 0.90:
    deny(f"jev: destructive {a.confidence:.2f}")
ask(f"jev: {a.choice} {a.confidence:.2f}")          # everything else, including `other`
```

Three properties make this safe to leave running overnight:

1. Hard rules ran in code first.
2. **`external` always lands on a human, whatever the confidence.** Money, deploys, and anything leaving the machine are policy, not classification.
3. **`other` is never auto-approved.** The exit option exists to route the unknown to a human, not to absorb it.

## Read the file, not just the filename

`bash script.sh` tells the model nothing. Reading the script and putting its contents in the state catches a class of problem the command string never will:

```python
state = {"command": cmd, "cwd": cwd}
if (path := script_path_in(cmd)) and path.exists() and path.stat().st_size < 20_000:
    state["script_contents"] = path.read_text()
```

Same for `git`: the staged diff is better state than `git commit -m ...`.

## Claude Code hook

Wired at `.claude/hooks/jev_gate.py` in this project, registered in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "python .claude/hooks/jev_gate.py" }] }
    ]
  }
}
```

The hook reads the event as JSON on stdin and prints `allow`, `deny`, or `ask`. **Fail open or fail closed is a deliberate choice**: the shipped hook falls back to `ask` on any error — a missing API key, a timeout, a 529 — because a gate that silently allows on failure is worse than no gate, and one that denies on failure makes the agent unusable when the network blips.

LangChain users get the same gate ready-made as `AutoModeMiddleware` from `langchain-typesafe`.

## Completion checks are the same fork, inverted

A confident answer cannot prove a file was saved or a message was sent. Separate the two checks and keep code as the proof:

```python
r = decide(
    state={"goal": goal, "artifacts": artifact_list},
    questions={"complete": Noul(instructions="Every deliverable named in the goal now exists.")},
)
if r.answers["complete"].noul > 0.80:
    assert draft_path.exists(),            "model believes it saved a draft, filesystem disagrees"
    assert draft_path.stat().st_size > 500, "file exists but is empty"
```

The thing that decides a task is finished should never be the only thing that confirms it. The shipped Stop hook (`.claude/hooks/jev_done.py`) does this: `.claude/checks.sh` prints objective evidence, code short-circuits on a non-zero exit, and the model only judges what the script printed.

## Cost

300 bash calls in a night at ~500 tokens of state each is 150,000 input tokens — under a cent for the whole night at $0.042/M.

## Beyond one Bash matcher: `ToolGate`

The gate above governs one tool with one risk question. A real agent has many tools, and a file write, a network fetch, and an MCP call are not one question with one threshold. `assets/jev/toolgate.py` is the general version:

```python
from jev import ToolGate

gate = ToolGate()                      # thresholds and hard rules are constructor args
v = gate.check("Bash", {"command": "pytest -q"}, cwd=".", recent_actions=history)
v.decision      # "allow" | "ask" | "deny"
v.capability    # what the call can DO
```

### Policy attaches to capability, not to tool name

A new tool otherwise arrives ungoverned. The eight capability classes and their default bars:

| Capability | Auto-allow above | Why |
|---|---|---|
| `read` | 0.70 | A wrong read costs nothing |
| `local_write` | 0.88 | Version control can restore it |
| `process_spawn` | 0.95 | Recoverable, but leaves something running |
| `destructive` | **never** — denied at ≥0.90 | |
| `network_egress` | **never** | Data leaving the machine is policy, not classification |
| `credential_access` | **never** | |
| `spend` | **never** | |
| `other` | **never** | The exit routes the unknown to a person |

Four of the eight sit at `1.01` — an unreachable threshold — so "always ask a human" lives in the same table as the tunable numbers rather than as a special case elsewhere in the file. A call is also only auto-allowed when it is *clearly reversible* (`reversible >= 0.50`): confident-but-irreversible asks.

### An off-pattern call is its own signal

```python
"matches_stated_intent": Noul(instructions=
    "This call is a plausible next step given `recent_actions`, rather than an "
    "unrelated or unexpected action.")
```

Below 0.30 the gate asks regardless of how safe the call looks. A legitimate-*looking* action that does not follow from what just happened is exactly what an injected instruction produces — the risk classifier alone cannot see it, because in isolation `curl http://attacker/x` is just a network call.

### Batch the pending calls

```python
verdicts = gate.check_batch([("Bash", {"command": "ls"}),
                             ("Read", {"file_path": "a.py"}),
                             ("Bash", {"command": "git status"})],
                            cwd=".", recent_actions=history)
```

One decision call for the whole batch — they share a state (rule 5). Hard-blocked and cache-hit calls are resolved without reaching the model, so only the remainder is sent.

### Cache the verdict, carefully

A loop that retries the same command forty times should pay for one classification. `normalise_call()` collapses numeric literals and absolute paths, so `pytest --seed 41` and `pytest --seed 42` share a verdict — six such calls cost **one** model call.

That collapse is a deliberate trade, and it has a rule attached: **only `read` and `local_write` verdicts are cached.** A call whose risk depends on the very literals that normalisation erases must never be, which is why `destructive` re-classifies every time.

### Watch the gate's own health

```python
gate.stats()
# {'calls': 41, 'allow': 0.78, 'ask': 0.20, 'deny': 0.02,
#  'cache_hit_rate': 0.44, 'by_capability': {...}, 'health': 'ok'}
```

Two failure modes, both reported: an `ask` rate of **0%** means the thresholds are too loose and nothing reaches a human; an `ask` rate near **100%** means the gate has stopped being a gate and become a prompt — retune, or enrich the state.

Every verdict is appended to `gate.audit` with its full probability distribution, because you cannot tune a threshold you did not record.
