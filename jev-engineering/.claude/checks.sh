#!/usr/bin/env bash
# Objective evidence for the Stop hook. The decision layer only ever sees what
# this script PRINTS -- so the richer the evidence, the better the verdict.
#
# Exit non-zero and the hook blocks without consulting any model: a failing
# check needs no judgement.
#
# Add your own project checks below. Each should print something a reader could
# verify, not just succeed silently.

set -uo pipefail
status=0

say() { printf '\n== %s\n' "$1"; }

# Resolve an interpreter rather than assuming `python` is on PATH. A shell
# launched from inside another process inherits that process's PATH, which on
# Windows frequently does not include the interpreter running it -- so the Stop
# hook exports $PYTHON with its own sys.executable.
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  for candidate in python3 python py; do
    if command -v "$candidate" >/dev/null 2>&1; then PY="$candidate"; break; fi
  done
fi
if [ -z "$PY" ]; then
  printf '\n== interpreter\n  MISSING no python found on PATH and $PYTHON is unset\n'
  exit 1
fi
printf '\n== interpreter\n  %s\n' "$PY"

say "skill structure"
missing=0
for required in \
  "skills/jev-engineering/SKILL.md" \
  "skills/jev-engineering/assets/jev/__init__.py" \
  "CLAUDE.md" "AGENTS.md" "UNKNOWNS.md" "HANDOFFS.md"
do
  if [ -f "$required" ]; then
    printf '  ok      %s\n' "$required"
  else
    printf '  MISSING %s\n' "$required"
    missing=$((missing + 1))
  fi
done
[ "$missing" -eq 0 ] || status=1

say "reference playbooks"
count=$(find skills/jev-engineering/references -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
printf '  %s playbooks present (expected 18)\n' "$count"
[ "$count" -ge 18 ] || status=1

say "python package imports and is self-consistent"
if "$PY" - <<'PY'
import sys
sys.path.insert(0, "skills/jev-engineering/assets")
import jev
from jev import (decide, Choice, Score, Noul, gate, cascade, available_providers,
                 Registry, route_task, worth_switching, self_route,
                 ToolGate, CAPABILITIES, ControlLoop, RiskLimits,
                 run_plan, speculative, two_stage_choice, ensemble,
                 compare_policies, router_breakeven_accuracy)
print("  version:   ", jev.__version__)
print("  providers: ", ", ".join(available_providers()))
print("  primitives: Choice, Score, Noul")
print("  gate exits:", ", ".join(e.value for e in jev.Exit))
print("  capabilities:", len(CAPABILITIES), "classes")
reg = Registry.load()
print("  registry:  ", len(reg.models), "models across",
      len({m.platform for m in reg.models}), "platforms")
for tier in ("high", "medium", "low"):
    n = len(reg.candidates(tier))
    assert n > 0, "tier " + tier + " is empty"
    print("    " + tier.ljust(7), n, "candidates")
print("  exports:   ", len(jev.__all__), "public names")
PY
then
  printf '  ok      import\n'
else
  printf '  FAILED  import\n'
  status=1
fi

say "registry integrity"
if "$PY" - <<'PY'
import sys, json
sys.path.insert(0, "skills/jev-engineering/assets")
from jev import Registry, TIER_ORDER
from jev.routing import Model
reg = Registry.load()
keys = [m.key for m in reg.models]
assert len(keys) == len(set(keys)), "duplicate model keys: " + str(keys)
for m in reg.models:
    assert m.tier in TIER_ORDER, m.key + " has unknown tier " + m.tier
    assert m.platform in reg.platforms, m.key + " has unknown platform " + m.platform
    if m.priced:
        assert m.input_usd_per_mtok >= 0 and m.output_usd_per_mtok >= 0, m.key
        assert m.price_source != "unset", m.key + " is priced but price_source is unset"
    if m.api_id_verified:
        assert m.api_id, m.key + " claims a verified api_id but has none"
audit = reg.audit()
assert not audit["empty_tiers"], "empty tiers: " + str(audit["empty_tiers"])
print("  " + str(len(reg.models)) + " models, keys unique, tiers and platforms resolve")
print("  unpriced: " + str(len(audit["missing_price"])) + " (expected while prices are unset)")
PY
then
  printf '  ok      models.json\n'
else
  printf '  FAILED  models.json\n'
  status=1
fi

say "behavioural smoke tests (stub backend, no network)"
if "$PY" skills/jev-engineering/eval/test_smoke.py; then
  printf '  ok      test_smoke.py\n'
else
  printf '  FAILED  test_smoke.py\n'
  status=1
fi

say "hooks are syntactically valid"
for hook in .claude/hooks/*.py; do
  if "$PY" -m py_compile "$hook" 2>/dev/null; then
    printf '  ok      %s\n' "$hook"
  else
    printf '  FAILED  %s\n' "$hook"
    status=1
  fi
done

say "examples are syntactically valid"
for example in skills/jev-engineering/assets/examples/*.py; do
  if "$PY" -m py_compile "$example" 2>/dev/null; then
    printf '  ok      %s\n' "$example"
  else
    printf '  FAILED  %s\n' "$example"
    status=1
  fi
done

say "result"
if [ "$status" -eq 0 ]; then
  printf '  all checks passed\n'
else
  printf '  checks failed\n'
fi
exit "$status"
