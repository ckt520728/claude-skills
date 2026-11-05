"""Offline tests: checks, rendering, server safety, providers, and the RSI loop with a scripted model."""

import asyncio
import json
import sys
import tempfile
import threading
import unittest
import xml.etree.ElementTree as ET
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from knowledge_agent import app as web
from knowledge_agent import checks, config, llm, pipeline, render, sources
from knowledge_agent.sources import Evidence, SourceStatus


def evidence():
    return {
        "E1": Evidence("PubMed", "Trial One", "Survival was 63.6% with HR 0.24 in 697 people.", "Lee J", "Chest", "2024", doi="10.1000/one", key="E1"),
        "E2": Evidence("arXiv preprint", "Preprint Two", "AUC reached 0.89.", "Chen Y", "arXiv", "2025", arxiv_id="2501.00001", key="E2"),
    }


class TestChecks(unittest.TestCase):

    def test_unknown_citation_fails(self):
        self.assertFalse(checks.check_citation_keys("Claim [E99].", evidence(), 1).passed)

    def test_hand_typed_identifier_fails(self):
        self.assertFalse(checks.check_citation_keys("See 10.1000/fake and [E1].", evidence(), 1).passed)

    def test_bare_key_in_prose_fails(self):
        self.assertFalse(checks.check_citation_keys("E1 reported this [E1].", evidence(), 1).passed)

    def test_too_few_sources_fails(self):
        self.assertFalse(checks.check_citation_keys("Claim [E1].", evidence(), 2).passed)

    def test_grouped_citations_count(self):
        self.assertTrue(checks.check_citation_keys("Claim [E1, E2].", evidence(), 2).passed)

    def test_number_in_cited_source_passes(self):
        self.assertTrue(checks.check_numbers("Survival was 63.6% with HR 0.24 [E1].", evidence()).passed)

    def test_invented_number_fails(self):
        result = checks.check_numbers("Survival was 71.2% [E1].", evidence())
        self.assertFalse(result.passed)
        self.assertIn("71.2", result.message)

    def test_number_from_the_wrong_source_fails(self):
        self.assertFalse(checks.check_numbers("Survival was 63.6% [E2].", evidence()).passed)

    def test_number_without_citation_fails(self):
        self.assertFalse(checks.check_numbers("Survival was 63.6%.", evidence()).passed)

    def test_citation_at_the_end_of_a_table_row_covers_the_row(self):
        table = "| Study | Survival | HR | Source |\n|---|---|---|---|\n| One | 63.6% | 0.24 | [E1] |"
        self.assertTrue(checks.check_numbers(table, evidence()).passed)

    def test_invented_number_in_a_table_row_fails(self):
        table = "| Study | Survival | Source |\n|---|---|---|\n| One | 71.2% | [E1] |"
        self.assertFalse(checks.check_numbers(table, evidence()).passed)

    def test_semicolon_does_not_separate_a_figure_from_its_citation(self):
        self.assertTrue(checks.check_numbers("Survival was 63.6%; HR 0.24 (95% CI) [E1].", evidence()).passed)

    def test_years_and_small_counts_are_ignored(self):
        self.assertTrue(checks.check_numbers("In 2024, 3 groups compared this [E1].", evidence()).passed)

    def test_chart_title_citation_covers_its_bars(self):
        panel = {"title": "t", "points": ["p [E1]"], "chart": {"title": "Survival [E1]", "bars": [{"label": "a", "value": 63.6}]}}
        self.assertTrue(checks.check_numbers(json.dumps({"panels": [panel]}), evidence()).passed)
        panel["chart"]["bars"][0]["value"] = 71.2
        self.assertFalse(checks.check_numbers(json.dumps({"panels": [panel]}), evidence()).passed)

    def test_chart_values(self):
        self.assertEqual(checks.number_value("55.4 [E4]"), 55.4)
        self.assertEqual(checks.number_value("63.6%"), 63.6)
        self.assertIsNone(checks.number_value("high"))
        self.assertIsNone(checks.number_value(True))

    def test_identifier_is_rejected_without_being_echoed(self):
        with mock.patch.object(checks, "load_phi_terms", return_value=["SECRET-ID"]):
            result = checks.check_clean("Case SECRET-ID here")
        self.assertFalse(result.passed)
        self.assertNotIn("SECRET-ID", result.message)

    def test_forbidden_term_fails(self):
        with mock.patch.dict(checks.CONFIG, {"terms": {"preferred": {"STAT": "right"}, "forbidden": ["wrongterm"]}}):
            self.assertFalse(checks.check_clean("uses wrongterm here").passed)

    def test_latex_and_placeholders_fail(self):
        self.assertFalse(checks.check_clean(r"Value $\text{x}$").passed)
        self.assertFalse(checks.check_clean("TODO finish").passed)

    def test_structures(self):
        headings = "\n".join(f"## {h}\nword" for h in ("Abstract", "摘要", "Introduction", "Methods", "Results", "Discussion", "Limitations", "Conclusion"))
        good = "# T\n" + headings + "\n" + "word " * 950
        self.assertEqual(checks.STRUCTURE["paper"](good), [])
        self.assertTrue(checks.STRUCTURE["paper"](good + "\n## References\n1. x"))
        self.assertEqual(checks.STRUCTURE["deck"](json.dumps({"slides": [{"title": "t", "bullets": ["b"]}] * 9})), [])
        self.assertTrue(checks.STRUCTURE["deck"]("not json"))
        self.assertTrue(checks.STRUCTURE["infographic"](json.dumps({"panels": [{"title": "t", "points": ["p"]}] * 5})))


