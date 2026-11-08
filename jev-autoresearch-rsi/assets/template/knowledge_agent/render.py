"""
Turns verified text into the five deliverables. Reference lists are built here from evidence
metadata, so the model cannot type a citation that was not collected.
"""

from __future__ import annotations

import datetime
import html
import io
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
from typing import Dict, List, Tuple

import markdown
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from .checks import extract_json, number_value
from .config import LANGUAGE
from .sources import Evidence
from .specs import BLOG_DISCLAIMER

STRINGS = {
    "zh-TW": {
        "verified": "AI 輔助產出，已通過自動查核：{note} 自動查核不等於專業審閱，發表或使用前仍須由專業人員確認。",
        "review": "<strong>需要人工審閱：</strong>未通過全部自動查核。{note}",
        "verified_note": "引用皆來自實際蒐集的文獻，數字皆可在其引用來源中找到。",
        "refs_review": "References（需要人工審閱）", "prev": "上一張", "next": "下一張",
    },
    "en": {
        "verified": "AI-assisted output that passed automated checks: {note} Automated checks are not expert review; a qualified person must confirm this before publication or use.",
        "review": "<strong>Needs human review:</strong> not all automated checks passed. {note}",
        "verified_note": "All citations come from collected sources, and all figures appear in the sources they cite.",
        "refs_review": "References (needs human review)", "prev": "Previous", "next": "Next",
    },
}


def label(key: str) -> str:
    return STRINGS.get(LANGUAGE, STRINGS["en"])[key]

CITE_GROUP = re.compile(r"\[(E\d+(?:\s*,\s*E\d+)*)\]")

CSS = """
:root{color-scheme:dark;--bg:#0a0f1e;--card:#111d3c;--teal:#4dd9cf;--purple:#8b5cf6;--gold:#f4a261;--text:#e8f4f8;--sec:#8ba8c4;--line:#22345c;--bad:#f87171}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:"Noto Sans TC","Microsoft JhengHei",Inter,-apple-system,"Segoe UI",sans-serif;line-height:1.75}
.article{max-width:860px;margin:0 auto;padding:40px 22px 70px}
h1{font-size:1.9rem;line-height:1.35;color:var(--teal)}h2{font-size:1.35rem;margin-top:2em;color:#fff;border-bottom:1px solid var(--line);padding-bottom:6px}h3{color:var(--gold)}
a{color:var(--teal)}sup a{text-decoration:none;font-size:.82em}
table{border-collapse:collapse;width:100%;display:block;overflow-x:auto;font-size:.92em}th,td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}th{background:var(--card)}
.status{border-radius:8px;padding:10px 14px;margin:14px 0 22px;font-size:.9rem;border:1px solid var(--teal);background:rgba(77,217,207,.08)}
.status.review{border-color:var(--bad);background:rgba(248,113,113,.1)}
.references{font-size:.86rem;color:var(--sec);overflow-wrap:anywhere}.references li{margin-bottom:7px}
@media(max-width:600px){.article{padding:22px 16px 50px}h1{font-size:1.5rem}}
"""


def number_citations(text: str, evidence: Dict[str, Evidence]) -> Tuple[str, List[str]]:
    """Replace [E#] keys with reader-facing numbers in order of first use."""
    order: List[str] = []

    def replace(match: "re.Match[str]") -> str:
        numbers = []
        for key in (k.strip() for k in match.group(1).split(",")):
            if key not in evidence:
                continue
            if key not in order:
                order.append(key)
            numbers.append(str(order.index(key) + 1))
        return f"[{', '.join(numbers)}]" if numbers else ""

    return CITE_GROUP.sub(replace, text), order


def references_md(order: List[str], evidence: Dict[str, Evidence]) -> str:
    return "\n".join(f"{i}. {evidence[k].citation()}" for i, k in enumerate(order, 1))


def _status_block(verified: bool, note: str) -> str:
    if verified:
        return f'<div class="status">{label("verified").format(note=html.escape(note))}</div>'
    return f'<div class="status review">{label("review").format(note=html.escape(note))}</div>'


def _page(title: str, body: str, extra_css: str = "") -> str:
    return (
        f'<!DOCTYPE html>\n<html lang="{LANGUAGE}"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">'
        f"<title>{html.escape(title)}</title><style>{CSS}{extra_css}</style></head><body>{body}</body></html>\n"
    )


def _link_citations(body_html: str) -> str:
    def replace(match: "re.Match[str]") -> str:
        links = ", ".join(f'<a href="#ref-{n.strip()}">{n.strip()}</a>' for n in match.group(1).split(","))
        return f"<sup>[{links}]</sup>"

    return re.sub(r"\[(\d+(?:\s*,\s*\d+)*)\](?!\()", replace, body_html)


def render_document(text: str, evidence: Dict[str, Evidence], out_dir: Path, stem: str, verified: bool, note: str) -> Dict[str, str]:
    """Academic paper and blog post: Markdown plus a styled HTML page."""
    numbered, order = number_citations(text, evidence)
    refs = references_md(order, evidence)
    md_path = out_dir / f"{stem}.md"
    md_path.write_text(f"{numbered.strip()}\n\n## References\n\n{refs}\n", encoding="utf-8")

    body = _link_citations(_safe_markdown(numbered))
    items = "".join(f'<li id="ref-{i}">{html.escape(evidence[k].citation())}</li>' for i, k in enumerate(order, 1))
    title_match = re.search(r"^#\s+(.+)$", text, re.M)
    title = CITE_GROUP.sub("", title_match.group(1)).strip() if title_match else stem
    if title_match:
        first_heading_end = body.find("</h1>")
        body = body[:first_heading_end + 5] + _status_block(verified, note) + body[first_heading_end + 5:]
    else:
        body = _status_block(verified, note) + body
    page = _page(title, f'<main class="article">{body}<section class="references"><h2>References</h2><ol>{items}</ol></section></main>')
    html_path = out_dir / f"{stem}.html"
    html_path.write_text(page, encoding="utf-8")
    return {"md": md_path.name, "html": html_path.name}


# ------------------------------------------------------------------ APA 7

_SEN_OPEN, _SEN_CLOSE = "\x01", "\x02"  # mark the journal title so Markdown / HTML can italicise it
_INITIALS = re.compile(r"^[A-Z]{1,4}$")


