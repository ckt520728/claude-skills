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
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

KERNEL_VERSION = "2.0.0"

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
        self.out = self.ws / "out"

        self.playbook_path = self.state / "playbook.json"
        self.registry_path = self.state / "registry.json"
        self.trace_path = self.logs / "trace.jsonl"
        self.guard_path = self.h / "guard.json"
        self.config_path = self.h / "config.json"

    # -- filesystem -------------------------------------------------------

    def boot(self, profile=None):
        for d in (self.h, self.state, self.jobs, self.logs, self.evals,
                  self.contracts, self.evidence, self.manifests,
                  self.archive, self.out):
            d.mkdir(parents=True, exist_ok=True)

        if not self.registry_path.exists():
            self._write_json(self.registry_path,
                             {"jobs": {}, "round": 0, "created": _now()})
        if not self.playbook_path.exists():
            self._write_json(self.playbook_path,
                             {"goal": None, "done_definition": None,
                              "milestones": [], "entries": [], "next_id": 1})
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

    def trace(self, job, action, detail="", status="INFO", signature=None):
        """Append one compact JSONL record. Traces live on disk, never in context."""
        self._require_boot()
        rec = {"t": _ts(), "job": job, "action": action,
               "status": status, "detail": (detail or "")[:600]}
        if signature:
            rec["sig"] = signature
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
        if kind != "cmd" and not target.exists():
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
        return False, "unknown check kind: %s" % kind

    def run_assert(self, name, round_no=None):
        """Physical verification. An agent saying 'done' is not evidence."""
        self._require_boot()
        c = self._read_json(self.contracts / ("%s.json" % name))
        if not c:
            raise SystemExit("no contract named '%s'" % name)
        target = Path(c["target"])
        if not target.is_absolute():
            target = self.ws / target

        results = {}
        passed = True
        for spec in c["checks"]:
            ok, msg = self._run_check(spec, target)
            results[spec] = {"pass": bool(ok), "msg": msg}
            if not ok:
                passed = False
                self.trace(name, "ASSERT_FAIL", "%s -> %s" % (spec, msg),
                           "FAIL",
                           signature="%s|verifier|%s" % (spec.split(":")[0], name))
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
        summary = {"passed": [], "failed": [], "round": round_no}
        for p in sorted(self.contracts.glob("*.json")):
            c = self._read_json(p, {})
            if split and c.get("split") != split:
                continue
            rep = self.run_assert(p.stem, round_no)
            (summary["passed"] if rep["passed"] else summary["failed"]).append(
                p.stem)
        summary["all_passed"] = not summary["failed"]
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

    def mine(self, round_no=None):
        """Cluster failures by signature triple (Self-Harness sec. 3.2).

        signature = (verifier_cause, causal_status, mechanism)
        Two failures group together only when the verifier rejected them for the
        same reason AND the same agent-side mechanism produced it. This is what
        stops the loop from patching symptoms.
        """
        self._require_boot()
        rows = [r for r in self.read_trace(limit=100000)
                if r.get("status") in ("FAIL", "ERROR")]
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
        for p in sorted(self.contracts.glob("*.json")):
            rep = self._read_json(self.evals / ("%s.json" % p.stem))
            contracts[p.stem] = ("PASS" if rep and rep["passed"]
                                 else ("FAIL" if rep else "unverified"))
        fails = len([r for r in self.read_trace(limit=100000)
                     if r.get("status") in ("FAIL", "ERROR")])
        return {"workspace": str(self.ws),
                "goal": pb.get("goal"),
                "done_definition": pb.get("done_definition"),
                "playbook_entries": len(pb.get("entries", [])),
                "jobs": dict((k, v.get("status")) for k, v in
                             reg.get("jobs", {}).items()),
                "contracts": contracts,
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
    s.add_argument("--split", default="held_in", choices=["held_in", "held_out"])
    s.add_argument("--notes", default="")

    s = sub.add_parser("assert")
    s.add_argument("--contract", required=True)
    s.add_argument("--round", type=int)

    s = sub.add_parser("assertall")
    s.add_argument("--round", type=int)
    s.add_argument("--split")

    s = sub.add_parser("mine")
    s.add_argument("--round", type=int)

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
        _emit(h.mine(a.round))
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
        for name in ("status", "poll", "readtrace", "mine", "playbook"):
            argv = [name] + (["list"] if name == "playbook" else [])
            c, o = cli(argv)
            if o == "" or o is None:
                unreachable.append(name)
        ck("no subcommand silently no-ops", not unreachable, unreachable)
    except Exception as exc:  # noqa: BLE001 -- selftest must always report
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
