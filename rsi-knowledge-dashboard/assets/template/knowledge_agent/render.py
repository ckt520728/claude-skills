"""
Turns verified text into the five deliverables. Reference lists are built here from evidence
metadata, so the model cannot type a citation that was not collected.
"""

from __future__ import annotations

import html
import io
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

import markdown
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

from .checks import extract_json, number_value
from .config import LANGUAGE
from .sources import Evidence

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

    body = _link_citations(markdown.markdown(numbered, extensions=["tables", "sane_lists"]))
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


def _deck_data(text: str, evidence: Dict[str, Evidence]) -> Tuple[List[Dict], List[str]]:
    slides = json.loads(extract_json(text))["slides"]
    numbered, order = number_citations(json.dumps(slides, ensure_ascii=False), evidence)
    return json.loads(numbered), order


def render_deck_html(text: str, evidence: Dict[str, Evidence], out_dir: Path, stem: str, verified: bool, note: str) -> str:
    slides, order = _deck_data(text, evidence)
    extra = """
    .slide{display:none;min-height:100vh;padding:48px 8vw 90px}.slide.on{display:block}
    .slide h2{border:none;font-size:clamp(1.5rem,3.2vw,2.5rem);color:var(--teal);margin:0 0 22px}
    .slide li{font-size:clamp(1.02rem,1.75vw,1.45rem);margin-bottom:14px}.refs{font-size:.86rem;color:var(--sec);overflow-wrap:anywhere}.refs li{font-size:.88rem;margin-bottom:6px}
    .nav{position:fixed;left:0;right:0;bottom:0;display:flex;gap:10px;align-items:center;justify-content:center;padding:10px;background:#060c14;border-top:1px solid var(--line)}
    button{background:var(--card);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:8px 18px;font-size:1rem;cursor:pointer}button:focus-visible{outline:2px solid var(--teal)}
    """
    sections = []
    for slide in slides:
        bullets = "".join(f"<li>{_link_citations(html.escape(str(b)))}</li>" for b in slide.get("bullets", []))
        sections.append(f'<section class="slide"><h2>{html.escape(str(slide.get("title", "")))}</h2><ul>{bullets}</ul></section>')
    refs = "".join(f'<li id="ref-{i}">{html.escape(evidence[k].citation())}</li>' for i, k in enumerate(order, 1))
    sections.append(f'<section class="slide"><h2>References</h2>{_status_block(verified, note)}<ol class="refs">{refs}</ol></section>')
    script = """
    const s=[...document.querySelectorAll('.slide')];let i=0;const c=document.getElementById('count');
    function show(n){i=Math.max(0,Math.min(s.length-1,n));s.forEach((e,k)=>e.classList.toggle('on',k===i));c.textContent=(i+1)+' / '+s.length;}
    document.getElementById('prev').onclick=()=>show(i-1);document.getElementById('next').onclick=()=>show(i+1);
    addEventListener('keydown',e=>{if(e.key==='ArrowRight'||e.key===' '){e.preventDefault();show(i+1)}if(e.key==='ArrowLeft')show(i-1)});show(0);
    """
    body = "".join(sections) + '<nav class="nav"><button id="prev" aria-label="' + label("prev") + '">←</button><span id="count"></span><button id="next" aria-label="' + label("next") + '">→</button></nav>' + f"<script>{script}</script>"
    path = out_dir / f"{stem}.html"
    path.write_text(_page(stem, body, extra), encoding="utf-8")
    return path.name


def render_deck_pptx(text: str, evidence: Dict[str, Evidence], out_dir: Path, stem: str, verified: bool) -> str:
    slides, order = _deck_data(text, evidence)
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    navy, teal, white, grey = RGBColor(0x0A, 0x0F, 0x1E), RGBColor(0x4D, 0xD9, 0xCF), RGBColor(0xE8, 0xF4, 0xF8), RGBColor(0x8B, 0xA8, 0xC4)

    def add(title: str, lines: List[str], size: int, notes: str = "") -> None:
        slide = prs.slides.add_slide(blank)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = navy
        box = slide.shapes.add_textbox(Inches(0.6), Inches(0.35), Inches(12.1), Inches(1.1)).text_frame
        box.word_wrap = True
        box.text = title
        box.paragraphs[0].runs[0].font.size, box.paragraphs[0].runs[0].font.bold = Pt(30), True
        box.paragraphs[0].runs[0].font.color.rgb = teal
        body = slide.shapes.add_textbox(Inches(0.6), Inches(1.5), Inches(12.1), Inches(5.6)).text_frame
        body.word_wrap = True
        for index, line in enumerate(lines):
            para = body.paragraphs[0] if index == 0 else body.add_paragraph()
            run = para.add_run()
            run.text = line
            run.font.size, run.font.color.rgb = Pt(size), white
            para.space_after = Pt(9)
        if notes:
            slide.notes_slide.notes_text_frame.text = notes

    for item in slides:
        add(str(item.get("title", "")), [f"• {b}" for b in item.get("bullets", [])], 20, str(item.get("notes", "")))
    per_slide = 12
    entries = [f"{i}. {evidence[k].citation()}" for i, k in enumerate(order, 1)]
    for start in range(0, len(entries), per_slide):
        add("References" if verified else label("refs_review"), entries[start:start + per_slide], 11)

    buffer = io.BytesIO()
    prs.save(buffer)  # Serialize first: python-pptx random access fails on the G: virtual drive.
    path = out_dir / f"{stem}.pptx"
    path.write_bytes(buffer.getvalue())
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
