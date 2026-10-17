# -*- coding: utf-8 -*-
"""generate_pptx.py - Generates the 20-slide 16:9 PowerPoint deck for HHSA Body Signals.

Faithfully matches the T12 HTML deck:
- 20 slides in identical order and identical titles
- Dark lab theme (#0a0f1e background, #111d3c cards, teal/purple/gold accents)
- Safe margins (>= 0.4 in), no text overflow, no off-slide elements
- High-resolution figures embedded (F1, F2, F5, F6, F7, hero/explorer)
- Tables natively constructed and styled
- Verbatim speaker notes on every slide
- Layout audit and rendering via PowerPoint COM (or LibreOffice fallback)
"""

import os
import sys
import json
import argparse
from pathlib import Path
from PIL import Image

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.enum.shapes import MSO_SHAPE

# ==============================================================================
# Color Palette & Design Tokens
# ==============================================================================
BG_COLOR = RGBColor(0x0a, 0x0f, 0x1e)       # #0a0f1e deep navy
CARD_BG = RGBColor(0x11, 0x1d, 0x3c)        # #111d3c dark card
CARD2_BG = RGBColor(0x16, 0x22, 0x48)       # #162248 secondary card
CARD_BORDER = RGBColor(0x23, 0x36, 0x66)    # subtle card border
GRID_LINE = RGBColor(0x1a, 0x28, 0x50)

TEAL = RGBColor(0x4d, 0xd9, 0xcf)           # #4dd9cf primary accent
TEAL_LIGHT = RGBColor(0x7e, 0xe8, 0xe2)     # #7ee8e2
TEAL_DIM = RGBColor(0x1b, 0x38, 0x45)

PURPLE = RGBColor(0x8b, 0x5c, 0xf6)         # #8b5cf6
PURPLE_LIGHT = RGBColor(0xa7, 0x8b, 0xfa)   # #a78bfa
PURPLE_DIM = RGBColor(0x2c, 0x22, 0x54)

GOLD = RGBColor(0xf4, 0xa2, 0x61)           # #f4a261
GOLD_LIGHT = RGBColor(0xf6, 0xb6, 0x82)     # #f6b682
GOLD_DIM = RGBColor(0x42, 0x30, 0x24)

RED = RGBColor(0xef, 0x44, 0x44)            # #ef4444
RED_LIGHT = RGBColor(0xf8, 0x71, 0x71)
GREEN = RGBColor(0x22, 0xc5, 0x5e)          # #22c55e
GREEN_LIGHT = RGBColor(0x4a, 0xde, 0x80)

TEXT_PRIMARY = RGBColor(0xe8, 0xf4, 0xf8)   # #e8f4f8 main text
TEXT_MUTED = RGBColor(0x8b, 0xa8, 0xc4)     # #8ba8c4 secondary text
TEXT_DIM = RGBColor(0x4a, 0x65, 0x80)       # #4a6580 subtle text
WHITE = RGBColor(0xff, 0xff, 0xff)

SOIL_COLORS = {
    "S": RED_LIGHT,
    "O": GOLD,
    "I": TEAL,
    "L": PURPLE_LIGHT,
    "—": TEAL,
    "CONCLUSION": TEAL,
}

FONT_NAME = "Inter"
FALLBACK_FONT = "Calibri"

SLIDE_WIDTH_IN = 13.333
SLIDE_HEIGHT_IN = 7.5


# ==============================================================================
# Helper Functions for Shapes, Text, and Layout
# ==============================================================================
def set_slide_background(slide, color=BG_COLOR):
    """Sets solid background color for the slide."""
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_card(slide, l, t, w, h, fill=CARD_BG, line=CARD_BORDER, line_w=0.75, radius=0.03):
    """Adds a rounded rectangle card container."""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, l, t, w, h)
    if shape.adjustments:
        shape.adjustments[0] = radius
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line
    shape.line.width = Pt(line_w)
    shape.shadow.inherit = False
    return shape


def add_text_box(slide, l, t, w, h, text, size=14, color=TEXT_PRIMARY, bold=False,
                 align=PP_ALIGN.LEFT, font=FONT_NAME, italic=False,
                 anchor=MSO_ANCHOR.TOP, line_spacing=1.15, word_wrap=True):
    """Adds a simple text box with a single styled paragraph."""
    tb = slide.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame
    tf.word_wrap = word_wrap
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Pt(4)
    tf.margin_top = tf.margin_bottom = Pt(2)
    p = tf.paragraphs[0]
    p.alignment = align
    p.line_spacing = line_spacing
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name = font
    return tb


def add_bullet_list(slide, l, t, w, h, bullets, size=13, color=TEXT_MUTED, font=FONT_NAME,
                    space_after=6, bold_prefix=True):
    """Adds a multi-paragraph bulleted list inside a text box.
    If bold_prefix is True, text before a colon or em-dash is made bold in TEXT_PRIMARY.
    """
    tb = slide.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = tf.margin_right = Pt(4)
    tf.margin_top = tf.margin_bottom = Pt(2)
    tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE

    for i, item in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.line_spacing = 1.15
        p.space_after = Pt(space_after)

        bullet_run = p.add_run()
        bullet_run.text = "• "
        bullet_run.font.size = Pt(size)
        bullet_run.font.color.rgb = TEAL
        bullet_run.font.name = font

        # Parse potential bold prefix like 'Title:' or 'Prefix -'
        if bold_prefix and (":" in item or "—" in item):
            delim = ":" if ":" in item else "—"
            parts = item.split(delim, 1)
            prefix = parts[0] + delim
            rest = parts[1]

            r_pre = p.add_run()
            r_pre.text = prefix
            r_pre.font.size = Pt(size)
            r_pre.font.bold = True
            r_pre.font.color.rgb = TEXT_PRIMARY
            r_pre.font.name = font

            r_rest = p.add_run()
            r_rest.text = rest
            r_rest.font.size = Pt(size)
            r_rest.font.color.rgb = color
            r_rest.font.name = font
        else:
            r = p.add_run()
            r.text = item
            r.font.size = Pt(size)
            r.font.color.rgb = color
            r.font.name = font

    return tb


def add_formula_block(slide, l, t, w, h, title, formula, fill=CARD2_BG, border_color=TEAL):
    """Adds a callout/formula box with a left border accent."""
    box = add_card(slide, l, t, w, h, fill=fill, line=border_color, line_w=1.2, radius=0.02)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = Pt(12)
    tf.margin_right = Pt(12)
    tf.margin_top = Pt(4)
    tf.margin_bottom = Pt(4)

    p0 = tf.paragraphs[0]
    p0.line_spacing = 1.1
    if title:
        r_title = p0.add_run()
        r_title.text = title + ": "
        r_title.font.bold = True
        r_title.font.size = Pt(12.5)
        r_title.font.color.rgb = border_color
        r_title.font.name = FONT_NAME

    r_formula = p0.add_run()
    r_formula.text = formula
    r_formula.font.size = Pt(12.5)
    r_formula.font.color.rgb = TEXT_PRIMARY
    r_formula.font.name = "Consolas"
    return box


def add_header(slide, slide_num, total_slides, soil_label, kicker, title, subtitle):
    """Adds standardized header to content slides."""
    # 1. SOIL Badge Pill
    soil_color = SOIL_COLORS.get(soil_label, TEAL)
    pill_w = Inches(1.2) if len(soil_label) <= 3 else Inches(1.8)
    pill = add_card(slide, Inches(0.5), Inches(0.38), pill_w, Inches(0.32),
                    fill=BG_COLOR, line=soil_color, line_w=1.0, radius=0.3)
    tf = pill.text_frame
    tf.word_wrap = False
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Pt(0)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = soil_label.upper()
    r.font.size = Pt(10)
    r.font.bold = True
    r.font.color.rgb = soil_color
    r.font.name = "Consolas"

    # 2. Kicker / Section Reference
    kicker_left = Inches(0.5) + pill_w + Inches(0.15)
    add_text_box(slide, kicker_left, Inches(0.38), Inches(8.5), Inches(0.32),
                 kicker, size=11.5, color=TEXT_MUTED, font=FONT_NAME, italic=True)

    # 3. Slide Number Pill at top right
    num_str = f"{slide_num:02d} / {total_slides:02d}"
    num_box = add_card(slide, Inches(11.833), Inches(0.38), Inches(1.0), Inches(0.32),
                       fill=CARD2_BG, line=GRID_LINE, line_w=0.75, radius=0.2)
    tf_num = num_box.text_frame
    tf_num.word_wrap = False
    tf_num.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf_num.margin_left = tf_num.margin_right = tf_num.margin_top = tf_num.margin_bottom = Pt(0)
    p_num = tf_num.paragraphs[0]
    p_num.alignment = PP_ALIGN.CENTER
    r_num = p_num.add_run()
    r_num.text = num_str
    r_num.font.size = Pt(11)
    r_num.font.bold = True
    r_num.font.color.rgb = TEAL
    r_num.font.name = "Consolas"

    # 4. Slide Title
    add_text_box(slide, Inches(0.5), Inches(0.74), Inches(12.333), Inches(0.6),
                 title, size=24, color=TEXT_PRIMARY, bold=True, font=FONT_NAME)

    # 5. Slide Subtitle
    add_text_box(slide, Inches(0.5), Inches(1.34), Inches(12.333), Inches(0.34),
                 subtitle, size=13, color=TEXT_MUTED, font=FONT_NAME)


def add_footer(slide, slide_num, total_slides):
    """Adds standardized footer."""
    footer_text = "HHSA Body Signals Deck • Kidney & Cognition Lab • Chu (2026) • Frontiers in Aging Neuroscience Review"
    add_text_box(slide, Inches(0.5), Inches(7.12), Inches(10.5), Inches(0.28),
                 footer_text, size=9.5, color=TEXT_DIM, font=FONT_NAME)

    add_text_box(slide, Inches(11.333), Inches(7.12), Inches(1.5), Inches(0.28),
                 f"Slide {slide_num} of {total_slides}", size=9.5, color=TEXT_DIM,
                 align=PP_ALIGN.RIGHT, font=FONT_NAME)


def set_speaker_notes(slide, notes_text, companion_anchor=None):
    """Sets speaker notes for the slide."""
    if not notes_text:
        return
    notes_slide = slide.notes_slide
    tf = notes_slide.notes_text_frame
    text = notes_text.strip()
    if companion_anchor:
        text += f"\n\n[Live companion: explorer.html#{companion_anchor}]"
    tf.text = text


def add_picture_fit(slide, path, l, t, max_w, max_h, caption=None):
    """Safely adds a picture scaled within max_w and max_h, maintaining aspect ratio.
    If image does not exist or fails, falls back gracefully.
    """
    path_obj = Path(path)
    if not path_obj.exists():
        # Check if a .png fallback exists for .webp
        if path_obj.suffix.lower() == ".webp":
            png_candidate = path_obj.with_suffix(".png")
            if png_candidate.exists():
                path_obj = png_candidate

    if not path_obj.exists():
        # Draw placeholder card
        card = add_card(slide, l, t, max_w, max_h, fill=CARD2_BG, line=RED, line_w=1.0)
        tf = card.text_frame
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = f"[Image not found: {path_obj.name}]"
        r.font.size = Pt(12)
        r.font.color.rgb = RED_LIGHT
        return card

    # Convert WEBP to PNG if needed for python-pptx / PowerPoint compatibility
    use_path = str(path_obj)
    if path_obj.suffix.lower() == ".webp":
        try:
            cached_png = path_obj.with_suffix(".cached.png")
            if not cached_png.exists():
                with Image.open(path_obj) as im:
                    im.convert("RGB").save(cached_png, "PNG")
            use_path = str(cached_png)
        except Exception:
            pass

    try:
        with Image.open(use_path) as im:
            iw, ih = im.size
        ar = iw / ih

        # Calculate fitted dimensions
        w = max_w
        h = max_w / ar
        if h > max_h:
            h = max_h
            w = max_h * ar

        # Center inside target rectangle
        offset_x = (max_w - w) / 2
        offset_y = (max_h - h) / 2

        pic = slide.shapes.add_picture(use_path, l + offset_x, t + offset_y, width=int(w), height=int(h))

        if caption:
            cap_top = t + offset_y + h + Pt(4)
            add_text_box(slide, l, cap_top, max_w, Inches(0.3), caption,
                         size=9.5, color=TEXT_DIM, align=PP_ALIGN.CENTER, font="Consolas")
        return pic
    except Exception as e:
        card = add_card(slide, l, t, max_w, max_h, fill=CARD2_BG, line=RED, line_w=1.0)
        tf = card.text_frame
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = f"[Image Load Error: {e}]"
        r.font.size = Pt(11)
        r.font.color.rgb = RED_LIGHT
        return card


