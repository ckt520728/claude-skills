"""Section C: APA 7 rendering, the 15-slide Scientific Storyteller deck, and the house-style zh-TW blog."""

import json
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pptx import Presentation

from knowledge_agent import checks, render, specs
from knowledge_agent.checks import CONFIG
from knowledge_agent.sources import Evidence

SECTIONS = [name for name, count in specs.DECK_SECTIONS for _ in range(count)]


def ev(**kw):
    return Evidence(**{"kind": "PubMed", "title": "A title", **kw})


def deck_json(n_bullets=2, **override):
    slides = []
    for i, name in enumerate(SECTIONS, 1):
        slides.append({"section": name, "title": f"Slide {i}", "bullets": [f"fact {j} [E1]" for j in range(n_bullets)],
                       "notes": f"say {i}", "visual_prompt": f"prompt {i} | pipe", "layout": "Split screen"})
    slides = override.get("slides", slides)
    return json.dumps({"slides": slides}, ensure_ascii=False)


def pack():
    return {
        "E1": ev(title="Trial One", authors="Lee J, Park S, Chen Y, et al", journal="Chest", year="2024", doi="10.1000/one", key="E1"),
        "E2": ev(kind="Europe PMC", title="Second Paper", authors="Chen Y.", journal="Lancet", year="2025", doi="10.1000/two", key="E2"),
        "E3": ev(title="Third", authors="Adams B", journal="Brain", year="2023", pmid="123456", key="E3"),
    }


class TestApa(unittest.TestCase):

    def test_one_author(self):
        e = ev(authors="Lee J", journal="Chest", year="2024", doi="10.1000/x")
        self.assertEqual(render.apa_reference(e), "Lee, J. (2024). A title. Chest. https://doi.org/10.1000/x")
        self.assertEqual(render.apa_intext(e), "Lee, 2024")

    def test_two_authors(self):
        e = ev(authors="Lee J, Park SK", journal="Chest", year="2024", doi="10.1000/x")
        self.assertIn("Lee, J., & Park, S. K. (2024).", render.apa_reference(e))
        self.assertEqual(render.apa_intext(e), "Lee & Park, 2024")

    def test_three_authors(self):
        e = ev(authors="Lee J, Park S, Chen Y", journal="Chest", year="2024", doi="10.1000/x")
        self.assertTrue(render.apa_reference(e).startswith("Lee, J., Park, S., & Chen, Y. (2024). A title. Chest."))
        self.assertEqual(render.apa_intext(e), "Lee et al., 2024")

    def test_et_al_string(self):
        e = ev(authors="Lee J, Park S, Chen Y, et al", year="2024", doi="10.1000/x")
        self.assertTrue(render.apa_reference(e).startswith("Lee, J., Park, S., Chen, Y., et al. (2024)."))
        self.assertEqual(render.apa_intext(e), "Lee et al., 2024")

    def test_europe_pmc_trailing_period(self):
        e = ev(kind="Europe PMC", authors="Lee J, Park S, Chen Y.", year="2024", doi="10.1000/x")
        ref = render.apa_reference(e)
        self.assertTrue(ref.startswith("Lee, J., Park, S., & Chen, Y. (2024)."), ref)
        self.assertNotIn("Y..", ref)

    def test_arxiv_full_names(self):
        e = ev(kind="arXiv preprint", title="Deep learning", authors="Yann LeCun, Ada Lovelace", journal="arXiv", year="2025", arxiv_id="2501.00001")
        self.assertEqual(render.apa_reference(e), "LeCun, Y., & Lovelace, A. (2025). Deep learning. arXiv. https://arxiv.org/abs/2501.00001")
        self.assertEqual(render.apa_intext(e), "LeCun & Lovelace, 2025")

    def test_no_authors_uses_title(self):
        e = ev(kind="Reference PDF", title="Annual guideline for kidney care today", year="2022", journal="Society")
        self.assertTrue(render.apa_reference(e).startswith("Annual guideline for kidney care today. (2022). Society."))
        self.assertEqual(render.apa_intext(e), '"Annual guideline for kidney", 2022')

    def test_missing_year(self):
        e = ev(authors="Lee J", doi="10.1000/x")
        self.assertIn("(n.d.)", render.apa_reference(e))
        self.assertEqual(render.apa_intext(e), "Lee, n.d.")

    def test_doi_url_not_doubled(self):
        e = ev(authors="Lee J", year="2024", doi="https://doi.org/10.1000/x")
        self.assertTrue(render.apa_reference(e).endswith("https://doi.org/10.1000/x"))

    def test_registry_nct_url(self):
        e = ev(kind="ClinicalTrials.gov registry entry", title="Kidney study", year="2023", nct_id="NCT01234567")
        self.assertEqual(render.apa_reference(e), "Kidney study. (2023). ClinicalTrials.gov. https://clinicaltrials.gov/study/NCT01234567")
        self.assertEqual(render.apa_intext(e), "ClinicalTrials.gov, 2023")

    def test_pubmed_url_when_only_pmid(self):
        e = ev(authors="Adams B", year="2023", journal="Brain", pmid="123456")
        self.assertTrue(render.apa_reference(e).endswith("https://pubmed.ncbi.nlm.nih.gov/123456/"))


