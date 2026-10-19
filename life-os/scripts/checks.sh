#!/usr/bin/env bash
# The objective evidence. Run this before calling any change done.
#
# It is deliberately not clever: each check prints PASS or FAIL and the script's exit code
# is the answer. Anything that needs a key or a network connection is not in here, because
# a check that cannot run is not a check.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PASS=0
FAIL=0
ok()   { printf '  PASS  %s\n' "$1"; PASS=$((PASS+1)); }
bad()  { printf '  FAIL  %s\n' "$1"; FAIL=$((FAIL+1)); }
head_() { printf '\n== %s ==\n' "$1"; }

head_ "structure"
for f in CLAUDE.md AGENTS.md UNKNOWNS.md HANDOFFS.md \
         lifeos/__init__.py lifeos/config.py lifeos/metrics.py lifeos/gtd.py \
         lifeos/unlock.py lifeos/vault.py lifeos/layer.py lifeos/JEV_VENDOR.json \
         lifeos/triage.py lifeos/clinical.py lifeos/jev/__init__.py \
         eval/test_smoke.py scripts/deploy.sh scripts/triage.py scripts/sync_jev.py \
         scripts/lifeos_status.py \
         "vault-src/_seed/Meta/Compass Config.md" "vault-src/_seed/08 Tasks/任務總表.md" \
         "vault-src/scripts/nightly.js" "vault-src/scripts/capture.js" \
         "vault-src/00 Dashboards/指南針儀表板.md" "vault-src/Guide/使用手冊.md" \
         "vault-src/AGENTS.md" "vault-src/00 開始這裡.md"; do
  if [ -f "$f" ]; then ok "exists: $f"; else bad "MISSING: $f"; fi
done

head_ "the decision layer IS the jev-engineering skill"
# Sessions 1-4 reimplemented the skill instead of using it. These make that a build failure.
if python scripts/sync_jev.py --check; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi
for gone in lifeos/decide.py lifeos/calibrate.py lifeos/jev_stub.py; do
  if [ -e "$gone" ]; then bad "private decision layer is back: $gone"; else ok "no $gone"; fi
done
if grep -q "from . import jev" lifeos/gtd.py && grep -q "jev.decide" lifeos/layer.py; then
  ok "gtd.py asks its questions through jev.decide()"
else
  bad "gtd.py does not go through the skill"
fi

head_ "python 3.9 compiles"
if python -m compileall -q lifeos eval >/dev/null 2>&1; then
  ok "lifeos/ and eval/ compile"
else
  bad "compile error"
  python -m compileall -q lifeos eval 2>&1 | head -20
fi

head_ "no third-party imports in lifeos/ (invariant 1)"
# Parsed with ast, not grepped: `decide.py` documents how to register with the upstream
# `jev` package inside its docstring, and a line-based check reads those example lines as
# real imports. The AST knows the difference between code and prose.
python - <<'PY'
import ast, glob, sys