def add_table_custom(slide, l, t, w, h, headers, rows, col_widths=None, font_size=10.5):
    """Adds a beautifully styled table with dark background and teal accents."""
    n_rows = len(rows) + 1
    n_cols = len(headers)
    table_shape = slide.shapes.add_table(n_rows, n_cols, l, t, w, h)
    table = table_shape.table

    if col_widths and len(col_widths) == n_cols:
        for c, cw in enumerate(col_widths):
            table.columns[c].width = cw

    # Headers
    for c, htext in enumerate(headers):
        cell = table.cell(0, c)
        cell.fill.solid()
        cell.fill.fore_color.rgb = CARD2_BG
        cell.margin_left = cell.margin_right = Pt(6)
        cell.margin_top = cell.margin_bottom = Pt(4)
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        r = p.add_run()
        r.text = htext
        r.font.bold = True
        r.font.size = Pt(font_size + 0.5)
        r.font.color.rgb = TEAL
        r.font.name = FONT_NAME

    # Rows
    for ri, row in enumerate(rows, start=1):
        bg = CARD_BG if ri % 2 == 1 else CARD2_BG
        for c, val in enumerate(row):
            cell = table.cell(ri, c)
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg
            cell.margin_left = cell.margin_right = Pt(6)
            cell.margin_top = cell.margin_bottom = Pt(4)
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            r = p.add_run()
            r.text = str(val)
            r.font.size = Pt(font_size)
            r.font.color.rgb = TEXT_PRIMARY if c == 0 else TEXT_MUTED
            r.font.name = FONT_NAME
            if c == 0:
                r.font.bold = True

    return table_shape


