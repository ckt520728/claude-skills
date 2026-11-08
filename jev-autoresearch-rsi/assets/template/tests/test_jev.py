"""Offline tests for the Jev graph: planner -> notes swarm -> draft -> audit -> replan, deliverables and KB merge."""

import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from knowledge_agent import app as web
from knowledge_agent import checks, config, jev, llm, pipeline
from knowledge_agent.sources import Evidence, SourceStatus

HEADINGS = "\n".join(f"## {h}\nSurvival was 63.6% in one trial [E1]. Another study reported an AUC of 0.89 [E2]." for h in ("Abstract", "Introduction", "Methods", "Results", "Discussion", "Limitations", "Conclusion"))
GOOD_PAPER = "# Agentic research review\n" + HEADINGS + "\n" + "word " * 950
SECTIONS = ["hook"] * 2 + ["concepts"] * 5 + ["evidence"] * 5 + ["misconceptions"] + ["conclusion"] * 2
DECK = json.dumps({"slides": [{"section": s, "title": f"Slide {chr(64 + i)}", "bullets": ["Survival was 63.6% [E1]", "AUC reached 0.89 [E2]"], "notes": "n",
                               "visual_prompt": "clean clinical chart", "layout": "left text, right chart"} for i, s in enumerate(SECTIONS, 1)]})
BLOG = "# 研究代理的自我改進\n" + "研究代理可以協助整理文獻並找出知識缺口 [E1]，也能比較不同來源 [E2]。" * 40 + "\n本文不能取代專業人員的個別評估與諮詢。"
PLAN = json.dumps({"status": "ready", "confidence": 0.9, "queries": {"pubmed": ["agentic research"], "arxiv": ["autoresearch"], "trials": []},
                   "aspects": [{"task_id": "A1", "objective": "How do agents improve themselves?", "acceptance": "Mechanisms compared with evidence"}]})
NOTES = json.dumps({"notes": [
    {"concept": "Recursive self-improvement", "definition": "Systems that improve their own procedures [E1].",
     "claims": [{"text": "Survival was 63.6% in the trial", "keys": ["E1"]}, {"text": "Invented figure of 71.2%", "keys": ["E1"]},
                {"text": "Claim citing a key outside the batch", "keys": ["E99"]}], "related": ["Autoresearch"]}],
    "conflicts": [{"concept": "Recursive self-improvement", "detail": "Sources disagree on scale", "keys": ["E1", "E2"]}],
    "off_topic": ["E3"]})


def audit(verdict):
    return json.dumps({"verdict": verdict, "score": 0.8 if verdict == "PASS" else 0.4,
                       "findings": [] if verdict == "PASS" else [{"severity": "high", "where": "Results", "problem": "Missing comparison", "evidence": "E2", "fix": "Compare"}],
                       "new_queries": {"pubmed": ["more"]}, "gaps": ["What limits self-improvement in practice?"]})


class Script(llm.Conversation):
    audits = []
    prompts = []
    models = []

    limits = []

    def __init__(self, system, model, budget=0.0):
        self.system, self.model = system, model
        Script.limits.append((budget, model))

    async def send(self, prompt):
        Script.prompts.append(prompt)
        Script.models.append((self.model, prompt[:40]))
        if "PAPER UNDER AUDIT" in prompt:
            answer = Script.audits.pop(0) if Script.audits else audit("PASS")
        elif '"aspects"' in prompt:
            answer = PLAN
        elif "Use 2-6 concepts" in prompt:
            answer = NOTES
        elif prompt.startswith("Create a slide deck"):
            answer = DECK
        elif prompt.startswith("Write a blog post"):
            answer = BLOG
        else:
            answer = GOOD_PAPER
        return llm.Reply(answer, 0.01, 100)


FOUND = [Evidence("PubMed", "Trial One", "Survival was 63.6% with HR 0.24 in 697 people.", "Lee J, Park S", "Chest", "2024", doi="10.1000/one"),
         Evidence("arXiv preprint", "Preprint Two", "AUC reached 0.89.", "Chen Y", "arXiv", "2025", arxiv_id="2501.00001"),
         Evidence("PubMed", "Unrelated leukaemia study", "Remission was 42.0% in 201 patients.", "Kim H", "Front Pharmacol", "2025", doi="10.1000/off")]