def _split_authors(text: str) -> Tuple[List[Tuple[str, str]], bool]:
    """Author string to [(surname, "J. K.")] plus whether the source said "et al"."""
    text = (text or "").strip()
    et_al = bool(re.search(r"(?:^|[\s,;])et\.?\s+al\.?\s*$", text, re.I))
    text = re.sub(r"[,;\s]*et\.?\s+al\.?\s*$", "", text, flags=re.I).strip().rstrip(".").strip()
    people: List[Tuple[str, str]] = []
    for part in re.split(r"\s*(?:;|,|\s&\s|\sand\s)\s*", text):
        tokens = part.replace(".", " ").split()
        if not tokens:
            continue
        if len(tokens) == 1:
            people.append((tokens[0], ""))
        elif _INITIALS.match(tokens[-1]):  # PubMed style: "Lee JK"
            people.append((" ".join(tokens[:-1]), " ".join(f"{c}." for c in tokens[-1])))
        else:  # full name: "Yann LeCun"
            given = " ".join("-".join(f"{p[0].upper()}." for p in word.split("-") if p) for word in tokens[:-1])
            people.append((tokens[-1], given))
    return people, et_al


def _year(e: Evidence) -> str:
    match = re.search(r"(?:19|20)\d{2}", e.year or "")
    return match.group(0) if match else "n.d."


def _is_registry(e: Evidence) -> bool:
    return "clinicaltrials" in e.kind.lower() or bool(e.nct_id and not e.doi)


def _link(e: Evidence) -> str:
    doi = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", (e.doi or "").strip(), flags=re.I)
    if e.arxiv_id and (e.kind.lower().startswith("arxiv") or not doi):
        return f"https://arxiv.org/abs/{e.arxiv_id}"
    if doi:
        return f"https://doi.org/{doi}"
    if e.nct_id and _is_registry(e):
        return f"https://clinicaltrials.gov/study/{e.nct_id}"
    if e.pmid:
        return f"https://pubmed.ncbi.nlm.nih.gov/{e.pmid}/"
    return e.url or ""


def _sentence(text: str) -> str:
    text = text.strip()
    return text if not text or text[-1] in ".?!" else text + "."


def _apa_names(people: List[Tuple[str, str]], et_al: bool) -> str:
    names = [f"{s}, {i}" if i else s for s, i in people]
    if et_al:
        return ", ".join(names) + ", et al."
    if len(names) == 1:
        return names[0]
    if len(names) > 20:
        return ", ".join(names[:19]) + ", . . . " + names[-1]
    if len(names) == 2:
        return f"{names[0]}, & {names[1]}"
    return ", ".join(names[:-1]) + f", & {names[-1]}"


def _apa(e: Evidence, suffix: str = "") -> str:
    people, et_al = _split_authors(e.authors)
    year = f"({_year(e)}{suffix})."
    title = _sentence(e.title)
    head = f"{_apa_names(people, et_al)} {year} {title}" if people else f"{title} {year}"
    parts = [head]
    link = _link(e)
    if e.arxiv_id and link.startswith("https://arxiv.org"):
        parts.append("arXiv.")
    elif _is_registry(e):
        parts.append("ClinicalTrials.gov.")
    elif e.journal.strip():
        parts.append(f"{_SEN_OPEN}{_sentence(e.journal)}{_SEN_CLOSE}")
    if link:
        parts.append(link)
    return " ".join(parts)


def apa_reference(e: Evidence, suffix: str = "") -> str:
    """APA 7 reference-list entry in plain text, built only from the evidence metadata."""
    return _apa(e, suffix).replace(_SEN_OPEN, "").replace(_SEN_CLOSE, "")


def apa_intext(e: Evidence, suffix: str = "") -> str:
    people, et_al = _split_authors(e.authors)
    year = f"{_year(e)}{suffix}"
    if people:
        surnames = [s for s, _ in people]
        if et_al or len(surnames) >= 3:
            who = f"{surnames[0]} et al."
        elif len(surnames) == 2:
            who = f"{surnames[0]} & {surnames[1]}"
        else:
            who = surnames[0]
    elif _is_registry(e):
        who = "ClinicalTrials.gov"
    else:
        who = '"' + " ".join(e.title.replace('"', "").split()[:4]) + '"'
    return f"{who}, {year}"


def _sort_key(e: Evidence) -> Tuple[str, str, str]:
    people, _ = _split_authors(e.authors)
    return ((people[0][0] if people else e.title).casefold(), _year(e), e.title.casefold())


def _apa_prepare(text: str, evidence: Dict[str, Evidence]) -> Tuple[str, List[str], Dict[str, str]]:
    """Text with APA in-text citations, cited keys (alphabetical by first author), a/b suffixes for same author-year pairs."""
    used: List[str] = []
    for match in CITE_GROUP.finditer(text):
        for key in (k.strip() for k in match.group(1).split(",")):
            if key in evidence and key not in used:
                used.append(key)
    ordered = sorted(used, key=lambda k: _sort_key(evidence[k]))
    groups: Dict[str, List[str]] = {}
    for key in ordered:
        groups.setdefault(apa_intext(evidence[key]), []).append(key)
    suffixes = {k: "abcdefghijklmnopqrstuvwxyz"[i % 26] for keys in groups.values() if len(keys) > 1 for i, k in enumerate(keys)}

    def replace(match: "re.Match[str]") -> str:
        labels: List[str] = []
        for key in (k.strip() for k in match.group(1).split(",")):
            if key in evidence:
                item = apa_intext(evidence[key], suffixes.get(key, ""))
                if item not in labels:
                    labels.append(item)
        return f"({'; '.join(labels)})" if labels else ""

    def spaced(match: "re.Match[str]") -> str:
        replacement = replace(match)
        return f" {replacement}" if replacement else ""

    body = re.sub(r"[ \t]*" + CITE_GROUP.pattern, spaced, text)
    body = re.sub(r"[ \t]+([。，、；,.;])", r"\1", body)
    return body, ordered, suffixes


def _safe_markdown(text: str) -> str:
    """Markdown to HTML where raw HTML in the model's text is shown as text, not executed."""
    out = markdown.markdown(text.replace("<", "&lt;"), extensions=["tables", "sane_lists"])
    return _safe_urls(out)


_URL_ATTR = re.compile(r'\b(href|src)\s*=\s*"([^"]*)"', re.I)


def _safe_urls(markup: str) -> str:
    """Allow-list link schemes after decoding entities and removing whitespace/control characters."""
    def check(match: "re.Match[str]") -> str:
        decoded = re.sub(r"[\x00-\x20\x7f]+", "", html.unescape(match.group(2))).lower()
        scheme = re.match(r"^([a-z][a-z0-9+.-]*):", decoded)
        if scheme and scheme.group(1) not in ("http", "https", "mailto"):
            return f'{match.group(1)}="#"'
        return match.group(0)

    return _URL_ATTR.sub(check, markup)