class TestCitationLookup(unittest.TestCase):

    def _response(self, status, body=None):
        resp = mock.Mock(status_code=status, ok=status == 200, text="")
        resp.json.return_value = body or {}
        return resp

    def test_real_doi_registered_to_another_title_is_flagged(self):
        item = Evidence("PubMed", "Segmentectomy as a New Standard", doi="10.1000/x")
        with mock.patch.object(sources.requests, "get", return_value=self._response(200, {"message": {"title": ["Aprepitant as a Cough Suppressant"]}})):
            self.assertIn("different title", sources.citation_problems(item)[0])

    def test_matching_title_passes(self):
        item = Evidence("PubMed", "Segmentectomy as a New Standard", doi="10.1000/x")
        with mock.patch.object(sources.requests, "get", return_value=self._response(200, {"message": {"title": ["Segmentectomy as a new standard"]}})):
            self.assertEqual(sources.citation_problems(item), [])

    def test_missing_doi_is_flagged(self):
        item = Evidence("PubMed", "Title", doi="10.1000/x")
        with mock.patch.object(sources.requests, "get", return_value=self._response(404)):
            self.assertIn("was not found", sources.citation_problems(item)[0])

    def test_doi_of_a_cited_paper_is_not_taken_as_this_papers_doi(self):
        cited = Evidence("Reference PDF", "A Completely Different Study Of Something Else", doi="10.1000/cited")
        own = Evidence("Reference PDF", "Extent of Resection for Air Spaces Disease", doi="10.1000/own")
        records = {"10.1000/cited": cited, "10.1000/own": own}
        page = "Extent of resection for air spaces disease. Authors."
        with mock.patch.object(sources, "_crossref_record", side_effect=records.get), mock.patch.object(sources, "_search_crossref", return_value=[]):
            found = sources._identify_pdf(Path("x_2024_y.pdf"), {}, page, f"{page} References: doi:10.1000/cited and doi:10.1000/own")
        self.assertEqual(found.doi, "10.1000/own")