class TestJevRun(unittest.TestCase):

    def run_graph(self, loops=2, audits=(), budget=5.0):
        tmp = Path(tempfile.mkdtemp())
        Script.audits, Script.prompts, Script.models = list(audits), [], []

        def collect(run_self, plan, first):
            return run_self._add_evidence(SourceStatus("Literature", "LIVE", 3), [Evidence(**vars(e)) for e in FOUND] if first else [])

        kb_cfg = {"knowledge_base": {"root": str(tmp / "vault" / "知識庫" / "2026 Autoresearch RSI"), "queue_md": str(tmp / "vault" / "知識庫" / "queue.md")},
                  "deliverables": ["deck", "blog"], "terms": {}}
        (tmp / "vault" / "知識庫").mkdir(parents=True)
        with mock.patch.object(pipeline, "RUNS_DIR", tmp / "runs"), mock.patch.object(pipeline, "RSI_DIR", tmp / ".rsi"), \
                mock.patch.object(jev, "OUTPUT_DIR", tmp / "outputs"), \
                mock.patch.object(pipeline.ResearchRun, "_collect", collect), \
                mock.patch.object(pipeline.ResearchRun, "_verify_citations", lambda self, texts: None), \
                mock.patch.dict(pipeline.CONFIG, kb_cfg), \
                mock.patch.object(llm, "conversation_factory", lambda s, m, b: Script(s, m, b)), \
                mock.patch.object(llm, "budget_problem", lambda models=None: None):
            (tmp / "outputs").mkdir()
            run = jev.JevRun(jev.JevRequest("Agentic autoresearch", loops, "", budget, "", "claude:claude-opus-5-5", "claude:claude-sonnet-5-5", "claude:claude-opus-5-5"))
            report = asyncio.run(run.execute())
        return run, report, tmp

    def test_full_graph_completes_and_writes_graph_files(self):
        run, report, tmp = self.run_graph(loops=1)
        self.assertEqual(report["status"], "COMPLETED", report["error"] or report["deliverables"] or report["kb"])
        self.assertEqual([d["kind"] for d in report["deliverables"]], ["paper", "deck", "blog"])
        statuses = {n["id"]: n["status"] for n in report["graph"]["nodes"]}
        for node in ("plan1", "collect1", "notes1", "draft1", "audit1", "deliver", "cite", "kb"):
            self.assertEqual(statuses.get(node), "passed", (node, statuses))
        for name in ("graph.md", "checks.md", "progress.md", "plan_loop1.json", "audit_loop1.json", "Academic_Paper.html", "Presentation.pptx", "Interactive_Deck.html", "Blog_Post.html"):
            self.assertTrue((run.dir / name).exists(), name)
        self.assertIn("```mermaid", (run.dir / "graph.md").read_text(encoding="utf-8"))

    def test_roles_route_to_the_right_models(self):
        self.run_graph(loops=1)
        by_kind = {}
        for model, head in Script.models:
            by_kind.setdefault(model, []).append(head)
        self.assertTrue(any("Research topic" in h for h in by_kind["claude:claude-opus-5-5"]))  # planner
        self.assertTrue(any("Topic:" in h for h in by_kind["claude:claude-sonnet-5-5"]))  # notes executor

    def test_off_topic_evidence_is_kept_out_of_the_paper(self):
        run, report, _ = self.run_graph(loops=1)
        self.assertEqual(report["off_topic"], ["E3"])
        drafts = [p for p in Script.prompts if "publication-style" in p]
        self.assertTrue(drafts)
        self.assertFalse(any("Unrelated leukaemia study" in p for p in drafts))

    def test_code_drops_ungrounded_and_foreign_claims(self):
        run, report, _ = self.run_graph(loops=1)
        texts = [c["text"] for n in run.notes for c in n["claims"]]
        self.assertIn("Survival was 63.6% in the trial", texts)
        self.assertFalse(any("71.2" in t for t in texts))
        self.assertEqual(report["dropped_claims"], 2)

    def test_audit_fail_triggers_replan_with_findings(self):
        run, report, _ = self.run_graph(loops=2, audits=[audit("FAIL"), audit("PASS")])
        self.assertEqual([a["verdict"] for a in report["audits"]], ["FAIL", "PASS"])
        self.assertTrue(any("Missing comparison" in p and '"aspects"' in p for p in Script.prompts))  # planner saw the findings
        self.assertTrue(any("Auditor findings" in p for p in Script.prompts))  # draft revised against findings
        self.assertIn({"source": "audit1", "target": "plan2"}, report["graph"]["edges"])

    def test_failed_audit_means_needs_review(self):
        _, report, _ = self.run_graph(loops=1, audits=[audit("FAIL")])
        self.assertEqual(report["status"], "NEEDS_REVIEW")
        self.assertFalse(report["deliverables"][0]["verified"])

    def test_code_overrides_an_audit_pass_when_checks_fail(self):
        run = jev.JevRun.__new__(jev.JevRun)
        result = pipeline.AskResult("x", checks=[checks.Check("Structure", False, 0.4, "bad")], failed_checks={"Structure"})
        self.assertFalse(result.passed)
        tmp = Path(tempfile.mkdtemp())
        with mock.patch.object(pipeline, "RUNS_DIR", tmp), mock.patch.object(pipeline, "RSI_DIR", tmp / ".rsi"), \
                mock.patch.object(llm, "conversation_factory", lambda s, m, b: Script(s, m)):
            run = jev.JevRun(jev.JevRequest("T", 1, "m", 5.0, "", "m", "m", "m"))
            Script.audits = [audit("PASS")]
            verdict = asyncio.run(run._audit_node(1, result, []))
        self.assertEqual(verdict["verdict"], "FAIL")

    def test_kb_pages_and_gaps_are_written(self):
        run, report, tmp = self.run_graph(loops=1)
        root = Path(report["kb"]["root"])
        self.assertTrue(any(root.rglob("*.md")))
        self.assertIn("What limits self-improvement in practice?", (root / "缺口" / "gaps.md").read_text(encoding="utf-8"))
        self.assertTrue((tmp / "outputs" / "kb_graph.json").exists())

    def test_budget_exhaustion_fails_cleanly(self):
        _, report, _ = self.run_graph(loops=1, budget=0.005)
        self.assertEqual(report["status"], "FAILED")
        self.assertIn("budget", report["error"])


