"""Offline tests for the Robin layer (ADR 0002): guard, BTL, consensus, cascade guard, ledger, and the wired graph."""

import json
import random
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from knowledge_agent import app as web
from knowledge_agent import jev, robin
from knowledge_agent.sources import Evidence

import test_jev
from test_jev import Script, TestJevRun

EV = {
    "E1": Evidence("PubMed", "Trial One", "Survival was 63.6% with HR 0.24.", doi="10.1/one", key="E1"),
    "E2": Evidence("arXiv preprint", "Preprint Two", "AUC reached 0.89.", arxiv_id="2501.1", key="E2"),
    "E3": Evidence("NotebookLM answer (secondary)", "Notebook answer", "A summary says 63.6%.", key="E3"),
    "E4": Evidence("PubMed", "Off topic", "Remission 42.0%.", pmid="9", key="E4"),
}
USABLE = {"E1", "E2", "E3"}
VERIFIED = {"E1", "E2"}


class TestCrowFalcon(unittest.TestCase):

    def test_library_verified_means_identifier_not_recall(self):
        lib = {r["citation_id"]: r for r in robin.citation_library(EV, {"E4"})}
        self.assertTrue(lib["E1"]["verified"] and lib["E2"]["verified"])
        self.assertFalse(lib["E3"]["verified"])  # a notebook answer has no registry identifier
        self.assertFalse(lib["E4"]["on_topic"])

    def test_guard_rejects_each_failure_and_measures_the_rate(self):
        raw = [
            {"claim": "Survival was 63.6% [E1]", "evidence_ids": ["E1"]},                 # accepted (cite stripped)
            {"claim": "No ids at all", "evidence_ids": []},                                 # no evidence_ids
            {"claim": "Cites off-topic", "evidence_ids": ["E4"]},                           # no on-topic entry
            {"claim": "Only the notebook says 63.6%", "evidence_ids": ["E3"]},              # no verified entry
            {"claim": "AUC reached 0.97", "evidence_ids": ["E2"]},                          # figure not in source
            {"claim": "survival was 63.6%", "evidence_ids": ["E1"]},                        # duplicate
            "not a dict",
        ]
        acc, rej, stats = robin.guard_claims(raw, EV, USABLE, VERIFIED)
        self.assertEqual([a["claim"] for a in acc], ["Survival was 63.6%"])
        reasons = " | ".join(r["reason"] for r in rej)
        for fragment in ("no evidence_ids", "no on-topic", "identifier-verified", "figure", "duplicate", "not a claim"):
            self.assertIn(fragment, reasons)
        self.assertEqual(stats, {"total_claims": 7, "unverified_claims": 6, "hallucination_rate": round(6 / 7, 4)})

    def test_empty_falcon_output_has_zero_rate_not_a_pass(self):
        acc, rej, stats = robin.guard_claims(None, EV, USABLE, VERIFIED)
        self.assertEqual((acc, stats["total_claims"]), ([], 0))
        self.assertEqual(robin.robin_status(0, 0.0), "DATA_UNAVAILABLE")