def _ref_html(text: str) -> str:
    """Escaped reference text with italic journal and clickable URLs."""
    out = html.escape(text).replace(_SEN_OPEN, "<i>").replace(_SEN_CLOSE, "</i>")
    return re.sub(r"(https?://[^\s<]*[^\s<.,;])", r'<a href="\1">\1</a>', out)


APA_CSS = """
:root{color-scheme:light}
body{background:#fff;color:#111;font-family:"Times New Roman","Noto Serif TC",Georgia,serif;font-size:17px;line-height:1.8}
h1{color:#111;text-align:center;font-size:1.6rem}h2{color:#111;border:none;font-size:1.25rem;font-weight:700}h3{color:#111;font-style:italic}
a{color:#0b4f8a}th{background:#f1f1f1}th,td{border-color:#bbb}
.status{border-color:#0b4f8a;background:#eef5fb;color:#111}.status.review{border-color:#b00020;background:#fdecee}
.references{color:#111;font-size:.95rem}.references ol{list-style:none;padding:0}.references li{padding-left:2em;text-indent:-2em;margin-bottom:10px}
"""


def render_paper_apa(text: str, evidence: Dict[str, Evidence], out_dir: Path, stem: str, verified: bool, note: str) -> Dict[str, str]:
    """Academic paper with APA 7 in-text citations and an alphabetical reference list."""
    body_md, ordered, suffixes = _apa_prepare(text, evidence)
    refs = [_apa(evidence[k], suffixes.get(k, "")) for k in ordered]
    md_refs = "\n\n".join(r.replace(_SEN_OPEN, "*").replace(_SEN_CLOSE, "*") for r in refs)
    md_path = out_dir / f"{stem}.md"
    md_path.write_text(f"{body_md.strip()}\n\n## References\n\n{md_refs}\n", encoding="utf-8")

    body = _safe_markdown(body_md)
    title_match = re.search(r"^#\s+(.+)$", body_md, re.M)
    title = title_match.group(1).strip() if title_match else stem
    end = body.find("</h1>")
    status = _status_block(verified, note)
    body = body[:end + 5] + status + body[end + 5:] if end >= 0 else status + body
    items = "".join(f"<li>{_ref_html(r)}</li>" for r in refs)
    page = _page(title, f'<main class="article">{body}<section class="references apa"><h2>References</h2><ol>{items}</ol></section></main>', APA_CSS)
    html_path = out_dir / f"{stem}.html"
    html_path.write_text(page, encoding="utf-8")
    return {"md": md_path.name, "html": html_path.name}


# ------------------------------------------------------------------ deck

SECTION_LABELS = {
    "zh-TW": {"hook": "開場", "concepts": "核心概念", "evidence": "證據", "misconceptions": "常見迷思", "conclusion": "結論"},
    "en": {"hook": "Hook", "concepts": "Core concepts", "evidence": "Evidence", "misconceptions": "Misconceptions", "conclusion": "Conclusion"},
}


def _section_label(section: str) -> str:
    key = str(section or "").strip().lower()
    return SECTION_LABELS.get(LANGUAGE, SECTION_LABELS["en"]).get(key, key.title())


def _deck_data(text: str, evidence: Dict[str, Evidence]) -> Tuple[List[Dict], List[str]]:
    slides = json.loads(extract_json(text))["slides"]
    numbered, order = number_citations(json.dumps(slides, ensure_ascii=False), evidence)
    return json.loads(numbered), order


DECK_CSS = """
:root{color-scheme:light;--bg:#fff;--ink:#12355B;--accent:#1F77B4;--muted:#5a6b7d;--line:#d5e2ee;--soft:#eef5fb}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:#1b2a3a;font-family:"Noto Sans TC","Microsoft JhengHei",Inter,-apple-system,"Segoe UI",sans-serif;line-height:1.6}
.progress{position:fixed;top:0;left:0;right:0;height:5px;background:var(--line);z-index:5}.progress div{height:100%;width:0;background:var(--accent)}
@media(prefers-reduced-motion:no-preference){.progress div{transition:width .25s}.slide.on{animation:fade .25s}}
@keyframes fade{from{opacity:0}to{opacity:1}}
.slide{display:none;min-height:100vh;padding:56px 8vw 96px;border-left:10px solid var(--accent)}.slide.on{display:block}
.chip{display:inline-block;background:var(--accent);color:#fff;font-size:.85rem;font-weight:600;letter-spacing:.04em;padding:3px 14px;border-radius:999px;margin-bottom:18px}
.slide[data-section=concepts] .chip{background:var(--ink)}.slide[data-section=evidence] .chip{background:#2a7f9e}.slide[data-section=misconceptions] .chip{background:#8a5a00}.slide[data-section=conclusion] .chip{background:#1d5c3a}
.slide h2{color:var(--ink);font-size:clamp(1.6rem,3.4vw,2.6rem);line-height:1.3;margin:0 0 24px}
.slide ul{padding-left:1.2em}.slide li{font-size:clamp(1.05rem,1.8vw,1.5rem);margin-bottom:14px}.slide li::marker{color:var(--accent)}
.notes{display:none;margin-top:26px;padding:12px 18px;border-left:4px solid var(--accent);background:var(--soft);color:var(--muted);font-size:1rem}
body.show-notes .slide.on .notes{display:block}
.refs{font-size:.88rem;color:var(--muted);overflow-wrap:anywhere}.refs li{font-size:.9rem;margin-bottom:6px}
.status{border:1px solid var(--accent);background:var(--soft);border-radius:8px;padding:10px 14px;margin:0 0 16px;font-size:.9rem}.status.review{border-color:#b00020;background:#fdecee}
sup a{text-decoration:none;color:var(--accent)}
.nav{position:fixed;left:0;right:0;bottom:0;display:flex;gap:10px;align-items:center;justify-content:center;padding:10px;background:#fff;border-top:1px solid var(--line)}
button{background:#fff;color:var(--ink);border:1px solid var(--accent);border-radius:6px;padding:8px 18px;font-size:1rem;cursor:pointer}button:hover{background:var(--soft)}button:focus-visible{outline:3px solid var(--accent)}
#count{min-width:5em;text-align:center;color:var(--muted)}
@media(max-width:600px){.slide{padding:40px 6vw 100px}}
"""
DECK_JS = """
const s=[...document.querySelectorAll('.slide')];let i=0;const c=document.getElementById('count'),bar=document.getElementById('bar');
function show(n){i=Math.max(0,Math.min(s.length-1,n));s.forEach((e,k)=>e.classList.toggle('on',k===i));c.textContent=(i+1)+' / '+s.length;bar.style.width=(100*(i+1)/Math.max(1,s.length))+'%';}
function notes(){document.body.classList.toggle('show-notes')}
document.getElementById('prev').onclick=()=>show(i-1);document.getElementById('next').onclick=()=>show(i+1);document.getElementById('notes').onclick=notes;
addEventListener('keydown',e=>{const k=e.key;if(k==='ArrowRight'||k==='PageDown'||k===' '){e.preventDefault();show(i+1)}else if(k==='ArrowLeft'||k==='PageUp')show(i-1);else if(k==='Home')show(0);else if(k==='End')show(s.length-1);else if(k==='n'||k==='N')notes()});
document.addEventListener('click',e=>{if(e.target.closest('button,a,aside,.nav'))return;show(i+(e.clientX<innerWidth*.2?-1:1))});
show(0);
"""