class TestRender(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_numbers_follow_first_use_and_skip_unknown_keys(self):
        text, order = render.number_citations("A [E2]. B [E1, E2]. C [E9].", evidence())
        self.assertEqual(order, ["E2", "E1"])
        self.assertEqual(text, "A [1]. B [2, 1]. C .")

    def test_reference_list_comes_from_evidence(self):
        files = render.render_document("# T\nClaim [E1].", evidence(), self.dir, "Doc", True, "ok")
        md = (self.dir / files["md"]).read_text(encoding="utf-8")
        self.assertIn("doi:10.1000/one", md)
        self.assertNotIn("Preprint Two", md)
        self.assertIn('href="#ref-1"', (self.dir / files["html"]).read_text(encoding="utf-8"))

    def test_failed_document_is_visibly_marked(self):
        files = render.render_document("# T\nClaim [E1].", evidence(), self.dir, "Doc", False, "broken")
        self.assertIn('class="status review"', (self.dir / files["html"]).read_text(encoding="utf-8"))

    def test_model_html_is_escaped(self):
        deck = json.dumps({"slides": [{"title": "<script>x</script>", "bullets": ["<img src=x> [E1]"]}]})
        page = (self.dir / render.render_deck_html(deck, evidence(), self.dir, "Deck", True, "ok")).read_text(encoding="utf-8")
        self.assertNotIn("<script>x</script>", page)
        self.assertNotIn("<img src=x>", page)

    def test_pptx_has_slides_and_references(self):
        deck = json.dumps({"slides": [{"title": "T", "bullets": ["fact [E1]"], "notes": "n"}] * 2})
        name = render.render_deck_pptx(deck, evidence(), self.dir, "Pres", True)
        with zipfile.ZipFile(self.dir / name) as z:
            self.assertEqual(len([n for n in z.namelist() if n.startswith("ppt/slides/slide")]), 3)

    def test_infographic_is_valid_xml(self):
        panel = {"title": "A & B", "stat": {"value": "63.6%", "label": "Survival [E1]"}, "points": ["short [E1]"], "chart": {"title": "c", "unit": "%", "bars": [{"label": "a", "value": "63.6 [E1]"}]}}
        files = render.render_infographic(json.dumps({"title": "T", "panels": [panel] * 6}), evidence(), self.dir, "Info", "T", True, "ok")
        self.assertEqual(ET.parse(self.dir / files["svg"]).getroot().get("height"), "2160")


class TestServerSafety(unittest.TestCase):

    def setUp(self):
        self.client = web.create_app().test_client()
        self.base = {"Host": "127.0.0.1:8080"}
        provider = config.CONFIG["provider"]
        self.good = {"topic": "A topic", "passes": 1, "model": provider["default_model"], "budget_usd": 1}

    def post(self, body, origin="http://127.0.0.1:8080"):
        headers = dict(self.base)
        if origin:
            headers["Origin"] = origin
        return self.client.post("/api/research", json=body, headers=headers)

    def test_remote_host_is_refused(self):
        self.assertEqual(self.client.get("/api/health", headers={"Host": "evil.example"}).status_code, 403)

    def test_post_from_another_site_is_refused(self):
        for origin in ("https://evil.example", "null", None):
            self.assertEqual(self.post(self.good, origin).status_code, 403, origin)

    def test_form_post_is_refused(self):
        response = self.client.post("/api/research", data="topic=x", headers={**self.base, "Origin": "http://127.0.0.1:8080", "Content-Type": "text/plain"})
        self.assertEqual(response.status_code, 415)

    def test_invalid_values_are_refused(self):
        for change in ({"topic": ""}, {"passes": 9}, {"budget_usd": 500}, {"model": "nope"}, {"budget_usd": "x"}):
            self.assertEqual(self.post({**self.good, **change}).status_code, 400, change)

    def test_identifier_in_feedback_is_refused(self):
        with mock.patch.object(web, "phi_hits", return_value=1):
            self.assertEqual(self.post(self.good).status_code, 400)

    def test_paths_cannot_escape(self):
        self.assertEqual(self.client.get("/api/runs/..%2f..%2fsecret", headers=self.base).status_code, 404)
        self.assertEqual(self.client.get("/outputs/../.env", headers=self.base).status_code, 404)

    def test_dashboard_budget_field_accepts_its_default(self):
        # min with a coarse step makes whole numbers invalid, and the browser silently refuses to submit.
        html = self.client.get("/", headers=self.base).get_data(as_text=True)
        self.assertIn('step="any"', html)


class FakeOpenAI(BaseHTTPRequestHandler):
    seen = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeOpenAI.seen.append((self.path, self.headers.get("Authorization"), len(body["messages"])))
        reply = {"choices": [{"message": {"content": f"reply {len(body['messages'])}"}}], "usage": {"prompt_tokens": 1000, "completion_tokens": 500}}
        data = json.dumps(reply).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class TestProviders(unittest.TestCase):

    def test_openai_compatible_keeps_history_and_computes_cost(self):
        server = HTTPServer(("127.0.0.1", 0), FakeOpenAI)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        FakeOpenAI.seen = []
        settings = {"base_url": f"http://127.0.0.1:{server.server_port}/v1", "api_key_env": "TEST_KEY", "price_per_mtok": {"input": 2, "output": 10}}

        async def talk():
            chat = llm.OpenAICompatibleConversation("system", "m", settings)
            async with chat:
                first = await chat.send("one")
                second = await chat.send("two")
            return first, second

        with mock.patch.dict("os.environ", {"TEST_KEY": "k"}):
            first, second = asyncio.run(talk())
        self.assertEqual(first.text, "reply 2")
        self.assertEqual(second.text, "reply 4")  # The repair turn can see the earlier answer.
        self.assertAlmostEqual(first.cost_usd, 0.007)
        self.assertEqual(FakeOpenAI.seen[0][:2], ("/v1/chat/completions", "Bearer k"))

    def test_missing_key_is_a_clear_error(self):
        with mock.patch.dict("os.environ", {}, clear=True), self.assertRaises(llm.ProviderError):
            llm.OpenAICompatibleConversation("s", "m", {"base_url": "http://x", "api_key_env": "ABSENT"})

    def test_paid_endpoint_without_prices_is_refused(self):
        settings = {"type": "openai_compatible", "base_url": "http://x"}
        with mock.patch.dict(llm.CONFIG, {"provider": settings}):
            self.assertIn("price_per_mtok", llm.budget_problem())
        with mock.patch.dict(llm.CONFIG, {"provider": {**settings, "free": True}}):
            self.assertIsNone(llm.budget_problem())


HEADINGS = "\n".join(f"## {h}\nFinding [E1]." for h in ("Abstract", "摘要", "Introduction", "Methods", "Results", "Discussion", "Limitations", "Conclusion"))
GOOD_PAPER = "# Title\n" + HEADINGS + "\n" + "word " * 950
BLOG = "# Title\n" + "內容與 content [E1]。" * 250 + "\n不能取代 does not replace professional advice."
PANEL = {"title": "t", "points": ["fact [E1]"]}


class ScriptedChat(llm.Conversation):
    """Plays a script per kind of request, with a real-looking cost."""
    paper_answers = []
    prompts = []

    def __init__(self):
        self.seen = False

    async def send(self, prompt):
        ScriptedChat.prompts.append(prompt)
        if "failed these automated checks" in prompt:
            answer = GOOD_PAPER
        elif "peer reviewer" in prompt:
            answer = '{"gaps":["needs more"],"pubmed":["q2"],"revisions":["add more"]}'
        elif "Plan literature" in prompt:
            answer = '{"pubmed":["q"],"questions":["q?"]}'
        elif "publication-style" in prompt:
            answer = ScriptedChat.paper_answers.pop(0) if ScriptedChat.paper_answers else GOOD_PAPER
        elif "slide deck" in prompt:
            answer = json.dumps({"slides": [{"title": "T", "bullets": ["fact [E1]"]}] * 9})
        elif "blog post" in prompt:
            answer = BLOG
        else:
            answer = json.dumps({"title": "T", "panels": [PANEL] * 6})
        return llm.Reply(answer, 0.01, 100)


class TestPipeline(unittest.TestCase):

    def run_pipeline(self, request, found=None, paper_answers=(), cancel=False):
        tmp = Path(tempfile.mkdtemp())
        ScriptedChat.paper_answers = list(paper_answers)
        ScriptedChat.prompts = []
        found = [Evidence("PubMed", "Real paper", "Text", doi="10.1000/real")] if found is None else found

        def collect(run_self, plan, first):
            return run_self._add_evidence(SourceStatus("Literature", "LIVE", len(found)), list(found) if first else [])

        terms = {"terms": {}, "deliverables": ["deck", "blog", "infographic"]}
        with mock.patch.object(pipeline, "RUNS_DIR", tmp / "runs"), mock.patch.object(pipeline, "RSI_DIR", tmp / ".rsi"), \
                mock.patch.object(pipeline.ResearchRun, "_collect", collect), \
                mock.patch.object(pipeline.ResearchRun, "_verify_citations", lambda self, texts: None), \
                mock.patch.object(pipeline, "LANGUAGE", "zh-TW"), mock.patch.object(checks, "LANGUAGE", "zh-TW"), \
                mock.patch.dict(pipeline.CONFIG, terms), \
                mock.patch.object(llm, "conversation_factory", lambda s, m, b: ScriptedChat()), \
                mock.patch.object(llm, "budget_problem", lambda: None):
            run = pipeline.ResearchRun(request)
            if cancel:
                run.cancel_event.set()
            report = asyncio.run(run.execute())
        return run, report, tmp

    def test_full_run_produces_all_deliverables(self):
        run, report, _ = self.run_pipeline(pipeline.ResearchRequest("Topic", passes=1, model="m"))
        self.assertEqual(report["status"], "COMPLETED", report["error"] or report["deliverables"])
        self.assertEqual([d["kind"] for d in report["deliverables"]], ["paper", "deck", "blog", "infographic"])
        for name in ("Academic_Paper.html", "Academic_Paper.md", "Interactive_Deck.html", "Presentation.pptx", "Blog_Post.html", "Infographic.svg", "Infographic_Viewer.html", "evidence.json", "run_report.json"):
            self.assertTrue((run.dir / name).exists(), name)

    def test_failed_check_is_sent_back_for_repair(self):
        _, report, _ = self.run_pipeline(pipeline.ResearchRequest("Topic", passes=1, model="m"), paper_answers=["# Title only"])
        self.assertEqual(report["passes"][0]["attempts"], 2)
        self.assertIn("Structure", report["passes"][0]["failed_checks"])
        self.assertEqual(report["status"], "COMPLETED")

    def test_second_pass_critiques_then_revises(self):
        _, report, _ = self.run_pipeline(pipeline.ResearchRequest("Topic", passes=2, model="m"))
        self.assertEqual(len(report["passes"]), 2)
        self.assertEqual(report["passes"][0]["gaps_found"], ["needs more"])
        self.assertTrue(any("Revise the draft" in p for p in ScriptedChat.prompts))

    def test_no_evidence_fails_instead_of_writing(self):
        _, report, _ = self.run_pipeline(pipeline.ResearchRequest("Topic", passes=1, model="m"), found=[])
        self.assertEqual(report["status"], "FAILED")
        self.assertFalse(any("publication-style" in p for p in ScriptedChat.prompts))

    def test_cancel_stops_the_run(self):
        _, report, _ = self.run_pipeline(pipeline.ResearchRequest("Topic", model="m"), cancel=True)
        self.assertEqual(report["status"], "CANCELLED")

    def test_budget_stops_the_run(self):
        _, report, _ = self.run_pipeline(pipeline.ResearchRequest("Topic", passes=1, model="m", budget_usd=0.005))
        self.assertEqual(report["status"], "FAILED")
        self.assertIn("budget", report["error"])

    def test_identifier_in_evidence_is_dropped(self):
        run = pipeline.ResearchRun.__new__(pipeline.ResearchRun)
        run.evidence, run._seen, run.source_status, run.dropped_for_privacy = {}, set(), {}, 0
        with mock.patch.object(pipeline, "phi_hits", side_effect=lambda t: 1 if "BAD" in t else 0):
            run._add_evidence(SourceStatus("X", "LIVE"), [Evidence("PubMed", "BAD title"), Evidence("PubMed", "Good title")])
        self.assertEqual(run.dropped_for_privacy, 1)
        self.assertEqual([e.title for e in run.evidence.values()], ["Good title"])

    def _with_passes(self, first_failed, second_failed):
        tmp = Path(tempfile.mkdtemp())
        with mock.patch.object(pipeline, "RUNS_DIR", tmp / "runs"), mock.patch.object(pipeline, "RSI_DIR", tmp / ".rsi"):
            run = pipeline.ResearchRun(pipeline.ResearchRequest("Topic", model="m"))
            run.passes_done = [{"pass": 1, "failed_checks": first_failed}, {"pass": 2, "failed_checks": second_failed}]
            run._evolve()
        return run, tmp

    def test_rule_is_promoted_only_when_the_failure_stops(self):
        run, tmp = self._with_passes(["NumericGrounding"], [])
        self.assertEqual([p["decision"] for p in run.promotions], ["PROMOTE"])
        self.assertIn("rule_numbers_beside_source", json.loads((tmp / ".rsi" / "playbook.json").read_text(encoding="utf-8")))

    def test_rule_is_rejected_when_the_failure_continues(self):
        run, tmp = self._with_passes(["NumericGrounding"], ["NumericGrounding"])
        self.assertEqual([p["decision"] for p in run.promotions], ["REJECT"])
        self.assertFalse((tmp / ".rsi" / "playbook.json").exists())
        self.assertEqual(len((tmp / ".rsi" / "ledger.jsonl").read_text(encoding="utf-8").splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