class TestRoles(unittest.TestCase):

    def test_auditor_prefers_another_provider(self):
        tiers = {"high": ["claude:claude-opus-5-5", "openai:gpt-high"], "medium": ["claude:claude-sonnet-5-5"]}
        providers = {"claude": {"type": "claude"}, "openai": {"type": "openai_compatible", "base_url": "http://x", "price_per_mtok": {"gpt-high": {"input": 1, "output": 2}}}}
        with mock.patch.dict(llm.CONFIG, {"tiers": tiers, "providers": providers}):
            roles = jev.default_roles()
        self.assertEqual(roles["executor"], "claude:claude-sonnet-5-5")
        self.assertEqual(roles["auditor"], "openai:gpt-high")

    def test_missing_price_blocks_a_tier_model(self):
        providers = {"openai": {"type": "openai_compatible", "base_url": "http://x", "price_per_mtok": {}}}
        with mock.patch.dict(llm.CONFIG, {"providers": providers}):
            self.assertIn("price_per_mtok", llm.budget_problem(["openai:gpt-x"]))

    def test_effort_suffix_is_priced_by_base_model_and_sent(self):
        settings = {"type": "openai_compatible", "base_url": "http://x", "price_per_mtok": {"gpt-sol": {"input": 2, "output": 10}}}
        providers = {"openai": settings}
        with mock.patch.dict(llm.CONFIG, {"providers": providers}):
            self.assertIsNone(llm.budget_problem(["openai:gpt-sol@high"]))
            self.assertIn("price_per_mtok", llm.budget_problem(["openai:gpt-other@high"]))
        sent = {}

        class Resp:
            status_code = 200
            def json(self):
                return {"choices": [{"message": {"content": "OK"}}], "usage": {"prompt_tokens": 1_000_000, "completion_tokens": 0}}

        def fake_post(url, json, headers, timeout):
            sent.update(json)
            return Resp()

        conv = llm.OpenAICompatibleConversation("s", "gpt-sol@medium", settings)
        with mock.patch.object(llm.requests, "post", fake_post):
            reply = asyncio.run(conv.send("hi"))
        self.assertEqual((sent["model"], sent["reasoning_effort"]), ("gpt-sol", "medium"))
        self.assertAlmostEqual(reply.cost_usd, 2.0)
        plain = llm.OpenAICompatibleConversation("s", "gpt-sol", settings)
        with mock.patch.object(llm.requests, "post", fake_post):
            sent.clear()
            asyncio.run(plain.send("hi"))
        self.assertNotIn("reasoning_effort", sent)

    def test_blog_slug_is_cut_on_a_word_boundary(self):
        topic = "Agentic autoresearch and recursive self-improvement in AI research agents"
        with mock.patch.object(jev.JevRun, "__init__", lambda self, req: None):
            run = jev.JevRun(None)
        run.request, run.evidence = jev.JevRequest(topic, 1, "m", 5.0, "", "m", "m", "m"), {}
        slug = run._blog_meta()["slug"]
        self.assertLessEqual(len(slug), 60)
        self.assertTrue(("-" + topic.lower().replace(" ", "-") + "-").startswith("-" + slug + "-"), slug)

    def test_unknown_effort_is_an_error(self):
        with self.assertRaises(llm.ProviderError):
            llm.split_effort("gpt-sol@turbo")

    def test_project_tiers_are_all_priced(self):
        self.assertIsNone(llm.budget_problem(llm.all_model_refs()))

    def test_model_reference_resolves_provider(self):
        name, settings, model_id = llm.resolve("gemini:some-model")
        self.assertEqual((name, model_id), ("gemini", "some-model"))