def render_deck_html(text: str, evidence: Dict[str, Evidence], out_dir: Path, stem: str, verified: bool, note: str) -> str:
    slides, order = _deck_data(text, evidence)
    esc = html.escape
    sections = []
    for number, slide in enumerate(slides, 1):
        section = str(slide.get("section", "")).strip().lower()
        bullets = "".join(f"<li>{_link_citations(esc(str(b)))}</li>" for b in slide.get("bullets", []))
        notes = f'<aside class="notes">{esc(str(slide["notes"]))}</aside>' if slide.get("notes") else ""
        chip = f'<div class="chip">{esc(_section_label(section))}</div>' if section else ""
        sections.append(f'<section class="slide" data-section="{esc(section)}" aria-label="{number}">{chip}<h2>{esc(str(slide.get("title", "")))}</h2><ul>{bullets}</ul>{notes}</section>')
    refs = "".join(f'<li id="ref-{i}">{_ref_html(apa_reference(evidence[k]))}</li>' for i, k in enumerate(order, 1))
    sections.append(f'<section class="slide" data-section="references"><div class="chip">References</div><h2>References</h2>{_status_block(verified, note)}<ol class="refs">{refs}</ol></section>')
    body = (
        '<div class="progress" role="progressbar" aria-label="progress"><div id="bar"></div></div>' + "".join(sections)
        + f'<nav class="nav"><button id="prev" aria-label="{label("prev")}">←</button><span id="count" aria-live="polite"></span><button id="next" aria-label="{label("next")}">→</button>'
        + '<button id="notes" aria-label="Speaker notes (N)">Notes (N)</button></nav>' + f"<script>{DECK_JS}</script>"
    )
    page = (
        f'<!DOCTYPE html>\n<html lang="{LANGUAGE}"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">'
        f"<title>{esc(stem)}</title><style>{DECK_CSS}</style></head><body>{body}</body></html>\n"
    )
    path = out_dir / f"{stem}.html"
    path.write_text(page, encoding="utf-8")
    return path.name


def render_deck_pptx(text: str, evidence: Dict[str, Evidence], out_dir: Path, stem: str, verified: bool, note: str = "") -> str:
    slides, order = _deck_data(text, evidence)
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    ink, accent, body_color, grey, white = RGBColor(0x12, 0x35, 0x5B), RGBColor(0x1F, 0x77, 0xB4), RGBColor(0x1B, 0x2A, 0x3A), RGBColor(0x5A, 0x6B, 0x7D), RGBColor(0xFF, 0xFF, 0xFF)
    per_slide = 12
    total = len(slides) + max(1, -(-len(order) // per_slide))

    def add(chip: str, title: str, lines: List[str], size: int, notes: str = "") -> None:
        slide = prs.slides.add_slide(blank)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = white
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.18), prs.slide_height)
        bar.fill.solid()
        bar.fill.fore_color.rgb = accent
        bar.line.fill.background()
        if chip:
            shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(0.4), Inches(2.6), Inches(0.38))
            shape.fill.solid()
            shape.fill.fore_color.rgb = accent
            shape.line.fill.background()
            frame = shape.text_frame
            frame.text = chip
            frame.paragraphs[0].alignment = PP_ALIGN.CENTER
            frame.paragraphs[0].runs[0].font.size, frame.paragraphs[0].runs[0].font.bold = Pt(13), True
            frame.paragraphs[0].runs[0].font.color.rgb = white
        box = slide.shapes.add_textbox(Inches(0.6), Inches(0.95), Inches(12.1), Inches(1.2)).text_frame
        box.word_wrap = True
        box.text = title
        run = box.paragraphs[0].runs[0]
        run.font.size, run.font.bold, run.font.color.rgb = Pt(32), True, ink
        body = slide.shapes.add_textbox(Inches(0.6), Inches(2.3), Inches(12.1), Inches(4.5)).text_frame
        body.word_wrap = True
        for index, line in enumerate(lines):
            para = body.paragraphs[0] if index == 0 else body.add_paragraph()
            run = para.add_run()
            run.text = line
            run.font.size, run.font.color.rgb = Pt(size), body_color
            para.space_after = Pt(10)
        footer = slide.shapes.add_textbox(Inches(11.4), Inches(6.95), Inches(1.6), Inches(0.35)).text_frame
        footer.text = f"{len(prs.slides)} / {total}"
        footer.paragraphs[0].alignment = PP_ALIGN.RIGHT
        footer.paragraphs[0].runs[0].font.size, footer.paragraphs[0].runs[0].font.color.rgb = Pt(11), grey
        if notes:
            slide.notes_slide.notes_text_frame.text = notes

    for item in slides:
        add(_section_label(item.get("section", "")), str(item.get("title", "")), [f"• {b}" for b in item.get("bullets", [])], 22, str(item.get("notes", "")))
    entries = [f"{i}. {apa_reference(evidence[k])}" for i, k in enumerate(order, 1)] or [""]
    for start in range(0, len(entries), per_slide):
        add("References", "References" if verified else label("refs_review"), entries[start:start + per_slide], 11)

    buffer = io.BytesIO()
    prs.save(buffer)  # Serialize first: python-pptx random access fails on the G: virtual drive.
    path = out_dir / f"{stem}.pptx"
    path.write_bytes(buffer.getvalue())
    return path.name


def _cell(text: str) -> str:
    return " ".join(str(text or "").split()).replace("|", "\\|") or "—"


def render_storyboard(text: str, evidence: Dict[str, Evidence], out_dir: Path, stem: str) -> str:
    """Markdown storyboard table: one row per slide, in the Scientific Storyteller column layout."""
    slides, _ = _deck_data(text, evidence)
    rows = ["| Slide # & Section | Key Content | Visual Prompt | Layout Instruction |", "| --- | --- | --- | --- |"]
    for number, slide in enumerate(slides, 1):
        content = "<br>".join("• " + _cell(b) for b in slide.get("bullets", []))
        rows.append(f"| {number} · {_cell(slide.get('section', ''))} | **{_cell(slide.get('title', ''))}**<br>{content} | {_cell(slide.get('visual_prompt', ''))} | {_cell(slide.get('layout', ''))} |")
    path = out_dir / f"{stem}.md"
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path.name


