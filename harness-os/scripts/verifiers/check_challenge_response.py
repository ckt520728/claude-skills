#!/usr/bin/env python3
"""Dynamic challenge-response verification -- the anti-gaming check.

A self-improvement loop optimises against whatever it is graded on. The cheapest
way to "pass" a verifier is not to do the work but to memorise the answer: h; a
contract that always expects the same output can be satisfied by a deliverable
that hardcodes that output and never actually runs. ExploitBench's graded oracle
closes this by issuing a *fresh random challenge every run* and requiring the
artifact to produce a response computed from it, so a memorised answer is stale
by construction.

This verifier is the general-purpose realisation of that idea. It is meant to be
driven by the kernel's `challenge:` check, which injects a fresh nonce as
`$HARNESS_CHALLENGE` on every assertion:

    $K contract --name repro --target solver.py \
      --checks "challenge:python .../check_challenge_response.py \
                --artifact 'python solver.py'"

Flow each run:
  1. read the fresh nonce from $HARNESS_CHALLENGE (the kernel sets it);
  2. run the artifact against that nonce (appended as the final argument, and
     also visible in the environment);
  3. compute the expected deterministic transform of the nonce;
  4. PASS only if the artifact's output matches -- and, on pass, echo the nonce
     so the kernel can confirm the check ran live on THIS challenge.

A deliverable that hardcodes a previous answer, or a verifier stub that fakes a
pass, cannot produce the transform of a nonce it has never seen. The transform
here (sha256 by default) stands in for the real deterministic property of the
deliverable -- for a signal-analysis pipeline it might be "metric for seed N",
for a solver "answer for input N". Swap `--algo`/`--expect-cmd` for the property
that actually matters; the mechanism is the point, not sha256.

Limit (stated plainly): this proves the artifact ran against a live, unrepeatable
challenge. It does not prove the artifact is *correct* in general -- only that it
responds correctly to the challenge, and cannot have memorised it. Pair it with
ordinary content checks for the rest.

Usage:
  # preferred inside a `challenge:` check -- artifact given as trailing UNQUOTED
  # tokens after `--`, so it survives any platform's shell quoting (Windows cmd
  # does not group single quotes; this form never needs a quoted multi-word arg):
  python check_challenge_response.py -- python solver.py
  python check_challenge_response.py --algo sha256 -- python solver.py

  # alternative: one quoted command string (fine on POSIX; use double quotes on
  # Windows). Handy when calling the verifier directly rather than via the kernel:
  python check_challenge_response.py --artifact "python solver.py"
  python check_challenge_response.py -- python p.py \
      --expect-cmd "python oracle.py"      # (put --expect-cmd before --)
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _verifier import Report, base_parser, main_guard  # noqa: E402

ALGOS = {"sha256", "sha1", "md5", "echo"}


def _transform(nonce, algo):
    if algo == "echo":
        return nonce
    h = hashlib.new(algo)
    h.update(nonce.encode("utf-8"))
    return h.hexdigest()


def _last_token(text):
    """The response is the last non-empty stripped line of stdout, so an
    artifact may print logs before its answer."""
    for line in reversed((text or "").splitlines()):
        if line.strip():
            return line.strip()
    return ""


def main():
    p = base_parser("Dynamic challenge-response (anti-gaming) verification.")
    p.add_argument("--artifact",
                   help="the deliverable command as one (quoted) string; the "
                        "fresh nonce is appended as its final argument. Prefer "
                        "the trailing '-- <cmd> <args>' form under the kernel.")
    p.add_argument("--algo", default="sha256", choices=sorted(ALGOS),
                   help="deterministic transform the artifact must apply to the "
                        "nonce (default sha256); 'echo' = must return the nonce")
    p.add_argument("--expect-cmd",
                   help="instead of --algo, a command that prints the expected "
                        "response for the nonce (a separate oracle)")
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("artifact_cmd", nargs=argparse.REMAINDER,
                   help="the deliverable command as trailing unquoted tokens "
                        "(everything after '--'); shell-quoting-proof")
    a = p.parse_args()

    r = Report("challenge-response")

    # Resolve the artifact command. Trailing tokens (after '--') win because they
    # need no shell quoting; fall back to the single --artifact string.
    tokens = list(a.artifact_cmd)
    if tokens and tokens[0] == "--":
        tokens = tokens[1:]
    use_list = bool(tokens)
    if not use_list and not a.artifact:
        r.fail("no artifact command given -- pass it after '--' "
               "(e.g. '-- python solver.py') or via --artifact \"...\"")
        return r.emit(a.as_json)

    nonce = os.environ.get("HARNESS_CHALLENGE", "").strip()
    if not nonce:
        r.fail("no $HARNESS_CHALLENGE in the environment -- this verifier must "
               "be driven by the kernel's `challenge:` check, which injects a "
               "fresh nonce each run")
        return r.emit(a.as_json)

    # 1. expected response for this exact nonce
    if a.expect_cmd:
        try:
            ex = subprocess.run("%s %s" % (a.expect_cmd, nonce), shell=True,
                                capture_output=True, text=True,
                                timeout=a.timeout, env=dict(os.environ))
        except Exception as e:  # noqa: BLE001
            r.fail("expected-value oracle failed to run: %s" % e)
            return r.emit(a.as_json)
        if ex.returncode != 0:
            r.fail("expected-value oracle exited %d" % ex.returncode)
            return r.emit(a.as_json)
        expected = _last_token(ex.stdout)
    else:
        expected = _transform(nonce, a.algo)

    # 2. run the artifact against this nonce
    try:
        if use_list:
            got = subprocess.run(tokens + [nonce], shell=False,
                                 capture_output=True, text=True,
                                 timeout=a.timeout, env=dict(os.environ))
        else:
            got = subprocess.run("%s %s" % (a.artifact, nonce), shell=True,
                                 capture_output=True, text=True,
                                 timeout=a.timeout, env=dict(os.environ))
    except subprocess.TimeoutExpired:
        r.fail("artifact did not respond within %ds" % a.timeout)
        return r.emit(a.as_json)
    except Exception as e:  # noqa: BLE001
        r.fail("artifact failed to run: %s" % e)
        return r.emit(a.as_json)

    if got.returncode != 0:
        r.fail("artifact exited %d against the challenge; stderr: %s"
               % (got.returncode, (got.stderr or "").strip()[-160:]))
        return r.emit(a.as_json)

    response = _last_token(got.stdout)

    # 3. compare
    if response == expected:
        r.note("live challenge %s.. answered correctly (%s)"
               % (nonce[:8], a.algo if not a.expect_cmd else "oracle"))
        # Echo the nonce so the kernel's challenge check confirms freshness.
        r.emit(a.as_json)
        print(nonce)
        return 0

    r.fail("wrong response to fresh challenge %s..: artifact returned %r, "
           "expected %r -- a hardcoded or memorised answer cannot match a "
           "nonce it has not seen"
           % (nonce[:8], response[:64], expected[:64]))
    return r.emit(a.as_json)


if __name__ == "__main__":
    main_guard(main)