class TestServer(unittest.TestCase):

    def setUp(self):
        self.client = web.create_app().test_client()
        self.h = {"Host": "127.0.0.1:8090", "Origin": "http://127.0.0.1:8090"}

    def test_unknown_role_model_is_refused(self):
        r = self.client.post("/api/research", json={"topic": "A topic", "loops": 1, "budget_usd": 1, "planner": "evil:model"}, headers=self.h)
        self.assertEqual(r.status_code, 400)

    def test_config_reports_tiers_and_real_provider_status(self):
        data = self.client.get("/api/config", headers=self.h).get_json()
        self.assertIn("high", data["tiers"])
        self.assertTrue(all("available" in p for p in data["providers"]))

    def test_kb_page_rejects_traversal(self):
        r = self.client.get("/api/kb/page?path=../../secret.md", headers=self.h)
        self.assertEqual(r.status_code, 400)

    def test_kb_improve_requires_same_origin(self):
        r = self.client.post("/api/kb/improve", json={}, headers={"Host": "127.0.0.1:8090", "Origin": "https://evil.example"})
        self.assertEqual(r.status_code, 403)


class TestAuditFixes(unittest.TestCase):
    """Regression tests for the wave-1 audit findings."""

    def graph(self, **kw):
        return TestJevRun.run_graph(TestJevRun(), **kw)

    def test_audit_pass_with_high_finding_is_overridden(self):
        bad = json.dumps({"verdict": "PASS", "score": 0.9, "findings": [{"severity": "High", "problem": "Fabricated figure"}], "gaps": []})
        _, report, _ = self.graph(loops=1, audits=[bad])
        self.assertEqual(report["audits"][0]["verdict"], "FAIL")
        self.assertEqual(report["status"], "NEEDS_REVIEW")

    def test_malformed_score_does_not_kill_the_run(self):
        odd = json.dumps({"verdict": "PASS", "score": "low", "findings": [], "gaps": []})
        _, report, _ = self.graph(loops=1, audits=[odd])
        self.assertEqual(report["status"], "COMPLETED", report["error"])
        self.assertEqual(report["audits"][0]["score"], 0.0)

    def test_cancel_inside_the_swarm_is_cancelled_not_failed(self):
        original = Script.send

        async def send(self_, prompt):
            if "Use 2-6 concepts" in prompt:
                RUNS[-1].cancel_event.set()
            return await original(self_, prompt)

        RUNS.clear()
        real_init = jev.JevRun.__init__

        def init(self_, *a, **k):
            real_init(self_, *a, **k)
            RUNS.append(self_)

        with mock.patch.object(Script, "send", send), mock.patch.object(jev.JevRun, "__init__", init):
            _, report, _ = self.graph(loops=1)
        self.assertEqual(report["status"], "CANCELLED", report["error"])
        self.assertNotIn("running", [n["status"] for n in report["graph"]["nodes"]])

    def test_parallel_deliverables_split_the_budget(self):
        Script.limits = []
        original = Script.send
        seen = []

        async def send(self_, prompt):
            seen.append(prompt[:20])
            return await original(self_, prompt)

        with mock.patch.object(Script, "send", send):
            run, report, _ = self.graph(loops=1, budget=1.0)
        # Conversations are opened in order; the last two are the parallel deck and blog.
        deck_blog = [b for b, _ in Script.limits[-2:]]
        self.assertEqual(len(deck_blog), 2)
        self.assertLessEqual(sum(deck_blog), 1.0 - 0.0)  # together they cannot exceed what remained
        self.assertTrue(all(0 < b <= 0.5 for b in deck_blog), deck_blog)

RUNS = []


if __name__ == "__main__":
    unittest.main()