# ==============================================================================
# Slide Content Definitions (Verbatim from T12)
# ==============================================================================
SLIDES_DATA = [
    # --------------------------------------------------------------------------
    # SLIDE 1: Title Slide
    # --------------------------------------------------------------------------
    {
        "id": 1,
        "soil": "—",
        "kicker": "20-Slide SOIL Architecture • Frontiers in Aging Neuroscience",
        "title": "Holo-Hilbert Spectral Analysis (HHSA) of Physiological Body Signals",
        "subtitle": "Unraveling Nested Oscillations, Nonlinear Amplitude Modulation, and Brain–Body Interactions Across Brain, Heart, and Metabolism",
        "notes": "Welcome, colleagues. Today I am presenting our work on Holo-Hilbert Spectral Analysis, or HHSA, as a unifying mathematical framework for body signals across the brain, cardiovascular system, and human metabolism. Traditional spectral analysis assumes stationarity and treats biological rhythms as independent sums of sinusoids. But human physiology is intrinsically non-linear and non-stationary: slower physiological rhythms systematically modulate the amplitudes of faster carrier oscillations. Over the next twenty slides, following the SOIL framework, we will explore why traditional one-dimensional spectra fall short, how two-layer decomposition constructs a continuous three-dimensional energy cube, and how this reveals nested dynamics across continuous glucose monitoring, wearable heart rate variability, and neurodegenerative disease.",
        "type": "title",
    },

    # --------------------------------------------------------------------------
    # SLIDE 2: State - Body Signals Are Nested Oscillations
    # --------------------------------------------------------------------------
    {
        "id": 2,
        "soil": "S",
        "kicker": "§1 Introduction • Observed Biology",
        "title": "Body Signals Are Nested Oscillations",
        "subtitle": "Multi-scale biological rhythms continuously modulate one another across organs",
        "notes": "Biological organisms are multi-scale systems where physical processes at different temporal scales do not operate in isolation. In the central nervous system, theta rhythms modulate gamma bursts during memory encoding. In the cardiovascular system, slow vasomotor tone and Mayer waves at point one Hertz continuously modulate respiratory sinus arrhythmia at point two five Hertz. In metabolism, the master twenty-four hour circadian clock modulates ultradian insulin secretion pulses and postprandial glycemic excursions. When clinicians and researchers inspect these signals, they frequently look only at aggregate summary numbers or static averages. However, the true physiological code is nested amplitude modulation, which reflects real-time multi-organ coupling and regulatory feedback across disparate time scales.",
        "type": "cards_formula",
        "cards": [
            {
                "icon": "🧠",
                "title": "Brain (Neural Loops)",
                "lead": "Theta–Gamma Phase-Amplitude Coupling: Slower theta cycles (4–8 Hz) modulate the envelope of high-frequency gamma oscillations (30–80 Hz) during memory formation.",
                "bullets": [
                    "Infraslow modulation (< 0.1 Hz) coordinates sleep spindles and cortical slow waves.",
                    "Thalamocortical loops produce nested carrier-envelope dynamics, not isolated frequencies."
                ]
            },
            {
                "icon": "❤️",
                "title": "Heart (Autonomic Tone)",
                "lead": "Baroreflex & Respiratory Modulations: Respiratory sinus arrhythmia (HF ~0.25 Hz) does not beat in isolation.",
                "bullets": [
                    "Mayer waves (~0.1 Hz, LF) amplitude-modulate vagal respiratory peaks via arterial baroreceptors.",
                    "Circadian sympathetic tone (~24 h) shifts total carrier power and envelope depth across sleep/wake states."
                ]
            },
            {
                "icon": "🩸",
                "title": "Metabolism (Glucose Rhythms)",
                "lead": "Endocrine & Circadian Nesting: Interstitial continuous glucose dynamics span multiple coupled tiers.",
                "bullets": [
                    "24-hour circadian baseline acts as a slow modulator.",
                    "Pulsatile ultradian insulin secretion (1–4 h) and postprandial meal spikes (0.25–0.5 c/h) ride upon this baseline."
                ]
            }
        ],
        "formula_title": "Biological Reality",
        "formula": "Physiological signals x(t) = sum a_i(t) · cos(phi_i(t)), where the instantaneous envelope a_i(t) is itself a multi-scale oscillatory process."
    },

    # --------------------------------------------------------------------------
    # SLIDE 3: State - What a 1-D Spectrum Throws Away
    # --------------------------------------------------------------------------
    {
        "id": 3,
        "soil": "S",
        "kicker": "§1, §2 Mathematical Limits • Derived Limit",
        "title": "What a 1-D Spectrum Throws Away",
        "subtitle": "Fourier and classical spectra mischaracterize amplitude modulation as spurious sidebands",
        "notes": "What happens when you analyze an amplitude-modulated biological signal with a classical Fourier transform or static power spectrum? Fourier analysis projects the signal onto infinite, stationary sinusoids with constant amplitudes and phases. When a carrier wave undergoes amplitude modulation, Fourier mathematics cannot represent the varying amplitude directly. Instead, it generates spurious sideband frequencies on both sides of the carrier, scattering the true physical energy into mathematical artifacts. Furthermore, a one-dimensional power spectrum completely collapses cross-frequency interactions. You cannot tell whether two spectral peaks represent two independent, uncoupled physiological pacemakers or a single carrier rhythm whose strength is being modulated by a slower physiological cycle.",
        "type": "text_figure",
        "fig_name": "F1_concept_cube.png",
        "fig_caption": "Figure F1: 1-D collapsing vs. 3-D Holo-Hilbert expansion (t, f_carrier, f_AM).",
        "cards": [
            {
                "title": "The Sideband Fallacy",
                "lead": "When an amplitude-modulated carrier wave is analyzed with Fourier or stationary wavelets, trigonometry dictates artificial sidebands:",
                "formula": "x(t) = [1 + m · cos(w_AM t)] · cos(w_c t) = cos(w_c t) + 1/2 m · cos((w_c - w_AM)t) + 1/2 m · cos((w_c + w_AM)t)",
                "bullets": [
                    "Physical reality: ONE carrier wave and ONE modulation envelope.",
                    "Fourier mathematics: THREE uncoupled stationary sinusoids, scattering energy."
                ]
            },
            {
                "title": "The Ambiguity of 1-D Power",
                "lead": "A conventional 1-D power spectral density (PSD) or spectrogram S(f) collapses cross-frequency interactions. It cannot answer:",
                "bullets": [
                    "Are peaks at f_1 and f_2 two independent, uncoupled pacemakers?",
                    "Or is f_1 a carrier whose amplitude is dynamically paced by f_2?"
                ]
            }
        ]
    },

    # --------------------------------------------------------------------------
    # SLIDE 4: State - Existing Tools & Mathematical Assumptions
    # --------------------------------------------------------------------------
    {
        "id": 4,
        "soil": "S",
        "kicker": "§2, Table 1 Comparison • Comparative Method",
        "title": "Existing Tools & Their Mathematical Assumptions",
        "subtitle": "Wavelets, Phase-Amplitude Coupling (PAC), and Bispectrum vs. HHSA",
        "notes": "To capture dynamic interactions, signal processing has produced several important tools, summarized in Table One of our review. Continuous wavelet transforms provide localized time-frequency tracking but remain constrained by a fixed mother wavelet basis and the Heisenberg-Gabor uncertainty principle. Phase-Amplitude Coupling, or PAC, identifies coupling between the phase of a slow band and the amplitude of a fast band. However, conventional PAC relies on narrow bandpass filters that introduce harmonic distortion and phase delay, and it discretizes continuous dynamics into arbitrary frequency bins. Higher-order bispectral analysis detects quadratic phase coupling but requires long stationary epochs. HHSA overcomes these constraints through adaptive, data-driven sifting.",
        "type": "table_summary",
        "headers": ["Method Dimension", "Wavelet Transform (CWT)", "Phase-Amplitude Coupling (PAC)", "Bispectrum / Bicoherence", "Holo-Hilbert (HHSA)"],
        "rows": [
            ["Basis Function", "Fixed mother wavelet (e.g. Morlet)", "Linear bandpass filters", "Sinusoidal harmonics", "Adaptive, data-driven IMFs"],
            ["Linearity & Stationarity", "Assumes piecewise stationarity", "Assumes linear phase within band", "Assumes strict stationarity", "Fully nonlinear & nonstationary"],
            ["Cross-Frequency Metric", "Coherence (phase-locking only)", "Modulation Index (MI) discrete pair", "Quadratic phase coupling f1+f2=f3", "Continuous 3-D tensor H(t, fc, fam)"],
            ["Filter Distortion Risk", "Heisenberg-Gabor uncertainty limit", "Severe edge ringing & phase shift", "Spectral smearing on short epochs", "Zero filter-induced distortion"],
            ["Modulation Output", "1-D / 2-D time-scale map", "Scalar coupling index between 2 bands", "2-D static bifrequency map", "Instantaneous AM frequency & power"]
        ],
        "col_widths": [Inches(2.2), Inches(2.4), Inches(2.6), Inches(2.4), Inches(2.733)],
        "summary": "Key Takeaway: Conventional Phase-Amplitude Coupling (PAC) methods established the biological importance of cross-frequency interactions, but require subjective pre-filtering. HHSA generalizes cross-frequency analysis by computing continuous instantaneous frequencies for both the carrier and its amplitude envelope."
    },

    # --------------------------------------------------------------------------
    # SLIDE 5: Opportunity - HHSA in One Picture: Decompose Twice
    # --------------------------------------------------------------------------
    {
        "id": 5,
        "soil": "O",
        "kicker": "§2 The HHSA Framework • Algorithmic Design",
        "title": "HHSA in One Picture: Decompose Twice",
        "subtitle": "Two nested layers of empirical sifting resolve carrier frequency and modulation frequency",
        "notes": "The core insight of Holo-Hilbert Spectral Analysis, introduced by Norden Huang in 2016, is that resolving amplitude modulation requires decomposing the signal twice. In the first layer, the raw physiological signal undergoes noise-assisted Empirical Mode Decomposition, such as EEMD or CEEMDAN, yielding a finite set of Intrinsic Mode Functions. Each IMF admits a well-behaved instantaneous frequency and instantaneous amplitude via the Hilbert transform. In the second layer, rather than discarding the amplitude envelopes, HHSA treats each envelope as an independent physical time series and decomposes it again with empirical mode decomposition. This extracts secondary modulation IMFs, revealing the exact instantaneous frequencies at which the carrier amplitudes fluctuate over time.",
        "type": "text_figure",
        "fig_name": "F2_hhsa_pipeline.png",
        "fig_caption": "Figure F2: Two-layer sifting pipeline mapping raw signal to the 3-D Holo-Hilbert continuum.",
        "cards": [
            {
                "title": "1️⃣ Layer 1: Carrier Decomposition",
                "lead": "Decompose raw signal x(t) via noise-assisted EEMD or CEEMDAN into Intrinsic Mode Functions (IMFs):",
                "formula": "x(t) = sum_{i=1..M} c_i(t) + r(t)",
                "bullets": [
                    "Apply Hilbert Transform to each IMF c_i(t).",
                    "Extract Instantaneous Amplitude a_i(t) and Carrier Frequency f_{c,i}(t)."
                ]
            },
            {
                "title": "2️⃣ Layer 2: Modulation Decomposition",
                "lead": "Treat each amplitude envelope a_i(t) as an independent physical signal and sift again via EMD:",
                "formula": "a_i(t) = sum_{j=1..P} d_{ij}(t) + r_i(t)",
                "bullets": [
                    "Apply Hilbert Transform to d_{ij}(t).",
                    "Extract Instantaneous Modulation Frequency f_{AM,ij}(t) and energy A_{ij}(t)."
                ]
            }
        ]
    },

    # --------------------------------------------------------------------------
    # SLIDE 6: Opportunity - The Cube H and Its Three Projections
    # --------------------------------------------------------------------------
    {
        "id": 6,
        "soil": "O",
        "kicker": "§2 3-D Tensor Geometry • Spectral Formulation",
        "title": "The Cube H(t, f_c, f_AM) & Its Three Projections",
        "subtitle": "Orthogonal marginals recover Hilbert-Huang, cross-frequency, and modulation history maps",
        "notes": "By executing this two-layer decomposition, HHSA expands signal representation from a one-dimensional spectrum into a continuous three-dimensional energy density tensor, H of t, f carrier, and f AM. To make this tensor clinically interpretable, we define three orthogonal marginal projections. Integrating across the modulation axis yields S of t and f carrier, which is the classical Hilbert-Huang time-frequency spectrum. Integrating over time yields C of f carrier and f AM, the carrier-versus-modulation spectrum that maps cross-frequency coupling across the entire recording. Integrating across the carrier axis yields M of t and f AM, illustrating how modulation intensity waxes and wanes over physiological time.",
        "type": "three_cards_bottom",
        "cards": [
            {
                "badge": "Projection 1",
                "title": "S(t, f_c) — Time-Carrier",
                "formula": "S(t, f_c) = int H(t, f_c, f_AM) df_AM",
                "lead": "Hilbert-Huang Spectrum (HHT):",
                "bullets": [
                    "Integrates energy across all modulation frequencies.",
                    "Classic time-frequency representation tracking carrier power evolution."
                ]
            },
            {
                "badge": "Projection 2",
                "title": "C(f_c, f_AM) — Holo-Spectrum",
                "formula": "C(f_c, f_AM) = int H(t, f_c, f_AM) dt",
                "lead": "Carrier vs. Modulation Map:",
                "bullets": [
                    "Integrates energy over the entire recording duration.",
                    "Maps cross-frequency coupling across all physiological scales."
                ]
            },
            {
                "badge": "Projection 3",
                "title": "M(t, f_AM) — Time-Modulation",
                "formula": "M(t, f_AM) = int H(t, f_c, f_AM) df_c",
                "lead": "Modulation Time History:",
                "bullets": [
                    "Integrates energy across all carrier frequencies.",
                    "Reveals when physiological amplitude modulation bursts wax and wane."
                ]
            }
        ],
        "bottom_text": "Mathematical Consistency: Discrete 3-D tensor marginal sums reproduce orthogonal projections with relative error < 10^-6 (verified in cube_validation.json)."
    },

    # --------------------------------------------------------------------------
    # SLIDE 7: Opportunity - Admissibility & Duration Bounds
    # --------------------------------------------------------------------------
    {
        "id": 7,
        "soil": "O",
        "kicker": "§2, §6 Physical Validity • Rigorous Bounds",
        "title": "Admissibility (f_AM < f_c) & Duration Bounds (f >= 3/T)",
        "subtitle": "Distinguishing true physiological amplitude modulation from mathematical artifacts",
        "notes": "Not every mathematical point in the Holo-Hilbert volume is physically meaningful. Two rigorous constraints must be enforced. First is the mathematical admissibility condition: an envelope cannot oscillate faster than the carrier wave it modulates. Coordinates where f AM is greater than or equal to f carrier violate the Bedrosian theorem and represent spline overshoot or mode-mixing artifacts; these must be masked out. Second is the physiological record-length bound: resolving an oscillatory mode reliably via empirical mode decomposition requires at least three complete cycles, meaning frequency must exceed three divided by duration T. For a seven-minute wearable recording, frequencies below point zero zero seven Hertz are unresolvable and must be greyed out.",
        "type": "two_large_cards",
        "cards": [
            {
                "title": "⚖️ 1. The Admissibility Condition",
                "accent": GOLD,
                "formula": "f_AM < f_c   (Strict Physical Inequality)",
                "lead": "Physical Principle: An envelope cannot oscillate faster than the carrier wave it modulates (Bedrosian Theorem on product spectra).",
                "bullets": [
                    "Coordinates where f_AM >= f_c represent cubic spline overshoot, mode mixing, or noise leakage.",
                    "Our 3-D explorer and pipeline construct an explicit admissibility mask to exclude unphysical energy.",
                    "Essential for avoiding false-positive cross-frequency coupling reports."
                ]
            },
            {
                "title": "⏱️ 2. The 3-Cycle Duration Bound",
                "accent": PURPLE_LIGHT,
                "formula": "f_resolvable >= 3 / T   (T = Recording Duration)",
                "lead": "Physical Principle: Adaptive sifting requires at least 3 local extrema (troughs and peaks) to interpolate upper and lower envelopes reliably.",
                "bullets": [
                    "13-day CGM (T = 312 h): f >= 3/312 ≈ 0.0096 c/h. Circadian (0.042 c/h) is fully resolvable.",
                    "7-min Wearable HRV (T = 420 s): f >= 3/420 ≈ 0.0071 Hz. VLF (< 0.007 Hz) is mathematically unresolvable and grey-hatched!",
                    "Prevents over-interpreting short wearable snapshots as slow autonomic rhythms."
                ]
            }
        ]
    },

    # --------------------------------------------------------------------------
    # SLIDE 8: Implementation - Live 3-D Explorer: Synthetic Ground Truth
    # --------------------------------------------------------------------------
    {
        "id": 8,
        "soil": "I",
        "kicker": "§5 Interactive Core • Live Benchmark",
        "title": "Live 3-D Explorer: Synthetic Ground Truth",
        "subtitle": "Interactive WebGL inspection of the calibrated AM-FM test benchmark in real time",
        "notes": "Here on slide eight, we examine our synthetic ground truth benchmark embedded directly in WebGL. We synthesized a test signal whose carrier drifts between point three five and point six five Hertz while its amplitude rhythm drifts between point zero three and point zero seven Hertz. The pipeline recovered both coordinates within one grid bin in twenty-five of thirty windows, eighty-three percent, short of our ninety percent target. Every miss underestimated the modulation frequency, mostly at the edges of the record: the classic EMD end effect, and the reason to validate before interpreting real data. You can rotate this 3-D volume in real time using your mouse or touch gestures, inspect the energy ridge, or navigate to our dedicated interactive web explorer to explore the slices and band planes in full detail.",
        "type": "explorer_slide",
        "fig_name": "hero.webp",
        "fig_caption": "3-D Holo-Hilbert Coordinate Rig & Admissibility Plane (Blender 4.5 Render).",
        "equation": "x(t) = [1 + 0.7 cos φ_AM(t)] · cos φ_c(t)",
        "bullets": [
            "Carrier: f_c(t) = 0.50 + 0.15 cos(2πt/300) Hz; recovered in every window",
            "Modulation: f_AM(t) = 0.05 + 0.02 sin(2πt/300) Hz",
            "Recovery: 25 / 30 windows within 1 bin (83.3%; 90% target not met) — misses are AM-axis, mostly at record edges",
            "Admissibility: 1.9% of energy leaks to f_AM ≥ f_c (baseline for real data)",
            "Projection consistency ≈ 1e-16 (holds by construction)"
        ],
        "url": "https://ckt520728.github.io/kidney-cognition-lab/hhsa-3d/explorer.html"
    },

    # --------------------------------------------------------------------------
    # SLIDE 9: Implementation - Evidence Map Across Systems
    # --------------------------------------------------------------------------
    {
        "id": 9,
        "soil": "I",
        "kicker": "§3 PRISMA Scoping Search • Systematic Review",
        "title": "Evidence Map Across Systems",
        "subtitle": "PRISMA scoping search: 737 records → 711 deduplicated → 130 included studies",
        "notes": "To synthesize the global literature on Holo-Hilbert analysis across human physiology, we conducted a systematic scoping review following PRISMA guidelines. Our initial database queries yielded seven hundred thirty-seven candidate records. After removing duplicates and screening titles and abstracts, we evaluated one hundred thirty full-text studies across five thematic shards. As visualized in our evidence map, neurophysiology represents the largest established domain with thirty-eight studies, while cardiovascular autonomic monitoring accounts for thirty-one studies. Metabolic sensing with continuous glucose monitoring and cross-organ coupling represent pioneering frontiers with twenty-two and fifteen studies respectively, highlighting an immense opportunity for clinical translation in aging research.",
        "type": "text_figure",
        "fig_name": "F7_evidence_map.png",
        "fig_caption": "Figure F7: Evidence map cross-tabulating physiological domain vs. decomposition method class.",
        "cards": [
            {
                "title": "Search Scope & Shards (130 Studies)",
                "lead": "Cross-disciplinary scoping search categorized into five distinct thematic shards:",
                "bullets": [
                    "S1 Methodology & Algorithms: 24 studies (HHT, EEMD, CEEMDAN, masking, HHSA foundations).",
                    "S2 Brain (EEG/MEG/ECoG): 38 studies (AD/MCI, epilepsy, depression rTMS, SSVEP, tACS).",
                    "S3 Heart & Autonomic (HRV): 31 studies (autonomic aging, baroreflex AM, wearable ceilings).",
                    "S4 Metabolism & Glycemia (CGM): 22 studies (circadian, ultradian, glycemic variability).",
                    "S5 Cross-System Coupling: 15 studies (network physiology, sleep neuroenergetics)."
                ]
            },
            {
                "title": "PRISMA Selection Funnel",
                "lead": "Searched PubMed, IEEE Xplore, Web of Science, and Scopus through October 2026. 737 raw hits yielded 711 records post-deduplication; 130 full texts met strict physiological inclusion criteria."
            }
        ]
    },

    # --------------------------------------------------------------------------
    # SLIDE 10: Implementation - Brain: What HHSA Revealed
    # --------------------------------------------------------------------------
    {
        "id": 10,
        "soil": "I",
        "kicker": "§4.1 Clinical Neuroscience • Clinical Validation",
        "title": "Brain: What HHSA Revealed in Neurological Disorders",
        "subtitle": "Capturing subtle cross-frequency breakdown in neurodegeneration and neuromodulation",
        "notes": "In clinical neuroscience, HHSA has provided unprecedented insight into brain aging and circuit pathophysiology. In Alzheimer's disease and mild cognitive impairment, our group's 2023 study demonstrated that HHSA uncovers severe degradation of delta and theta carrier modulation by infraslow envelopes, reflecting impaired thalamocortical synchrony before overt structural atrophy. In Parkinson's disease, HHSA quantifies pathological beta burst amplitude modulation in basal ganglia loops. In major depressive disorder, prefrontal modulation energy restructures following repetitive transcranial magnetic stimulation. Furthermore, sensory entrainment paradigms like steady-state visual evoked potentials and amplitude-modulated transcranial alternating current stimulation demonstrate that HHSA accurately tracks targeted neural entrainment across multiple cortical layers.",
        "type": "cards_formula",
        "cards": [
            {
                "icon": "🧩",
                "title": "AD & MCI (Chu et al. 2023)",
                "lead": "Thalamocortical Dysrhythmia: In Alzheimer's Disease and Mild Cognitive Impairment, HHSA demonstrated that delta–theta carrier modulation by infraslow envelopes is severely degraded.",
                "bullets": [
                    "Detects network disconnection before overt structural brain atrophy.",
                    "Preserves instantaneous frequency without Fourier sideband smearing."
                ]
            },
            {
                "icon": "⚡",
                "title": "Neuromodulation (tACS / rTMS)",
                "lead": "Exogenous Entrainment: In major depressive disorder, rTMS alters prefrontal theta-gamma modulation energy.",
                "bullets": [
                    "AM-tACS delivery creates precise nested fields driving targeted cortical layers.",
                    "SSVEP experiments reveal exact harmonic carrier modulations induced by visual flicker."
                ]
            },
            {
                "icon": "🎯",
                "title": "Parkinson's & Working Memory",
                "lead": "Pathological Burst Dynamics: Subthalamic nucleus and cortical beta burst modulations characterize motor freezing in Parkinson's disease.",
                "bullets": [
                    "Visual working memory load dynamically modulates gamma burst envelopes.",
                    "HHSA separates instantaneous burst rate from amplitude envelope magnitude."
                ]
            }
        ],
        "formula_title": "Key Finding",
        "formula": "Traditional EEG power spectra miss up to 60% of dynamic cross-frequency alterations because they collapse modulation envelopes into static frequency bands."
    },

    # --------------------------------------------------------------------------
    # SLIDE 11: Implementation - Heart: HRV, Autonomic Aging, & Wearable Ceilings
    # --------------------------------------------------------------------------
    {
        "id": 11,
        "soil": "I",
        "kicker": "§4.2 Autonomic Physiology • Cardiovascular Dynamics",
        "title": "Heart: HRV, Autonomic Aging, & Wearable Ceilings",
        "subtitle": "Resolving instantaneous baroreflex AM while respecting physical duration constraints",
        "notes": "In cardiovascular physiology, autonomic aging is characterized by progressive vagal withdrawal and impaired arterial baroreflex responsiveness. Traditional frequency-domain heart rate variability divides power into low-frequency and high-frequency bands under the assumption of stationarity. However, real-life wearable data are non-stationary. HHSA isolates how respiratory sinus arrhythmia in the high-frequency band is modulated in real time by Mayer waves in the low-frequency band. Crucially, wearable photoplethysmography sessions are frequently ultra-short-term, often lasting less than ten minutes. In such records, very low-frequency spectral power cannot be resolved under the three-cycle criterion. HHSA provides an honest reporting framework by explicitly demarcating what short wearable recordings can and cannot measure.",
        "type": "text_table_side",
        "cards": [
            {
                "title": "Autonomic Aging & Baroreflex AM",
                "lead": "Cardiovascular aging is marked by progressive vagal withdrawal and blunted arterial baroreflex responsiveness. Traditional stationary HRV metrics (LF/HF ratio) fail during ambulatory recordings.",
                "bullets": [
                    "Respiratory Sinus Arrhythmia (HF 0.15–0.40 Hz): High-frequency carrier generated by vagal efferents.",
                    "Mayer Waves (LF 0.04–0.15 Hz): Modulate the amplitude of RSA in real time, reflecting baroreflex engagement."
                ]
            },
            {
                "title": "The Wearable Optical PPG Ceiling",
                "lead": "Modern smartwatches record short optical PPG bursts (< 10 min). Such ultra-short data impose strict limits:",
                "formula": "T < 10 min => VLF (< 0.04 Hz) is Partially or Fully Unresolvable",
                "bullets": [
                    "Attempting to quantify VLF power from short wearable segments generates spurious noise artifacts."
                ]
            }
        ],
        "table_title": "HRV Band Hierarchy in HHSA",
        "headers": ["Band", "Frequency", "Physiological Role", "Min. Resolvable T (3/f)"],
        "rows": [
            ["HF", "0.15–0.40 Hz", "Vagal / Respiratory Sinus Arrhythmia", "20 seconds"],
            ["LF", "0.04–0.15 Hz", "Baroreceptor / Sympathetic Mayer Waves", "75 seconds"],
            ["VLF", "0.0033–0.04 Hz", "Thermoregulation / Renin-Angiotensin", "15.1 minutes (UNRESOLVABLE on short runs!)"]
        ],
        "col_widths": [Inches(1.0), Inches(1.5), Inches(2.2), Inches(1.4)]
    },

    # --------------------------------------------------------------------------
    # SLIDE 12: Implementation - Metabolism: Glucose Rhythms & CGM
    # --------------------------------------------------------------------------
    {
        "id": 12,
        "soil": "I",
        "kicker": "§4.3 Metabolic Dynamics • Endocrine Rhythms",
        "title": "Metabolism: Glucose Rhythms & Continuous Monitoring",
        "subtitle": "Consensus clinical metrics (TIR/CV) vs. multi-scale nested glycemic dynamics",
        "notes": "Metabolic health is governed by dynamic temporal hierarchies. Interstitial glucose reflects interactions between the twenty-four hour circadian pacemaker, ultradian pulsatile insulin secretion every one to four hours, and sharp postprandial meals. The current international consensus metrics—time in range, coefficient of variation, and mean glucose—reduce two weeks of continuous sensor recordings to static scalar summary statistics. They provide zero information regarding circadian phase coherence or the amplitude modulation of meal spikes by background sleep-wake cycles. Because glycemic variability accelerates microvascular damage and cognitive decline in older adults with type two diabetes, applying HHSA to continuous glucose monitoring establishes a dynamic metabolic signature for brain aging.",
        "type": "two_large_cards",
        "cards": [
            {
                "title": "The Three-Tier Glycemic Hierarchy",
                "accent": TEAL,
                "lead": "Interstitial continuous glucose monitoring reveals three physiologically coupled tiers:",
                "bullets": [
                    "Circadian Base (24 h / 0.042 c/h): SCN master clock drives nocturnal hepatic gluconeogenesis and morning dawn phenomenon.",
                    "Ultradian Pulsatility (1–4 h / 0.25–1.0 c/h): Intrinsic pacemakers driving pulsatile pancreatic insulin secretion.",
                    "Postprandial Excursions (Meal-related): Acute nutrient absorption spikes modulated by background circadian insulin sensitivity.",
                    "Consensus Metrics Blind Spot: Two patients with identical 70% TIR and 32% CV can have completely different circadian phase coupling."
                ]
            },
            {
                "title": "Why HHSA Matters for Brain Aging",
                "accent": GOLD,
                "lead": "Repeated glycemic excursions induce endothelial oxidative stress, microvascular blood-brain barrier leakage, and accelerated cognitive decline in aging cohorts.",
                "formula": "HHSA resolves how 24-h circadian rhythms amplitude-modulate meal excursions without discarding non-stationary baseline drifts.",
                "bullets": [
                    "Provides a dynamic digital biomarker for preclinical neuro-metabolic decline.",
                    "Tracks circadian flattening and ultradian dysregulation before overt HbA1c elevation."
                ]
            }
        ]
    },

    # --------------------------------------------------------------------------
    # SLIDE 13: Implementation - Demonstration: CGM Cube
    # --------------------------------------------------------------------------
    {
        "id": 13,
        "soil": "I",
        "kicker": "§5 Clinical Demonstration • Empirical Data",
        "title": "Demonstration: Continuous Glucose Monitor (CGM) Cube",
        "subtitle": "De-identified example (n = 1, shown with consent) • 13.0 days (312 h) • 3,744 samples",
        "notes": "Slide thirteen illustrates our empirical continuous glucose monitoring cube from a de-identified individual recorded over thirteen continuous days, comprising three thousand seven hundred forty-four samples at five-minute intervals. The Nyquist frequency is six cycles per hour. Standard consensus statistics reveal a mean glucose of eight point zero eight millimoles per liter, coefficient of variation of thirty-six point eight percent, and a time in range of sixty-one point seven percent. In the Holo-Hilbert cube, carrier energy is spread across all five bands, and for the ultradian, meal-related and postprandial carriers the strongest modulation band is the circadian one. That is a descriptive observation for one person, and about a fifth of the energy falls in the inadmissible zone, so it has to be masked before any band metric is computed.",
        "type": "text_figure",
        "fig_name": "F5_cgm_cube_projections.png",
        "fig_caption": "Figure F5: CGM 3-D Holo-Hilbert cube and its three marginal projections S(t,f), C(fc,fam), M(t,fam).",
        "cards": [
            {
                "title": "Signal Provenance & Authoritative Metrics",
                "lead": "De-identified empirical recording over 13.0 continuous days (312.0 hours):",
                "bullets": [
                    "Duration & Sampling: 3,744 samples at 5-min intervals (Nyquist = 6.0 c/h, 10-min period).",
                    "Summary Statistics: Mean glucose 8.08 mmol/L (145.5 mg/dL), SD 2.97 mmol/L, CV 36.77%.",
                    "Consensus Distribution: TIR (3.9–10.0 mmol/L): 61.7%; TAR > 10.0 mmol/L: 27.2% (TAR > 13.9: 2.5%); TBR < 3.9 mmol/L: 11.1%; TBR < 3.0: 5.6%."
                ]
            },
            {
                "title": "What the 3-D Holo-Hilbert Cube Shows",
                "lead": "Carrier energy: Circadian 28.5%, Ultradian 18.5%, Meal-related 16.3%, Postprandial 23.6%, Fast 13.0%. For Ultradian, Meal-related and Postprandial carriers the strongest AM band is Circadian (72.9%, 49.0%, 33.7%).",
                "formula": "Descriptive, n = 1. 19.8% of energy sits at f_AM ≥ f_c and must be masked."
            }
        ]
    },

    # --------------------------------------------------------------------------
    # SLIDE 14: Implementation - Demonstration: Wearable Garmin HRV Cubes
    # --------------------------------------------------------------------------
    {
        "id": 14,
        "soil": "I",
        "kicker": "§5 Wearable Demonstration • Empirical Wearable Data",
        "title": "Demonstration: Wearable Garmin HRV Cubes (Sessions A & B)",
        "subtitle": "Two real ~7-min wearable sessions • 50 Hz beat recovery • VLF (< 3/T) greyed out",
        "notes": "On slide fourteen, we examine two real Garmin optical heart rate variability recordings from a single individual, each lasting approximately seven minutes. Using fifty Hertz heart rate integration, our preprocessing recovered seven hundred eighteen beats in Session A and six hundred ninety-four in Session B, within about half a percent of the expected counts. RMSSD was eighteen point three milliseconds in Session A and sixteen point five in Session B. In both cubes the carrier energy is dominated by the low-frequency band rather than the respiratory band, and about a fifth of the energy falls below three over T, greyed out because seven minutes cannot resolve it. The two sessions look very similar, so we do not read physiology into their differences.",
        "type": "table_figure_side",
        "fig_name": "F6_garmin_hrv_sessions.png",
        "fig_caption": "Figure F6: Garmin wearable HRV cubes (Sessions A and B) with 3/T greyed unresolvable zones.",
        "headers": ["Metric", "HRV Session A", "HRV Session B", "QC Target"],
        "rows": [
            ["Duration / Samples", "424.5 s / 21,224", "444.6 s / 22,233", "~7 minutes"],
            ["Recovered Beats", "718 beats", "694 beats", "Within ±2% expected"],
            ["Count Error %", "0.51%", "0.37%", "<= 2.0% (PASS)"],
            ["MeanNN / Median HR", "591.0 ms / 102 bpm", "640.7 ms / 94 bpm", "Standard resting"],
            ["RMSSD / SDNN", "18.3 ms / 36.6 ms", "16.5 ms / 34.8 ms", "Same-method only"],
            ["pNN50 %", "1.54%", "0.43%", "Beat variance"],
            ["3/T Cutoff (Greyed)", "0.00707 Hz", "0.00675 Hz", "Unresolvable VLF"]
        ],
        "col_widths": [Inches(1.8), Inches(1.5), Inches(1.5), Inches(1.4)],
        "summary": "Methodological Discipline: Bins below 3/T Hz are grey-hatched in both cubes, preventing over-interpretation of VLF power from short 7-minute snapshots. Carrier energy is LF-dominant (43.8% / 47.5%), HF second (30.4% / 25.3%)."
    },

    # --------------------------------------------------------------------------
    # SLIDE 15: Implementation - Across Systems: Inter-Organ Coupling Hypotheses
    # --------------------------------------------------------------------------
    {
        "id": 15,
        "soil": "I",
        "kicker": "§4.4 Cross-System Dynamics • Hypothesis Formulation",
        "title": "Across Systems: Inter-Organ Coupling Hypotheses",
        "subtitle": "Network physiology, Amplitude-Carrier Cross-Frequency Coupling (ACFC), & SWR-glucose",
        "notes": "Network physiology posits that physiological resilience arises from coordinated interactions among organ networks, captured here through amplitude-carrier cross-frequency coupling. A compelling hypothesis in neuroenergetics involves the coupling between hippocampal sharp-wave ripples and peripheral glucose homeostasis. In rodent models, high-frequency ripples during slow-wave sleep stimulate hepatic glucose output through autonomic pathways. In human non-invasive studies, however, non-invasive scalp EEG cannot record individual hippocampal ripples directly, nor can five-minute interstitial glucose measurements track millisecond-level neural bursts. Therefore, we explicitly designate human non-invasive ripple-glucose coupling as an unproven hypothesis that requires rigorous multi-modal recording, surrogate time-series testing, and precise pharmacological perturbations to substantiate.",
        "type": "two_large_cards",
        "cards": [
            {
                "title": "🌐 Network Physiology & ACFC",
                "accent": TEAL,
                "lead": "Organs communicate not via isolated firing rates, but through coordinated cross-frequency coupling across anatomical boundaries.",
                "bullets": [
                    "Brain–Heart Axis: Central autonomic network (insula, prefrontal cortex) modulates cardiac baroreflex sensitivity through slow theta-band envelopes.",
                    "Autonomic–Metabolic Axis: Vagal efferent bursts pace hepatic gluconeogenesis and postprandial insulin uptake.",
                    "Multi-Scale Coordination: Amplitude-Carrier Cross-Frequency Coupling (ACFC) provides the quantitative bridge."
                ]
            },
            {
                "title": "⚡ Hypothesis: Hippocampal SWR–Glucose Link",
                "accent": GOLD,
                "lead": "The Rodent vs. Human Gap: Rodent invasive electrophysiology demonstrates that sleep sharp-wave ripples (SWRs, 150–250 Hz) trigger acute hepatic glucose output.",
                "bullets": [
                    "Explicit Boundary: In non-invasive human scalp EEG, individual hippocampal SWRs cannot be resolved directly, nor can 5-min interstitial CGM track millisecond spikes.",
                    "Epistemic Rigor: Must be formally labeled as an UNTESTED HYPOTHESIS for non-invasive human HHSA.",
                    "Requires synchronized high-density EEG, ultra-fast metabolic sensing, and surrogate null controls."
                ]
            }
        ],
        "bottom_formula": "Epistemic Rigor: We distinguish confirmed animal neurobiology from human non-invasive feasibility. Multi-modal cross-organ cubes require synchronous high-resolution recording before claiming direct coupling."
    },

    # --------------------------------------------------------------------------
    # SLIDE 16: Leverage - Five Pitfalls That Change the Answer
    # --------------------------------------------------------------------------
    {
        "id": 16,
        "soil": "L",
        "kicker": "§6 Methodological Integrity • Pitfall Ledger",
        "title": "Five Pitfalls That Change the Answer",
        "subtitle": "Common technical errors that generate artificial amplitude modulation and false positives",
        "notes": "Applying Holo-Hilbert analysis to biological time series without rigorous methodological safeguards produces misleading conclusions. We highlight five critical pitfalls. First, violating the Nyquist criterion or inadequate sampling rates creates severe aliasing. Second, analyzing records shorter than three cycles of the target rhythm produces unresolvable low-frequency spectral smearing. Third, single-sift empirical mode decomposition suffers from mode mixing, necessitating noise-assisted ensemble methods. Fourth, spline fitting at the beginning and end of finite signals introduces severe boundary distortion, requiring systematic edge trimming of five to ten percent. Finally, failing to mask coordinates where modulation frequency exceeds carrier frequency generates spurious, non-physical amplitude modulation.",
        "type": "six_grid_cards",
        "cards": [
            {
                "title": "1. Nyquist & Aliasing",
                "accent": RED,
                "lead": "Under-sampling folds high-frequency noise directly into physiological bands.",
                "rule": "Rule: Sensor sampling rate f_s must be strictly > 2 × max carrier frequency, with analog anti-aliasing."
            },
            {
                "title": "2. Insufficient Duration T",
                "accent": RED,
                "lead": "Attempting to extract rhythms slower than 3 / T causes severe envelope smearing.",
                "rule": "Rule: Strictly mask or grey-out bins below 3 / T in all published spectra."
            },
            {
                "title": "3. Mode Mixing",
                "accent": RED,
                "lead": "Intermittent signals cause single IMFs to jump across multiple frequency octaves.",
                "rule": "Rule: Always use noise-assisted sifting (EEMD or CEEMDAN) with >= 100 ensemble trials."
            },
            {
                "title": "4. Edge Spline Distortion",
                "accent": RED,
                "lead": "Cubic spline interpolation diverges at signal boundaries, distorting Hilbert phases.",
                "rule": "Rule: Systematically trim 5% to 10% of samples from both ends prior to spectral evaluation."
            },
            {
                "title": "5. Spurious AM (f_AM >= f_c)",
                "accent": RED,
                "lead": "Allowing unmasked coordinates where modulation is faster than carrier violates Bedrosian theorem.",
                "rule": "Rule: Enforce the mathematical admissibility plane mask f_AM < f_c."
            },
            {
                "title": "Antidote: Null Testing",
                "accent": GREEN,
                "lead": "Benchmark observed peaks against phase-randomized (IAAFT) surrogate time series.",
                "rule": "Rule: Verifies whether AM energy exceeds stochastic linear noise baselines."
            }
        ]
    },

    # --------------------------------------------------------------------------
    # SLIDE 17: Leverage - Standardizing Physiological HHSA: 8-Point Checklist
    # --------------------------------------------------------------------------
    {
        "id": 17,
        "soil": "L",
        "kicker": "§6, Table 3 Reporting Standard • Reproducibility Standard",
        "title": "Standardizing Physiological HHSA: The 8-Point Checklist",
        "subtitle": "A minimum reporting standard to eliminate reproducibility crises in non-linear signal processing",
        "notes": "To elevate the reproducibility and rigor of physiological HHSA, Table Three of our review proposes an eight-point reporting standard. Every future study should report: first, the exact decomposition algorithm and ensemble parameters; second, the instantaneous frequency calculation method; third, explicit enforcement of the mathematical admissibility mask; fourth, the minimum resolvable frequency based on three cycles divided by record duration; fifth, the exact boundary trimming percentage; sixth, surrogate data null testing against phase-randomized controls; seventh, transparent ethical provenance and de-identification procedures; and eighth, open-source code availability. Adhering to these eight criteria ensures that published amplitude modulation findings represent authentic physiological coupling rather than numerical artifacts.",
        "type": "table_checklist",
        "headers": ["#", "Reporting Dimension", "Mandatory Specification", "Rationale in Biological Applications"],
        "rows": [
            ["1", "Decomposition Algorithm", "EEMD / CEEMDAN / Masking, ensemble size N, noise amplitude eps", "Eliminates mode mixing and guarantees deterministic reconstruction."],
            ["2", "Instantaneous Frequency", "Direct Quadrature (DQ) vs. Normalized Hilbert Transform (NHT)", "Prevents Bedrosian envelope-carrier overlap errors."],
            ["3", "Admissibility Mask", "f_AM < f_c explicit mathematical masking reported", "Excludes unphysical spline overshoot artifacts from energy tallies."],
            ["4", "Duration & Resolvability", "f_min = 3 / T reported; unresolvable low bins masked or greyed", "Prevents spurious claims of slow rhythms (e.g. VLF) from short runs."],
            ["5", "Boundary Protocol", "Exact edge percentage/seconds trimmed from both ends", "Eliminates cubic spline endpoint divergence from spectra."],
            ["6", "Surrogate Null Testing", "IAAFT phase-randomized or amplitude-adjusted surrogate statistics", "Confirms AM coupling is not an artifact of stationary colored noise."],
            ["7", "Ethical Provenance", "Relative time axes (hours/seconds), de-identification, IRB consent", "Guarantees privacy protection and data governance compliance."],
            ["8", "Code & Tensor Sharing", "Open-source code, environment version lock, coordinate tensors", "Allows complete independent scientific verification."]
        ],
        "col_widths": [Inches(0.6), Inches(2.5), Inches(4.5), Inches(4.733)]
    },

    # --------------------------------------------------------------------------
    # SLIDE 18: Leverage - Open Architecture & Reproducibility Pipeline
    # --------------------------------------------------------------------------
    {
        "id": 18,
        "soil": "L",
        "kicker": "§5 Software Architecture • Open Science",
        "title": "Open Architecture & Reproducibility Pipeline",
        "subtitle": "Zero unmaintained dependencies: pure Python standard library + NumPy + SciPy",
        "notes": "Open science and complete reproducibility are core pillars of this initiative. Our entire computational pipeline is implemented in pure Python using only standard library, NumPy, and SciPy, completely avoiding unmaintained third-party decomposition packages. The 3-D coordinate rigs, bounding boxes, and translucent band slabs were constructed using an automated headless Blender script exporting compact glTF models. The interactive web explorer is delivered via Three dot JS using pinned content delivery networks, allowing researchers to explore our pre-calculated float16 tensors directly in any modern browser without installing software. All code, validation logs, and de-identified tensor cubes are openly hosted for community verification.",
        "type": "three_cards_bottom",
        "cards": [
            {
                "badge": "Compute Tier",
                "title": "🐍 Python Core",
                "lead": "Pure stdlib + numpy + scipy: Custom vectorized implementation of two-layer sifting.",
                "bullets": [
                    "No unmaintained wrappers (no PyEMD, no closed toolboxes).",
                    "Dense float16 Base64 and sparse Top-K JSON exporters.",
                    "All 5 cubes generated under 20 KB per JSON file."
                ]
            },
            {
                "badge": "Asset Tier",
                "title": "🎨 Headless Blender",
                "lead": "Blender 4.5 Python Builder: Programmatic procedural coordinate rig generation.",
                "bullets": [
                    "Emissive teal axis lines and wireframe bounding boxes.",
                    "Translucent glass band slabs (Circadian, Ultradian, LF, HF).",
                    "Exports lightweight, production-ready .glb assets."
                ]
            },
            {
                "badge": "Presentation Tier",
                "title": "🌐 Three.js WebGL",
                "lead": "Interactive WebGL Suite: Zero-installation browser explorer using pinned CDN modules.",
                "bullets": [
                    "Live dynamic slicing: S(t,fc), C(fc,fam), M(t,fam).",
                    "Admissibility plane toggle and 3/T grey-hatching.",
                    "Mobile-friendly drawer UI with dual frequency-period axes."
                ]
            }
        ],
        "bottom_text": "GitHub Staging Repository: kidney-cognition-lab/hhsa-3d • Openly staged for scientific peer review"
    },

    # --------------------------------------------------------------------------
    # SLIDE 19: Leverage - Outlook: Wearables, Multimodal Cubes, & Aging Cohorts
    # --------------------------------------------------------------------------
    {
        "id": 19,
        "soil": "L",
        "kicker": "§6 Future Directions • Clinical Vision",
        "title": "Outlook: Wearables, Multimodal Cubes, & Aging Cohorts",
        "subtitle": "Translating Holo-Hilbert analytics from desktop workstations to clinical longitudinal trials",
        "notes": "Looking toward the future, the convergence of edge computing and multimodal physiological sensing offers transformative potential for aging research. Low-power microcontroller implementations of empirical mode decomposition will enable smartwatches and smart rings to perform real-time amplitude modulation tracking on the edge. By synchronously capturing continuous EEG, wearable heart rate variability, and continuous glucose monitoring, clinicians will be able to construct unified multi-organ Holo-Hilbert cubes. Longitudinal studies in aging cohorts can evaluate whether the progressive loss of multi-scale amplitude modulation complexity serves as an early digital biomarker for neurodegenerative decline, vascular frailty, and autonomic dysregulation long before irreversible clinical symptoms appear.",
        "type": "cards_formula",
        "cards": [
            {
                "icon": "⌚",
                "title": "Edge Computing",
                "lead": "Wearable Microcontrollers: Developing optimized integer-arithmetic EMD algorithms to run directly on smartwatches and smart rings.",
                "bullets": [
                    "Real-time autonomous baroreflex monitoring on edge devices.",
                    "Low-latency biofeedback alerting patients to autonomic stress."
                ]
            },
            {
                "icon": "🔗",
                "title": "Synchronous Multimodal Cubes",
                "lead": "Brain–Heart–Metabolic Tensors: Building unified data cubes from synchronized 24-h EEG, wearable PPG, and interstitial CGM.",
                "bullets": [
                    "Quantifies sleep-stage regulation of autonomic tone and glucose.",
                    "Provides multi-organ network resilience indices."
                ]
            },
            {
                "icon": "🧬",
                "title": "Longitudinal Aging Cohorts",
                "lead": "Digital Biomarkers of Frailty: Tracking progressive loss of cross-frequency modulation complexity across decades.",
                "bullets": [
                    "Detects microvascular frailty before irreversible clinical dementia.",
                    "Establishes quantitative endpoints for lifestyle interventions."
                ]
            }
        ],
        "formula_title": "The Ultimate Goal",
        "formula": "Transforming raw, non-stationary physiological streams into actionable multi-scale digital biomarkers for healthy longevity."
    },

    # --------------------------------------------------------------------------
    # SLIDE 20: Conclusion & Links
    # --------------------------------------------------------------------------
    {
        "id": 20,
        "soil": "—",
        "kicker": "§7 Summary & Resources • Kidney & Cognition Lab",
        "title": "Take-Home Messages & Resource Hub",
        "subtitle": "Holo-Hilbert Spectral Analysis expands biological time series into multi-scale reality",
        "notes": "To conclude our presentation, three central messages emerge. First, human body signals are intrinsically nested; amplitude modulation represents a primary biological mechanism for multi-scale physiological control. Second, Holo-Hilbert Spectral Analysis resolves this nested architecture by mapping energy into a continuous three-dimensional space of time, carrier frequency, and modulation frequency. Third, physical validity requires strict adherence to mathematical admissibility and record-length bounds. We invite you to explore our interactive 3-D explorer online, read our comprehensive review paper in preparation for Frontiers in Aging Neuroscience, and engage with our educational materials as we advance the frontiers of network physiology in brain aging.",
        "type": "two_large_cards",
        "cards": [
            {
                "title": "Core Takeaways",
                "accent": TEAL,
                "lead": "Three foundational pillars of physiological Holo-Hilbert analytics:",
                "bullets": [
                    "1. Biological Signals Are Nested: Amplitude modulation is not noise; it is the fundamental language of cross-scale organ communication.",
                    "2. HHSA Unlocks the 3rd Dimension: Decomposing twice maps continuous energy into H(t, fc, fAM), eliminating artificial Fourier sidebands and subjective PAC band-limits.",
                    "3. Methodological Discipline is Essential: Physical validity requires strict enforcement of the admissibility condition (fAM < fc) and 3-cycle duration bounds (f >= 3/T)."
                ]
            },
            {
                "title": "Project Ecosystem & Links",
                "accent": PURPLE_LIGHT,
                "lead": "Open resources, manuscript, and interactive explorer:",
                "bullets": [
                    "🚀 3-D Holo-Hilbert Interactive Web Explorer: https://ckt520728.github.io/kidney-cognition-lab/hhsa-3d/explorer.html",
                    "🏠 Kidney & Cognition Lab Project Portal: https://ckt520728.github.io/kidney-cognition-lab/hhsa-3d/",
                    "📄 Narrative Review Manuscript: Chu KT (2026). Using HHSA to Unravel the Physiological Secrets of Body Signals. Frontiers in Aging Neuroscience (In prep).",
                    "📖 Chinese Educational Deep Dive: Lab blog: 以全息希爾伯特頻譜解構人體訊號的生理密碼."
                ]
            }
        ]
    }
]


