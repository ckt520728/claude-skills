#!/usr/bin/env python3
"""
Harness OS Kernel -- an OS-shaped control plane for long-horizon agent work.

Design sources (see ../references/evidence-ledger.md):
  * Self-Harness (Zhang et al., 2026)  -- failure signatures, bounded proposals,
                                          held-in / held-out promotion gate
  * AHE (Lin et al., 2026)             -- component / experience / decision
                                          observability, change manifests,
                                          read-only verifier ("controllability")
  * ACE (Zhang et al., ICLR 2026)      -- incremental delta playbook updates,
                                          no full rewrites (context collapse)
  * Meta-Harness (Lee et al., 2026)    -- prior attempts reachable on the
                                          filesystem, not compressed to scalars
  * DGM (Zhang et al., 2025/26)        -- archive of stepping stones, rollback

  Upgrade sources (v2.1.0 -- 2026 frontier-benchmark corpus; see
  ../references/evidence-ledger.md "v2.1.0 upgrade"):
  * Codex system architecture          -- invariant prefix layer that survives
                                          context compaction  -> `constraint`
  * AgencyBench (Li et al., 2026)       -- long tasks fail by losing constraints,
                                          not by lacking skill               ->  `constraint`
  * ExploitBench graded oracle          -- per-run challenge-response defeats
                                          memorised/hardcoded answers        ->  `challenge:`
                                          16-tier ladder gives dense partial
                                          credit vs binary pass/fail          -> `ladder`

  Upgrade source (v2.2.0 -- Test-Time Harness Learning; see
  ../references/evidence-ledger.md "v2.2.0 upgrade"):
  * Harness Learning (Zhang et al., CMU, 2026)
      - Q_fb / Q_score / Q_eval partition: feedback, selection and blind
        evaluation never share items                -> `sealed` split, `final`
      - proposer reads an execution report on Q_fb  -> `report`
      - structured SEARCH/REPLACE edits; validity
        (parses / runnable) is part of the reward   -> `patch`
      - G candidates scored on Q_score, retain the
        incumbent unless strictly beaten            -> `score`, `select`
      - iterative rounds beat one-shot best-of-N    -> adaptation curve

This kernel is deliberately *not* an LLM. It is the deterministic substrate the
agent drives through Bash: it owns state, processes, traces, contracts,
verification, evidence and rollback. The agent supplies judgement; the kernel
supplies facts that cannot be talked around.

Python 3.8+. Standard library only. Cross-platform (Windows / macOS / Linux).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

KERNEL_VERSION = "2.2.0"

# Contract splits (Harness Learning question partition):
#   held_in  = Q_fb    -- failures are mined and shown to the proposer
#   held_out = Q_score -- scores candidates; proposer sees aggregates only
#   sealed   = Q_eval  -- never run during adaptation; only `final` runs it
SPLITS = ("held_in", "held_out", "sealed")
SPLIT_ALIASES = {"feedback": "held_in", "fb": "held_in",
                 "score": "held_out", "eval": "sealed"}

# Messages from _run_check that mean the check could not *execute*, as opposed
# to executing and failing. Used for the validity term of `score`.
EXEC_ERROR_PREFIXES = ("verifier error", "verifier command timed out",
                       "challenge verifier timed out", "challenge verifier error",
                       "unknown check kind")

# Validity bonus weights, taken from the Harness Learning reward
# r = J + 0.05*parses + 0.10*runnable + 0.15*rho_run. Here they only break
# ties between candidates with equal J (see `select`).
VALIDITY_WEIGHTS = (0.05, 0.10, 0.15)

PLACEHOLDER_PATTERNS = [
    r"\bTODO\b", r"\bFIXME\b", r"\bXXX\b", r"\bTBD\b",
    r"lorem ipsum", r"<placeholder>", r"\[insert .{0,40}\]",
    r"\byour .{0,20} here\b", r"\.\.\.rest of", r"# rest of the (code|file)",
]

DEFAULT_TIMEOUT = 900  # 15 min; long-horizon jobs are the norm here


def _now():
    return time.time()


def _ts():
    return time.strftime("%Y-%m-%d %H:%M:%S")


class Harness:
    """The kernel. Everything is a file; nothing lives only in a context window."""

    def __init__(self, workspace=None):
        root = workspace or os.environ.get("HARNESS_WORKSPACE") or os.getcwd()
        self.ws = Path(root).resolve()
        self.h = self.ws / ".harness"
        self.state = self.h / "state"
        self.jobs = self.state / "jobs"
        self.logs = self.h / "logs"
        self.evals = self.logs / "eval"
        self.contracts = self.h / "contracts"
        self.evidence = self.h / "evidence"
        self.manifests = self.h / "manifests"
        self.archive = self.h / "archive"
        self.ladders = self.state / "ladders"
        self.candidates = self.h / "candidates"
        self.out = self.ws / "out"

        self.playbook_path = self.state / "playbook.json"
        self.registry_path = self.state / "registry.json"
        self.constraints_path = self.state / "constraints.json"
        self.patch_stats_path = self.state / "patch_stats.json"
        self.curve_path = self.logs / "adaptation_curve.json"
        self.trace_path = self.logs / "trace.jsonl"
        self.guard_path = self.h / "guard.json"
        self.config_path = self.h / "config.json"

    # -- filesystem -------------------------------------------------------

    def boot(self, profile=None):
        for d in (self.h, self.state, self.jobs, self.logs, self.evals,
                  self.contracts, self.evidence, self.manifests,
                  self.archive, self.ladders, self.candidates, self.out):
            d.mkdir(parents=True, exist_ok=True)

        if not self.registry_path.exists():
            self._write_json(self.registry_path,
                             {"jobs": {}, "round": 0, "created": _now()})
        if not self.playbook_path.exists():
            self._write_json(self.playbook_path,
                             {"goal": None, "done_definition": None,
                              "milestones": [], "entries": [], "next_id": 1})
        if not self.constraints_path.exists():
            self._write_json(self.constraints_path,
                             {"invariants": [], "next_id": 1})
        if not self.config_path.exists():
            self._write_json(self.config_path, {
                "kernel_version": KERNEL_VERSION,
                "profile": profile,
                "default_timeout": DEFAULT_TIMEOUT,
                "loop_threshold": 3,
                "created": _now(),
            })
        elif profile:
            cfg = self._read_json(self.config_path, {})
            cfg["profile"] = profile
            self._write_json(self.config_path, cfg)

        if not self.trace_path.exists():
            self.trace_path.touch()

        gitignore = self.h / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("state/jobs/\nlogs/\n", encoding="utf-8")

        return {"workspace": str(self.ws), "harness": str(self.h),
                "kernel_version": KERNEL_VERSION,
                "profile": self._read_json(self.config_path, {}).get("profile")}

    def _require_boot(self):
        if not self.h.exists():
            raise SystemExit(
                "harness not booted in %s -- run: harness_kernel.py boot" % self.ws)

    @staticmethod
    def _read_json(path, default=None):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    @staticmethod
    def _write_json(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        tmp.replace(path)

    def cfg(self):
        return self._read_json(self.config_path, {}) or {}

    # -- tracer -----------------------------------------------------------

    def trace(self, job, action, detail="", status="INFO", signature=None,
              split=None):
        """Append one compact JSONL record. Traces live on disk, never in context."""
        self._require_boot()
        rec = {"t": _ts(), "job": job, "action": action,
               "status": status, "detail": (detail or "")[:600]}
        if signature:
            rec["sig"] = signature
        if split:
            rec["split"] = split
        with open(self.trace_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    def read_trace(self, job=None, limit=50, status=None):
        self._require_boot()
        rows = []
        if not self.trace_path.exists():
            return rows
        with open(self.trace_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if job and rec.get("job") != job:
                    continue
                if status and rec.get("status") != status:
                    continue
                rows.append(rec)
        return rows[-limit:]

    def loopcheck(self, job):
        """Loop breaker: same action + same detail repeated N times in a row."""
        n = int(self.cfg().get("loop_threshold", 3))
        rows = self.read_trace(job=job, limit=n)
        if len(rows) < n:
            return {"loop": False, "reason": "insufficient history"}
        keys = set((r.get("action"), r.get("detail")) for r in rows)
        if len(keys) == 1:
            return {"loop": True, "repeated": rows[-1].get("action"),
                    "count": n,
                    "advice": "Stop retrying. Re-read the evidence, change the "
                              "mechanism, or escalate to the user."}
        return {"loop": False}

    # -- process manager --------------------------------------------------

    def fork(self, job, cmd, timeout=None, cwd=None, shell=False):
        """Start a job WITHOUT blocking. Poll or wait for it later."""
        self._require_boot()
        timeout = int(timeout or self.cfg().get("default_timeout", DEFAULT_TIMEOUT))
        sandbox = self.jobs / job
        sandbox.mkdir(parents=True, exist_ok=True)
        workdir = Path(cwd).resolve() if cwd else sandbox

        stdout_p = sandbox / "stdout.log"
        stderr_p = sandbox / "stderr.log"
        exit_p = sandbox / "exit_code"
        for stale in (exit_p,):
            if stale.exists():
                stale.unlink()

        env = os.environ.copy()
        env["HARNESS_WORKSPACE"] = str(self.ws)
        env["HARNESS_JOB_ID"] = job
        env["HARNESS_SANDBOX"] = str(sandbox)

        args = cmd if shell else shlex.split(cmd, posix=(os.name != "nt"))
        out_f = open(stdout_p, "w", encoding="utf-8", errors="replace")
        err_f = open(stderr_p, "w", encoding="utf-8", errors="replace")
        popen_kwargs = {"cwd": str(workdir), "env": env, "shell": shell,
                        "stdout": out_f, "stderr": err_f}
        if os.name != "nt":
            popen_kwargs["start_new_session"] = True
        else:
            popen_kwargs["creationflags"] = getattr(
                subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

        proc = subprocess.Popen(args, **popen_kwargs)
        out_f.close()
        err_f.close()

        meta = {"job": job, "pid": proc.pid, "cmd": cmd, "shell": shell,
                "cwd": str(workdir), "sandbox": str(sandbox),
                "status": "running", "start": _now(), "timeout": timeout,
                "stdout": str(stdout_p), "stderr": str(stderr_p)}
        self._write_json(sandbox / "meta.json", meta)

        reg = self._read_json(self.registry_path, {"jobs": {}})
        reg.setdefault("jobs", {})[job] = {"status": "running",
                                           "pid": proc.pid,
                                           "start": meta["start"],
                                           "sandbox": str(sandbox)}
        self._write_json(self.registry_path, reg)
        self.trace(job, "FORK", cmd[:200])
        return meta

    @staticmethod
    def _alive(pid):
        if pid is None:
            return False
        try:
            if os.name == "nt":
                out = subprocess.run(
                    ["tasklist", "/FI", "PID eq %d" % pid, "/NH"],
                    capture_output=True, text=True, timeout=20)
                return str(pid) in (out.stdout or "")
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False
        except Exception:
            return False

    @staticmethod
    def _kill(pid):
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                               capture_output=True, timeout=30)
            else:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
        except Exception:
            pass

    def _tail(self, path, n=25):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return "".join(f.readlines()[-n:]).strip()
        except Exception:
            return ""

    def poll(self, job=None):
        """Reap finished jobs, kill timed-out ones. Never blocks."""
        self._require_boot()
        reg = self._read_json(self.registry_path, {"jobs": {}})
        names = [job] if job else list(reg.get("jobs", {}).keys())
        results = []
        for name in names:
            meta_p = self.jobs / name / "meta.json"
            meta = self._read_json(meta_p)
            if not meta:
                results.append({"job": name, "status": "unknown"})
                continue
            if meta["status"] == "running":
                elapsed = _now() - meta["start"]
                if self._alive(meta["pid"]):
                    if elapsed > meta["timeout"]:
                        self._kill(meta["pid"])
                        meta.update(status="timeout", end=_now(),
                                    elapsed=elapsed)
                        self.trace(name, "TIMEOUT",
                                   "killed after %.0fs" % elapsed, "ERROR",
                                   signature="timeout|direct|unbounded_runtime")
                    else:
                        meta["elapsed"] = elapsed
                else:
                    meta.update(status="finished", end=_now(), elapsed=elapsed)
                    tail_err = self._tail(meta["stderr"], 20)
                    meta["stderr_tail"] = tail_err
                    meta["stdout_tail"] = self._tail(meta["stdout"], 20)
                    self.trace(name, "JOB_DONE",
                               "%.1fs%s" % (elapsed,
                                            " stderr:" + tail_err[:120]
                                            if tail_err else ""))
                self._write_json(meta_p, meta)
                reg.setdefault("jobs", {}).setdefault(name, {})["status"] = \
                    meta["status"]
            results.append(dict((k, meta.get(k)) for k in
                                ("job", "status", "elapsed", "pid", "sandbox",
                                 "stderr_tail")))
        self._write_json(self.registry_path, reg)
        return results

    def wait(self, job=None, timeout=None, interval=2.0):
        """Block until named job (or all jobs) leave 'running'."""
        deadline = _now() + (timeout or 3600)
        while _now() < deadline:
            res = self.poll(job)
            if all(r.get("status") != "running" for r in res):
                return res
            time.sleep(interval)
        return self.poll(job)

    # -- contracts & assertions ------------------------------------------

    def put_contract(self, name, target, checks, notes="", split="held_in"):
        """A contract is what 'done' means, written BEFORE the work starts."""
        self._require_boot()
        split = self._norm_split(split)
        c = {"name": name, "target": target, "checks": checks,
             "split": split, "notes": notes, "created": _now()}
        self._write_json(self.contracts / ("%s.json" % name), c)
        return c

    def _run_check(self, spec, target):
        """Return (passed, message). Every check is deterministic."""
        kind, _, arg = spec.partition(":")
        kind = kind.strip()

        if kind == "exists":
            return target.exists(), str(target)
        if kind not in ("cmd", "challenge") and not target.exists():
            return False, "target missing: %s" % target

        if kind == "not_empty":
            return target.stat().st_size > 0, "%dB" % target.stat().st_size
        if kind == "min_bytes":
            size = target.stat().st_size
            return size >= int(arg), "%dB (need %s)" % (size, arg)
        if kind == "valid_json":
            try:
                json.loads(target.read_text(encoding="utf-8"))
                return True, "parsed"
            except Exception as e:
                return False, "json error: %s" % e
        if kind == "json_keys":
            try:
                data = json.loads(target.read_text(encoding="utf-8"))
            except Exception as e:
                return False, "json error: %s" % e
            want = [k.strip() for k in arg.split(",") if k.strip()]
            missing = [k for k in want if k not in data]
            return not missing, ("ok" if not missing
                                 else "missing keys: %s" % ",".join(missing))

        text = ""
        if kind in ("sections", "regex_present", "regex_absent",
                    "no_placeholder", "min_words", "python_compiles"):
            text = target.read_text(encoding="utf-8", errors="replace")

        if kind == "sections":
            want = [s.strip() for s in arg.split("|") if s.strip()]
            heads = re.findall(r"^#{1,6}\s*(.+)$", text, re.M)
            joined = "\n".join(heads).lower()
            missing = [s for s in want if s.lower() not in joined]
            return not missing, ("ok" if not missing
                                 else "missing sections: %s" % "; ".join(missing))
        if kind == "regex_present":
            return bool(re.search(arg, text, re.M | re.I)), "/%s/" % arg
        if kind == "regex_absent":
            m = re.search(arg, text, re.M | re.I)
            return not m, ("clean" if not m else "found: %s" % m.group(0)[:80])
        if kind == "no_placeholder":
            hits = []
            for p in PLACEHOLDER_PATTERNS:
                m = re.search(p, text, re.I)
                if m:
                    hits.append(m.group(0)[:40])
            return not hits, ("clean" if not hits
                              else "placeholders: %s" % ", ".join(hits[:5]))
        if kind == "min_words":
            n = len(re.findall(r"\S+", text))
            return n >= int(arg), "%d words (need %s)" % (n, arg)
        if kind == "python_compiles":
            try:
                compile(text, str(target), "exec")
                return True, "compiles"
            except SyntaxError as e:
                return False, "SyntaxError line %s: %s" % (e.lineno, e.msg)
        if kind == "cmd":
            try:
                p = subprocess.run(arg, shell=True, cwd=str(self.ws),
                                   capture_output=True, text=True, timeout=600)
                tail = (p.stderr or p.stdout or "").strip()[-200:]
                return p.returncode == 0, "exit=%d %s" % (p.returncode, tail)
            except subprocess.TimeoutExpired:
                return False, "verifier command timed out"
            except Exception as e:
                return False, "verifier error: %s" % e
        if kind == "challenge":
            # Dynamic challenge-response (ExploitBench graded oracle): a fresh
            # random nonce is injected each run as $HARNESS_CHALLENGE. The
            # verifier must exit 0 *and* echo this exact nonce on stdout, which
            # it can only do by running the artifact against THIS nonce. A
            # memorised or hardcoded PASS carries a stale nonce and is rejected.
            # Limit: this proves the verifier ran live; the contract author must
            # route the nonce through the artifact so the artifact -- not a stub
            # echoing $HARNESS_CHALLENGE -- is what has to produce it.
            nonce = secrets.token_hex(16)
            env = dict(os.environ)
            env["HARNESS_CHALLENGE"] = nonce
            try:
                p = subprocess.run(arg, shell=True, cwd=str(self.ws),
                                   capture_output=True, text=True,
                                   timeout=600, env=env)
            except subprocess.TimeoutExpired:
                return False, "challenge verifier timed out"
            except Exception as e:
                return False, "challenge verifier error: %s" % e
            fresh = nonce in (p.stdout or "")
            tail = (p.stderr or p.stdout or "").strip()[-160:]
            if p.returncode == 0 and not fresh:
                return False, ("exit 0 but stale: verifier did not echo the "
                               "fresh challenge %s.. -- hardcoded or replayed "
                               "result; %s" % (nonce[:8], tail))
            return (p.returncode == 0 and fresh,
                    "exit=%d fresh=%s %s" % (p.returncode, fresh, tail))
        return False, "unknown check kind: %s" % kind

    @staticmethod
    def _norm_split(split):
        split = SPLIT_ALIASES.get(split or "held_in", split or "held_in")
        if split not in SPLITS:
            raise SystemExit("unknown split '%s' (use %s, or aliases %s)"
                             % (split, "/".join(SPLITS),
                                "/".join(sorted(SPLIT_ALIASES))))
        return split

    def _contracts(self, split=None):
        out = []
        for p in sorted(self.contracts.glob("*.json")):
            c = self._read_json(p, {}) or {}
            c.setdefault("name", p.stem)
            if split is None or c.get("split", "held_in") == split:
                out.append(c)
        return out

    def _check_contract(self, c):
        """Run every check of contract c. No traces, no eval files."""
        target = Path(c["target"])
        if not target.is_absolute():
            target = self.ws / target
        results = {}
        for spec in c["checks"]:
            ok, msg = self._run_check(spec, target)
            results[spec] = {"pass": bool(ok), "msg": msg}
        return all(r["pass"] for r in results.values()), results, target

    def run_assert(self, name, round_no=None):
        """Physical verification. An agent saying 'done' is not evidence."""
        self._require_boot()
        c = self._read_json(self.contracts / ("%s.json" % name))
        if not c:
            raise SystemExit("no contract named '%s'" % name)
        if c.get("split") == "sealed":
            raise SystemExit(
                "contract '%s' is sealed (Q_eval). It is never run during "
                "adaptation -- running it would leak the blind set into the "
                "loop. It runs once, via `final`." % name)

        passed, results, target = self._check_contract(c)
        for spec, r in results.items():
            if not r["pass"]:
                self.trace(name, "ASSERT_FAIL", "%s -> %s" % (spec, r["msg"]),
                           "FAIL",
                           signature="%s|verifier|%s" % (spec.split(":")[0], name),
                           split=c.get("split"))
        report = {"contract": name, "target": str(target), "split": c.get("split"),
                  "passed": passed, "checks": results, "t": _now()}
        if passed:
            self.trace(name, "ASSERT_PASS", str(target))
        if round_no is not None:
            self._merge_round_eval(round_no, name, report)
        self._write_json(self.evals / ("%s.json" % name), report)
        return report

    def assert_all(self, round_no=None, split=None):
        self._require_boot()
        if split:
            split = self._norm_split(split)
            if split == "sealed":
                raise SystemExit("sealed contracts run only via `final`")
        summary = {"passed": [], "failed": [], "round": round_no}
        sealed = 0
        for p in sorted(self.contracts.glob("*.json")):
            c = self._read_json(p, {})
            if c.get("split") == "sealed":
                sealed += 1
                continue
            if split and c.get("split") != split:
                continue
            rep = self.run_assert(p.stem, round_no)
            (summary["passed"] if rep["passed"] else summary["failed"]).append(
                p.stem)
        summary["all_passed"] = not summary["failed"]
        if sealed:
            summary["sealed_skipped"] = sealed
        return summary

    def _merge_round_eval(self, round_no, name, report):
        path = self.evals / ("round_%s.json" % round_no)
        data = self._read_json(path, {}) or {}
        data[name] = {"passed": report["passed"],
                      "split": report.get("split"),
                      "failed_checks": [k for k, v in report["checks"].items()
                                        if not v["pass"]]}
        self._write_json(path, data)

    # -- weakness mining --------------------------------------------------

    def mine(self, round_no=None, all_splits=False):
        """Cluster failures by signature triple (Self-Harness sec. 3.2).

        signature = (verifier_cause, causal_status, mechanism)
        Two failures group together only when the verifier rejected them for the
        same reason AND the same agent-side mechanism produced it. This is what
        stops the loop from patching symptoms.

        Only feedback-split (held_in) and unsplit failures are mined by
        default: held_out is the selection set (Q_score) and sealed is the
        blind set (Q_eval). Mining them would turn both into training data.
        """
        self._require_boot()
        hidden = ("sealed",) if all_splits else ("held_out", "sealed")
        rows = [r for r in self.read_trace(limit=100000)
                if r.get("status") in ("FAIL", "ERROR")
                and r.get("split") not in hidden]
        clusters = {}
        for r in rows:
            sig = r.get("sig") or "%s|unknown|unannotated" % r.get("action", "?")
            c = clusters.setdefault(sig, {"signature": sig, "size": 0,
                                          "examples": [], "jobs": set()})
            c["size"] += 1
            c["jobs"].add(r.get("job"))
            if len(c["examples"]) < 4:
                c["examples"].append({"t": r["t"], "job": r.get("job"),
                                      "detail": r.get("detail", "")[:220]})
        out = []
        for c in clusters.values():
            c["jobs"] = sorted(x for x in c["jobs"] if x)
            parts = c["signature"].split("|")
            c["verifier_cause"] = parts[0] if parts else ""
            c["causal_status"] = parts[1] if len(parts) > 1 else ""
            c["mechanism"] = parts[2] if len(parts) > 2 else ""
            c["addressable"] = c["causal_status"] != "unknown"
            out.append(c)
        out.sort(key=lambda x: (-x["size"], x["signature"]))

        bundle = {"round": round_no, "t": _now(), "total_failures": len(rows),
                  "excluded_splits": list(hidden),
                  "clusters": out,
                  "note": "Clusters marked addressable=false lack an annotated "
                          "agent mechanism. Annotate them with "
                          "`trace --signature 'cause|causal_status|mechanism'` "
                          "before proposing an edit, or exclude them: not every "
                          "failure implies a harness change."}
        rd = "round_%s" % (round_no if round_no is not None else "adhoc")
        self._write_json(self.evidence / rd / "bundle.json", bundle)
        return bundle

    # -- change manifest / decision observability -------------------------

    def add_manifest(self, round_no, edit_id, component, evidence,
                     root_cause, fix, predict_fix, predict_regress):
        """Every edit ships a falsifiable prediction (AHE sec. 3.3)."""
        self._require_boot()
        path = self.manifests / ("round_%s.json" % round_no)
        data = self._read_json(path, {"round": round_no, "edits": []})
        data["edits"] = [e for e in data.get("edits", [])
                         if e["edit_id"] != edit_id]
        data["edits"].append({
            "edit_id": edit_id, "component": component, "evidence": evidence,
            "root_cause": root_cause, "fix": fix,
            "predict_fix": predict_fix, "predict_regress": predict_regress,
            "t": _now(), "verdict": None})
        self._write_json(path, data)
        return data

    def attribute(self, round_no):
        """Score round N's predictions against round N+1's measured outcomes.

        An edit that predicted fixes it did not deliver, or caused regressions
        it did not predict, is REFUTED -- roll it back. This is the mechanism
        that keeps evolution from drifting into rationalised trial and error.
        """
        self._require_boot()
        man_p = self.manifests / ("round_%s.json" % round_no)
        man = self._read_json(man_p)
        if not man:
            raise SystemExit("no manifest for round %s" % round_no)
        before = self._read_json(self.evals / ("round_%s.json" % round_no), {}) or {}
        after = self._read_json(
            self.evals / ("round_%s.json" % (round_no + 1)), {}) or {}
        if not after:
            raise SystemExit(
                "no eval for round %s -- run `assertall --round %s` after "
                "applying the edits" % (round_no + 1, round_no + 1))

        newly_pass = sorted(k for k in after
                            if after[k]["passed"] and not before.get(
                                k, {}).get("passed", False))
        newly_fail = sorted(k for k in after
                            if not after[k]["passed"] and before.get(
                                k, {}).get("passed", False))

        for e in man["edits"]:
            delivered = [c for c in e["predict_fix"] if c in newly_pass]
            unpredicted = [c for c in newly_fail
                           if c not in e.get("predict_regress", [])]
            if delivered and not unpredicted:
                e["verdict"] = "confirmed"
            elif delivered and unpredicted:
                e["verdict"] = "partial"
            else:
                e["verdict"] = "refuted"
            e["delivered"] = delivered
            e["unpredicted_regressions"] = unpredicted

        man.update(newly_pass=newly_pass, newly_fail=newly_fail,
                   attributed_at=_now())
        self._write_json(man_p, man)
        man["rollback_recommended"] = [e["edit_id"] for e in man["edits"]
                                       if e["verdict"] == "refuted"]
        return man

    def promotion_gate(self, round_no):
        """Held-in must improve; held-out must not regress (Self-Harness 3.4)."""
        self._require_boot()
        before = self._read_json(self.evals / ("round_%s.json" % round_no), {}) or {}
        after = self._read_json(
            self.evals / ("round_%s.json" % (round_no + 1)), {}) or {}
        if not before or not after:
            raise SystemExit("need eval reports for rounds %s and %s"
                             % (round_no, round_no + 1))

        def tally(d, split):
            items = [v for v in d.values() if v.get("split") == split]
            return sum(1 for v in items if v["passed"]), len(items)

        hi_b, hi_n = tally(before, "held_in")
        hi_a, _ = tally(after, "held_in")
        ho_b, ho_n = tally(before, "held_out")
        ho_a, _ = tally(after, "held_out")

        improved = hi_a > hi_b
        no_regress = ho_a >= ho_b
        decision = "PROMOTE" if (improved and no_regress) else "REJECT"
        reason = []
        if not improved:
            reason.append("held-in did not improve (%d -> %d of %d)"
                          % (hi_b, hi_a, hi_n))
        if not no_regress:
            reason.append("held-out regressed (%d -> %d of %d)"
                          % (ho_b, ho_a, ho_n))
        if ho_n == 0:
            reason.append("WARNING: no held-out contracts exist -- the gate "
                          "cannot detect overfitting. Add contracts with "
                          "--split held_out.")
        return {"round": round_no, "held_in": [hi_b, hi_a, hi_n],
                "held_out": [ho_b, ho_a, ho_n], "decision": decision,
                "reasons": reason}

    # -- archive / rollback ----------------------------------------------

    def snapshot(self, round_no, paths):
        """Stepping stones: every accepted harness state stays reachable."""
        self._require_boot()
        import shutil
        dest = self.archive / ("round_%s" % round_no)
        dest.mkdir(parents=True, exist_ok=True)
        copied = []
        for rel in paths:
            src = Path(rel)
            if not src.is_absolute():
                src = self.ws / rel
            if not src.exists():
                continue
            tgt = dest / src.name
            if src.is_dir():
                if tgt.exists():
                    shutil.rmtree(tgt)
                shutil.copytree(src, tgt)
            else:
                shutil.copy2(src, tgt)
            try:
                copied.append(str(src.relative_to(self.ws)))
            except ValueError:
                copied.append(str(src))
        self._write_json(dest / "_snapshot.json",
                         {"round": round_no, "paths": copied, "t": _now()})
        return {"archive": str(dest), "copied": copied}

    def rollback(self, round_no):
        self._require_boot()
        import shutil
        src_dir = self.archive / ("round_%s" % round_no)
        meta = self._read_json(src_dir / "_snapshot.json")
        if not meta:
            raise SystemExit("no snapshot for round %s" % round_no)
        restored = []
        for rel in meta["paths"]:
            src = src_dir / Path(rel).name
            dst = Path(rel)
            if not dst.is_absolute():
                dst = self.ws / rel
            if not src.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            restored.append(rel)
        self.trace("kernel", "ROLLBACK", "round %s: %s"
                   % (round_no, ", ".join(restored)), "WARN")
        return {"round": round_no, "restored": restored}

    # -- playbook (ACE-style incremental delta updates) -------------------

    def playbook_add(self, section, text):
        """Append a delta bullet. Never rewrite the playbook wholesale --
        full rewrites are what cause context collapse and brevity bias."""
        self._require_boot()
        pb = self._read_json(self.playbook_path, {"entries": [], "next_id": 1})
        norm = re.sub(r"\s+", " ", text.strip().lower())
        for e in pb["entries"]:
            if re.sub(r"\s+", " ", e["text"].strip().lower()) == norm:
                e["helpful"] = e.get("helpful", 0) + 1
                e["updated"] = _now()
                self._write_json(self.playbook_path, pb)
                return {"deduped": True, "id": e["id"], "helpful": e["helpful"]}
        entry = {"id": pb.get("next_id", 1), "section": section, "text": text,
                 "helpful": 1, "harmful": 0, "created": _now(),
                 "updated": _now()}
        pb["entries"].append(entry)
        pb["next_id"] = entry["id"] + 1
        self._write_json(self.playbook_path, pb)
        return {"deduped": False, "id": entry["id"]}

    def playbook_mark(self, entry_id, harmful=True):
        self._require_boot()
        pb = self._read_json(self.playbook_path, {"entries": []})
        for e in pb["entries"]:
            if e["id"] == entry_id:
                key = "harmful" if harmful else "helpful"
                e[key] = e.get(key, 0) + 1
                e["updated"] = _now()
                self._write_json(self.playbook_path, pb)
                return e
        raise SystemExit("no playbook entry %s" % entry_id)

    def playbook_prune(self):
        self._require_boot()
        pb = self._read_json(self.playbook_path, {"entries": []})
        keep, dropped = [], []
        for e in pb["entries"]:
            if e.get("harmful", 0) > e.get("helpful", 0):
                dropped.append(e["id"])
            else:
                keep.append(e)
        pb["entries"] = keep
        self._write_json(self.playbook_path, pb)
        return {"kept": len(keep), "dropped": dropped}

    def playbook_set_goal(self, goal, done=None):
        self._require_boot()
        pb = self._read_json(self.playbook_path, {"entries": [], "next_id": 1})
        pb["goal"] = goal
        if done:
            pb["done_definition"] = done
        self._write_json(self.playbook_path, pb)
        return {"goal": goal, "done_definition": pb.get("done_definition")}

    # -- invariant constraints (Codex prefix layer / AgencyBench) ---------

    def constraint_add(self, text):
        """Record a hard invariant that must survive context compaction.

        Distinct from the playbook: the playbook is *learned* and prunable;
        constraints are *given* and immutable. Long-horizon agents fail by
        losing track of constraints (AgencyBench, 2026), and iterative context
        rewriting erodes exactly this kind of detail (ACE context collapse).
        These are surfaced verbatim by `status` and are never compacted, never
        summarised, never pruned -- the on-disk analogue of Codex's invariant
        prefix layer.
        """
        self._require_boot()
        text = (text or "").strip()
        if not text:
            raise SystemExit("constraint text is empty")
        data = self._read_json(self.constraints_path,
                               {"invariants": [], "next_id": 1})
        norm = re.sub(r"\s+", " ", text).lower()
        for c in data["invariants"]:
            if re.sub(r"\s+", " ", c["text"]).lower() == norm:
                return {"deduped": True, "id": c["id"], "text": c["text"]}
        cid = data.get("next_id", 1)
        entry = {"id": cid, "text": text, "added": _now(), "at": _ts()}
        data["invariants"].append(entry)
        data["next_id"] = cid + 1
        self._write_json(self.constraints_path, data)
        return {"deduped": False, "id": cid, "text": text,
                "count": len(data["invariants"])}

    def constraint_list(self):
        self._require_boot()
        data = self._read_json(self.constraints_path,
                               {"invariants": [], "next_id": 1})
        return {"invariants": data.get("invariants", []),
                "count": len(data.get("invariants", []))}

    # -- graded capability ladder (ExploitBench 16-tier oracle) -----------

    def ladder_set(self, name, target, tiers):
        """Define an ordered ladder of checks for one deliverable.

        A contract answers a binary question -- is this done? A ladder answers a
        graded one -- how far along is it? -- by scoring the highest *contiguous*
        tier passed. This gives long-horizon work the dense partial-credit signal
        that ExploitBench's graded oracle gives exploitation, instead of a single
        all-or-nothing verdict that says nothing until the very end.
        """
        self._require_boot()
        if not tiers:
            raise SystemExit("a ladder needs at least one tier")
        spec = {"name": name, "target": target, "tiers": list(tiers),
                "created": _now()}
        self._write_json(self.ladders / ("%s.json" % name), spec)
        return spec

    def ladder_assert(self, name):
        """Score a ladder: highest contiguous passing tier + fraction passed."""
        self._require_boot()
        spec = self._read_json(self.ladders / ("%s.json" % name))
        if not spec:
            raise SystemExit("no ladder named '%s'" % name)
        target = Path(spec["target"])
        if not target.is_absolute():
            target = self.ws / target
        tiers = spec["tiers"]
        results = []
        reached = 0
        broke = False
        for i, spec_check in enumerate(tiers, start=1):
            ok, msg = self._run_check(spec_check, target)
            results.append({"tier": i, "check": spec_check,
                            "pass": bool(ok), "msg": msg})
            if ok and not broke:
                reached = i
            elif not ok:
                broke = True
        passed = sum(1 for r in results if r["pass"])
        report = {"ladder": name, "target": str(target),
                  "tiers_total": len(tiers),
                  "tier_reached": reached,
                  "tiers_passed": passed,
                  "fraction": round(reached / float(len(tiers)), 4),
                  "results": results, "t": _now()}
        self._write_json(self.evals / ("ladder_%s.json" % name), report)
        if reached < len(tiers):
            nxt = results[reached] if reached < len(results) else None
            self.trace(name, "LADDER", "tier %d/%d; next blocked: %s"
                       % (reached, len(tiers),
                          nxt["check"] if nxt else "?"), "INFO")
        return report

    # -- test-time harness learning (Zhang et al., CMU 2026) --------------
    #
    # The inner loop of Harness Learning, without the RL-trained proposer:
    #   report  -> proposer input: task spec + execution report on Q_fb
    #   patch   -> structured SEARCH/REPLACE edit, all-or-nothing, validated
    #   score   -> J(h; Q_score) per candidate, plus validity terms
    #   select  -> keep the incumbent unless a candidate strictly beats it
    #   final   -> one blind run on Q_eval (sealed), then the set is spent

    def _spent_warning(self):
        s = self.cfg().get("sealed_spent")
        if not s:
            return None
        return ("Q_eval was spent by `final` at %s. Adaptation after that point "
                "makes any later `final` non-blind -- report the first final "
                "score, not a later one." % s.get("at"))

    @staticmethod
    def _parse_patch(text):
        """Parse FILE: + SEARCH/REPLACE blocks. Prose outside the blocks is
        ignored, so a proposal can (and should) lead with its diagnosis."""
        edits, cur_file, mode, buf, search = [], None, None, [], None
        for line in text.splitlines():
            s = line.rstrip("\r")
            if mode is None:
                m = re.match(r"^FILE:\s*(.+?)\s*$", s)
                if m:
                    cur_file = m.group(1)
                elif s.strip() == "<<<<<<< SEARCH":
                    if not cur_file:
                        raise ValueError("SEARCH block before any FILE: line")
                    mode, buf = "search", []
            elif mode == "search":
                if s.strip() == "=======":
                    search, mode, buf = buf, "replace", []
                else:
                    buf.append(s)
            elif s.strip() == ">>>>>>> REPLACE":
                edits.append((cur_file, search, buf))
                mode, buf = None, []
            else:
                buf.append(s)
        if mode is not None:
            raise ValueError("unterminated SEARCH/REPLACE block")
        if not edits:
            raise ValueError("no SEARCH/REPLACE blocks found")
        return edits

    @staticmethod
    def _diagnosis(text):
        head = text.split("FILE:", 1)[0]
        lines = [l.strip() for l in head.splitlines() if l.strip()]
        return " ".join(lines)[:300]

    def _snapshot_cover(self, round_no):
        meta = self._read_json(self.archive / ("round_%s" % round_no)
                               / "_snapshot.json")
        if not meta:
            return None
        return [(Path(r) if Path(r).is_absolute() else self.ws / r).resolve()
                for r in meta["paths"]]

    def _apply_patch(self, text, cover_round=None, dry_run=False):
        """Validate every block first, then write all files or none."""
        try:
            edits = self._parse_patch(text)
        except ValueError as e:
            return {"applied": False, "reason": "malformed", "detail": str(e)}
        guarded = set()
        for rel in (self._read_json(self.guard_path, {}) or {}).get("hashes", {}):
            p = Path(rel)
            guarded.add(str((p if p.is_absolute() else self.ws / p).resolve()))
        cover = None
        if cover_round is not None:
            cover = self._snapshot_cover(cover_round)
            if cover is None:
                return {"applied": False, "reason": "no_snapshot",
                        "detail": "candidate edits need `snapshot --round %s` "
                                  "first, so the incumbent can be restored"
                                  % cover_round}
        hdir = self.h.resolve()
        files, order = {}, []
        for rel, s_lines, r_lines in edits:
            p = Path(rel)
            p = (p if p.is_absolute() else self.ws / p).resolve()

            def fail(reason, detail):
                return {"applied": False, "reason": reason, "file": rel,
                        "detail": detail}

            if p != self.ws and self.ws not in p.parents:
                return fail("outside_workspace", str(p))
            if p == hdir or hdir in p.parents:
                return fail("kernel_state", "edits may not touch .harness/")
            if str(p) in guarded:
                return fail("guarded", "protected by `guard`: a repair edit may "
                                       "not touch a contract or verifier")
            if cover is not None and not any(p == c or c in p.parents
                                             for c in cover):
                return fail("not_snapshotted",
                            "outside this round's snapshot paths, so rollback "
                            "could not undo it")
            key = str(p)
            if key not in files:
                if p.exists():
                    with open(p, "r", encoding="utf-8", newline="") as f:
                        raw = f.read()
                    files[key] = [raw, "\r\n" in raw, p]
                else:
                    files[key] = [None, False, p]
                order.append(key)
            cur, crlf, _ = files[key]
            nl = "\r\n" if crlf else "\n"
            search = nl.join(s_lines) + (nl if s_lines else "")
            replace = nl.join(r_lines) + (nl if r_lines else "")
            if not s_lines:
                if cur is not None:
                    return fail("create_exists",
                                "empty SEARCH creates a file, but it exists")
                files[key][0] = replace
                continue
            if cur is None:
                return fail("missing_file", "file does not exist")
            n = cur.count(search)
            if n == 0 and cur.endswith(search[:-len(nl)]) \
                    and cur.count(search[:-len(nl)]) == 1:
                # SEARCH reaches the last line of a file with no final newline
                search = search[:-len(nl)]
                if replace.endswith(nl):
                    replace = replace[:-len(nl)]
                n = 1
            if n == 0:
                return fail("search_not_found",
                            "SEARCH text not found (first line: %r)"
                            % s_lines[0][:80])
            if n > 1:
                return fail("search_ambiguous",
                            "SEARCH matches %d times; add context lines" % n)
            files[key][0] = cur.replace(search, replace, 1)
        for key in order:
            new, _, p = files[key]
            if p.suffix == ".py":
                try:
                    compile(new, str(p), "exec")
                except SyntaxError as e:
                    return {"applied": False, "reason": "does_not_parse",
                            "file": str(p.relative_to(self.ws)),
                            "detail": "SyntaxError line %s: %s"
                                      % (e.lineno, e.msg)}
        touched = [str(files[k][2].relative_to(self.ws)) for k in order]
        if dry_run:
            return {"applied": False, "dry_run": True, "valid": True,
                    "files": touched, "blocks": len(edits)}
        for key in order:
            new, _, p = files[key]
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(new)
        return {"applied": True, "files": touched, "blocks": len(edits)}

    def _cand_index(self, round_no):
        path = self.candidates / ("round_%s" % round_no) / "index.json"
        return path, (self._read_json(path, None)
                      or {"candidates": {}, "active": None})

    def patch(self, patch_file, round_no=None, label=None, dry_run=False):
        """Apply a structured SEARCH/REPLACE edit, atomically.

        With --label this registers a tournament candidate for --round: the
        workspace is first restored to the round's snapshot (the incumbent),
        then the candidate is applied on top, so candidates never stack.
        """
        self._require_boot()
        pf = Path(patch_file)
        if not pf.is_absolute():
            pf = self.ws / pf
        if not pf.exists():
            raise SystemExit("no patch file %s" % pf)
        text = pf.read_text(encoding="utf-8")
        if label and round_no is None:
            raise SystemExit("--label (a candidate) needs --round")
        if label == "incumbent":
            raise SystemExit("'incumbent' is reserved for the unpatched state")

        if label:
            sc = self._read_json(self.evals / ("score_round_%s.json" % round_no),
                                 {}) or {}
            if "incumbent" not in sc:
                raise SystemExit(
                    "score the incumbent before any candidate: "
                    "`score --round %s --label incumbent`" % round_no)
            if self._snapshot_cover(round_no) is None:
                raise SystemExit("no snapshot for round %s -- `snapshot` the "
                                 "incumbent first" % round_no)
            if not dry_run:
                self.rollback(round_no)

        res = self._apply_patch(text, cover_round=round_no if label else None,
                                dry_run=dry_run)
        res["patch"] = str(pf)
        if dry_run:
            return res

        stats = self._read_json(self.patch_stats_path,
                                {"applied": 0, "rejected": 0, "reasons": {}})
        if res["applied"]:
            stats["applied"] += 1
            self.trace(label or "patch", "PATCH_OK", ", ".join(res["files"]))
        else:
            stats["rejected"] += 1
            stats["reasons"][res["reason"]] = \
                stats["reasons"].get(res["reason"], 0) + 1
            self.trace(label or "patch", "PATCH_REJECT",
                       "%s: %s" % (res["reason"], res.get("detail", "")),
                       "FAIL", signature="edit_rejected|direct|%s" % res["reason"])
        total = stats["applied"] + stats["rejected"]
        stats["validity_rate"] = round(stats["applied"] / float(total), 4)
        self._write_json(self.patch_stats_path, stats)

        if label:
            path, idx = self._cand_index(round_no)
            path.parent.mkdir(parents=True, exist_ok=True)
            (path.parent / ("%s.patch" % label)).write_text(text,
                                                            encoding="utf-8")
            idx["candidates"][label] = {
                "applied": res["applied"], "reason": res.get("reason"),
                "files": res.get("files", []),
                "diagnosis": self._diagnosis(text), "t": _now()}
            idx["active"] = label if res["applied"] else None
            self._write_json(path, idx)
        w = self._spent_warning()
        if w:
            res["warning"] = w
        return res

    def score(self, round_no, label, split="held_out"):
        """J(h; Q_score): mean per-contract check-pass fraction on the score
        split (dense, so near-misses rank above misses), plus validity terms.

        Writes no trace: scoring is selection, and its per-check detail must
        not become proposer feedback.
        """
        self._require_boot()
        split = self._norm_split(split)
        if split == "sealed":
            raise SystemExit("sealed contracts run only via `final`")
        _, idx = self._cand_index(round_no)
        active = idx.get("active")
        if label == "incumbent" and active:
            raise SystemExit("the workspace holds candidate '%s'; the incumbent "
                             "must be scored before any candidate is applied"
                             % active)
        if label != "incumbent" and label != active:
            raise SystemExit("the workspace holds %s, not '%s' -- apply it with "
                             "`patch --round %s --label %s` first"
                             % (("candidate '%s'" % active) if active
                                else "the incumbent", label, round_no, label))
        cs = self._contracts(split)
        if not cs:
            raise SystemExit("no %s contracts -- Q_score is empty. Add some with "
                             "`contract --split held_out` (alias: score)." % split)
        per, fracs, binary, completed, errors = {}, [], 0, 0, 0
        exists_all = True
        for c in cs:
            passed, results, target = self._check_contract(c)
            n = len(results)
            k = sum(1 for r in results.values() if r["pass"])
            err = sum(1 for r in results.values() if not r["pass"]
                      and str(r["msg"]).startswith(EXEC_ERROR_PREFIXES))
            frac = k / float(n) if n else 0.0
            per[c["name"]] = {"passed": passed, "fraction": round(frac, 4)}
            fracs.append(frac)
            binary += 1 if passed else 0
            completed += 0 if err else 1
            errors += err
            exists_all = exists_all and target.exists()
        J = sum(fracs) / len(fracs)
        rho = completed / float(len(cs))
        w = VALIDITY_WEIGHTS
        v = w[0] * exists_all + w[1] * (errors == 0) + w[2] * rho
        entry = {"label": label, "split": split, "J": round(J, 4),
                 "v": round(v, 4), "r": round(J + v, 4),
                 "binary": [binary, len(cs)], "contracts": per, "t": _now()}
        path = self.evals / ("score_round_%s.json" % round_no)
        data = self._read_json(path, {}) or {}
        data[label] = entry
        self._write_json(path, data)
        return entry

    def select(self, round_no):
        """Retention rule: promote the best candidate only if its J on Q_score
        is strictly greater than the incumbent's. v breaks ties between
        candidates but can never promote one over the incumbent on its own --
        a runnable-but-wrong harness must not beat a correct one.

        The workspace is restored to the incumbent either way; a winner is
        re-applied from its stored patch.
        """
        self._require_boot()
        sc = self._read_json(self.evals / ("score_round_%s.json" % round_no),
                             {}) or {}
        if "incumbent" not in sc:
            raise SystemExit("score the incumbent first: "
                             "`score --round %s --label incumbent`" % round_no)
        path, idx = self._cand_index(round_no)
        cands = idx["candidates"]
        inc = sc["incumbent"]
        ranked = sorted(((k, sc[k]) for k in cands
                         if cands[k].get("applied") and k in sc),
                        key=lambda kv: (kv[1]["J"], kv[1]["v"]), reverse=True)
        unscored = sorted(k for k in cands
                          if cands[k].get("applied") and k not in sc)
        best = ranked[0] if ranked else None
        promote = bool(best) and best[1]["J"] > inc["J"]

        self.rollback(round_no)
        if promote:
            again = self._apply_patch(
                (path.parent / ("%s.patch" % best[0])).read_text(
                    encoding="utf-8"), cover_round=round_no)
            if not again["applied"]:
                self.rollback(round_no)
                promote = False
        winner = best[0] if promote else None
        for k in cands:
            cands[k]["outcome"] = "promoted" if k == winner else "rejected"
        idx["active"] = winner
        idx["decision"] = "PROMOTE" if promote else "RETAIN"
        self._write_json(path, idx)

        if not ranked:
            reason = "no applied and scored candidates"
        elif promote:
            reason = "%s J=%.4f > incumbent J=%.4f" % (winner, best[1]["J"],
                                                        inc["J"])
        else:
            reason = ("best candidate %s J=%.4f did not strictly beat the "
                      "incumbent J=%.4f" % (best[0], best[1]["J"], inc["J"]))
        result = {"round": round_no, "decision": idx["decision"],
                  "incumbent_J": inc["J"], "winner": winner,
                  "winner_J": best[1]["J"] if promote else None,
                  "ranking": [[k, v["J"], v["v"]] for k, v in ranked],
                  "rejected": sorted(k for k in cands if k != winner),
                  "unscored": unscored, "reason": reason}
        self._write_json(path.parent / "tournament.json", result)

        curve = self._read_json(self.curve_path, {"rounds": []}) or {"rounds": []}
        curve["rounds"] = [r for r in curve["rounds"] if r["round"] != round_no]
        curve["rounds"].append({
            "round": round_no, "incumbent_J": inc["J"],
            "best_candidate_J": best[1]["J"] if best else None,
            "decision": idx["decision"], "candidates": len(cands),
            "J_after": best[1]["J"] if promote else inc["J"], "t": _ts()})
        curve["rounds"].sort(key=lambda r: r["round"])
        self._write_json(self.curve_path, curve)
        self.trace("kernel", "SELECT", "round %s: %s (%s)"
                   % (round_no, idx["decision"], reason))
        w = self._spent_warning()
        if w:
            result["warning"] = w
        return result

    def report(self, round_no):
        """The proposer's input (Harness Learning inner loop): task spec,
        invariants, and the execution report on Q_fb. Score-split and sealed
        contracts appear only as aggregates -- read this, not the raw trace."""
        self._require_boot()
        pb = self._read_json(self.playbook_path, {}) or {}
        cons = self._read_json(self.constraints_path, {}) or {}
        fb = []
        for c in self._contracts("held_in"):
            rep = self._read_json(self.evals / ("%s.json" % c["name"]))
            if not rep:
                fb.append({"contract": c["name"], "status": "unverified"})
            elif rep["passed"]:
                fb.append({"contract": c["name"], "status": "PASS"})
            else:
                fb.append({"contract": c["name"], "status": "FAIL",
                           "target": rep["target"],
                           "failed_checks": [{"check": k, "msg": v["msg"]}
                                             for k, v in rep["checks"].items()
                                             if not v["pass"]]})
        bundle = self.mine(round_no)
        score_hist = []
        for p in sorted(self.evals.glob("score_round_*.json")):
            inc = (self._read_json(p, {}) or {}).get("incumbent")
            if inc:
                score_hist.append({"round": p.stem.replace("score_round_", ""),
                                   "incumbent_J": inc["J"],
                                   "binary": inc["binary"]})
        prior = []
        for d in sorted(self.candidates.glob("round_*")):
            idx = self._read_json(d / "index.json", {}) or {}
            for k, v in (idx.get("candidates") or {}).items():
                prior.append({"round": d.name, "label": k,
                              "outcome": v.get("outcome", "pending"),
                              "applied": v.get("applied"),
                              "reason": v.get("reason"),
                              "diagnosis": v.get("diagnosis")})
        entries = sorted(pb.get("entries", []),
                         key=lambda e: -(e.get("helpful", 0) - e.get("harmful", 0)))
        rep = {
            "round": round_no,
            "goal": pb.get("goal"), "done_definition": pb.get("done_definition"),
            "invariants": [c["text"] for c in cons.get("invariants", [])],
            "feedback_split": fb,
            "failure_clusters": [
                {"signature": c["signature"], "size": c["size"],
                 "addressable": c["addressable"], "examples": c["examples"][:2]}
                for c in bundle["clusters"][:8]],
            "score_split": {"contracts": len(self._contracts("held_out")),
                            "incumbent_J_by_round": score_hist},
            "sealed": {"contracts": len(self._contracts("sealed")),
                       "spent": bool(self.cfg().get("sealed_spent"))},
            "prior_candidates": prior,
            "patch_validity": self._read_json(self.patch_stats_path),
            "adaptation_curve": (self._read_json(self.curve_path, {}) or {}
                                 ).get("rounds", []),
            "playbook": [e["text"] for e in entries[:10]],
            "proposer_rules": [
                "Propose edits against the feedback_split failures only.",
                "Do not re-propose a rejected prior candidate's mechanism.",
                "One mechanism per candidate; candidates must differ.",
                "Edit tools / middleware / memory before instructions.",
                "Output FILE: + SEARCH/REPLACE blocks, diagnosis first."]}
        self._write_json(self.evidence / ("round_%s" % round_no)
                         / "execution_report.json", rep)
        return rep

    def final(self, sealed_dir=None):
        """One blind run on Q_eval. Aggregates only; marks the set spent.

        --sealed-dir lets the contracts live outside the workspace (held by the
        user), which is the only arrangement in which the proposer genuinely
        never saw them.
        """
        self._require_boot()
        if sealed_dir:
            sd = Path(sealed_dir)
            if not sd.is_dir():
                raise SystemExit("no sealed dir %s" % sd)
            cs = []
            for p in sorted(sd.glob("*.json")):
                c = self._read_json(p)
                if c and "checks" in c and "target" in c:
                    c.setdefault("name", p.stem)
                    cs.append(c)
            source = str(sd)
        else:
            cs = self._contracts("sealed")
            source = "workspace"
        if not cs:
            raise SystemExit("no sealed contracts -- add some with "
                             "`contract --split sealed` (alias: eval), or pass "
                             "--sealed-dir")
        per, fracs, k = {}, [], 0
        for c in cs:
            passed, results, _ = self._check_contract(c)
            n = len(results)
            fracs.append(sum(1 for r in results.values() if r["pass"])
                         / float(n) if n else 0.0)
            per[c["name"]] = "PASS" if passed else "FAIL"
            k += 1 if passed else 0
        cfg = self.cfg()
        prior = cfg.get("sealed_spent")
        cfg["sealed_spent"] = {"at": prior["at"] if prior else _ts(),
                               "runs": (prior or {}).get("runs", 0) + 1,
                               "last": _ts()}
        self._write_json(self.config_path, cfg)
        res = {"source": source, "passed": k, "total": len(cs),
               "J_eval": round(sum(fracs) / len(fracs), 4),
               "contracts": per, "first_run": not prior}
        if prior:
            res["warning"] = ("Q_eval was already spent at %s. If the harness "
                              "changed since, this score is not blind -- "
                              "report the first final." % prior["at"])
        hist = self._read_json(self.evals / "final.json", {"runs": []}) or {
            "runs": []}
        hist["runs"].append(dict(res, t=_ts()))
        self._write_json(self.evals / "final.json", hist)
        self.trace("kernel", "FINAL", "sealed %d/%d J_eval=%.4f"
                   % (k, len(cs), res["J_eval"]))
        return res

    # -- guard (anti reward-hacking tripwire) -----------------------------

    def guard_init(self, extra=None):
        """Hash everything the evolving agent must not edit.

        NOT a security boundary -- a determined self-modifier can recompute
        these hashes. It is a TRIPWIRE that makes verifier tampering visible
        in the record. Real isolation needs OS permissions or a container.
        """
        self._require_boot()
        targets = [self.contracts]
        for rel in (extra or []):
            p = Path(rel)
            targets.append(p if p.is_absolute() else self.ws / rel)
        hashes = {}
        for t in targets:
            files = sorted(t.rglob("*")) if t.is_dir() else [t]
            for f in files:
                if f.is_file():
                    try:
                        key = str(f.relative_to(self.ws))
                    except ValueError:
                        key = str(f)
                    hashes[key] = hashlib.sha256(f.read_bytes()).hexdigest()
        self._write_json(self.guard_path,
                         {"t": _now(), "count": len(hashes), "hashes": hashes})
        return {"protected_files": len(hashes)}

    def guard_check(self):
        self._require_boot()
        g = self._read_json(self.guard_path)
        if not g:
            return {"status": "NOT_INITIALISED",
                    "advice": "run `guard init` before starting an evolve loop"}
        modified, missing = [], []
        for rel, want in g["hashes"].items():
            p = Path(rel)
            if not p.is_absolute():
                p = self.ws / rel
            if not p.exists():
                missing.append(rel)
            elif hashlib.sha256(p.read_bytes()).hexdigest() != want:
                modified.append(rel)
        status = "OK" if not (modified or missing) else "TAMPERED"
        if status == "TAMPERED":
            self.trace("kernel", "GUARD_TRIPPED",
                       "modified=%s missing=%s" % (modified, missing), "ERROR")
        return {"status": status, "modified": modified, "missing": missing,
                "advice": ("Verifier/contract files changed mid-loop. Treat "
                           "every result since the last clean check as void."
                           if status == "TAMPERED" else "")}

    # -- publish ----------------------------------------------------------

    def publish(self, name):
        """Only verified artifacts reach out/. The gate is the whole point."""
        self._require_boot()
        import shutil
        rep = self.run_assert(name)
        if not rep["passed"]:
            failed = [k for k, v in rep["checks"].items() if not v["pass"]]
            return {"published": False, "contract": name,
                    "failed_checks": failed,
                    "advice": "Fix the failures, then publish. Do not report "
                              "this deliverable as complete."}
        src = Path(rep["target"])
        dst = self.out / src.name
        self.out.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        self.trace(name, "PUBLISH", str(dst))
        return {"published": True, "contract": name, "path": str(dst)}

    # -- status -----------------------------------------------------------

    def status(self):
        self._require_boot()
        pb = self._read_json(self.playbook_path, {}) or {}
        reg = self._read_json(self.registry_path, {"jobs": {}}) or {}
        contracts = {}
        for c in self._contracts():
            if c.get("split") == "sealed":
                contracts[c["name"]] = "sealed"
                continue
            rep = self._read_json(self.evals / ("%s.json" % c["name"]))
            contracts[c["name"]] = ("PASS" if rep and rep["passed"]
                                    else ("FAIL" if rep else "unverified"))
        fails = len([r for r in self.read_trace(limit=100000)
                     if r.get("status") in ("FAIL", "ERROR")])
        cons = self._read_json(self.constraints_path, {}) or {}
        ladders = {}
        for p in sorted(self.ladders.glob("*.json")):
            rep = self._read_json(self.evals / ("ladder_%s.json" % p.stem))
            ladders[p.stem] = ("%d/%d" % (rep["tier_reached"], rep["tiers_total"])
                               if rep else "unscored")
        return {"workspace": str(self.ws),
                "goal": pb.get("goal"),
                "done_definition": pb.get("done_definition"),
                # invariants are surfaced verbatim: they must never be compacted
                "invariants": [c["text"] for c in cons.get("invariants", [])],
                "playbook_entries": len(pb.get("entries", [])),
                "jobs": dict((k, v.get("status")) for k, v in
                             reg.get("jobs", {}).items()),
                "contracts": contracts,
                "ladders": ladders,
                "splits": dict((s, len(self._contracts(s))) for s in SPLITS),
                "sealed": (self.cfg().get("sealed_spent") or "unspent"),
                "patch_validity": self._read_json(self.patch_stats_path),
                "adaptation": ((self._read_json(self.curve_path, {}) or {}
                                ).get("rounds") or [None])[-1],
                "logged_failures": fails,
                "guard": self.guard_check().get("status")}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _emit(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="harness_kernel.py",
        description="Harness OS kernel -- state, processes, verification, evidence.")
    p.add_argument("--workspace",
                   help="workspace root (default: $HARNESS_WORKSPACE or cwd)")
    # NOTE: dest must NOT be "cmd" -- the `fork` subparser defines --cmd, which
    # would overwrite the subcommand name and make `fork` silently do nothing.
    sub = p.add_subparsers(dest="subcommand")

    s = sub.add_parser("boot")
    s.add_argument("--profile")
    sub.add_parser("status")
    sub.add_parser("selftest")

    s = sub.add_parser("goal")
    s.add_argument("--text", required=True)
    s.add_argument("--done")

    s = sub.add_parser("fork")
    s.add_argument("--job", required=True)
    s.add_argument("--cmd", required=True)
    s.add_argument("--timeout", type=int)
    s.add_argument("--cwd")
    s.add_argument("--shell", action="store_true")

    s = sub.add_parser("poll")
    s.add_argument("--job")
    s = sub.add_parser("wait")
    s.add_argument("--job")
    s.add_argument("--timeout", type=int)

    s = sub.add_parser("trace")
    s.add_argument("--job", required=True)
    s.add_argument("--action", required=True)
    s.add_argument("--detail", default="")
    s.add_argument("--status", default="INFO")
    s.add_argument("--signature", help="verifier_cause|causal_status|mechanism")

    s = sub.add_parser("readtrace")
    s.add_argument("--job")
    s.add_argument("--limit", type=int, default=40)
    s.add_argument("--status")

    s = sub.add_parser("loopcheck")
    s.add_argument("--job", required=True)

    s = sub.add_parser("contract")
    s.add_argument("--name", required=True)
    s.add_argument("--target", required=True)
    s.add_argument("--checks", required=True,
                   help="comma-separated checks; use ';' where a check "
                        "argument itself needs a comma")
    s.add_argument("--split", default="held_in",
                   choices=list(SPLITS) + sorted(SPLIT_ALIASES),
                   help="held_in=feedback (Q_fb), held_out=score (Q_score), "
                        "sealed=eval (Q_eval, runs only via `final`)")
    s.add_argument("--notes", default="")

    s = sub.add_parser("assert")
    s.add_argument("--contract", required=True)
    s.add_argument("--round", type=int)

    s = sub.add_parser("assertall")
    s.add_argument("--round", type=int)
    s.add_argument("--split")

    s = sub.add_parser("mine")
    s.add_argument("--round", type=int)
    s.add_argument("--all-splits", action="store_true",
                   help="also mine held_out (score-split) failures")

    s = sub.add_parser("report")
    s.add_argument("--round", type=int, required=True)

    s = sub.add_parser("patch")
    s.add_argument("--file", required=True,
                   help="FILE: + SEARCH/REPLACE blocks")
    s.add_argument("--round", type=int)
    s.add_argument("--label", help="register as a tournament candidate")
    s.add_argument("--dry-run", action="store_true")

    s = sub.add_parser("score")
    s.add_argument("--round", type=int, required=True)
    s.add_argument("--label", required=True,
                   help="'incumbent' or the active candidate's label")
    s.add_argument("--split", default="held_out")

    s = sub.add_parser("select")
    s.add_argument("--round", type=int, required=True)

    s = sub.add_parser("final")
    s.add_argument("--sealed-dir")

    s = sub.add_parser("manifest")
    s.add_argument("--round", type=int, required=True)
    s.add_argument("--edit-id", required=True)
    s.add_argument("--component", required=True)
    s.add_argument("--evidence", required=True)
    s.add_argument("--root-cause", required=True)
    s.add_argument("--fix", required=True)
    s.add_argument("--predict-fix", default="")
    s.add_argument("--predict-regress", default="")

    s = sub.add_parser("attribute")
    s.add_argument("--round", type=int, required=True)
    s = sub.add_parser("gate")
    s.add_argument("--round", type=int, required=True)

    s = sub.add_parser("snapshot")
    s.add_argument("--round", type=int, required=True)
    s.add_argument("--paths", required=True)
    s = sub.add_parser("rollback")
    s.add_argument("--round", type=int, required=True)

    s = sub.add_parser("playbook")
    s.add_argument("op", choices=["add", "list", "mark", "prune"])
    s.add_argument("--section", default="general")
    s.add_argument("--text")
    s.add_argument("--id", type=int)
    s.add_argument("--helpful", action="store_true")

    s = sub.add_parser("constraint")
    s.add_argument("op", choices=["add", "list"])
    s.add_argument("--text")

    s = sub.add_parser("ladder")
    s.add_argument("op", choices=["set", "assert"])
    s.add_argument("--name", required=True)
    s.add_argument("--target")
    s.add_argument("--tiers",
                   help="ordered checks, same syntax as contract --checks: "
                        "comma-separated, use ';' where a check argument itself "
                        "needs a comma")

    s = sub.add_parser("guard")
    s.add_argument("op", choices=["init", "check"])
    s.add_argument("--extra", default="")

    s = sub.add_parser("publish")
    s.add_argument("--contract", required=True)

    a = p.parse_args(argv)
    if not a.subcommand:
        p.print_help()
        return
    h = Harness(a.workspace)

    def csv(v):
        return [x.strip() for x in (v or "").split(",") if x.strip()]

    if a.subcommand == "boot":
        _emit(h.boot(a.profile))
    elif a.subcommand == "status":
        _emit(h.status())
    elif a.subcommand == "selftest":
        r = selftest()
        _emit(r)
        sys.exit(0 if r["result"] == "PASS" else 1)
    elif a.subcommand == "goal":
        _emit(h.playbook_set_goal(a.text, a.done))
    elif a.subcommand == "fork":
        _emit(h.fork(a.job, a.cmd, a.timeout, a.cwd, a.shell))
    elif a.subcommand == "poll":
        _emit(h.poll(a.job))
    elif a.subcommand == "wait":
        _emit(h.wait(a.job, a.timeout))
    elif a.subcommand == "trace":
        _emit(h.trace(a.job, a.action, a.detail, a.status, a.signature))
    elif a.subcommand == "readtrace":
        _emit(h.read_trace(a.job, a.limit, a.status))
    elif a.subcommand == "loopcheck":
        _emit(h.loopcheck(a.job))
    elif a.subcommand == "contract":
        checks = [c.replace(";", ",") for c in csv(a.checks)]
        _emit(h.put_contract(a.name, a.target, checks, a.notes, a.split))
    elif a.subcommand == "assert":
        r = h.run_assert(a.contract, a.round)
        _emit(r)
        sys.exit(0 if r["passed"] else 1)
    elif a.subcommand == "assertall":
        r = h.assert_all(a.round, a.split)
        _emit(r)
        sys.exit(0 if r["all_passed"] else 1)
    elif a.subcommand == "mine":
        _emit(h.mine(a.round, a.all_splits))
    elif a.subcommand == "report":
        _emit(h.report(a.round))
    elif a.subcommand == "patch":
        r = h.patch(a.file, a.round, a.label, a.dry_run)
        _emit(r)
        sys.exit(0 if (r.get("applied") or r.get("valid")) else 1)
    elif a.subcommand == "score":
        _emit(h.score(a.round, a.label, a.split))
    elif a.subcommand == "select":
        r = h.select(a.round)
        _emit(r)
        sys.exit(0 if r["decision"] == "PROMOTE" else 1)
    elif a.subcommand == "final":
        _emit(h.final(a.sealed_dir))
    elif a.subcommand == "manifest":
        _emit(h.add_manifest(a.round, a.edit_id, a.component, a.evidence,
                             a.root_cause, a.fix, csv(a.predict_fix),
                             csv(a.predict_regress)))
    elif a.subcommand == "attribute":
        _emit(h.attribute(a.round))
    elif a.subcommand == "gate":
        r = h.promotion_gate(a.round)
        _emit(r)
        sys.exit(0 if r["decision"] == "PROMOTE" else 1)
    elif a.subcommand == "snapshot":
        _emit(h.snapshot(a.round, csv(a.paths)))
    elif a.subcommand == "rollback":
        _emit(h.rollback(a.round))
    elif a.subcommand == "playbook":
        if a.op == "add":
            _emit(h.playbook_add(a.section, a.text))
        elif a.op == "list":
            _emit(h._read_json(h.playbook_path, {}))
        elif a.op == "mark":
            _emit(h.playbook_mark(a.id, harmful=not a.helpful))
        else:
            _emit(h.playbook_prune())
    elif a.subcommand == "constraint":
        if a.op == "add":
            _emit(h.constraint_add(a.text))
        else:
            _emit(h.constraint_list())
    elif a.subcommand == "ladder":
        if a.op == "set":
            tiers = [c.replace(";", ",") for c in csv(a.tiers)]
            _emit(h.ladder_set(a.name, a.target, tiers))
        else:
            r = h.ladder_assert(a.name)
            _emit(r)
            sys.exit(0 if r["tier_reached"] == r["tiers_total"] else 1)
    elif a.subcommand == "guard":
        _emit(h.guard_init(csv(a.extra)) if a.op == "init" else h.guard_check())
    elif a.subcommand == "publish":
        r = h.publish(a.contract)
        _emit(r)
        sys.exit(0 if r["published"] else 1)


# --------------------------------------------------------------------------
# Self-test: proves the kernel actually works before any real task uses it.
# --------------------------------------------------------------------------

def selftest():
    import io
    import tempfile
    import shutil
    tmp = tempfile.mkdtemp(prefix="harness_selftest_")
    checks, failures = [], []
    py = sys.executable

    def ck(name, cond, extra=""):
        checks.append({"check": name, "pass": bool(cond), "info": str(extra)})
        if not cond:
            failures.append(name)

    try:
        h = Harness(tmp)
        h.boot(profile="selftest")
        ck("boot creates layout", h.contracts.exists() and h.evals.exists())

        h.playbook_set_goal("selftest goal", "all checks pass")
        h.playbook_add("lesson", "always verify before publishing")
        dup = h.playbook_add("lesson", "Always verify  before publishing")
        ck("playbook dedupes", dup.get("deduped") is True)

        # non-blocking fork + wait
        h.fork("j1", '"%s" -c "import time;time.sleep(2);print(\'hi\')"' % py,
               timeout=60, shell=True)
        polled = h.poll("j1")
        ck("fork is non-blocking", polled[0]["status"] == "running",
           polled[0]["status"])
        res = h.wait("j1", timeout=60)
        ck("job reaped", res[0]["status"] == "finished", res[0]["status"])
        ck("stdout captured",
           "hi" in (h.jobs / "j1" / "stdout.log").read_text(encoding="utf-8"))

        # timeout enforcement
        h.fork("j2", '"%s" -c "import time;time.sleep(60)"' % py,
               timeout=2, shell=True)
        time.sleep(4)
        r2 = h.poll("j2")
        ck("timeout kills job", r2[0]["status"] == "timeout", r2[0]["status"])

        # contracts: a failing then passing deliverable
        target = Path(tmp) / "report.md"
        target.write_text("# Intro\n\nTODO: write this\n", encoding="utf-8")
        h.put_contract("report", "report.md",
                       ["exists", "min_bytes:20", "sections:Intro|Method",
                        "no_placeholder", "min_words:50"], split="held_in")
        rep = h.run_assert("report", round_no=0)
        ck("assert catches incomplete deliverable", not rep["passed"])
        ck("placeholder check fires",
           rep["checks"]["no_placeholder"]["pass"] is False)
        ck("section check fires",
           rep["checks"]["sections:Intro|Method"]["pass"] is False)

        target.write_text("# Intro\n\n" + ("word " * 60) +
                          "\n\n# Method\n\n" + ("word " * 60) + "\n",
                          encoding="utf-8")
        rep2 = h.run_assert("report", round_no=1)
        ck("assert passes when contract met", rep2["passed"], rep2["checks"])

        # publish gate
        bad = Path(tmp) / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        h.put_contract("bad", "bad.json", ["exists", "valid_json"])
        ck("publish blocked on failure", h.publish("bad")["published"] is False)
        ck("published good artifact", h.publish("report")["published"] is True)
        ck("artifact lands in out/", (Path(tmp) / "out" / "report.md").exists())

        # cmd check (external verifier)
        h.put_contract("cmdok", "report.md",
                       ["exists", 'cmd:"%s" -c "import sys;sys.exit(0)"' % py])
        ck("cmd check runs external verifier",
           h.run_assert("cmdok")["passed"] is True)

        # loop breaker
        for _ in range(3):
            h.trace("j3", "grep_same_thing", "no matches")
        ck("loop breaker fires", h.loopcheck("j3")["loop"] is True)

        # weakness mining clusters by signature triple
        h.trace("j4", "build", "missing artifact", "FAIL",
                signature="missing_artifact|direct|no_output_path_registered")
        h.trace("j5", "build", "missing artifact", "FAIL",
                signature="missing_artifact|direct|no_output_path_registered")
        h.trace("j6", "build", "timeout", "FAIL",
                signature="timeout|direct|unbounded_retry")
        b = h.mine(round_no=1)
        top = b["clusters"][0]
        ck("mining clusters by signature", top["size"] >= 2, top["signature"])
        ck("signature triple parsed",
           top["mechanism"] == "no_output_path_registered", top["mechanism"])

        # manifest -> attribution (a prediction that does not land is refuted)
        h.put_contract("ho_a", "report.md", ["exists"], split="held_out")
        h.run_assert("ho_a", round_no=1)
        h.add_manifest(1, "e1", "middleware", "cluster missing_artifact",
                       "output path never registered",
                       "register output path before run", ["bad"], [])
        h.run_assert("report", round_no=2)
        h.run_assert("ho_a", round_no=2)
        h.run_assert("bad", round_no=2)
        att = h.attribute(1)
        ck("refuted edit is flagged for rollback",
           att["edits"][0]["verdict"] == "refuted", att["edits"][0]["verdict"])

        gate = h.promotion_gate(1)
        ck("promotion gate returns a decision",
           gate["decision"] in ("PROMOTE", "REJECT"), gate["decision"])
        ck("gate reports held-out coverage",
           gate["held_out"][2] >= 1, gate["held_out"])

        # snapshot + rollback
        h.snapshot(1, ["report.md"])
        target.write_text("# broken\n", encoding="utf-8")
        h.rollback(1)
        ck("rollback restores artifact",
           "Method" in target.read_text(encoding="utf-8"))

        # guard tripwire
        h.guard_init()
        ck("guard clean after init", h.guard_check()["status"] == "OK")
        cpath = h.contracts / "report.json"
        cpath.write_text(cpath.read_text(encoding="utf-8").replace(
            "min_words:50", "min_words:1"), encoding="utf-8")
        ck("guard detects contract tampering",
           h.guard_check()["status"] == "TAMPERED")

        st = h.status()
        ck("status reports contracts", "report" in st["contracts"])

        # ---- v2.1.0: invariant constraints -----------------------------
        h.constraint_add("nginx.conf is READ-ONLY -- never chmod it")
        dupc = h.constraint_add("nginx.conf is READ-ONLY   -- never chmod it")
        ck("constraint dedupes", dupc.get("deduped") is True, dupc)
        cl = h.constraint_list()
        ck("constraint persisted", cl["count"] == 1, cl)
        stc = h.status()
        ck("status surfaces invariants verbatim",
           any("READ-ONLY" in x for x in stc["invariants"]), stc["invariants"])

        # ---- v2.1.0: challenge-response (anti-gaming) ------------------
        # A verifier that emits the live nonce passes; one that emits a
        # hardcoded/stale answer is rejected even though it exits 0.
        h.put_contract("chal_live", "report.md",
                       ['challenge:"%s" -c "import os;'
                        'print(os.environ[\'HARNESS_CHALLENGE\'])"' % py])
        ck("challenge passes on a live fresh response",
           h.run_assert("chal_live")["passed"] is True)
        h.put_contract("chal_stale", "report.md",
                       ['challenge:"%s" -c "print(\'deadbeefdeadbeef\')"' % py])
        rst = h.run_assert("chal_stale")
        ck("challenge rejects a hardcoded exit-0 answer",
           rst["passed"] is False, rst["checks"])

        # ---- v2.1.0: graded capability ladder --------------------------
        # report.md has ~120 words: tier 1 (exists) and tier 2 (>=50 words)
        # pass, tier 3 (>=100000 words) blocks -> highest contiguous tier = 2.
        h.ladder_set("progress", "report.md",
                     ["exists", "min_words:50", "min_words:100000"])
        lad = h.ladder_assert("progress")
        ck("ladder scores highest contiguous tier",
           lad["tier_reached"] == 2 and lad["tiers_total"] == 3, lad)
        ck("ladder reports a fraction",
           abs(lad["fraction"] - 2 / 3.0) < 0.01, lad["fraction"])
        std = h.status()
        ck("status shows ladder progress",
           std["ladders"].get("progress") == "2/3", std["ladders"])

        # ---- v2.2.0: test-time harness learning ------------------------
        # Isolated workspace: tool.py is a toy "harness"; contracts on it are
        # split into feedback (Q_fb), score (Q_score) and sealed (Q_eval).
        w2 = Path(tmp) / "v22"
        w2.mkdir()
        (w2 / "edits").mkdir()
        g = Harness(str(w2))
        g.boot(profile="selftest")
        tool = w2 / "tool.py"
        tool.write_text("def answer():\n    return 1\n\nprint(answer())\n",
                        encoding="utf-8")

        def pw(name, body):
            (w2 / "edits" / name).write_text(body, encoding="utf-8")
            return "edits/" + name

        def blk(path, old, new):
            return ("FILE: %s\n<<<<<<< SEARCH\n%s\n=======\n%s\n"
                    ">>>>>>> REPLACE\n" % (path, old, new))

        g.put_contract("fb1", "tool.py", ["exists", "regex_present:return 2"],
                       split="feedback")
        sc1 = g.put_contract("sc1", "tool.py",
                             ["exists", "regex_present:return 2",
                              "regex_present:# verified"], split="score")
        ev1 = g.put_contract("ev1", "tool.py", ["regex_present:return 2"],
                             split="eval")
        ck("split aliases map to held_out / sealed",
           sc1["split"] == "held_out" and ev1["split"] == "sealed")
        try:
            g.run_assert("ev1")
            refused = False
        except SystemExit:
            refused = True
        ck("assert refuses a sealed contract", refused)
        sa = g.assert_all(round_no=1)
        ck("assertall skips sealed contracts",
           "ev1" not in sa["passed"] + sa["failed"]
           and sa.get("sealed_skipped") == 1, sa)

        jobs = set(j for c in g.mine(1)["clusters"] for j in c["jobs"])
        ck("mine excludes score-split failures by default",
           "fb1" in jobs and "sc1" not in jobs, jobs)
        jobs_all = set(j for c in g.mine(1, all_splits=True)["clusters"]
                       for j in c["jobs"])
        ck("mine --all-splits includes them", "sc1" in jobs_all, jobs_all)

        rp = g.report(1)
        fbrow = [r for r in rp["feedback_split"] if r["contract"] == "fb1"]
        ck("report carries feedback-split failure detail",
           fbrow and fbrow[0]["status"] == "FAIL"
           and fbrow[0]["failed_checks"], fbrow)
        ck("report hides score-split check detail",
           "# verified" not in json.dumps(rp), rp["score_split"])

        p1 = pw("c1.patch", "Diagnosis: wrong constant.\n"
                + blk("tool.py", "    return 1", "    return 2"))
        g.snapshot(1, ["tool.py"])
        try:
            g.patch(p1, 1, "c1")
            early = False
        except SystemExit:
            early = True
        ck("candidate refused before the incumbent is scored", early)
        s0 = g.score(1, "incumbent")
        ck("score is a dense mean check fraction",
           abs(s0["J"] - 1 / 3.0) < 0.01 and s0["binary"] == [0, 1], s0)
        ck("validity terms computed", abs(s0["v"] - 0.30) < 1e-6, s0["v"])

        r1 = g.patch(p1, 1, "c1")
        ck("patch applies a SEARCH/REPLACE block",
           r1["applied"] and "return 2" in tool.read_text(encoding="utf-8"), r1)
        g.score(1, "c1")
        p2 = pw("c2.patch", blk("tool.py", "    return 1",
                                "    return 2  # verified"))
        r2 = g.patch(p2, 1, "c2")
        ck("candidates do not stack (each applies to the incumbent)",
           r2["applied"], r2)
        s2 = g.score(1, "c2")
        p3 = pw("c3.patch", blk("tool.py", "    return 99", "    return 5"))
        r3 = g.patch(p3, 1, "c3")
        ck("patch rejects SEARCH text that is not found",
           not r3["applied"] and r3["reason"] == "search_not_found", r3)
        ck("rejected candidate leaves the incumbent in place",
           "return 1" in tool.read_text(encoding="utf-8"))
        try:
            g.score(1, "c3")
            scored_inactive = True
        except SystemExit:
            scored_inactive = False
        ck("score refuses a label that is not in the workspace",
           not scored_inactive)
        sel = g.select(1)
        ck("select promotes the strictly best candidate",
           sel["decision"] == "PROMOTE" and sel["winner"] == "c2"
           and s2["J"] == 1.0, sel)
        ck("winner is re-applied after select",
           "# verified" in tool.read_text(encoding="utf-8"))
        pv = g._read_json(g.patch_stats_path)
        ck("patch validity rate tracked",
           pv["applied"] == 2 and pv["rejected"] == 1
           and abs(pv["validity_rate"] - 2 / 3.0) < 0.01, pv)

        g.snapshot(2, ["tool.py"])
        g.score(2, "incumbent")
        g.patch(pw("c4.patch", blk("tool.py", "    return 2  # verified",
                                   "    return 3")), 2, "c4")
        g.score(2, "c4")
        # c4b ties the incumbent (J=1.0): a tie must not promote
        g.patch(pw("c4b.patch", blk("tool.py", "def answer():",
                                    "def answer():  # tie")), 2, "c4b")
        g.score(2, "c4b")
        sel2 = g.select(2)
        txt = tool.read_text(encoding="utf-8")
        ck("select retains the incumbent on a tie or a loss",
           sel2["decision"] == "RETAIN" and "# verified" in txt
           and "# tie" not in txt, sel2)
        ck("adaptation curve records each round",
           [r["decision"] for r in g._read_json(g.curve_path)["rounds"]]
           == ["PROMOTE", "RETAIN"])

        before = tool.read_text(encoding="utf-8")
        ra = g.patch(pw("atomic.patch",
                        blk("tool.py", "def answer():", "def answer2():")
                        + blk("tool.py", "no such line", "x")))
        ck("patch is all-or-nothing",
           not ra["applied"] and tool.read_text(encoding="utf-8") == before, ra)
        (w2 / "dup.txt").write_text("x\nx\n", encoding="utf-8")
        rd = g.patch(pw("dup.patch", blk("dup.txt", "x", "y")))
        ck("patch rejects an ambiguous SEARCH",
           rd.get("reason") == "search_ambiguous", rd)
        rs = g.patch(pw("syn.patch", blk("tool.py", "    return 2  # verified",
                                         "    return (")))
        ck("patch rejects a .py edit that does not parse",
           rs.get("reason") == "does_not_parse"
           and tool.read_text(encoding="utf-8") == before, rs)
        ro = g.patch(pw("out.patch", blk("../evil.txt", "", "pwned")))
        ck("patch refuses paths outside the workspace",
           ro.get("reason") == "outside_workspace", ro)
        (w2 / "verify.py").write_text("import sys\nsys.exit(0)\n",
                                      encoding="utf-8")
        g.guard_init(["verify.py"])
        rg = g.patch(pw("g.patch", blk("verify.py", "sys.exit(0)",
                                       "sys.exit(0)  # always pass")))
        ck("patch refuses guarded verifier files",
           rg.get("reason") == "guarded", rg)
        rk = g.patch(pw("k.patch", blk(".harness/config.json", "", "{}")))
        ck("patch refuses kernel state", rk.get("reason") == "kernel_state", rk)
        (w2 / "other.txt").write_text("a\n", encoding="utf-8")
        g.snapshot(3, ["tool.py"])
        g.score(3, "incumbent")
        rn = g.patch(pw("n.patch", blk("other.txt", "a", "b")), 3, "c5")
        ck("candidate edits must stay inside the snapshot",
           rn.get("reason") == "not_snapshotted", rn)
        with open(w2 / "crlf.txt", "wb") as f:
            f.write(b"a\r\nb\r\n")
        g.patch(pw("crlf.patch", blk("crlf.txt", "b", "B")))
        ck("patch preserves CRLF line endings",
           (w2 / "crlf.txt").read_bytes() == b"a\r\nB\r\n",
           (w2 / "crlf.txt").read_bytes())

        f1 = g.final()
        ck("final runs the sealed set once, blind",
           f1["passed"] == 1 and f1["total"] == 1 and f1["first_run"], f1)
        ck("status marks Q_eval spent", g.status()["sealed"] != "unspent")
        f2 = g.final()
        ck("a second final is flagged as not blind", "warning" in f2, f2)
        (w2 / "note.txt").write_text("n\n", encoding="utf-8")
        rw = g.patch(pw("w.patch", blk("note.txt", "n", "m")))
        ck("adaptation after final carries a warning", "warning" in rw, rw)
        ext = Path(tmp) / "held_by_user"
        ext.mkdir()
        (ext / "x1.json").write_text(json.dumps(
            {"name": "x1", "target": str(tool), "checks": ["exists"]}),
            encoding="utf-8")
        fx = g.final(str(ext))
        ck("final --sealed-dir reads contracts held outside the workspace",
           fx["source"] == str(ext) and fx["passed"] == 1, fx)

        # ---- CLI layer -------------------------------------------------
        # The API can be correct while the CLI silently misroutes. It has
        # happened: `fork` defines --cmd, which collided with the subparser
        # dest and made the whole subcommand a no-op. Exercise the CLI.
        import contextlib

        def cli(argv):
            buf = io.StringIO()
            code = 0
            try:
                with contextlib.redirect_stdout(buf):
                    main(["--workspace", tmp] + argv)
            except SystemExit as e:
                code = e.code if isinstance(e.code, int) else 1
            out = buf.getvalue()
            try:
                return code, json.loads(out)
            except Exception:
                return code, out

        _, forked = cli(["fork", "--job", "cli1", "--shell",
                         "--cmd", '"%s" -c "print(7)"' % py, "--timeout", "30"])
        ck("CLI fork actually starts a job",
           isinstance(forked, dict) and forked.get("status") == "running",
           forked)
        _, waited = cli(["wait", "--job", "cli1", "--timeout", "40"])
        ck("CLI wait reaps the job",
           isinstance(waited, list) and waited[0]["status"] == "finished",
           waited)
        ck("CLI job produced output",
           "7" in (h.jobs / "cli1" / "stdout.log").read_text(encoding="utf-8"))

        _, made = cli(["contract", "--name", "cli_c", "--target", "report.md",
                       "--checks", "exists,min_words:10"])
        ck("CLI contract parses checks",
           made.get("checks") == ["exists", "min_words:10"], made.get("checks"))
        code, _ = cli(["assert", "--contract", "cli_c"])
        ck("CLI assert exits 0 on pass", code == 0, code)
        code, _ = cli(["assert", "--contract", "bad"])
        ck("CLI assert exits 1 on fail", code == 1, code)

        # every declared subcommand must reach a real branch
        unreachable = []
        sweep = {
            "status": ["status"],
            "poll": ["poll"],
            "readtrace": ["readtrace"],
            "mine": ["mine"],
            "playbook": ["playbook", "list"],
            "constraint": ["constraint", "list"],
            "ladder": ["ladder", "assert", "--name", "progress"],
            "report": ["report", "--round", "1"],
        }
        for name, argv in sweep.items():
            c, o = cli(argv)
            if o == "" or o is None:
                unreachable.append(name)
        ck("no subcommand silently no-ops", not unreachable, unreachable)

        # CLI parses constraint add and ladder set end to end
        _, cadd = cli(["constraint", "add", "--text", "held-out set is frozen"])
        ck("CLI constraint add works",
           isinstance(cadd, dict) and cadd.get("id"), cadd)
        _, lset = cli(["ladder", "set", "--name", "cli_lad",
                       "--target", "report.md", "--tiers", "exists,min_words:10"])
        ck("CLI ladder set parses tiers",
           isinstance(lset, dict) and lset.get("tiers") == ["exists",
                                                            "min_words:10"], lset)
        code, _ = cli(["ladder", "assert", "--name", "cli_lad"])
        ck("CLI ladder assert exits 0 when all tiers pass", code == 0, code)

        (Path(tmp) / "dry.patch").write_text(
            "FILE: report.md\n<<<<<<< SEARCH\n# Intro\n=======\n"
            "# Introduction\n>>>>>>> REPLACE\n", encoding="utf-8")
        code, dry = cli(["patch", "--file", "dry.patch", "--dry-run"])
        ck("CLI patch --dry-run validates without writing",
           code == 0 and isinstance(dry, dict) and dry.get("valid")
           and "# Introduction" not in target.read_text(encoding="utf-8"), dry)
        _, ctr = cli(["contract", "--name", "cli_ev", "--target", "report.md",
                      "--checks", "exists", "--split", "eval"])
        ck("CLI contract accepts split aliases",
           isinstance(ctr, dict) and ctr.get("split") == "sealed", ctr)
    # SystemExit too: kernel refusals raise it, and an unexpected refusal
    # must surface as a failed check, not end the selftest silently.
    except (Exception, SystemExit) as exc:  # noqa: BLE001 -- must always report
        ck("selftest ran without exception", False, repr(exc))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return {"kernel_version": KERNEL_VERSION,
            "total": len(checks), "failed": len(failures),
            "failures": failures,
            "result": "PASS" if not failures else "FAIL",
            "checks": checks}


if __name__ == "__main__":
    main()