class TestTournament(unittest.TestCase):

    def test_btl_orders_a_transitive_tournament(self):
        # 0 beats everyone, 1 beats 2 and 3, 2 beats 3
        results = [(0, 1, 1.0), (0, 2, 1.0), (0, 3, 1.0), (1, 2, 1.0), (1, 3, 1.0), (2, 3, 1.0)]
        scores, rates, games = robin.fit_btl(4, results)
        self.assertEqual(sorted(range(4), key=lambda i: -scores[i]), [0, 1, 2, 3])
        self.assertEqual(rates, [1.0, 0.667, 0.333, 0.0])
        self.assertTrue(all(abs(s) < 50 for s in scores))  # the prior keeps an unbeaten candidate finite

    def test_ties_count_half_and_symmetric_play_is_level(self):
        scores, rates, _ = robin.fit_btl(2, [(0, 1, 0.5), (1, 0, 0.5)])
        self.assertAlmostEqual(scores[0], scores[1], places=6)
        self.assertEqual(rates, [0.5, 0.5])

    def test_btl_recovers_true_strengths_from_noisy_matches(self):
        rng = random.Random(7)
        true = [3.0, 2.0, 1.0, 0.5, 0.25]
        results = []
        for _ in range(400):
            i, j = rng.sample(range(5), 2)
            results.append((i, j, 1.0 if rng.random() < true[i] / (true[i] + true[j]) else 0.0))
        scores, _, _ = robin.fit_btl(5, results)
        self.assertEqual(sorted(range(5), key=lambda i: -scores[i]), [0, 1, 2, 3, 4])

    def test_every_candidate_plays_at_least_four_games(self):
        for n in (3, 4, 5, 6, 7, 10):
            pairs = robin.schedule_pairings(n, 4, seed=42)
            counts = [sum(1 for p in pairs if i in p) for i in range(n)]
            self.assertGreaterEqual(min(counts), 4, (n, counts))
            self.assertTrue(all(a != b for a, b in pairs))
        self.assertEqual(robin.schedule_pairings(6, 4, 1), robin.schedule_pairings(6, 4, 1))  # seeded, reproducible

    def test_counterbalance_turns_order_flips_into_ties(self):
        games = [(0, 0, 1, 1.0), (0, 1, 0, 0.0),   # pairing 0: candidate 0 wins in both orders
                 (1, 1, 2, 1.0), (1, 2, 1, 1.0),   # pairing 1: whoever is shown first wins -> tie
                 (2, 0, 2, 1.0)]                   # pairing 2: one order survived
        self.assertEqual(robin.counterbalance(games), [(0, 1, 1.0), (1, 2, 0.5), (0, 2, 1.0)])
        self.assertEqual(robin.position_a_share(["A", "A", "B", "TIE"]), 0.667)
        self.assertIsNone(robin.position_a_share(["TIE"]))

    def test_judge_template_is_lint_clean_and_lint_catches_absolute_scales(self):
        blank = {"statement": "", "rationale": "", "test": "", "evidence_ids": []}
        self.assertEqual(robin.lint_judge(robin.JUDGE_SYSTEM + robin.judge_prompt("", blank, blank, "")), [])
        for bad in ("Score each from 1-10", "rate the hypothesis", "give a rating out of 10", "1–10 scale"):
            self.assertTrue(robin.lint_judge(bad), bad)
        for ok in ("generate", "accurate", "separately", "moderate"):
            self.assertEqual(robin.lint_judge(ok), [], ok)

    def test_hypotheses_are_validated_by_code(self):
        raw = [{"statement": "Memory drives gains", "evidence_ids": ["E1"], "rationale": "r", "test": "t"},
               {"statement": "", "evidence_ids": ["E1"]},
               {"statement": "Off topic only", "evidence_ids": ["E4"]},
               {"statement": "Gains are 99.9%", "evidence_ids": ["E1"]},
               {"statement": "memory drives gains", "evidence_ids": ["E2"]}]
        kept, rejected = robin.validate_hypotheses(raw, EV, USABLE)
        self.assertEqual([(k["id"], k["statement"]) for k in kept], [("H1", "Memory drives gains")])
        self.assertEqual(len(rejected), 4)


class TestConsensus(unittest.TestCase):

    def claim(self, text, ids):
        return {"claim": text, "evidence_ids": ids, "claim_type": "literature"}

    def test_threshold_one_is_refused(self):
        with self.assertRaises(ValueError):
            robin.consensus([[]], 1.0)
        with self.assertRaises(ValueError):
            robin.check_threshold(0.3)

    def test_findings_need_agreement_and_shared_evidence(self):
        t1 = [self.claim("Survival improved to 63.6% in the trial", ["E1"]), self.claim("AUC reached 0.89 for detection", ["E2"])]
        t2 = [self.claim("In the trial survival improved to 63.6%", ["E1"]), self.claim("Lone claim about costs", ["E2"])]
        t3 = [self.claim("Survival improved to 63.6% in the trial", ["E9"])]  # same words, different evidence: not the same finding
        out = robin.consensus([t1, t2, t3], 0.5)
        included = {f["claim"]: f["agreement"] for f in out["included"]}
        self.assertEqual(list(included.values()), [0.667])
        self.assertTrue(any("63.6" in c for c in included))
        self.assertEqual(len(out["excluded"]), 3)
        self.assertEqual(len(out["matrix"][0]["votes"]), 3)