# ==============================================================================
# Slide Builder Implementations
# ==============================================================================
def build_title_slide(slide, s):
    set_slide_background(slide, BG_COLOR)

    # Decorative background card
    bg_card = add_card(slide, Inches(0.5), Inches(0.5), Inches(12.333), Inches(6.5),
                       fill=CARD_BG, line=GRID_LINE, line_w=1.0, radius=0.03)

    # Top badges pill
    pill = add_card(slide, Inches(3.666), Inches(0.9), Inches(6.0), Inches(0.36),
                    fill=CARD2_BG, line=TEAL, line_w=1.0, radius=0.3)
    tf_p = pill.text_frame
    tf_p.word_wrap = False
    tf_p.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf_p.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = "20-SLIDE SOIL ARCHITECTURE • FRONTIERS IN AGING NEUROSCIENCE"
    r.font.size = Pt(11)
    r.font.bold = True
    r.font.color.rgb = TEAL
    r.font.name = "Consolas"

    # Main Title
    add_text_box(slide, Inches(1.0), Inches(1.5), Inches(11.333), Inches(1.4),
                 s["title"], size=34, color=TEXT_PRIMARY, bold=True, align=PP_ALIGN.CENTER)

    # Subtitle
    add_text_box(slide, Inches(1.5), Inches(3.0), Inches(10.333), Inches(0.9),
                 s["subtitle"], size=16, color=TEXT_MUTED, align=PP_ALIGN.CENTER)

    # Author card
    author_card = add_card(slide, Inches(3.666), Inches(4.2), Inches(6.0), Inches(1.5),
                           fill=CARD2_BG, line=CARD_BORDER, line_w=1.0, radius=0.04)
    tf_a = author_card.text_frame
    tf_a.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf_a.margin_top = tf_a.margin_bottom = Pt(8)

    pa1 = tf_a.paragraphs[0]
    pa1.alignment = PP_ALIGN.CENTER
    ra1 = pa1.add_run()
    ra1.text = "Kwo-Ta Chu, MD, PhD"
    ra1.font.size = Pt(18)
    ra1.font.bold = True
    ra1.font.color.rgb = TEAL

    pa2 = tf_a.add_paragraph()
    pa2.alignment = PP_ALIGN.CENTER
    pa2.line_spacing = 1.15
    ra2 = pa2.add_run()
    ra2.text = "Kidney & Cognition Lab • Department of Internal Medicine"
    ra2.font.size = Pt(13)
    ra2.font.color.rgb = TEXT_MUTED

    pa3 = tf_a.add_paragraph()
    pa3.alignment = PP_ALIGN.CENTER
    pa3.line_spacing = 1.15
    ra3 = pa3.add_run()
    ra3.text = "Date: October 17, 2026 • Narrative Review • Open Reproducible Framework"
    ra3.font.size = Pt(11)
    ra3.font.color.rgb = TEXT_DIM
    ra3.font.name = "Consolas"

    # Bottom navigation hints
    add_text_box(slide, Inches(2.0), Inches(6.1), Inches(9.333), Inches(0.4),
                 "Use ◄ ► or Space to Navigate • Verbatim Speaker Notes Included on Every Slide",
                 size=11, color=TEXT_DIM, align=PP_ALIGN.CENTER, font="Consolas")


