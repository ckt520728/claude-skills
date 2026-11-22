"""python-pptx helpers for a PPTX that links back to the published HTML deck and the companion sites.

Set HTML_URL to the *published* deck URL (publish the HTML first) and TOTAL to its final slide count.
"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

HTML_URL = "https://claude.ai/artifact/<id>"   # the published v2 deck, never the confidential v1
TOTAL = 31
CY, MG, WHITE = RGBColor(0x22, 0xD3, 0xEE), RGBColor(0xE8, 0x79, 0xF9), RGBColor(0xFF, 0xFF, 0xFF)

def new_deck():
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    return prs

def btn(slide, x, y, w, label, url, color=CY, h=0.42):
    """Rounded button whose whole shape is a hyperlink."""
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid(); s.fill.fore_color.rgb = color; s.line.fill.background()
    tf = s.text_frame; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = label; r.font.size = Pt(12); r.font.bold = True; r.font.color.rgb = WHITE
    s.click_action.hyperlink.address = url
    return s

def interactive_link(slide, n):
    """Bottom-right button that opens slide n of the HTML deck (the interactive version)."""
    assert 1 <= n <= TOTAL, n
    return btn(slide, 9.6, 7.0, 2.45, "▶ Open interactive slide", f"{HTML_URL}#{n}", MG)

def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text

def links_slide(slide, links, y=5.3):
    """links: [(label, url), ...]; the closing slide lists every companion site."""
    w = 12.0 / max(len(links), 1) - 0.15
    for i, (label, url) in enumerate(links):
        btn(slide, 0.65 + i * (w + 0.15), y, w, label, url)