class TestCascadeAndLedger(unittest.TestCase):

    def test_cascade_needs_three_identical_errors(self):
        self.assertFalse(robin.is_cascade(["invalid JSON: line 1", "invalid JSON: line 2"]))
        self.assertTrue(robin.is_cascade(["x", "invalid JSON: col 3", "invalid JSON: col 9", "invalid JSON: col 12"]))
        self.assertFalse(robin.is_cascade(["invalid JSON: col 3", "missing key 'winner'", "invalid JSON: col 9"]))
        self.assertIn("schema", robin.diagnose("missing key 'winner'").lower())

    def test_ledger_forbids_observed_and_unknown_keys(self):
        rows = robin.ledger_rows([{"claim": "c", "evidence_ids": ["E1"]}], [{"claim": "u", "evidence_ids": [], "reason": "no ids"}],
                                 [{"id": "H1", "statement": "h", "evidence_ids": ["E1"], "rank": 1, "btl_score": 0.4}])
        self.assertEqual([r["claim_type"] for r in rows], ["literature", "unsupported", "hypothesis"])
        self.assertEqual(robin.ledger_problems(rows, {"E1"}), [])
        self.assertTrue(robin.ledger_csv(rows).startswith("claim_id,claim_type,claim,evidence_ids,artifact_path"))
        rows[0]["claim_type"] = "observed"
        self.assertTrue(any("not allowed" in p for p in robin.ledger_problems(rows, {"E1"})))
        rows[0]["claim_type"] = "literature"
        self.assertTrue(robin.ledger_problems(rows, set()))

    def test_status_follows_the_measured_rate(self):
        self.assertEqual(robin.robin_status(5, 0.0), "PROPOSAL_ONLY")
        self.assertEqual(robin.robin_status(5, 0.05), "FAILED_REPRODUCIBILITY")