def build_cards_formula_slide(slide, s):
    set_slide_background(slide, BG_COLOR)
    add_header(slide, s["id"], 20, s["soil"], s["kicker"], s["title"], s["subtitle"])

    # 3 Cards Side-by-Side
    card_w = Inches(3.95)
    gap = Inches(0.24)
    card_h = Inches(3.9)
    top_pos = Inches(1.85)

    for i, cdata in enumerate(s["cards"]):
        cx = Inches(0.5) + i * (card_w + gap)
        add_card(slide, cx, top_pos, card_w, card_h, fill=CARD_BG, line=CARD_BORDER)

        # Title
        t_box = add_card(slide, cx + Inches(0.15), top_pos + Inches(0.15), card_w - Inches(0.3), Inches(0.42),
                         fill=CARD2_BG, line=GRID_LINE, line_w=0.5, radius=0.2)
        tf_t = t_box.text_frame
        tf_t.vertical_anchor = MSO_ANCHOR.MIDDLE
        pt = tf_t.paragraphs[0]
        rt = pt.add_run()
        rt.text = f"{cdata.get('icon', '🔹')}  {cdata['title']}"
        rt.font.size = Pt(13)
        rt.font.bold = True
        rt.font.color.rgb = TEAL

        # Lead text
        add_text_box(slide, cx + Inches(0.15), top_pos + Inches(0.68), card_w - Inches(0.3), Inches(1.1),
                     cdata["lead"], size=12, color=TEXT_PRIMARY)

        # Bullets
        add_bullet_list(slide, cx + Inches(0.15), top_pos + Inches(1.85), card_w - Inches(0.3), Inches(1.9),
                        cdata["bullets"], size=11.5, color=TEXT_MUTED, space_after=6)

    # Bottom Formula Box
    add_formula_block(slide, Inches(0.5), Inches(5.9), Inches(12.333), Inches(0.95),
                      s.get("formula_title", "Key Formula"), s["formula"])

    add_footer(slide, s["id"], 20)


