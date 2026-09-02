#!/usr/bin/env python3
"""Test suite for the profile verifiers.

Each verifier is tested twice: once on data that should fail (and the specific
diagnostic must appear in the output) and once on data that should pass. A
verifier that cannot be shown to catch its own failure mode is decoration.

Run:  python test_verifiers.py
Exit: 0 all passed, 1 otherwise.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable
RESULTS = []


def run(script, *args):
    proc = subprocess.run([PY, str(HERE / script)] + [str(x) for x in args],
                          capture_output=True, text=True, timeout=120)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def expect(label, cond, detail=""):
    RESULTS.append((label, bool(cond), str(detail)[:300]))


def case(label, script, args, want_fail, must_contain=None):
    code, out = run(script, *args)
    if want_fail:
        expect("%s -> fails" % label, code == 1,
               "exit=%s out=%s" % (code, out[:200]))
        if must_contain:
            expect("%s -> diagnostic names the problem" % label,
                   must_contain.lower() in out.lower(),
                   "wanted %r in: %s" % (must_contain, out[:300]))
    else:
        expect("%s -> passes" % label, code == 0,
               "exit=%s out=%s" % (code, out[:300]))
    return out


def main():
    tmp = Path(tempfile.mkdtemp(prefix="verifier_tests_"))
    try:
        # ---------------- budget alignment ----------------------------
        (tmp / "proposal_bad.md").write_text(
            "# 一、研究背景\n\n背景說明。\n\n"
            "# 三、研究方法\n\n本研究使用 EEG-64 導聯系統記錄腦波。\n",
            encoding="utf-8")
        (tmp / "budget_bad.json").write_text(json.dumps({
            "equipment": [{"name": "EEG-64", "amount": 500000},
                          {"name": "眼動儀", "amount": 300000}],
            "personnel": [{"name": "研究助理", "amount": 200000}],
            "total": 900000}, ensure_ascii=False), encoding="utf-8")
        out = case("budget: total mismatch + unjustified equipment",
                   "check_budget_alignment.py",
                   ["--doc", tmp / "proposal_bad.md",
                    "--budget", tmp / "budget_bad.json"],
                   want_fail=True, must_contain="眼動儀")
        expect("budget: arithmetic error also reported",
               "total 900000.0 != sum" in out or "!= sum of categories" in out,
               out[:250])

        (tmp / "proposal_ok.md").write_text(
            "# 一、研究背景\n\n背景說明。\n\n"
            "# 三、研究方法\n\n本研究使用 EEG-64 導聯系統記錄腦波，"
            "並以眼動儀同步記錄凝視位置。研究助理負責資料整理。\n",
            encoding="utf-8")
        (tmp / "budget_ok.json").write_text(json.dumps({
            "equipment": [{"name": "EEG-64", "amount": 500000},
                          {"name": "眼動儀", "amount": 300000}],
            "personnel": [{"name": "研究助理", "amount": 200000}],
            "total": 1000000}, ensure_ascii=False), encoding="utf-8")
        case("budget: clean", "check_budget_alignment.py",
             ["--doc", tmp / "proposal_ok.md",
              "--budget", tmp / "budget_ok.json"], want_fail=False)

        # ---------------- coherence -----------------------------------
        dup = ("The harness mediates how the model perceives and acts on its "
               "environment, exposing the action and observation interfaces "
               "over which tool augmented reasoning unfolds in practice today. "
               "This matters a great deal for long horizon tasks in general.")
        (tmp / "paper_bad.md").write_text(
            "# Introduction\n\n%s\n\n# Methods\n\n%s\n\n# Results\n\n"
            "We measured RSI across conditions and found an effect.\n\n"
            "# Discussion\n" % (dup, dup), encoding="utf-8")
        case("coherence: duplicate paragraph + empty section + undefined abbrev",
             "check_coherence.py", ["--doc", tmp / "paper_bad.md"],
             want_fail=True, must_contain="near-duplicate")
        _, out = run("check_coherence.py", "--doc", tmp / "paper_bad.md")
        expect("coherence: empty section named", "Discussion" in out, out[:250])
        expect("coherence: undefined abbreviation named", "RSI" in out, out[:250])

        (tmp / "paper_ok.md").write_text(
            "# Introduction\n\nRecursive self improvement (RSI) is the topic "
            "of this paper and we introduce it here with enough length that "
            "the paragraph passes the minimum length filter comfortably.\n\n"
            "# Methods\n\nWe evaluated three harnesses across two benchmarks "
            "using a fixed model and a fixed evaluator, holding every other "
            "variable constant throughout the whole experiment.\n\n"
            "# Results\n\nRSI improved pass rates in every condition we "
            "tested, with the largest gain on the held out split of the "
            "second benchmark by a comfortable margin.\n",
            encoding="utf-8")
        case("coherence: clean", "check_coherence.py",
             ["--doc", tmp / "paper_ok.md"], want_fail=False)

        # ---------------- citations -----------------------------------
        vault = tmp / "vault"
        vault.mkdir()
        (vault / "lin2026_ahe.json").write_text(json.dumps({
            "id": "lin2026_ahe", "citation": "Lin et al., 2026, AHE",
            "question": "q", "method": "m", "findings": ["f"]},
            ensure_ascii=False), encoding="utf-8")
        (tmp / "review_bad.md").write_text(
            "Harness work [[lin2026_ahe]] is established, and so is "
            "[[zhang2026_ghost]] which we never read. [citation needed]\n",
            encoding="utf-8")
        case("citations: unresolved marker + placeholder",
             "check_citations_resolve.py",
             ["--doc", tmp / "review_bad.md", "--vault", vault],
             want_fail=True, must_contain="zhang2026_ghost")
        _, out = run("check_citations_resolve.py", "--doc", tmp / "review_bad.md",
                     "--vault", vault)
        expect("citations: placeholder flagged",
               "citation needed" in out.lower(), out[:250])

        (tmp / "review_ok.md").write_text(
            "Harness work [[lin2026_ahe]] is established.\n", encoding="utf-8")
        case("citations: clean (vault backend)", "check_citations_resolve.py",
             ["--doc", tmp / "review_ok.md", "--vault", vault], want_fail=False)

        (tmp / "numeric_ok.md").write_text(
            "Claim one [1] and claim two [2].\n\n"
            "# References\n\n[1] Lin et al. 2026.\n[2] Zhang et al. 2026.\n",
            encoding="utf-8")
        out = case("citations: numeric via in-document reference list",
                   "check_citations_resolve.py",
                   ["--doc", tmp / "numeric_ok.md"], want_fail=False)
        expect("citations: weak backend is labelled as weak",
               "weak" in out.lower(), out[:250])

        (tmp / "numeric_bad.md").write_text(
            "Claim one [1] and claim three [3].\n\n"
            "# References\n\n[1] Lin et al. 2026.\n[2] Zhang et al. 2026.\n",
            encoding="utf-8")
        case("citations: dangling marker + uncited reference",
             "check_citations_resolve.py", ["--doc", tmp / "numeric_bad.md"],
             want_fail=True, must_contain="do not resolve")

        # ---------------- coverage ------------------------------------
        srcs = tmp / "refs"
        srcs.mkdir()
        for n in ("Lin_2026_AHE.pdf", "Zhang_2026_Self-Harness.pdf",
                  "Ye_2026_MCE.pdf"):
            (srcs / n).write_bytes(b"%PDF-1.4 stub")
        cvault = tmp / "cvault"
        cvault.mkdir()
        (cvault / "lin_2026_ahe.json").write_text(json.dumps({
            "id": "lin_2026_ahe", "citation": "Lin 2026",
            "question": "q" * 80, "method": "m" * 80,
            "findings": ["f" * 200]}), encoding="utf-8")
        case("coverage: missing entries for 2 of 3 sources",
             "check_coverage.py",
             ["--sources", srcs, "--vault", cvault],
             want_fail=True, must_contain="Zhang_2026_Self-Harness.pdf")

        for stem, cite in (("zhang_2026_self-harness", "Zhang 2026"),
                           ("ye_2026_mce", "Ye 2026")):
            (cvault / ("%s.json" % stem)).write_text(json.dumps({
                "id": stem, "citation": cite, "question": "q" * 80,
                "method": "m" * 80, "findings": ["f" * 200]}), encoding="utf-8")
        case("coverage: complete", "check_coverage.py",
             ["--sources", srcs, "--vault", cvault], want_fail=False)

        # an entry whose required fields are blank must fail even though the
        # source it covers is present
        (srcs / "Lee_2026_Meta-Harness.pdf").write_bytes(b"%PDF-1.4 stub")
        (cvault / "lee_2026_meta-harness.json").write_text(json.dumps({
            "id": "lee_2026_meta-harness", "citation": "", "question": "q",
            "method": "m", "findings": []}), encoding="utf-8")
        case("coverage: empty required field caught", "check_coverage.py",
             ["--sources", srcs, "--vault", cvault],
             want_fail=True, must_contain="required field")
        (cvault / "lee_2026_meta-harness.json").unlink()
        (srcs / "Lee_2026_Meta-Harness.pdf").unlink()

        # two entries claiming the same id would silently shadow one another
        (cvault / "shadow.json").write_text(json.dumps({
            "id": "ye_2026_mce", "citation": "dup", "question": "q" * 80,
            "method": "m" * 80, "findings": ["f" * 200]}), encoding="utf-8")
        case("coverage: duplicate vault id caught", "check_coverage.py",
             ["--sources", srcs, "--vault", cvault],
             want_fail=True, must_contain="duplicate vault id")
        (cvault / "shadow.json").unlink()

        # ---------------- glossary ------------------------------------
        (tmp / "glossary.json").write_text(json.dumps({"terms": [
            {"canonical": "心率變異性 (HRV)", "variants": ["心率變異度",
                                                          "心跳變異性"]},
            {"canonical": "Stroop task", "variants": ["Stroop test"]}]},
            ensure_ascii=False), encoding="utf-8")
        (tmp / "terms_bad.md").write_text(
            "本研究測量心率變異性 (HRV)。第二節改稱心率變異度，"
            "第三節又寫成心跳變異性。We used the Stroop test.\n",
            encoding="utf-8")
        case("glossary: variant terminology", "check_glossary.py",
             ["--doc", tmp / "terms_bad.md", "--glossary", tmp / "glossary.json"],
             want_fail=True, must_contain="心率變異度")
        (tmp / "terms_ok.md").write_text(
            "本研究測量心率變異性 (HRV)，全文一致使用此詞。"
            "We used the Stroop task throughout.\n", encoding="utf-8")
        case("glossary: consistent", "check_glossary.py",
             ["--doc", tmp / "terms_ok.md", "--glossary", tmp / "glossary.json"],
             want_fail=False)

        # ---------------- reproducibility -----------------------------
        (tmp / "res_bad.json").write_text(json.dumps({
            "metric": 0.91, "n_subjects": 20,
            "dev_subjects": ["s1", "s2", "s3"],
            "holdout_subjects": ["s3", "s4"]}), encoding="utf-8")
        case("reproducible: missing seed + subject leakage",
             "check_reproducible.py", ["--results", tmp / "res_bad.json"],
             want_fail=True, must_contain="leakage")
        _, out = run("check_reproducible.py", "--results", tmp / "res_bad.json")
        expect("reproducible: missing provenance named",
               "seed" in out and "missing provenance" in out, out[:250])

        good = {"seed": 42, "n_subjects": 4, "metric": 0.83,
                "dataset_version": "physionet-fantasia-1.0.0",
                "code_version": "abc1234", "ci_low": 0.78, "ci_high": 0.88,
                "dev_subjects": ["s1", "s2"], "holdout_subjects": ["s3", "s4"]}
        (tmp / "res_ok.json").write_text(json.dumps(good), encoding="utf-8")
        case("reproducible: clean", "check_reproducible.py",
             ["--results", tmp / "res_ok.json"], want_fail=False)

        drift = dict(good, metric=0.87)
        (tmp / "res_drift.json").write_text(json.dumps(drift), encoding="utf-8")
        case("reproducible: same seed, different numbers",
             "check_reproducible.py",
             ["--results", tmp / "res_drift.json",
              "--baseline", tmp / "res_ok.json"],
             want_fail=True, must_contain="not deterministic")

        (tmp / "prereg.json").write_text(
            json.dumps({"thresholds": {"rt_cutoff": 200}}), encoding="utf-8")
        (tmp / "res_thresh.json").write_text(
            json.dumps(dict(good, thresholds={"rt_cutoff": 350})),
            encoding="utf-8")
        case("reproducible: threshold changed after the fact",
             "check_reproducible.py",
             ["--results", tmp / "res_thresh.json",
              "--thresholds", tmp / "prereg.json"],
             want_fail=True, must_contain="pre-registered")

        # ---------------- trial data ----------------------------------
        head = "subject_id,trial_index,condition,stimulus,response,rt_ms,timed_out,is_practice\n"
        bad_rows = [
            "P01,1,congruent,red,red,,false,false",      # null rt, not timeout
            "P01,2,incongruent,blue,blue,0,false,false",  # zero rt
            "P01,4,congruent,green,green,540,false,false",  # gap at 3
            "P01,4,congruent,green,green,551,false,false",  # duplicate index
        ]
        (tmp / "trials_bad.csv").write_text(head + "\n".join(bad_rows) + "\n",
                                            encoding="utf-8")
        out = case("trials: null rt, gap, duplicate", "check_no_null_rt.py",
                   ["--csv", tmp / "trials_bad.csv"],
                   want_fail=True, must_contain="null/empty")
        expect("trials: gap reported", "missing trial" in out, out[:250])
        expect("trials: duplicate reported", "duplicate" in out, out[:250])

        ok_rows = ["P01,%d,%s,stim,resp,%d,false,false"
                   % (i, "congruent" if i % 2 else "incongruent", 430 + i * 7)
                   for i in range(1, 25)]
        ok_rows.append("P01,25,congruent,stim,,,true,true".replace(
            ",true,true", ",true,false"))
        (tmp / "trials_ok.csv").write_text(head + "\n".join(ok_rows) + "\n",
                                           encoding="utf-8")
        case("trials: clean", "check_no_null_rt.py",
             ["--csv", tmp / "trials_ok.csv"], want_fail=False)
        case("trials: expected count enforced", "check_no_null_rt.py",
             ["--csv", tmp / "trials_ok.csv", "--expected-trials", 96],
             want_fail=True, must_contain="trial(s) lost")

        # ---------------- timing distribution -------------------------
        quantised = ["P01,%d,%s,stim,resp,%d,false,false"
                     % (i, "congruent" if i % 2 else "incongruent",
                        round((420 + i * 11) / 15.0) * 15)
                     for i in range(1, 31)]
        (tmp / "timing_bad.csv").write_text(head + "\n".join(quantised) + "\n",
                                            encoding="utf-8")
        case("timing: low-resolution clock detected",
             "check_timing_distribution.py", ["--csv", tmp / "timing_bad.csv"],
             want_fail=True, must_contain="performance.now")

        const = ["P01,%d,congruent,stim,resp,500,false,false" % i
                 for i in range(1, 20)]
        (tmp / "timing_const.csv").write_text(head + "\n".join(const) + "\n",
                                              encoding="utf-8")
        case("timing: constant value detected", "check_timing_distribution.py",
             ["--csv", tmp / "timing_const.csv"],
             want_fail=True, must_contain="identical")

        varied = ["P01,%d,%s,stim,resp,%d,false,false"
                  % (i, "congruent" if i % 2 else "incongruent",
                     413 + (i * 37) % 291)
                  for i in range(1, 41)]
        (tmp / "timing_ok.csv").write_text(head + "\n".join(varied) + "\n",
                                           encoding="utf-8")
        case("timing: clean", "check_timing_distribution.py",
             ["--csv", tmp / "timing_ok.csv",
              "--condition-col", "condition"], want_fail=False)

        # ---------------- cross-cutting -------------------------------
        code, out = run("check_coherence.py", "--doc", tmp / "nope.md")
        expect("missing input fails, never passes silently",
               code == 1 and "not found" in out, "exit=%s %s" % (code, out[:150]))

        for script in sorted(HERE.glob("check_*.py")):
            code, out = run(script.name, "--help")
            expect("%s has --help" % script.name, code == 0, out[:120])
            code, out = run(script.name)
            expect("%s fails without required args" % script.name,
                   code != 0, "exit=%s" % code)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [(n, d) for n, ok, d in RESULTS if not ok]
    print("=" * 68)
    for name, ok, detail in RESULTS:
        if not ok:
            print("FAIL  %s\n      %s" % (name, detail))
    print("=" * 68)
    print("verifier tests: %d/%d passed" % (len(RESULTS) - len(failed),
                                            len(RESULTS)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