class TestRobinGraph(unittest.TestCase):

    def setUp(self):
        Script.falcon, Script.judge = test_jev.FALCON, staticmethod(test_jev.judge)

    def tearDown(self):
        self.setUp()

    def graph(self, **kw):
        return TestJevRun.run_graph(TestJevRun(), **kw)

    def test_robin_nodes_artifacts_and_ranking(self):
        run, report, tmp = self.graph(loops=1)
        self.assertEqual(report["status"], "COMPLETED", report["robin"]["qc"])
        statuses = {n["id"]: n["status"] for n in report["graph"]["nodes"]}
        for node in ("falcon1", "hypotheses1", "tournament1", "robinqc"):
            self.assertEqual(statuses.get(node), "passed", (node, statuses))
        for name in ("citation_library.json", "evidence_report.json", "hallucination_rate_log.jsonl", "seed_ideas.json",
                     "ranked_candidates.json", "tournament.json", "claim_ledger.csv", "robin_qc.md"):
            self.assertTrue((run.dir / "robin" / name).exists(), name)
        rb = report["robin"]
        self.assertEqual(rb["status"], "PROPOSAL_ONLY")
        self.assertEqual(rb["final_rate"], 0.0)
        self.assertEqual([h["statement"] for h in rb["ranked"]][0], "Alpha memory drives gains")  # judge prefers alphabetical
        self.assertEqual(rb["tournament"]["pairings"], 8)  # 4 candidates x 4 pairings / 2
        self.assertEqual(rb["tournament"]["matches"], 16)  # each pairing judged in both orders
        self.assertEqual(rb["tournament"]["position_a_share"], 0.5)  # an order-consistent judge
        self.assertTrue(any(q["verdict"] == "N/A" and "Finch" in q["item"] for q in rb["qc"]))
        # The judge is the auditor model; the writer gets findings and hypotheses; the auditor sees them too.
        judge_models = {m for m, head in Script.models if head.startswith("Topic: Agentic autoresearch\n\nSUPPORTING")}
        self.assertEqual(judge_models, {"claude:claude-opus-5-5"})
        self.assertTrue(any("Pre-checked claims" in p and "publication-style" in p for p in Script.prompts))
        self.assertTrue(any("RANKED HYPOTHESES" in p and "PAPER UNDER AUDIT" in p for p in Script.prompts))
        topic_pages = list((Path(report["kb"]["root"]) / "主題").glob("*.md"))
        self.assertTrue(any("排名假說" in p.read_text(encoding="utf-8") for p in topic_pages))

    def test_robin_off_reproduces_the_plain_graph(self):
        run, report, _ = self.graph(loops=1, robin=False)
        self.assertEqual(report["status"], "COMPLETED")
        ids = {n["id"] for n in report["graph"]["nodes"]}
        self.assertFalse(ids & {"falcon1", "hypotheses1", "tournament1", "robinqc"})
        self.assertFalse((run.dir / "robin").exists())
        self.assertFalse(any("CITATION LIBRARY" in p or "Pre-checked claims" in p for p in Script.prompts))

    def test_hallucinating_falcon_is_respawned_once_then_fails(self):
        Script.falcon = json.dumps({"claims": [{"claim": "Survival was 63.6%", "evidence_ids": ["E1"]},
                                               {"claim": "Invented accuracy of 97.5%", "evidence_ids": ["E1"]}]})
        run, report, _ = self.graph(loops=1)
        falcon_prompts = [p for p in Script.prompts if "CITATION LIBRARY" in p]
        self.assertEqual(len(falcon_prompts), 2)
        self.assertIn("code guard rejected", falcon_prompts[1])
        self.assertEqual(report["robin"]["status"], "FAILED_REPRODUCIBILITY")
        self.assertEqual(report["status"], "NEEDS_REVIEW")
        log = (run.dir / "robin" / "hallucination_rate_log.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual([json.loads(l)["attempt"] for l in log], [1, 2])
        self.assertTrue(all("97.5" not in f["claim"] for f in report["robin"]["findings"]))  # rejected claims never reach the writer

    def test_position_biased_judge_cannot_move_the_ranking(self):
        # Regression for live run 20261109-084205-30511d (judge chose "A" in 7 of 8 matches).
        Script.judge = staticmethod(lambda prompt: json.dumps({"winner": "A", "reason": "first"}))
        _, report, _ = self.graph(loops=1)
        tour, ranked = report["robin"]["tournament"], report["robin"]["ranked"]
        self.assertEqual(tour["position_a_share"], 1.0)  # the bias is measured and reported
        self.assertEqual(len({h["btl_score"] for h in ranked}), 1, ranked)  # and it gives no candidate an edge
        self.assertTrue(all(h["win_rate"] == 0.5 for h in ranked))

    def test_broken_judge_cascades_and_is_reported(self):
        Script.judge = staticmethod(lambda prompt: "I prefer the first one.")
        run, report, _ = self.graph(loops=1)
        rb = report["robin"]
        self.assertFalse(rb["tournament"]["ran"])
        self.assertTrue(rb["cascades"] and all(c["diagnosis"] for c in rb["cascades"]))
        self.assertTrue((run.dir / "robin" / "react_cascade_log.jsonl").exists())
        self.assertEqual(report["status"], "NEEDS_REVIEW")
        judge_calls = [p for p in Script.prompts if "could not be used" in p]
        self.assertTrue(judge_calls)  # errors were fed back before the guard stopped

    def test_parallel_trajectories_write_consensus(self):
        run, report, _ = self.graph(loops=1, trajectories=3, consensus=0.5)
        self.assertEqual(len([p for p in Script.prompts if "CITATION LIBRARY" in p]), 3)
        cons = json.loads((run.dir / "robin" / "consensus_findings.json").read_text(encoding="utf-8"))
        self.assertEqual(cons["threshold"], 0.5)
        self.assertEqual(len(cons["included"]), 2)
        self.assertTrue(all(f["agreement"] == 1.0 for f in cons["included"]))
        self.assertEqual(report["status"], "COMPLETED", report["robin"]["qc"])


class TestLiveRunRegressions(unittest.TestCase):
    """Turned into checks after reading run 20261109-091620-b8f1c4 by hand."""

    E2 = {"E2": Evidence("arXiv preprint", "RSI of research agents", "On a held-out family the rate falls from 55% to 32% during the run, "
                         "7 percentage points below the human-engineered agent.", arxiv_id="2609.26457", key="E2")}

    def test_multi_sentence_claim_with_faithful_figures_is_accepted(self):
        claim = ("On a separate held-out task family, the reward hacking rate fell from 55% to 32% during the run, "
                 "7 percentage points below the human-engineered agent. The loop never explicitly optimized for this property.")
        acc, rej, stats = robin.guard_claims([{"claim": claim, "evidence_ids": ["E2"]}], self.E2, {"E2"}, {"E2"})
        self.assertEqual((len(acc), stats["hallucination_rate"]), (1, 0.0), rej)

    def test_multi_sentence_claim_with_an_invented_figure_is_still_rejected(self):
        claim = "The rate fell from 55% to 32%. A later replication found 12% drift."
        acc, rej, _ = robin.guard_claims([{"claim": claim, "evidence_ids": ["E2"]}], self.E2, {"E2"}, {"E2"})
        self.assertEqual((acc, rej[0]["reason"]), ([], "a figure is not in the cited sources"))

    def test_internal_workflow_labels_fail_clean_text_but_topic_words_pass(self):
        from knowledge_agent.checks import check_clean
        for leak in ("We built Results on Falcon-verified findings.", "VERIFIED FINDINGS: x", "The Crow swarm screened sources."):
            self.assertFalse(check_clean(leak).passed, leak)
        for ok in ("Robin ranks drugs with a pairwise tournament.", "Falcon 180B was evaluated.", "Verified findings were rare."):
            self.assertTrue(check_clean(ok).passed, ok)

    def test_writer_brief_carries_no_internal_label(self):
        from knowledge_agent.checks import INTERNAL_LABELS
        run = jev.JevRun.__new__(jev.JevRun)
        run.rb = {"enabled": True, "findings": [{"claim": "c", "evidence_ids": ["E1"]}],
                  "ranked": [{"rank": 1, "statement": "h", "evidence_ids": ["E1"], "test": "t"}]}
        brief = run._robin_brief()
        self.assertIn("Hypotheses for future work", brief)
        self.assertIsNone(INTERNAL_LABELS.search(brief.replace("never mention", "")))


class TestArxivBackoff(unittest.TestCase):
    """Regression for run 20261109-090308-42fd8f: arXiv HTTP 429 left Falcon without verified sources."""

    ATOM = (b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/2501.00001v1</id>'
            b'<title>Agent paper</title><summary>Text.</summary><published>2025-01-01</published>'
            b'<author><name>A B</name></author></entry></feed>')

    def fake(self, codes):
        from knowledge_agent import sources
        calls = []

        class Resp:
            def __init__(self, code):
                self.status_code, self.content, self.headers = code, TestArxivBackoff.ATOM, {"Retry-After": "7"} if code == 429 else {}
            def raise_for_status(self):
                pass

        def get(url, params=None, headers=None, timeout=None):
            calls.append(url)
            return Resp(codes.pop(0) if codes else 200)
        return sources, calls, get

    def test_429_is_retried_with_backoff_and_retry_after(self):
        sources, calls, get = self.fake([429, 429])
        sleeps = []
        with mock.patch.object(sources.requests, "get", get), mock.patch.object(sources.time, "sleep", sleeps.append):
            items, status = sources.search_arxiv(["autoresearch agents"], 1)
        self.assertEqual(status.state, "LIVE")
        self.assertEqual(len(items), 1)
        self.assertEqual(sleeps, [7.0, 7.0])  # Retry-After honoured
        self.assertEqual(len(calls), 3)

    def test_queries_are_spaced_and_persistent_429_is_unavailable(self):
        sources, calls, get = self.fake([200, 429, 429, 429, 429])
        sleeps = []
        with mock.patch.object(sources.requests, "get", get), mock.patch.object(sources.time, "sleep", sleeps.append):
            items, status = sources.search_arxiv(["one", "two"], 1)
        self.assertEqual(sleeps[0], sources.ARXIV_PAUSE)  # pause before the second query
        self.assertEqual(status.state, "LIVE")  # the first query's item still counts
        sources2, _, get2 = self.fake([429] * 4)
        with mock.patch.object(sources2.requests, "get", get2), mock.patch.object(sources2.time, "sleep", lambda s: None):
            items, status = sources2.search_arxiv(["one"], 1)
        self.assertEqual((items, status.state), ([], "UNAVAILABLE"))
        self.assertIn("429", status.detail)


class TestRobinServer(unittest.TestCase):

    def setUp(self):
        self.client = web.create_app().test_client()
        self.h = {"Host": "127.0.0.1:8090", "Origin": "http://127.0.0.1:8090"}

    def post(self, **extra):
        return self.client.post("/api/research", json={"topic": "A topic", "loops": 1, "budget_usd": 1, **extra}, headers=self.h)

    def test_out_of_range_robin_settings_are_refused(self):
        for bad in ({"consensus": 1.0}, {"trajectories": 2}, {"candidates": 2}, {"robin": "yes"}, {"candidates": "many"}):
            r = self.post(**bad)
            self.assertEqual(r.status_code, 400, bad)

    def test_settings_reach_the_request(self):
        parsed, problem = web._parse_request({"topic": "A topic", "loops": 1, "budget_usd": 1, "robin": False, "candidates": 5, "trajectories": 3, "consensus": 0.75})
        self.assertIsNone(problem)
        self.assertEqual((parsed.robin, parsed.candidates, parsed.trajectories, parsed.consensus), (False, 5, 3, 0.75))

    def test_config_exposes_robin_defaults(self):
        data = self.client.get("/api/config", headers=self.h).get_json()
        self.assertEqual(data["robin"]["trajectory_choices"], [1, 3, 5, 8])
        self.assertIn("candidates", data["robin"])


if __name__ == "__main__":
    unittest.main()