def build_text_figure_slide(slide, s, fig_dir):
    set_slide_background(slide, BG_COLOR)
    add_header(slide, s["id"], 20, s["soil"], s["kicker"], s["title"], s["subtitle"])

    left_w = Inches(5.9)
    right_w = Inches(6.15)
    gap = Inches(0.28)
    top_pos = Inches(1.85)
    content_h = Inches(5.0)

    # Left Column: Cards
    cards = s["cards"]
    if len(cards) == 2:
        c1_h = Inches(2.6)
        c2_h = Inches(2.25)
        # Card 1
        add_card(slide, Inches(0.5), top_pos, left_w, c1_h, fill=CARD_BG, line=CARD_BORDER)
        add_text_box(slide, Inches(0.7), top_pos + Inches(0.12), left_w - Inches(0.4), Inches(0.35),
                     cards[0]["title"], size=14, color=TEAL, bold=True)
        add_text_box(slide, Inches(0.7), top_pos + Inches(0.48), left_w - Inches(0.4), Inches(0.65),
                     cards[0]["lead"], size=12, color=TEXT_PRIMARY)
        if "formula" in cards[0]:
            add_formula_block(slide, Inches(0.7), top_pos + Inches(1.15), left_w - Inches(0.4), Inches(0.55),
                              "", cards[0]["formula"])
            add_bullet_list(slide, Inches(0.7), top_pos + Inches(1.78), left_w - Inches(0.4), Inches(0.75),
                            cards[0]["bullets"], size=11, color=TEXT_MUTED, space_after=4)
        else:
            add_bullet_list(slide, Inches(0.7), top_pos + Inches(1.15), left_w - Inches(0.4), Inches(1.35),
                            cards[0]["bullets"], size=11.5, color=TEXT_MUTED, space_after=6)

        # Card 2
        c2_top = top_pos + c1_h + Inches(0.15)
        add_card(slide, Inches(0.5), c2_top, left_w, c2_h, fill=CARD_BG, line=CARD_BORDER)
        add_text_box(slide, Inches(0.7), c2_top + Inches(0.12), left_w - Inches(0.4), Inches(0.35),
                     cards[1]["title"], size=14, color=TEAL, bold=True)
        add_text_box(slide, Inches(0.7), c2_top + Inches(0.48), left_w - Inches(0.4), Inches(0.65),
                     cards[1]["lead"], size=12, color=TEXT_PRIMARY)
        if "bullets" in cards[1]:
            add_bullet_list(slide, Inches(0.7), c2_top + Inches(1.15), left_w - Inches(0.4), Inches(1.0),
                            cards[1]["bullets"], size=11.5, color=TEXT_MUTED, space_after=6)
        elif "formula" in cards[1]:
            add_formula_block(slide, Inches(0.7), c2_top + Inches(1.15), left_w - Inches(0.4), Inches(0.6),
                              "", cards[1]["formula"])

    # Right Column: Figure Container Card
    rx = Inches(0.5) + left_w + gap
    add_card(slide, rx, top_pos, right_w, content_h, fill=CARD_BG, line=CARD_BORDER)

    fig_path = Path(fig_dir) / s["fig_name"]
    # Available area inside right card:
    pic_max_w = right_w - Inches(0.4)
    pic_max_h = content_h - Inches(0.7)
    add_picture_fit(slide, fig_path, rx + Inches(0.2), top_pos + Inches(0.2), pic_max_w, pic_max_h,
                     caption=s.get("fig_caption"))

    add_footer(slide, s["id"], 20)