class TestPaperApa(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_replaces_keys_and_sorts_references(self):
        text = "# Paper\n\nFirst claim [E1, E2]. Another [E3] and ghost [E99]. Again [E2].\n"
        files = render.render_paper_apa(text, pack(), self.dir, "Paper", True, "ok")
        md = (self.dir / files["md"]).read_text(encoding="utf-8")
        page = (self.dir / files["html"]).read_text(encoding="utf-8")
        self.assertNotRegex(md, r"\[E\d+")
        self.assertNotRegex(page, r"\[E\d+")
        self.assertIn("(Lee et al., 2024; Chen, 2025)", md)
        self.assertIn("(Adams, 2023)", md)
        refs = md.split("## References")[1]
        self.assertLess(refs.index("Adams"), refs.index("Chen"))
        self.assertLess(refs.index("Chen"), refs.index("Lee"))
        self.assertNotIn("E99", refs)
        self.assertEqual(refs.count("Lee, J."), 1)
        self.assertIn("text-indent:-2em", page)
        self.assertIn("<i>Chest.</i>", page)

    def test_same_author_year_gets_suffix(self):
        both = {"E1": ev(title="Alpha", authors="Lee J", year="2024", doi="10.1/a", key="E1"), "E2": ev(title="Beta", authors="Lee J", year="2024", doi="10.1/b", key="E2")}
        files = render.render_paper_apa("# T\n\nx [E1] y [E2].", both, self.dir, "P", True, "ok")
        md = (self.dir / files["md"]).read_text(encoding="utf-8")
        self.assertIn("Lee, 2024a", md)
        self.assertIn("Lee, 2024b", md)
        self.assertIn("(2024a)", md)

    def test_model_html_is_escaped(self):
        text = "# <script>alert(1)</script>\n\nHello <img src=x onerror=alert(1)> [E1] [bad](javascript:alert(1))\n"
        page = (self.dir / render.render_paper_apa(text, pack(), self.dir, "P", False, "<b>n</b>")["html"]).read_text(encoding="utf-8")
        self.assertNotIn("<script>alert", page)
        self.assertNotIn("<img src=x", page)
        self.assertNotIn("javascript:", page)
        self.assertNotIn("<b>n</b>", page)
        self.assertIn('class="status review"', page)


class TestDeckChecks(unittest.TestCase):

    def test_valid_deck_passes(self):
        self.assertEqual(checks.STRUCTURE["deck"](deck_json()), [])

    def test_fourteen_slides_fail(self):
        slides = json.loads(deck_json())["slides"][:-1]
        problems = checks.STRUCTURE["deck"](json.dumps({"slides": slides}))
        self.assertTrue(any("exactly 15" in p for p in problems), problems)

    def test_wrong_section_counts_fail(self):
        slides = json.loads(deck_json())["slides"]
        slides[0]["section"] = "concepts"
        problems = checks.STRUCTURE["deck"](json.dumps({"slides": slides}))
        self.assertTrue(any('"hook" needs 2 slides, found 1' in p for p in problems), problems)

    def test_wrong_section_order_fails(self):
        slides = json.loads(deck_json())["slides"]
        slides[1], slides[2] = slides[2], slides[1]
        problems = checks.STRUCTURE["deck"](json.dumps({"slides": slides}))
        self.assertTrue(any("out of order" in p for p in problems), problems)

    def test_six_bullets_fail(self):
        slides = json.loads(deck_json())["slides"]
        slides[4]["bullets"] = ["a [E1]"] * 6
        problems = checks.STRUCTURE["deck"](json.dumps({"slides": slides}))
        self.assertTrue(any("Slide 5" in p and "at most 5" in p for p in problems), problems)

    def test_missing_title_or_bullets_fail(self):
        slides = json.loads(deck_json())["slides"]
        slides[2]["title"] = ""
        slides[3]["bullets"] = []
        problems = checks.STRUCTURE["deck"](json.dumps({"slides": slides}))
        self.assertTrue(any("Slide 3 needs" in p for p in problems))
        self.assertTrue(any("Slide 4 needs" in p for p in problems))

    def test_not_json_fails(self):
        self.assertTrue(checks.STRUCTURE["deck"]("nope"))


class TestDeckRender(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_html_deck(self):
        name = render.render_deck_html(deck_json(), pack(), self.dir, "Deck", True, "ok")
        page = (self.dir / name).read_text(encoding="utf-8")
        self.assertEqual(page.count('class="slide"'), 16)  # 15 + references
        for needle in ("#12355B", "#1F77B4", 'class="chip"', 'id="bar"', 'id="notes"', "ArrowRight", "'n'", "show-notes", 'data-section="hook"'):
            self.assertIn(needle, page)
        self.assertIn("[<a href=\"#ref-1\">1</a>]", page)
        self.assertNotRegex(page, r"\[E\d+")

    def test_html_deck_escapes_model_text(self):
        slides = json.loads(deck_json())["slides"]
        slides[0].update(title="<script>x</script>", notes="<img src=x>", section='"><b>')
        slides[0]["bullets"] = ["<svg onload=1> [E1]"]
        page = (self.dir / render.render_deck_html(json.dumps({"slides": slides}), pack(), self.dir, "Deck", True, "ok")).read_text(encoding="utf-8")
        for bad in ("<script>x</script>", "<img src=x>", "<svg onload", "<b>"):
            self.assertNotIn(bad, page)

    def test_pptx_has_15_plus_references_with_notes(self):
        name = render.render_deck_pptx(deck_json(), pack(), self.dir, "Pres", True)
        prs = Presentation(str(self.dir / name))
        self.assertEqual(len(prs.slides), 16)
        self.assertEqual(prs.slides[0].notes_slide.notes_text_frame.text, "say 1")
        self.assertEqual(prs.slides[14].notes_slide.notes_text_frame.text, "say 15")
        self.assertIn("References", [s.text_frame.text for s in prs.slides[15].shapes if s.has_text_frame])

    def test_pptx_many_references_paginate(self):
        many = {f"E{i}": ev(title=f"T{i}", authors="Lee J", year="2024", doi=f"10.1/{i}", key=f"E{i}") for i in range(1, 30)}
        slides = json.loads(deck_json())["slides"]
        slides[0]["bullets"] = [" ".join(f"[E{i}]" for i in range(1, 30))]
        name = render.render_deck_pptx(json.dumps({"slides": slides}), many, self.dir, "Pres", True)
        self.assertEqual(len(Presentation(str(self.dir / name)).slides), 15 + 3)

    def test_storyboard_has_15_rows(self):
        name = render.render_storyboard(deck_json(), pack(), self.dir, "Storyboard")
        lines = (self.dir / name).read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(lines[0], "| Slide # & Section | Key Content | Visual Prompt | Layout Instruction |")
        rows = lines[2:]
        self.assertEqual(len(rows), 15)
        self.assertTrue(rows[0].startswith("| 1 · hook |"))
        self.assertIn("prompt 1 \\| pipe", rows[0])
        self.assertIn("[1]", rows[0])


def blog_text(chars=1300, disclaimer=True):
    text = "# 標題\n\n" + "這是一段說明 with term [E1]。" * (chars // 7)
    return text + ("\n\n本文不能取代專業人員的個別評估與諮詢。" if disclaimer else "")


class TestBlogChecks(unittest.TestCase):

    def run_blog(self, text, language="zh-TW"):
        with mock.patch.dict(CONFIG, {"blog_language": language}):
            return checks.STRUCTURE["blog"](text)

    def test_valid_zh_tw_passes(self):
        self.assertEqual(self.run_blog(blog_text()), [])

    def test_english_text_fails(self):
        problems = self.run_blog("# Title\n\n" + "plain english words here. " * 200 + "\nThis does not replace professional advice.")
        self.assertTrue(any("Traditional Chinese" in p for p in problems), problems)

    def test_too_short_fails(self):
        self.assertTrue(any("900" in p for p in self.run_blog(blog_text(chars=200))))

    def test_missing_disclaimer_fails(self):
        problems = self.run_blog(blog_text(disclaimer=False))
        self.assertTrue(any("不能取代專業人員的個別評估與諮詢" in p for p in problems), problems)

    def test_second_title_fails(self):
        self.assertTrue(any("exactly one" in p for p in self.run_blog(blog_text() + "\n# 另一個標題")))

    def test_english_blog_language_still_supported(self):
        self.assertEqual(self.run_blog("# T\n\n" + "word " * 400 + "this does not replace professional advice", "en"), [])


class TestBlogHouse(unittest.TestCase):

    META = {"slug": "kidney-cognition", "date": "2026-11-08", "category": "腎臟與認知", "subtitle": "副標 <b>x</b>", "tags": ["腎臟", "認知"],
            "evidence_kinds": {"PubMed": 5, "arXiv preprint": 2}, "years": {"2023": 1, "2024": 3, "2025": 3}}

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.files = render.render_blog_house(blog_text(), pack(), self.dir, "Blog_Post", True, "ok", dict(self.META))
        self.page = (self.dir / self.files["html"]).read_text(encoding="utf-8")

    def test_structure(self):
        p = self.page
        self.assertIn('<html lang="zh-TW">', p)
        self.assertGreaterEqual(p.count("<svg"), 2)
        self.assertGreaterEqual(p.count("<canvas"), 1)
        for needle in ("--bg:#0a0f1e", "--card:#111d3c", "--teal:#4dd9cf", "--purple:#8b5cf6", "--gold:#f4a261", "--text:#e8f4f8", "--sec:#8ba8c4",
                       "top-bar", "article-header", 'class="article-meta">2026 / 11 / 08 · 腎臟與認知', "article-title", "article-subtitle", render.BLOG_AUTHOR or "article-author",
                       '<section class="references">', "article-footer", "Noto+Sans+TC", "JetBrains+Mono", "Inter"):
            self.assertIn(needle, p)
        self.assertNotRegex(p, r"\[E\d+")
        self.assertIn('href="#ref-1"', p)

    def test_script_guards(self):
        p = self.page
        self.assertIn("devicePixelRatio", p)
        self.assertIn("prefers-reduced-motion", p)
        self.assertIn("Math.max(1,", p)  # divide-by-zero guards on peak and slot count

    def test_chart_data_comes_from_meta(self):
        self.assertIn('"PubMed": 5', self.page)
        self.assertIn('"2024": 3', self.page)
        svg_numbers = re.findall(r">(\d+)</text>", "".join(re.findall(r"<svg.*?</svg>", self.page, re.S)))
        self.assertTrue(set(svg_numbers) <= {"5", "2", "1", "3", "2023", "2024", "2025"}, svg_numbers)

    def test_empty_meta_still_valid(self):
        files = render.render_blog_house(blog_text(), {}, self.dir, "Empty", True, "ok", {})
        page = (self.dir / files["html"]).read_text(encoding="utf-8")
        self.assertGreaterEqual(page.count("<svg"), 2)
        self.assertIn("沒有可繪製的資料", page)

    def test_svg_is_well_formed(self):
        for svg in re.findall(r"<svg.*?</svg>", self.page, re.S):
            ET.fromstring(svg)

    def test_publish_files(self):
        publish = self.dir / self.files["publish_dir"]
        self.assertEqual(sorted(p.name for p in publish.iterdir()), ["kidney-cognition.html", "sitemap-entry.xml", "teach-card.html"])
        self.assertEqual((publish / "kidney-cognition.html").read_text(encoding="utf-8"), self.page)
        card = (publish / "teach-card.html").read_text(encoding="utf-8")
        self.assertIn('class="teach-card teach-card-link"', card)
        self.assertIn('href="blog/kidney-cognition.html"', card)
        self.assertIn("2026 / 11 / 08", card)
        self.assertNotIn("<b>x</b>", card)
        url = ET.fromstring('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + (publish / "sitemap-entry.xml").read_text(encoding="utf-8") + "</urlset>")
        self.assertEqual(len(url), 1)
        self.assertIn("/blog/kidney-cognition.html", ET.tostring(url, encoding="unicode"))

    def test_model_text_is_escaped(self):
        text = "# <script>x</script>\n\n<img src=x onerror=1> 內容 [E1]\n\n## 二\n\ntext\n\n不能取代專業人員的個別評估與諮詢"
        meta = {**self.META, "tags": ["<i>"], "evidence_kinds": {"</script><script>": 1}}
        page = (self.dir / render.render_blog_house(text, pack(), self.dir, "B2", False, "<u>n</u>", meta)["html"]).read_text(encoding="utf-8")
        for bad in ("<script>x</script>", "<img src=x", "<i>", "<u>n</u>"):
            self.assertNotIn(bad, page)
        self.assertEqual((page.count("<script"), page.count("</script")), (2, 2))  # only our data and code blocks
        self.assertIn("model-warning", page)

    def test_slug_is_sanitised(self):
        files = render.render_blog_house(blog_text(), pack(), self.dir, "B3", True, "ok", {"slug": "../../Evil Name!"})
        self.assertEqual(sorted(p.name for p in (self.dir / files["publish_dir"]).iterdir()), ["evil-name.html", "kidney-cognition.html", "sitemap-entry.xml", "teach-card.html"])

    def test_blog_notice_and_kind_labels_are_chinese(self):
        meta = {"evidence_kinds": {"NotebookLM answer (secondary)": 4, "PubMed": 2}}
        note = render.STRINGS["en"]["verified_note"]
        page = (self.dir / render.render_blog_house(blog_text(), pack(), self.dir, "B4", True, note, meta)["html"]).read_text(encoding="utf-8")
        self.assertNotIn("All citations come from", page)
        self.assertIn(render.STRINGS["zh-TW"]["verified_note"], page)
        self.assertIn("NotebookLM 二手摘要", page)
        self.assertNotIn("(seconda<", page)


class TestSpecs(unittest.TestCase):

    def test_deck_spec(self):
        text = specs.deck_spec("Traditional Chinese (Taiwan)")
        for needle in ("exactly 15 slides", "Clean Clinical", "Professional, Trustworthy, Precision", "at most 5", "slide deck", "Traditional Chinese (Taiwan)"):
            self.assertIn(needle, text)

    def test_blog_spec(self):
        text = specs.blog_spec("Traditional Chinese (Taiwan)")
        for needle in ("不能取代專業人員的個別評估與諮詢", "900-1800", "blog post", "fictional composite"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()


class TestSanitizerBypass(unittest.TestCase):
    """Wave-1 audit: entity-encoded and whitespace-split schemes must not survive."""

    def test_encoded_schemes_are_neutralised(self):
        from knowledge_agent.render import _safe_markdown
        for text in ("[a](&#x6A;avascript:alert(1))", "[a](java&#09;script:x)", "![a](javascript:x)", "[a](data:text/html,x)"):
            out = _safe_markdown(text).lower()
            self.assertNotIn("script:", out.replace("&#", ""), text)
            self.assertNotIn("data:", out, text)

    def test_safe_links_survive(self):
        from knowledge_agent.render import _safe_markdown
        self.assertIn('href="https://x.org"', _safe_markdown("[ok](https://x.org)"))
        self.assertIn('href="#ref-1"', _safe_markdown("[r](#ref-1)"))