def _wrap(text: str, width_px: float, size: int) -> List[str]:
    lines, current, used = [], "", 0.0
    for char in text:
        step = size if ord(char) > 0x2E7F else size * 0.56
        if used + step > width_px and current:
            lines.append(current.rstrip())
            current, used = "", 0.0
        current += char
        used += step
    if current.strip():
        lines.append(current.strip())
    return lines


def render_infographic(text: str, evidence: Dict[str, Evidence], out_dir: Path, stem: str, title: str, verified: bool, note: str) -> Dict[str, str]:
    data = json.loads(extract_json(text))
    numbered, order = number_citations(json.dumps(data, ensure_ascii=False), evidence)
    data = json.loads(numbered)
    esc = html.escape
    width, panel_w, panel_h, gap, top = 1200, 570, 610, 20, 150
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 2160" width="{width}" height="2160" font-family="Noto Sans TC, Microsoft JhengHei, Inter, sans-serif">',
        f'<rect width="{width}" height="2160" fill="#0a0f1e"/>',
    ]
    for line_no, line in enumerate(_wrap(str(data.get("title") or title), 1120, 38)[:2]):
        parts.append(f'<text x="40" y="{62 + line_no * 46}" fill="#4dd9cf" font-size="38" font-weight="700">{esc(line)}</text>')
    for index, panel in enumerate(data["panels"][:6]):
        x, y = 20 + (index % 2) * (panel_w + gap), top + (index // 2) * (panel_h + gap)
        parts.append(f'<rect x="{x}" y="{y}" width="{panel_w}" height="{panel_h}" rx="14" fill="#111d3c" stroke="#22345c"/>')
        cursor = y + 42
        for line in _wrap(f"{index + 1}. {panel.get('title', '')}", panel_w - 40, 24)[:2]:
            parts.append(f'<text x="{x + 20}" y="{cursor}" fill="#f4a261" font-size="24" font-weight="700">{esc(line)}</text>')
            cursor += 32
        stat = panel.get("stat") or {}
        if stat.get("value"):
            cursor += 26
            parts.append(f'<text x="{x + 20}" y="{cursor}" fill="#4dd9cf" font-size="42" font-weight="700">{esc(str(stat["value"]))}</text>')
            cursor += 28
            for line in _wrap(str(stat.get("label", "")), panel_w - 40, 19)[:2]:
                parts.append(f'<text x="{x + 20}" y="{cursor}" fill="#8ba8c4" font-size="19">{esc(line)}</text>')
                cursor += 26
        cursor += 12
        bars = [{**b, "value": number_value(b.get("value"))} for b in (panel.get("chart") or {}).get("bars", []) if number_value(b.get("value")) is not None][:5]
        for point in panel.get("points", [])[:5 if not bars else 3]:
            for number, line in enumerate(_wrap(str(point), panel_w - 62, 22)[:4]):
                prefix = "• " if number == 0 else "  "
                parts.append(f'<text x="{x + 20}" y="{cursor}" fill="#e8f4f8" font-size="22" xml:space="preserve">{esc(prefix + line)}</text>')
                cursor += 31
            cursor += 9
        if bars:
            chart = panel["chart"]
            peak = max(abs(b["value"]) for b in bars) or 1
            cursor += 6
            parts.append(f'<text x="{x + 20}" y="{cursor}" fill="#8ba8c4" font-size="15">{esc(str(chart.get("title", "")))}</text>')
            cursor += 12
            bottom = y + panel_h - 14
            row = min(34, (bottom - cursor) / len(bars))
            for bar in bars:
                length = (panel_w - 300) * abs(bar["value"]) / peak
                parts.append(f'<text x="{x + 20}" y="{cursor + row * .62:.0f}" fill="#e8f4f8" font-size="14">{esc(str(bar.get("label", ""))[:17])}</text>')
                parts.append(f'<rect x="{x + 190}" y="{cursor + 4:.0f}" width="{length:.0f}" height="{max(8, row - 12):.0f}" rx="3" fill="#8b5cf6"/>')
                parts.append(f'<text x="{x + 196 + length:.0f}" y="{cursor + row * .62:.0f}" fill="#4dd9cf" font-size="14">{bar["value"]:g}{esc(str(chart.get("unit", "")))}</text>')
                cursor += row
    parts.append(f'<text x="40" y="2135" fill="#8ba8c4" font-size="15">{esc("Numbers in brackets refer to the reference list in the viewer." + ("" if verified else " NEEDS REVIEW: not all automated checks passed."))}</text></svg>')
    svg = "\n".join(parts)
    svg_path = out_dir / f"{stem}.svg"
    svg_path.write_text(svg, encoding="utf-8")
    refs = "".join(f"<li>{esc(evidence[k].citation())}</li>" for k in order)
    viewer = _page(
        stem,
        f'<main class="article" style="max-width:1240px"><h1>{esc(str(data.get("title") or title))}</h1>{_status_block(verified, note)}'
        f'<div style="overflow-x:auto">{svg}</div><section class="references"><h2>References</h2><ol>{refs}</ol></section></main>',
    )
    viewer_path = out_dir / f"{stem}_Viewer.html"
    viewer_path.write_text(viewer, encoding="utf-8")
    return {"svg": svg_path.name, "html": viewer_path.name}


# ------------------------------------------------------------------ house-style blog

from .config import CONFIG as _CONFIG

_BLOG = _CONFIG.get("blog") or {}
# Site and author come from project.json "blog"; nothing personal is hard-coded.
SITE_URL = str(_BLOG.get("site_url") or "https://example.org").rstrip("/")
BLOG_AUTHOR = str(_BLOG.get("author") or "")
BLOG_AVATAR = str(_BLOG.get("avatar") or BLOG_AUTHOR[:1] or "·")
BLOG_AUTHOR_BIO = str(_BLOG.get("author_bio") or "")

BLOG_CSS = """
:root{
  --bg:#0a0f1e;--bg-primary:#0a0f1e;--card:#111d3c;--bg-card:#111d3c;--bg-card2:#162248;
  --teal:#4dd9cf;--teal-light:#7ee8e2;--purple:#8b5cf6;--purple-light:#a78bfa;--gold:#f4a261;
  --text:#e8f4f8;--sec:#8ba8c4;--text-sec:#8ba8c4;--text-dim:#4a6580;
  --border:rgba(77,217,207,0.15);--shadow:0 8px 32px rgba(0,0,0,0.45);--radius:12px;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Noto Sans TC','Inter',sans-serif;background:var(--bg);color:var(--text);line-height:1.9}
a{color:var(--teal);text-decoration:none}a:hover{color:var(--teal-light)}
.top-bar{position:sticky;top:0;z-index:100;background:rgba(10,15,30,0.92);backdrop-filter:blur(10px);border-bottom:1px solid var(--border);padding:14px 0}
.top-bar-inner{max-width:980px;margin:0 auto;padding:0 24px;display:flex;justify-content:space-between;align-items:center;gap:16px}
.back-link{color:var(--sec);font-size:0.9rem}
.top-bar-title{font-size:0.82rem;color:var(--text-dim);font-family:'JetBrains Mono',monospace}
.article{max-width:860px;margin:0 auto;padding:58px 24px 82px}
.article-header{margin-bottom:44px;padding-bottom:34px;border-bottom:1px solid var(--border)}
.article-meta{color:var(--teal);font-size:0.85rem;font-family:'JetBrains Mono',monospace;margin-bottom:14px}
.article-title{font-size:2.25rem;line-height:1.35;margin-bottom:18px;background:linear-gradient(135deg,var(--text),var(--teal-light));-webkit-background-clip:text;background-clip:text;color:transparent}
.article-subtitle{color:var(--sec);font-size:1.04rem}
.article-author{margin-top:24px;padding-top:20px;border-top:1px solid var(--border);display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.author-avatar{width:48px;height:48px;border-radius:50%;background:linear-gradient(135deg,#2a9d8f,var(--purple));display:flex;align-items:center;justify-content:center;font-weight:700;font-size:1.1rem}
.author-info{color:var(--sec);font-size:0.88rem;line-height:1.65}.author-info strong{color:var(--text)}
.article-tags{margin-top:18px;display:flex;flex-wrap:wrap;gap:8px}
.tag{font-size:0.72rem;padding:3px 12px;border-radius:20px;background:rgba(77,217,207,0.08);color:var(--teal);border:1px solid rgba(77,217,207,0.2)}
h2{font-size:1.55rem;margin:54px 0 20px;padding-bottom:10px;border-bottom:2px solid var(--teal);display:inline-block}
h3{font-size:1.18rem;color:var(--teal-light);margin:34px 0 14px}
p{color:var(--sec);margin:0 0 20px}p strong,li strong{color:var(--text)}em{color:var(--teal-light)}
ul,ol{color:var(--sec);padding-left:24px;margin:0 0 24px}li{margin-bottom:10px}li::marker{color:var(--teal)}
sup a{font-size:.8em}
blockquote{margin:34px 0;padding:24px 28px;background:linear-gradient(135deg,rgba(77,217,207,0.06),rgba(139,92,246,0.06));border-left:4px solid var(--teal);border-radius:8px;color:var(--text)}
table{width:100%;border-collapse:collapse;background:var(--card);border-radius:var(--radius);overflow:hidden;font-size:0.92rem;display:block;overflow-x:auto}
th{text-align:left;color:var(--teal);background:rgba(77,217,207,0.1);padding:12px 14px;border-bottom:1px solid var(--border)}
td{padding:12px 14px;color:var(--sec);border-bottom:1px solid rgba(77,217,207,0.08);vertical-align:top}
.model-warning{border-left:4px solid var(--gold);background:rgba(244,162,97,.08);padding:14px 16px;color:var(--sec);border-radius:8px;margin:0 0 28px;font-size:.9rem}
.model-warning strong{color:var(--gold)}
.data-figures{margin:46px 0}
.data-figures figure{margin:0 0 30px;background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:18px;box-shadow:var(--shadow)}
.data-figures svg,.data-figures canvas{width:100%;height:auto;display:block}
.data-figures canvas{background:#08101f;border-radius:8px}
figcaption{margin-top:12px;color:var(--sec);font-size:0.85rem;text-align:center;line-height:1.7}
.control-row{display:flex;gap:12px;align-items:center;color:var(--sec);font-size:.85rem;margin-top:12px}
.control-row input[type=range]{flex:1;accent-color:var(--teal)}
.control-row output{color:var(--teal-light);font-family:'JetBrains Mono',monospace;min-width:11em;text-align:right}
.references{margin-top:60px;padding-top:34px;border-top:2px solid var(--teal)}
.references h2{border:none;margin-top:0;padding:0}
.references ol{list-style:none;counter-reset:ref;padding-left:0}
.references li{counter-increment:ref;position:relative;padding-left:42px;font-size:0.88rem;color:var(--sec);margin-bottom:14px;overflow-wrap:anywhere}
.references li::before{content:counter(ref);position:absolute;left:0;top:2px;width:26px;height:26px;border-radius:50%;background:rgba(77,217,207,0.12);color:var(--teal);display:flex;align-items:center;justify-content:center;font-family:'JetBrains Mono',monospace;font-size:0.75rem}
.article-footer{margin-top:54px;padding-top:28px;border-top:1px solid var(--border);color:var(--text-dim);font-size:0.88rem;text-align:center}
@media(max-width:640px){.article{padding:42px 18px 64px}.article-title{font-size:1.65rem}.top-bar-title{display:none}.control-row{flex-wrap:wrap}.control-row output{text-align:left}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
"""

BLOG_JS = """
(function(){
  var node=document.getElementById('blog-data');if(!node)return;
  var data=JSON.parse(node.textContent);
  var canvas=document.getElementById('year-canvas');if(!canvas||!canvas.getContext)return;
  var ctx=canvas.getContext('2d'),slider=document.getElementById('year-slider'),out=document.getElementById('year-out');
  var reduce=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var years=Object.keys(data.years||{}).map(Number).filter(function(y){return isFinite(y)}).sort(function(a,b){return a-b});
  var counts=years.map(function(y){return Number(data.years[y])||0});
  var grow=reduce?1:0,selected=years.length?years[years.length-1]:0;
  function setup(){
    var dpr=window.devicePixelRatio||1,w=Math.max(1,canvas.clientWidth||720),h=Math.round(w*0.45);
    canvas.style.height=h+'px';canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
    ctx.setTransform(dpr,0,0,dpr,0,0);return {w:w,h:h};
  }
  function draw(){
    var s=setup(),w=s.w,h=s.h,pad=34,base=h-34;
    ctx.clearRect(0,0,w,h);ctx.font='12px "JetBrains Mono",monospace';ctx.textAlign='center';
    if(!years.length){ctx.fillStyle='#8ba8c4';ctx.fillText(data.empty||'No data',w/2,h/2);return;}
    var peak=Math.max(1,Math.max.apply(null,counts)),slot=(w-pad*2)/Math.max(1,years.length),bw=Math.max(2,Math.min(48,slot*0.62)),total=0;
    ctx.strokeStyle='rgba(139,168,196,.35)';ctx.beginPath();ctx.moveTo(pad,base);ctx.lineTo(w-pad,base);ctx.stroke();
    for(var i=0;i<years.length;i++){
      var x=pad+slot*i+slot/2,bh=(base-pad)*(counts[i]/peak)*grow,on=years[i]<=selected;
      if(on)total+=counts[i];
      ctx.fillStyle=on?'#4dd9cf':'rgba(139,92,246,.35)';ctx.fillRect(x-bw/2,base-bh,bw,bh);
      ctx.fillStyle='#e8f4f8';if(counts[i]>0&&grow>0.95)ctx.fillText(String(counts[i]),x,base-bh-6);
      if(years.length<=14||i%Math.ceil(years.length/14)===0){ctx.fillStyle='#8ba8c4';ctx.fillText(String(years[i]),x,base+18);}
    }
    if(out)out.textContent=data.label.replace('{year}',selected).replace('{total}',total);
  }
  function animate(){grow=Math.min(1,grow+0.06);draw();if(grow<1)requestAnimationFrame(animate);}
  if(slider){
    if(years.length){slider.min=years[0];slider.max=years[years.length-1];slider.step=1;slider.value=selected;}else{slider.disabled=true;}
    slider.addEventListener('input',function(){selected=Number(slider.value);draw();});
  }
  window.addEventListener('resize',draw);
  if(reduce){draw();}else{animate();}
})();
"""


def _blog_date(value: str) -> Tuple[str, str, str]:
    match = re.match(r"\s*(\d{4})\D+(\d{1,2})\D+(\d{1,2})", str(value or ""))
    if match:
        return match.group(1), match.group(2).zfill(2), match.group(3).zfill(2)
    today = datetime.date.today()
    return f"{today.year:04d}", f"{today.month:02d}", f"{today.day:02d}"


def _blog_slug(meta: Dict, stem: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(meta.get("slug") or stem).lower()).strip("-")
    return slug or "blog-post"


def _count_map(raw) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for key, value in (raw or {}).items():
        try:
            count = int(value)
        except (TypeError, ValueError):
            continue
        if count > 0:
            out[str(key)] = count
    return out


ZH_KINDS = {
    "PubMed": "PubMed 期刊文獻",
    "arXiv preprint": "arXiv 預印本",
    "ClinicalTrials.gov": "ClinicalTrials.gov 登錄",
    "NotebookLM answer (secondary)": "NotebookLM 二手摘要",
    "Saved answer (secondary)": "已存答案（二手）",
    "Reference PDF (no registered record)": "參考 PDF（無登錄紀錄）",
}


def _zh_kind(kind: str) -> str:
    name = ZH_KINDS.get(kind, kind)
    return name if len(name) <= 22 else name[:21] + "…"


def _svg_bars(title: str, rows: List[Tuple[str, int]], empty: str) -> str:
    """Horizontal bar chart as inline SVG; every bar length comes from the counts."""
    esc = html.escape
    height = 60 + 36 * max(1, len(rows))
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 {height}" role="img" aria-labelledby="svg-kinds-t" font-family="Noto Sans TC, Inter, sans-serif">',
             f'<title id="svg-kinds-t">{esc(title)}</title>', f'<text x="16" y="28" fill="#4dd9cf" font-size="16" font-weight="700">{esc(title)}</text>']
    if not rows:
        parts.append(f'<text x="16" y="70" fill="#8ba8c4" font-size="14">{esc(empty)}</text>')
    peak = max([count for _, count in rows] + [1])
    for index, (name, count) in enumerate(rows):
        y = 48 + index * 36
        length = 330 * count / peak
        parts.append(f'<text x="16" y="{y + 18}" fill="#e8f4f8" font-size="13">{esc(name[:26])}</text>')
        parts.append(f'<rect x="220" y="{y}" width="{length:.1f}" height="24" rx="4" fill="#8b5cf6"/>')
        parts.append(f'<text x="{228 + length:.1f}" y="{y + 17}" fill="#4dd9cf" font-size="13">{count}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _svg_years(title: str, years: Dict[str, int], empty: str) -> str:
    """Column chart of evidence per publication year as inline SVG."""
    esc = html.escape
    rows = sorted((k, v) for k, v in years.items() if re.fullmatch(r"\d{4}", k))
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 300" role="img" aria-labelledby="svg-years-t" font-family="Noto Sans TC, Inter, sans-serif">',
             f'<title id="svg-years-t">{esc(title)}</title>', f'<text x="16" y="28" fill="#4dd9cf" font-size="16" font-weight="700">{esc(title)}</text>',
             '<line x1="30" y1="250" x2="620" y2="250" stroke="#8ba8c4" stroke-opacity=".4"/>']
    if not rows:
        parts.append(f'<text x="30" y="140" fill="#8ba8c4" font-size="14">{esc(empty)}</text>')
    peak = max([v for _, v in rows] + [1])
    slot = 590 / max(1, len(rows))
    width = max(3.0, min(46.0, slot * 0.62))
    step = max(1, -(-len(rows) // 12))
    for index, (year, count) in enumerate(rows):
        x = 30 + slot * index + slot / 2
        bar = 190 * count / peak
        parts.append(f'<rect x="{x - width / 2:.1f}" y="{250 - bar:.1f}" width="{width:.1f}" height="{bar:.1f}" rx="3" fill="#4dd9cf"/>')
        parts.append(f'<text x="{x:.1f}" y="{244 - bar:.1f}" fill="#e8f4f8" font-size="12" text-anchor="middle">{count}</text>')
        if index % step == 0:
            parts.append(f'<text x="{x:.1f}" y="270" fill="#8ba8c4" font-size="12" text-anchor="middle">{esc(year)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _teach_card(slug: str, title: str, subtitle: str, category: str, tags: List[str], date: Tuple[str, str, str]) -> str:
    esc = html.escape
    venue = " · ".join(tags[:5])
    return (
        f'<a href="blog/{esc(slug)}.html" class="teach-card teach-card-link" data-aos="fade-up" style="grid-column:1/-1;text-decoration:none;color:inherit;display:block;">\n'
        f'  <div class="teach-date">{date[0]} / {date[1]} / {date[2]}</div>\n'
        f'  <span class="teach-badge">{esc(category)}</span>\n'
        f'  <span class="teach-badge purple" style="margin-left:6px;">Blog 專文 · 互動圖表</span>\n'
        f'  <div class="teach-title" style="font-size:1.05rem;margin-top:4px;">{esc(title)}</div>\n'
        f'  <div class="teach-venue" style="margin-top:8px;"><i class="fas fa-map-pin" style="color:var(--teal);margin-right:5px;"></i>{esc(venue)}</div>\n'
        f'  <div style="margin-top:14px;font-size:0.85rem;color:var(--text-sec);line-height:1.75;">\n    {esc(subtitle)}\n  </div>\n'
        f'  <div style="margin-top:14px;font-size:0.85rem;color:var(--teal);font-weight:500;">\n'
        f'    閱讀完整專文 <i class="fas fa-arrow-right" style="margin-left:4px;font-size:0.78rem;"></i>\n  </div>\n</a>\n'
    )


def render_blog_house(text: str, evidence: Dict[str, Evidence], out_dir: Path, stem: str, verified: bool, note: str, meta: Dict) -> Dict[str, str]:
    """Self-contained zh-TW page in the kidney-cognition-lab house style, plus blog_publish/ snippets."""
    esc = html.escape
    zh = STRINGS["zh-TW"]
    meta = meta or {}
    numbered, order = number_citations(text, evidence)
    title_match = re.search(r"^#\s+(.+)$", numbered, re.M)
    title = title_match.group(1).strip() if title_match else stem
    body_md = re.sub(r"^#\s+.+\n?", "", numbered, count=1, flags=re.M)
    refs = [apa_reference(evidence[k]) for k in order]
    refs_md = "\n".join(f"{i}. {r}" for i, r in enumerate(refs, 1))
    md_path = out_dir / f"{stem}.md"
    md_path.write_text(f"{numbered.strip()}\n\n## 參考資料\n\n{refs_md}\n", encoding="utf-8")

    slug = _blog_slug(meta, stem)
    date = _blog_date(meta.get("date", ""))
    category = str(meta.get("category") or "科普專文")
    subtitle = str(meta.get("subtitle") or f"依據 {len(order)} 篇已蒐集的文獻整理")
    tags = [str(t) for t in (meta.get("tags") or [])][:8]
    kinds = _count_map(meta.get("evidence_kinds"))
    years = _count_map(meta.get("years"))
    kind_rows = [(_zh_kind(k), v) for k, v in sorted(kinds.items(), key=lambda kv: (-kv[1], kv[0]))[:8]]
    if verified and note == STRINGS["en"]["verified_note"]:
        note = zh["verified_note"]  # the engine's note is English; the blog is zh-TW
    empty = "沒有可繪製的資料"
    kinds_title, years_title = "證據來源類型", "各年份證據數量"

    body = _link_citations(_safe_markdown(body_md))
    figures = (
        '<section class="data-figures" aria-label="本次研究蒐集的證據概況">'
        f'<figure>{_svg_bars(kinds_title, kind_rows, empty)}<figcaption>本次蒐集的證據依來源類型計數；長度與數字皆來自實際蒐集的文獻清單。</figcaption></figure>'
        f'<figure>{_svg_years(years_title, years, empty)}<figcaption>各出版年份的證據數量（靜態版）。</figcaption></figure>'
        f'<figure><canvas id="year-canvas" width="720" height="324" role="img" aria-label="{esc(years_title)}，可用滑桿選擇年份"></canvas>'
        '<div class="control-row"><label for="year-slider">截止年份</label><input type="range" id="year-slider" min="0" max="0" value="0"><output id="year-out" for="year-slider" aria-live="polite"></output></div>'
        '<figcaption>互動版：拖曳滑桿，青色為截止年份以前的證據，累計數即時計算。</figcaption></figure></section>'
    )
    splits = [m.start() for m in re.finditer(r"<h2", body)]
    body = body[:splits[1]] + figures + body[splits[1]:] if len(splits) >= 2 else body + figures

    status = (
        f'<div class="model-warning">{esc(zh["verified"].format(note=note))}</div>' if verified
        else f'<div class="model-warning">{zh["review"].format(note=esc(note))}</div>'
    )
    data = {"kinds": kinds, "years": years, "empty": empty, "label": "截至 {year} 年累計 {total} 筆證據"}
    data_json = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    ref_items = "".join(f'<li id="ref-{i}">{_ref_html(r)}</li>' for i, r in enumerate(refs, 1))
    tag_html = "".join(f'<span class="tag">{esc(t)}</span>' for t in tags)
    page = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="{esc(subtitle, quote=True)}">
<title>{esc(title)}{(" | " + esc(BLOG_AUTHOR)) if BLOG_AUTHOR else ""}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700&family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{BLOG_CSS}</style>
</head>
<body>
<div class="top-bar"><div class="top-bar-inner"><a href="../index.html#teaching" class="back-link">← 返回首頁</a><div class="top-bar-title">{esc(category)}</div></div></div>
<article class="article">
<header class="article-header">
  <div class="article-meta">{date[0]} / {date[1]} / {date[2]} · {esc(category)}</div>
  <h1 class="article-title">{esc(title)}</h1>
  <p class="article-subtitle">{esc(subtitle)}</p>
  <div class="article-author"><div class="author-avatar">{esc(BLOG_AVATAR)}</div><div class="author-info"><strong>{esc(BLOG_AUTHOR)}</strong><br>{(esc(BLOG_AUTHOR_BIO) + " · ") if BLOG_AUTHOR_BIO else ""}依據 {len(order)} 篇已蒐集文獻整理</div></div>
  <div class="article-tags">{tag_html}</div>
</header>
{status}
{body}
<section class="references">
<h2>參考資料</h2>
<ol>{ref_items}</ol>
</section>
<footer class="article-footer">
  本文為科普改寫，比喻僅為輔助理解，數值與結論以原始文獻為準；{BLOG_DISCLAIMER}。<br>
  <a href="../index.html#teaching">← 回到演講教學列表</a>
</footer>
</article>
<script type="application/json" id="blog-data">{data_json}</script>
<script>{BLOG_JS}</script>
</body>
</html>
"""
    html_path = out_dir / f"{stem}.html"
    html_path.write_text(page, encoding="utf-8")

    publish = out_dir / "blog_publish"
    publish.mkdir(parents=True, exist_ok=True)
    (publish / f"{slug}.html").write_text(page, encoding="utf-8")
    (publish / "teach-card.html").write_text(_teach_card(slug, title, subtitle, category, tags, date), encoding="utf-8")
    (publish / "sitemap-entry.xml").write_text(
        "  <url>\n"
        f"    <loc>{xml_escape(SITE_URL)}/blog/{xml_escape(slug)}.html</loc>\n"
        f"    <lastmod>{date[0]}-{date[1]}-{date[2]}</lastmod>\n"
        "    <changefreq>monthly</changefreq>\n    <priority>0.9</priority>\n  </url>\n",
        encoding="utf-8",
    )
    return {"md": md_path.name, "html": html_path.name, "publish_dir": publish.name}