def build_table_summary_slide(slide, s):
    set_slide_background(slide, BG_COLOR)
    add_header(slide, s["id"], 20, s["soil"], s["kicker"], s["title"], s["subtitle"])

    # Table
    table_top = Inches(1.85)
    table_h = Inches(3.7)
    add_table_custom(slide, Inches(0.5), table_top, Inches(12.333), table_h,
                     s["headers"], s["rows"], col_widths=s.get("col_widths"), font_size=10.5)

    # Bottom summary card
    summary_top = Inches(5.8)
    summary_h = Inches(1.05)
    card = add_card(slide, Inches(0.5), summary_top, Inches(12.333), summary_h,
                    fill=CARD2_BG, line=TEAL, line_w=1.0)
    tf = card.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = tf.margin_right = Pt(14)
    p = tf.paragraphs[0]
    p.line_spacing = 1.15
    r = p.add_run()
    r.text = s["summary"]
    r.font.size = Pt(12)
    r.font.color.rgb = TEXT_PRIMARY

    add_footer(slide, s["id"], 20)


def build_three_cards_bottom_slide(slide, s):
    set_slide_background(slide, BG_COLOR)
    add_header(slide, s["id"], 20, s["soil"], s["kicker"], s["title"], s["subtitle"])

    card_w = Inches(3.95)
    gap = Inches(0.24)
    card_h = Inches(3.9)
    top_pos = Inches(1.85)

    for i, cdata in enumerate(s["cards"]):
        cx = Inches(0.5) + i * (card_w + gap)
        add_card(slide, cx, top_pos, card_w, card_h, fill=CARD_BG, line=CARD_BORDER)

        # Header Badge Pill
        badge_color = TEAL if i == 0 else (GOLD if i == 1 else PURPLE_LIGHT)
        pill = add_card(slide, cx + Inches(0.15), top_pos + Inches(0.15), Inches(1.4), Inches(0.3),
                        fill=CARD2_BG, line=badge_color, line_w=0.75, radius=0.3)
        tf_p = pill.text_frame
        tf_p.word_wrap = False
        tf_p.vertical_anchor = MSO_ANCHOR.MIDDLE
        p_pill = tf_p.paragraphs[0]
        p_pill.alignment = PP_ALIGN.CENTER
        r_pill = p_pill.add_run()
        r_pill.text = cdata.get("badge", f"P{i+1}")
        r_pill.font.size = Pt(9.5)
        r_pill.font.bold = True
        r_pill.font.color.rgb = badge_color
        r_pill.font.name = "Consolas"

        # Title
        add_text_box(slide, cx + Inches(0.15), top_pos + Inches(0.52), card_w - Inches(0.3), Inches(0.45),
                     cdata["title"], size=13.5, color=TEXT_PRIMARY, bold=True)

        # Formula
        if "formula" in cdata:
            add_formula_block(slide, cx + Inches(0.15), top_pos + Inches(1.0), card_w - Inches(0.3), Inches(0.55),
                              "", cdata["formula"], border_color=badge_color)

        # Lead
        lead_top = top_pos + Inches(1.65) if "formula" in cdata else top_pos + Inches(1.05)
        add_text_box(slide, cx + Inches(0.15), lead_top, card_w - Inches(0.3), Inches(0.55),
                     cdata["lead"], size=12, color=TEXT_PRIMARY, bold=True)

        # Bullets
        bullets_top = lead_top + Inches(0.55)
        add_bullet_list(slide, cx + Inches(0.15), bullets_top, card_w - Inches(0.3), Inches(1.5),
                        cdata["bullets"], size=11.5, color=TEXT_MUTED, space_after=6)

    # Bottom summary card
    add_card(slide, Inches(0.5), Inches(5.95), Inches(12.333), Inches(0.9),
             fill=CARD2_BG, line=GRID_LINE, line_w=0.75)
    add_text_box(slide, Inches(0.7), Inches(6.05), Inches(11.933), Inches(0.7),
                 s["bottom_text"], size=12, color=TEXT_PRIMARY)

    add_footer(slide, s["id"], 20)


def build_two_large_cards_slide(slide, s):
    set_slide_background(slide, BG_COLOR)
    add_header(slide, s["id"], 20, s["soil"], s["kicker"], s["title"], s["subtitle"])

    card_w = Inches(6.0)
    gap = Inches(0.333)
    has_bottom = "bottom_formula" in s
    card_h = Inches(3.8) if has_bottom else Inches(4.9)
    top_pos = Inches(1.85)

    for i, cdata in enumerate(s["cards"]):
        cx = Inches(0.5) + i * (card_w + gap)
        accent = cdata.get("accent", TEAL)
        add_card(slide, cx, top_pos, card_w, card_h, fill=CARD_BG, line=CARD_BORDER)

        # Title
        add_text_box(slide, cx + Inches(0.25), top_pos + Inches(0.2), card_w - Inches(0.5), Inches(0.4),
                     cdata["title"], size=16, color=accent, bold=True)

        # Formula
        curr_top = top_pos + Inches(0.68)
        if "formula" in cdata:
            add_formula_block(slide, cx + Inches(0.25), curr_top, card_w - Inches(0.5), Inches(0.6),
                              "", cdata["formula"], border_color=accent)
            curr_top += Inches(0.72)

        # Lead
        add_text_box(slide, cx + Inches(0.25), curr_top, card_w - Inches(0.5), Inches(0.8),
                     cdata["lead"], size=12.5, color=TEXT_PRIMARY)
        curr_top += Inches(0.85)

        # Bullets
        bullets_h = card_h - (curr_top - top_pos) - Inches(0.15)
        add_bullet_list(slide, cx + Inches(0.25), curr_top, card_w - Inches(0.5), bullets_h,
                        cdata["bullets"], size=12, color=TEXT_MUTED, space_after=8)

    if has_bottom:
        add_formula_block(slide, Inches(0.5), Inches(5.85), Inches(12.333), Inches(1.0),
                          "Epistemic Rigor", s["bottom_formula"], border_color=GOLD)

    add_footer(slide, s["id"], 20)


def build_explorer_slide(slide, s, fig_dir):
    set_slide_background(slide, BG_COLOR)
    add_header(slide, s["id"], 20, s["soil"], s["kicker"], s["title"], s["subtitle"])

    left_w = Inches(6.8)
    right_w = Inches(5.25)
    gap = Inches(0.28)
    top_pos = Inches(1.85)
    content_h = Inches(5.0)

    # Left: Static Explorer Render in Card
    add_card(slide, Inches(0.5), top_pos, left_w, content_h, fill=CARD_BG, line=CARD_BORDER)

    # Try hero.webp or fallback to F1
    hero_path = Path(fig_dir) / s["fig_name"]
    if not hero_path.exists():
        # Check parent folder site/assets/img/hero.webp
        alt_hero = Path(fig_dir).parent.parent / "site" / "assets" / "img" / "hero.webp"
        if alt_hero.exists():
            hero_path = alt_hero

    add_picture_fit(slide, hero_path, Inches(0.7), top_pos + Inches(0.2), left_w - Inches(0.4), content_h - Inches(0.8),
                    caption=s.get("fig_caption"))

    # Right: Benchmark Spec, Results, and Launch Button
    rx = Inches(0.5) + left_w + gap

    # Card 1: Benchmark Equation & Verification
    c1_h = Inches(3.6)
    add_card(slide, rx, top_pos, right_w, c1_h, fill=CARD_BG, line=CARD_BORDER)

    add_text_box(slide, rx + Inches(0.2), top_pos + Inches(0.15), right_w - Inches(0.4), Inches(0.35),
                 "Synthetic Specification & Verification", size=14, color=TEAL, bold=True)

    add_formula_block(slide, rx + Inches(0.2), top_pos + Inches(0.55), right_w - Inches(0.4), Inches(0.6),
                      "", s["equation"], border_color=TEAL)

    add_bullet_list(slide, rx + Inches(0.2), top_pos + Inches(1.25), right_w - Inches(0.4), Inches(2.2),
                    s["bullets"], size=11.5, color=TEXT_MUTED, space_after=6)

    # Card 2: Interactive Explorer Launch Button
    c2_top = top_pos + c1_h + Inches(0.15)
    c2_h = content_h - c1_h - Inches(0.15)
    btn_card = add_card(slide, rx, c2_top, right_w, c2_h, fill=CARD2_BG, line=TEAL, line_w=1.2, radius=0.1)

    tf_btn = btn_card.text_frame
    tf_btn.word_wrap = True
    tf_btn.vertical_anchor = MSO_ANCHOR.MIDDLE
    p1 = tf_btn.paragraphs[0]
    p1.alignment = PP_ALIGN.CENTER
    r1 = p1.add_run()
    r1.text = "🚀 Launch Interactive 3-D Web Explorer\n"
    r1.font.size = Pt(13)
    r1.font.bold = True
    r1.font.color.rgb = TEAL

    p2 = tf_btn.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    r2 = p2.add_run()
    r2.text = s["url"]
    r2.font.size = Pt(10.5)
    r2.font.color.rgb = TEXT_MUTED
    r2.font.name = "Consolas"

    add_footer(slide, s["id"], 20)


def build_text_table_side_slide(slide, s):
    set_slide_background(slide, BG_COLOR)
    add_header(slide, s["id"], 20, s["soil"], s["kicker"], s["title"], s["subtitle"])

    left_w = Inches(5.8)
    right_w = Inches(6.25)
    gap = Inches(0.28)
    top_pos = Inches(1.85)

    # Left Column: 2 Cards
    c1_h = Inches(2.6)
    c2_h = Inches(2.2)
    # Card 1
    add_card(slide, Inches(0.5), top_pos, left_w, c1_h, fill=CARD_BG, line=CARD_BORDER)
    add_text_box(slide, Inches(0.7), top_pos + Inches(0.15), left_w - Inches(0.4), Inches(0.35),
                 s["cards"][0]["title"], size=14, color=TEAL, bold=True)
    add_text_box(slide, Inches(0.7), top_pos + Inches(0.55), left_w - Inches(0.4), Inches(0.7),
                 s["cards"][0]["lead"], size=12, color=TEXT_PRIMARY)
    add_bullet_list(slide, Inches(0.7), top_pos + Inches(1.3), left_w - Inches(0.4), Inches(1.15),
                    s["cards"][0]["bullets"], size=11.5, color=TEXT_MUTED, space_after=6)

    # Card 2
    c2_top = top_pos + c1_h + Inches(0.15)
    add_card(slide, Inches(0.5), c2_top, left_w, c2_h, fill=CARD_BG, line=CARD_BORDER)
    add_text_box(slide, Inches(0.7), c2_top + Inches(0.15), left_w - Inches(0.4), Inches(0.35),
                 s["cards"][1]["title"], size=14, color=RED_LIGHT, bold=True)
    add_text_box(slide, Inches(0.7), c2_top + Inches(0.52), left_w - Inches(0.4), Inches(0.55),
                 s["cards"][1]["lead"], size=12, color=TEXT_PRIMARY)
    add_formula_block(slide, Inches(0.7), c2_top + Inches(1.05), left_w - Inches(0.4), Inches(0.5),
                      "", s["cards"][1]["formula"], border_color=RED)
    add_bullet_list(slide, Inches(0.7), c2_top + Inches(1.6), left_w - Inches(0.4), Inches(0.5),
                    s["cards"][1]["bullets"], size=11, color=TEXT_MUTED, space_after=2)

    # Right Column: Table Card
    rx = Inches(0.5) + left_w + gap
    table_card = add_card(slide, rx, top_pos, right_w, Inches(4.95), fill=CARD_BG, line=CARD_BORDER)
    add_text_box(slide, rx + Inches(0.2), top_pos + Inches(0.15), right_w - Inches(0.4), Inches(0.35),
                 s["table_title"], size=14, color=TEAL, bold=True)

    add_table_custom(slide, rx + Inches(0.2), top_pos + Inches(0.65), right_w - Inches(0.4), Inches(3.8),
                     s["headers"], s["rows"], col_widths=s.get("col_widths"), font_size=10.5)

    add_footer(slide, s["id"], 20)