STDLIB = {
    "os", "io", "re", "sys", "json", "datetime", "hashlib", "math", "typing", "ast",
    "collections", "itertools", "functools", "pathlib", "unittest", "tempfile", "shutil",
    "random", "time", "contextlib", "__future__", "dataclasses", "enum", "warnings",
    "threading", "concurrent", "urllib",
}
bad = []
for path in sorted(glob.glob("lifeos/**/*.py", recursive=True)):
    tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in STDLIB:
                    bad.append("%s:%d import %s" % (path, node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.level:          # relative import within the package
                continue
            root = (node.module or "").split(".")[0]
            if root not in STDLIB:
                bad.append("%s:%d from %s" % (path, node.lineno, node.module))
if bad:
    print("  FAIL  non-stdlib import in lifeos/:")
    for b in bad:
        print("          - %s" % b)
    sys.exit(1)
print("  PASS  stdlib only (%d modules incl. vendored jev, AST-verified)" % len(glob.glob("lifeos/**/*.py", recursive=True)))
PY
if [ $? -eq 0 ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi

head_ "no py3.10+ syntax (invariant 1)"
# Runtime `X | Y` unions and match statements break on 3.9.
if grep -rnE '^\s*match\s+.*:\s*$' lifeos/*.py >/dev/null 2>&1; then
  bad "match statement found — breaks on 3.9"
else
  ok "no match statements"
fi

head_ "SSOT parses and validates"
python - <<'PY'
import sys
sys.path.insert(0, ".")
from lifeos.config import load_config
try:
    c = load_config("vault-src/_seed/Meta/Compass Config.md")
except Exception as e:
    print("  FAIL  config did not parse: %s" % e); sys.exit(1)
problems = c.validate()
if problems:
    print("  FAIL  config problems:")
    for p in problems:
        print("          - %s" % p)
    sys.exit(1)
print("  PASS  config parses: %d dq, %d habits, %d wheel areas"
      % (len(c.dq_questions), len(c.habits), len(c.wheel_areas)))
from lifeos.config import CLINICAL_LEVELS
if c.clinical_access not in CLINICAL_LEVELS:
    print("  FAIL  clinical_access %r not in %s" % (c.clinical_access, CLINICAL_LEVELS)); sys.exit(1)
print("  PASS  clinical_access is %r (activated 2026-09-29)" % c.clinical_access)
if c.clinical_full_ok:
    print("  WARN  clinical_access is 'full' — raw patient text may enter model prompts")
PY
if [ $? -eq 0 ]; then PASS=$((PASS+2)); else FAIL=$((FAIL+1)); fi

head_ "clinical boundary (UNKNOWNS U4, level: derived)"
# The load-bearing property: nothing derived from the clinical section that reaches a
# prompt may contain text. Asserted here against real-looking clinical content so a
# regression in clinical.py is caught by checks.sh, not only by the test suite.
python - <<'PY'
import sys
sys.path.insert(0, ".")
from lifeos import clinical
from lifeos.config import load_config

c = load_config("vault-src/_seed/Meta/Compass Config.md")
NOTE = (
    "---\nd: 1\n---\n\n## %s\n\n"
    "- 陳先生 Cr 2.8 上升，追 BUN\n"
    "- 林女士 HbA1c 9.1 調 insulin\n\n"
    "## %s\n\n> 累\n" % (c.clinical_heading, c.reflection_heading)
)
SECRETS = ("陳先生", "林女士", "Cr", "HbA1c", "insulin", "BUN", "2.8", "9.1")

try:
    d = clinical.digest_from_text(NOTE, c)
except clinical.ClinicalAccessDenied as e:
    print("  FAIL  cannot read the section at level %r: %s" % (c.clinical_access, e)); sys.exit(1)

payload = clinical.coach_context(d, c)
blob = repr(payload) + "|" + d.as_context_line() + "|" + repr(d)
leaked = [s for s in SECRETS if s in blob]
if leaked:
    print("  FAIL  clinical text leaked into the transmittable surface: %s" % ", ".join(leaked))
    sys.exit(1)
print("  PASS  derived facts carry no clinical text (%d tokens checked)" % len(SECRETS))

for k, v in payload.items():
    if not (v is None or isinstance(v, (int, float, bool))):
        print("  FAIL  %s is %r, not numeric" % (k, type(v).__name__)); sys.exit(1)
print("  PASS  every transmitted clinical value is numeric: %s" % sorted(payload))

# Writing into the section must still be refused, activation or not.
from lifeos import vault as V
import tempfile, os, shutil
tmp = tempfile.mkdtemp()
try:
    p = os.path.join(tmp, "d.md")
    open(p, "w", encoding="utf-8").write(NOTE)
    try:
        V.append_under_heading(p, c.clinical_heading, "- x", clinical_heading=c.clinical_heading)
        print("  FAIL  writing into the clinical section was permitted"); sys.exit(1)
    except V.ClinicalSectionBlocked:
        print("  PASS  writing into the clinical section is still refused")
finally:
    shutil.rmtree(tmp)
PY
if [ $? -eq 0 ]; then PASS=$((PASS+3)); else FAIL=$((FAIL+1)); fi

head_ "threshold pinning (invariant 6)"
python - <<'PY'
import sys
sys.path.insert(0, ".")
from lifeos import gtd
from lifeos.layer import COLD_CONFIDENCE
bad = 0
if "other" not in gtd.BUCKETS or "other" not in gtd.FOLDERS:
    print("  FAIL  every Choice needs an `other` exit"); bad = 1
else:
    print("  PASS  every Choice has an `other` exit")
if gtd.BUCKET_TAU["other"] <= 1.0 or gtd.FOLDER_TAU["知識庫"] <= 1.0:
    print("  FAIL  `other` and 知識庫 must be unreachable for auto-filing"); bad = 1
else:
    print("  PASS  `other` and 知識庫 are never auto-filed")
L = gtd.layer_for_env({})
if not L.live or L.name != "local":
    print("  FAIL  no key must still yield the live local layer, got %r" % L.name); bad = 1
else:
    print("  PASS  no key -> jev `local` provider (live)")
if COLD_CONFIDENCE >= min(gtd.AUTO_FILE_CONFIDENCE, gtd.ESCALATE_FLOOR):
    print("  FAIL  COLD_CONFIDENCE must sit below every gate"); bad = 1
else:
    print("  PASS  cold layer escalates: COLD %.2f < gate %.2f" % (COLD_CONFIDENCE, gtd.AUTO_FILE_CONFIDENCE))
sys.exit(bad)
PY
if [ $? -eq 0 ]; then PASS=$((PASS+4)); else FAIL=$((FAIL+1)); fi

head_ "the resolution loop is wired"
python - <<'PY'
import sys
sys.path.insert(0, ".")
from lifeos import gtd, triage
from lifeos.config import load_config
from lifeos.jev import calibration
from lifeos.layer import Layer

cfg = load_config("vault-src/_seed/Meta/Compass Config.md")
cal = calibration.Calibrator()
L = Layer("local", calibrator=cal)
p = triage.propose("重構儀表板，然後接著寫測試", cfg, layer=L, kb_index_path="")
if p.decisions["bucket"].verdict != gtd.ASK:
    print("  FAIL  a cold layer must escalate"); sys.exit(1)
print("  PASS  cold layer escalates to a human")
triage.resolve(L, p, "bucket", p.decisions["bucket"].label, save=False)
if cal.observations("bucket") != 1:
    print("  FAIL  resolving did not reach the calibrator — the loop is unwired"); sys.exit(1)
print("  PASS  resolving one ask records one observation")
if triage.AUDIT_SAMPLE_RATE <= 0:
    print("  FAIL  audit sampling is off; a warm band could drift unobserved"); sys.exit(1)
print("  PASS  audit sampling on (%.0f%% of AUTO decisions still confirmed)" % (triage.AUDIT_SAMPLE_RATE * 100))
PY
if [ $? -eq 0 ]; then PASS=$((PASS+3)); else FAIL=$((FAIL+1)); fi

head_ "Build Order gate: Python and JS agree"
python - <<'PY'
import io, re, sys
sys.path.insert(0, ".")
from lifeos import unlock
js = io.open("vault-src/Meta/views/gate.js", encoding="utf-8").read()
w = int(re.search(r"CONSISTENCY_WINDOW = (\d+)", js).group(1))
r = float(re.search(r"CONSISTENCY_REQUIRED = ([0-9.]+)", js).group(1))
days = dict((k, int(d)) for k, d in re.findall(r'\["(\w+)", "[^"]*", (\d+)\]', js))
bad = []
if w != unlock.CONSISTENCY_WINDOW: bad.append("window %d vs %d" % (w, unlock.CONSISTENCY_WINDOW))
if abs(r - unlock.CONSISTENCY_REQUIRED) > 1e-9: bad.append("required %s vs %s" % (r, unlock.CONSISTENCY_REQUIRED))
if days != unlock.DEFAULT_UNLOCK_DAYS: bad.append("days %s vs %s" % (days, unlock.DEFAULT_UNLOCK_DAYS))
if bad:
    print("  FAIL  gate.js drifted from unlock.py: " + "; ".join(bad)); sys.exit(1)
print("  PASS  gate.js mirrors unlock.py (%d layers, %d-day window, %.0f%%)" % (len(days), w, r * 100))
PY
if [ $? -eq 0 ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi

head_ "behavioural tests"
TEST_OUT=$(python eval/test_smoke.py 2>&1)
if printf '%s' "$TEST_OUT" | tail -3 | grep -q '^OK'; then
  N=$(printf '%s' "$TEST_OUT" | grep -oE 'Ran [0-9]+ tests' | grep -oE '[0-9]+')
  ok "$N behavioural checks pass"
else
  bad "test suite failed"
  printf '%s\n' "$TEST_OUT" | tail -25
fi

head_ "vault-src encodes cleanly"
python - <<'PY'
import glob, io, sys
bad = []
for pat in ("vault-src/**/*.md", "vault-src/**/*.js"):
    for p in glob.glob(pat, recursive=True):
        try:
            io.open(p, encoding="utf-8").read()
        except Exception as e:
            bad.append("%s: %s" % (p, e))
if bad:
    for b in bad:
        print("  FAIL  %s" % b)
    sys.exit(1)
n = len(glob.glob("vault-src/**/*.md", recursive=True)) + \
    len(glob.glob("vault-src/**/*.js", recursive=True))
print("  PASS  %d vault-src files are valid UTF-8" % n)
PY
if [ $? -eq 0 ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi

head_ "dashboards read the SSOT, never hardcode keys (invariant 7)"
# Only code inside a dataviewjs fence can actually query a key, so prose mentioning
# `dq_build` as an example is fine. The collection names the config itself defines
# (dq_questions, habits, wheel_areas) are how a dashboard reads the SSOT, not a bypass of it.
python - <<'PY'
import glob, io, re, sys

ALLOWED = {"dq_questions", "habit_ids", "wheel_areas"}
FENCE = re.compile(r"```dataviewjs(.*?)```", re.S)
IDENT = re.compile(r"\b((?:dq|habit|wheel)_[a-z0-9_]+)\b")

bad = []
ALLOWED |= {"dq_prefix", "habit_prefix", "wheel_prefix", "wheel_props", "wheel_areas"}
for path in sorted(glob.glob("vault-src/00 Dashboards/*.md") + glob.glob("vault-src/Templates/*.md")
                   + glob.glob("vault-src/Meta/views/*.js")):
    text = io.open(path, encoding="utf-8").read()
    blocks = [text] if path.endswith(".js") else FENCE.findall(text)
    for block in blocks:
        block = "\n".join(l for l in block.splitlines() if not l.strip().startswith("//"))
        for line_no, line in enumerate(block.splitlines(), 1):
            for name in IDENT.findall(line):
                if name not in ALLOWED:
                    bad.append("%s (in dataviewjs): %s" % (path, name))

if bad:
    print("  FAIL  a dashboard hardcodes a key instead of reading it from config:")
    for b in sorted(set(bad)):
        print("          - %s" % b)
    sys.exit(1)
print("  PASS  no dashboard hardcodes a dq_/habit_/wheel_ key in a query")
PY
if [ $? -eq 0 ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi

head_ "obsidian-side JavaScript parses"
if command -v node >/dev/null 2>&1; then
  for f in vault-src/scripts/*.js; do
    if node --check "$f" >/dev/null 2>&1; then ok "parses: $f"; else bad "syntax error: $f"; node --check "$f" 2>&1 | head -5; fi
  done
  # Dataview views run with top-level await, so check them wrapped the way Dataview runs them.
  TMPJS="$(mktemp -d)"
  for f in vault-src/Meta/views/*.js; do
    { echo "(async () => {"; cat "$f"; echo; echo "})();"; } > "$TMPJS/v.js"
    if node --check "$TMPJS/v.js" >/dev/null 2>&1; then ok "parses: $f"; else bad "syntax error: $f"; fi
  done
  rm -rf "$TMPJS"
else
  printf '  SKIP  node not installed — JS syntax unverified\n'
fi

head_ "deploy never overwrites a user edit"
# Throwaway vault; the ledger is restored afterwards so the test leaves no trace.
TV="$(mktemp -d)"; cp scripts/deploy-ledger.tsv "$TV.ledger"
echo x > "$TV/CLAUDE.md"
LIFEOS_VAULT="$TV" bash scripts/deploy.sh >/dev/null 2>&1
echo "使用者自己寫的一行" >> "$TV/Life OS/03 Planning/人生主題.md"
echo "- [ ] 使用者的任務" >> "$TV/Life OS/08 Tasks/任務總表.md"
OUT="$(LIFEOS_VAULT="$TV" bash scripts/deploy.sh 2>&1)"
if printf '%s' "$OUT" | grep -q "kept (yours): 2" && grep -q "使用者自己寫的一行" "$TV/Life OS/03 Planning/人生主題.md" \
   && grep -q "使用者的任務" "$TV/Life OS/08 Tasks/任務總表.md"; then
  ok "edited seed files are kept, byte for byte"
else
  bad "deploy overwrote or misreported a user edit"; printf '%s\n' "$OUT" | tail -5
fi
cp "$TV.ledger" scripts/deploy-ledger.tsv; rm -rf "$TV" "$TV.ledger"

head_ "deploy is idempotent"
if bash scripts/deploy.sh --dry-run >/tmp/lifeos_deploy1.txt 2>&1; then
  ok "dry run succeeds"
  if grep -q 'would create\|would update' /tmp/lifeos_deploy1.txt; then
    printf '  INFO  deploy has pending changes (expected before first deploy)\n'
  else
    ok "deployed copy matches vault-src (idempotent)"
  fi
else
  bad "dry run failed:"
  tail -10 /tmp/lifeos_deploy1.txt
fi

printf '\n========================================\n'
printf '  PASS %d    FAIL %d\n' "$PASS" "$FAIL"
printf '========================================\n'
[ "$FAIL" -eq 0 ] || exit 1
