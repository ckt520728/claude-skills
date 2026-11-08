"""
Prompts for the two story-shaped deliverables. They are plain strings (no str.format placeholders),
so the JSON braces below are literal. The matching structure checks live in checks.py.
"""

from __future__ import annotations

DECK_SECTIONS = (("hook", 2), ("concepts", 5), ("evidence", 5), ("misconceptions", 1), ("conclusion", 2))
DECK_SLIDES = sum(n for _, n in DECK_SECTIONS)
BLOG_DISCLAIMER = "不能取代專業人員的個別評估與諮詢"


def deck_spec(language_name: str) -> str:
    """Scientific Storyteller: 15 slides in a fixed narrative arc, returned as one JSON object."""
    return f"""Create a slide deck in {language_name}, keeping standard English technical terms, as an expert scientific communicator and slide designer. Base it on the paper and evidence below.
Return only one JSON object: {{"slides":[{{"section":"hook","title":"one-takeaway title","bullets":["short fact [E1]"],"notes":"speaker notes","visual_prompt":"image-generation prompt","layout":"one short layout instruction"}}]}}
Follow this narrative arc with exactly 15 slides, in this order, using these exact lowercase "section" values:
1. "hook" x 2: why this matters (clinical relevance).
2. "concepts" x 5: the mechanisms or hypotheses.
3. "evidence" x 5: seminal experiments, trials or case studies.
4. "misconceptions" x 1: common pitfalls and counter-arguments.
5. "conclusion" x 2: summary and actionable next steps.
Readability: at most 5 short bullets per slide; one slide = one clear takeaway stated in the title; prefer diagrams over long text. Every bullet that states a fact or number cites its key inside that same bullet, like [E3].
"visual_prompt": a detailed image-generation prompt that combines the style native (magazine / data journalism), the skin "Clean Clinical" (white background, deep blue accents, high-resolution medical imagery) and the emotion keywords Professional, Trustworthy, Precision. Never put invented numbers into a visual prompt.
"layout": one short instruction, for example "Split screen: text on the left, diagram on the right".
"notes": two or three sentences a presenter can say aloud."""


def blog_spec(language_name: str) -> str:
    """House-style blog for general readers (Traditional Chinese for the lab blog)."""
    return f"""Write a blog post in {language_name} (Traditional Chinese as used in Taiwan, keeping standard English technical terms) for general readers, as Markdown. Base it on the paper and evidence below.
Use exactly one # title. Structure with ## headings:
1. An everyday opening scene that introduces the topic. It must be a fictional composite, not based on a real person.
2. Plain analogies first, then the technical terms they explain.
3. What the evidence shows, and where it is uncertain or still unproven (separate peer-reviewed work from preprints and registry entries).
4. Questions readers can ask their own clinician or care team.
5. A closing note that contains the exact sentence 「{BLOG_DISCLAIMER}」.
Length: 900-1800 Chinese characters. Cite facts with [E#] inside the same sentence and explain any number in plain language beside its citation. Do not write a references section; it is generated automatically. Output only the Markdown."""