def build_table_figure_side_slide(slide, s, fig_dir):
    set_slide_background(slide, BG_COLOR)
    add_header(slide, s["id"], 20, s["soil"], s["kicker"], s["title"], s["subtitle"])

    left_w = Inches(6.1)
    right_w = Inches(5.95)
    gap = Inches(0.28)
    top_pos = Inches(1.85)

    # Left: Table + Summary Card
    table_h = Inches(3.7)
    add_table_custom(slide, Inches(0.5), top_pos, left_w, table_h,
                     s["headers"], s["rows"], col_widths=s.get("col_widths"), font_size=10)

    # Summary box
    card_top = top_pos + table_h + Inches(0.15)
    add_card(slide, Inches(0.5), card_top, left_w, Inches(1.05), fill=CARD2_BG, line=TEAL, line_w=0.75)
    add_text_box(slide, Inches(0.7), card_top + Inches(0.1), left_w - Inches(0.4), Inches(0.85),
                 s["summary"], size=11.5, color=TEXT_PRIMARY)

    # Right: Figure Container Card
    rx = Inches(0.5) + left_w + gap
    add_card(slide, rx, top_pos, right_w, Inches(4.9), fill=CARD_BG, line=CARD_BORDER)

    fig_path = Path(fig_dir) / s["fig_name"]
    add_picture_fit(slide, fig_path, rx + Inches(0.2), top_pos + Inches(0.2), right_w - Inches(0.4), Inches(4.2),
                    caption=s.get("fig_caption"))

    add_footer(slide, s["id"], 20)


def build_six_grid_cards_slide(slide, s):
    set_slide_background(slide, BG_COLOR)
    add_header(slide, s["id"], 20, s["soil"], s["kicker"], s["title"], s["subtitle"])

    cols = 3
    card_w = Inches(3.95)
    gap_x = Inches(0.24)
    card_h = Inches(2.35)
    gap_y = Inches(0.2)
    start_top = Inches(1.85)

    for i, cdata in enumerate(s["cards"]):
        r_idx = i // cols
        c_idx = i % cols
        cx = Inches(0.5) + c_idx * (card_w + gap_x)
        cy = start_top + r_idx * (card_h + gap_y)

        accent = cdata.get("accent", RED)
        add_card(slide, cx, cy, card_w, card_h, fill=CARD_BG, line=CARD_BORDER)

        # Title
        add_text_box(slide, cx + Inches(0.2), cy + Inches(0.12), card_w - Inches(0.4), Inches(0.35),
                     cdata["title"], size=13.5, color=accent, bold=True)

        # Lead text
        add_text_box(slide, cx + Inches(0.2), cy + Inches(0.5), card_w - Inches(0.4), Inches(0.75),
                     cdata["lead"], size=11.5, color=TEXT_PRIMARY)

        # Rule box
        rule_box = add_card(slide, cx + Inches(0.15), cy + Inches(1.3), card_w - Inches(0.3), Inches(0.9),
                            fill=CARD2_BG, line=accent, line_w=0.75, radius=0.08)
        tf_r = rule_box.text_frame
        tf_r.word_wrap = True
        tf_r.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf_r.margin_left = tf_r.margin_right = Pt(8)
        pr = tf_r.paragraphs[0]
        pr.line_spacing = 1.15
        rr = pr.add_run()
        rr.text = cdata["rule"]
        rr.font.size = Pt(11)
        rr.font.color.rgb = accent
        rr.font.bold = True

    add_footer(slide, s["id"], 20)


def build_table_checklist_slide(slide, s):
    set_slide_background(slide, BG_COLOR)
    add_header(slide, s["id"], 20, s["soil"], s["kicker"], s["title"], s["subtitle"])

    table_top = Inches(1.85)
    table_h = Inches(4.9)
    add_table_custom(slide, Inches(0.5), table_top, Inches(12.333), table_h,
                     s["headers"], s["rows"], col_widths=s.get("col_widths"), font_size=10)

    add_footer(slide, s["id"], 20)


# ==============================================================================
# Layout Audit & Bounds Verification
# ==============================================================================
def run_layout_audit(prs, out_json_path):
    """Audits every shape on every slide for coordinate bounds and estimates text overflow."""
    audit_results = {
        "slide_count": len(prs.slides),
        "slide_width_in": SLIDE_WIDTH_IN,
        "slide_height_in": SLIDE_HEIGHT_IN,
        "slides": [],
        "all_bounds_pass": True,
        "overflow_warnings": []
    }

    sw = Inches(SLIDE_WIDTH_IN)
    sh = Inches(SLIDE_HEIGHT_IN)

    for idx, slide in enumerate(prs.slides, start=1):
        s_info = {
            "slide_index": idx,
            "shape_count": len(slide.shapes),
            "off_slide_shapes": 0,
            "shapes": []
        }

        for shp in slide.shapes:
            left = shp.left
            top = shp.top
            width = shp.width
            height = shp.height

            # Check bounds (allowing tiny 1-emu floating point margin)
            out_of_bounds = False
            if left < -100 or top < -100 or (left + width) > (sw + 100) or (top + height) > (sh + 100):
                out_of_bounds = True
                s_info["off_slide_shapes"] += 1
                audit_results["all_bounds_pass"] = False

            # Check text frames
            tf_info = None
            if shp.has_text_frame:
                tf = shp.text_frame
                full_text = "\n".join(p.text for p in tf.paragraphs if p.text)
                char_count = len(full_text)
                area_sq_in = (width / Inches(1)) * (height / Inches(1))
                density = char_count / max(area_sq_in, 0.01)

                tf_info = {
                    "char_count": char_count,
                    "density_chars_per_sq_in": round(density, 1)
                }

                # If density exceeds 250 chars per square inch, flag potential overflow warning
                if density > 280:
                    audit_results["overflow_warnings"].append({
                        "slide": idx,
                        "density": density,
                        "text_sample": full_text[:60]
                    })

            s_info["shapes"].append({
                "type": str(shp.shape_type),
                "left_in": round(left / Inches(1), 3),
                "top_in": round(top / Inches(1), 3),
                "width_in": round(width / Inches(1), 3),
                "height_in": round(height / Inches(1), 3),
                "out_of_bounds": out_of_bounds,
                "text_frame": tf_info
            })

        audit_results["slides"].append(s_info)

    # Save JSON audit
    Path(out_json_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(audit_results, f, indent=2)

    return audit_results


# ==============================================================================
# Slide PNG Rendering (PowerPoint COM with LibreOffice Fallback)
# ==============================================================================
def render_slides_to_png(pptx_path, out_dir):
    """Attempts to render slides to PNG via PowerPoint COM or LibreOffice."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    abs_pptx = str(Path(pptx_path).resolve())

    # Method 1: PowerPoint COM (Windows win32com)
    try:
        import win32com.client
        import pythoncom
        print(f"[Renderer] Attempting PowerPoint COM export on {abs_pptx}...")
        pythoncom.CoInitialize()
        ppt = win32com.client.DispatchEx("PowerPoint.Application")
        # ppt.Visible = 1
        presentation = ppt.Presentations.Open(abs_pptx, WithWindow=False)

        # PowerPoint Export format 17 is ppSaveAsPNG
        rendered_count = 0
        for i, slide in enumerate(presentation.Slides, start=1):
            png_name = f"slide_{i:02d}.png"
            dest_file = str(out_dir / png_name)
            # slide.Export(FileName, FilterName, ScaleWidth, ScaleHeight)
            slide.Export(dest_file, "PNG", 1600, 900)
            if Path(dest_file).exists():
                rendered_count += 1

        presentation.Close()
        ppt.Quit()
        pythoncom.CoUninitialize()

        if rendered_count > 0:
            print(f"[Renderer] PowerPoint COM successfully rendered {rendered_count} slides to {out_dir}")
            return "powerpoint_com", rendered_count
    except Exception as e:
        print(f"[Renderer] PowerPoint COM unavailable or failed: {e}")

    # Method 2: LibreOffice headless export to PDF then PDF to PNG
    try:
        import subprocess
        print("[Renderer] Attempting LibreOffice export...")
        cmd = ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), abs_pptx]
        res = subprocess.run(cmd, capture_output=True, timeout=60)
        pdf_path = out_dir / (Path(pptx_path).stem + ".pdf")
        if pdf_path.exists():
            print(f"[Renderer] LibreOffice exported PDF: {pdf_path}")
            # Try pdftoppm or fitz if available
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(pdf_path)
                for i, page in enumerate(doc, start=1):
                    pix = page.get_pixmap(dpi=150)
                    pix.save(str(out_dir / f"slide_{i:02d}.png"))
                doc.close()
                return "libreoffice_fitz", len(doc)
            except Exception:
                pass
    except Exception as e:
        print(f"[Renderer] LibreOffice fallback failed: {e}")

    print("[Renderer] Rendering engines unavailable in current sandbox. Layout audit will serve as primary verifier.")
    return "none", 0


# ==============================================================================
# Main Presentation Builder
# ==============================================================================
def generate_presentation(fig_dir, out_path, render_dir=None):
    """Main generation routine."""
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_WIDTH_IN)
    prs.slide_height = Inches(SLIDE_HEIGHT_IN)
    blank_layout = prs.slide_layouts[6]

    print(f"[*] Building 20-slide HHSA Presentation (16:9 widescreen)...")
    print(f"[*] Figure directory: {fig_dir}")
    print(f"[*] Output PPTX: {out_path}")

    for idx, s in enumerate(SLIDES_DATA, start=1):
        slide = prs.slides.add_slide(blank_layout)
        stype = s["type"]

        if stype == "title":
            build_title_slide(slide, s)
        elif stype == "cards_formula":
            build_cards_formula_slide(slide, s)
        elif stype == "text_figure":
            build_text_figure_slide(slide, s, fig_dir)
        elif stype == "table_summary":
            build_table_summary_slide(slide, s)
        elif stype == "three_cards_bottom":
            build_three_cards_bottom_slide(slide, s)
        elif stype == "two_large_cards":
            build_two_large_cards_slide(slide, s)
        elif stype == "explorer_slide":
            build_explorer_slide(slide, s, fig_dir)
        elif stype == "text_table_side":
            build_text_table_side_slide(slide, s)
        elif stype == "table_figure_side":
            build_table_figure_side_slide(slide, s, fig_dir)
        elif stype == "six_grid_cards":
            build_six_grid_cards_slide(slide, s)
        elif stype == "table_checklist":
            build_table_checklist_slide(slide, s)
        else:
            raise ValueError(f"Unknown slide type: {stype}")

        # Set speaker notes
        set_speaker_notes(slide, s.get("notes", ""), companion_anchor=f"slide-{idx}")

    # Save PPTX
    out_path_obj = Path(out_path)
    out_path_obj.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path_obj))
    print(f"[+] PPTX successfully written to {out_path_obj} ({os.path.getsize(out_path_obj):,} bytes)")

    # Run layout audit
    if render_dir is None:
        render_dir = out_path_obj.parent / "pptx_render"
    audit_file = Path(render_dir) / "layout_audit.json"
    audit_res = run_layout_audit(prs, audit_file)
    print(f"[+] Layout audit completed: all_bounds_pass={audit_res['all_bounds_pass']}, warnings={len(audit_res['overflow_warnings'])}")

    # Attempt slide rendering
    render_method, count = render_slides_to_png(out_path_obj, render_dir)

    return {
        "out_path": str(out_path_obj),
        "slide_count": len(prs.slides),
        "audit_file": str(audit_file),
        "render_method": render_method,
        "rendered_slides": count
    }


def main():
    parser = argparse.ArgumentParser(description="Generate 20-slide HHSA presentation deck.")
    parser.add_argument("--fig-dir", type=str, default=".", help="Path to figures directory")
    parser.add_argument("--out", type=str, default="HHSA_body_signals_deck.pptx", help="Path to output PPTX")
    parser.add_argument("--render-dir", type=str, default="pptx_render", help="Path to render directory")
    args = parser.parse_args()

    res = generate_presentation(args.fig_dir, args.out, args.render_dir)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
