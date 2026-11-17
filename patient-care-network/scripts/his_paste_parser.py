#!/usr/bin/env python3
"""Standalone HIS paste parser: clinician-copied HIS text -> reviewable values -> import CSV.

Deterministic rules only (no LLM): label patterns (Chinese and English), NFKC
folding, re.ASCII word boundaries, span claiming in priority order, several
values per line, reference-range skipping, unit conversion with notes, ROC
dates, yes/no history with negation, plausibility and duplicate warnings, and
a list of numeric lines that no rule used.

Usage:
    python his_paste_parser.py --selftest
    python his_paste_parser.py report.txt                # JSON of fields
    python his_paste_parser.py report.txt --csv --chart TST-0001 --date 2026-11-10 \
        [--existing TST-0001,CH-123]                     # import CSV per record type

Copied from the Smart Diabetes Care Network reference build
(app/services/his_input.py). Adapt the label table and the CSV columns to your
own import schema. Never store or log the pasted text.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from typing import Any


def today() -> date:
    return date.today()


LAB_FIELDS = (
    "hba1c", "fpg", "egfr", "uacr", "ast", "alt", "platelets", "creatinine",
    "total_cholesterol", "ldl", "hdl", "triglycerides", "potassium", "sbp", "dbp",
    "weight_kg", "bmi",
)
BOOL_FIELDS = ("current_smoker", "prior_mi", "prior_cabg", "ascvd")
CONDITION_NAMES = {
    "current_smoker": "Current smoker",
    "prior_mi": "Prior myocardial infarction",
    "prior_cabg": "Prior CABG",
    "ascvd": "Established ASCVD",
}
DR_GRADES = ("none", "mild_npdr", "moderate_npdr", "severe_npdr", "pdr", "maculopathy")

# Plausible range after conversion to the canonical unit. Outside it the value
# is still filled in but flagged, so a unit mistake is caught by a person.
RANGES: dict[str, tuple[float, float]] = {
    "hba1c": (3, 20), "fpg": (20, 1000), "egfr": (1, 200), "uacr": (0, 10000),
    "ast": (1, 5000), "alt": (1, 5000), "platelets": (5, 1500), "creatinine": (0.1, 20),
    "total_cholesterol": (50, 600), "ldl": (10, 400), "hdl": (5, 200), "triglycerides": (10, 5000),
    "potassium": (1.5, 9), "sbp": (60, 260), "dbp": (30, 160), "weight_kg": (20, 300),
    "height_cm": (100, 230), "bmi": (10, 80), "qrs_ms": (40, 250), "age": (18, 110),
}
UNITS = {
    "hba1c": "%", "fpg": "mg/dL", "egfr": "mL/min/1.73m²", "uacr": "mg/g", "ast": "U/L", "alt": "U/L",
    "platelets": "10³/µL", "creatinine": "mg/dL", "total_cholesterol": "mg/dL", "ldl": "mg/dL",
    "hdl": "mg/dL", "triglycerides": "mg/dL", "potassium": "mmol/L", "sbp": "mmHg", "dbp": "mmHg",
    "weight_kg": "kg", "height_cm": "cm", "bmi": "kg/m²", "qrs_ms": "ms", "age": "years",
}

_I = re.IGNORECASE | re.ASCII  # ASCII: CJK characters count as word boundaries
_NUM = r"(\d+(?:\.\d+)?)"
_DATE = r"((?:19|20)\d{2}|\d{2,3})[-/.年](\d{1,2})[-/.月](\d{1,2})日?"

# (field, label regex). Order matters: a line is claimed by the first numeric
# field that matches, so specific labels (UACR, HDL) come before generic ones
# (creatinine, cholesterol).
_NUMERIC_LABELS: list[tuple[str, str]] = [
    ("uacr", r"UACR|\bACR\b|alb(?:umin)?\s*/\s*cre(?:atinine)?|micro\s*-?alb\w*\s*/\s*cre\w*|MAU\s*/\s*CRE|"
             r"白蛋白\s*/\s*肌酸酐|微白蛋白.{0,6}肌酸酐|尿液?白蛋白.{0,4}比"),
    ("egfr", r"\beGFR\b|\bGFR\b|腎絲球過濾率"),
    ("hba1c", r"Hb\s*A1c|\bA1c\b|HbA1C|糖化血色素|糖化血紅素"),
    ("fpg", r"\bFPG\b|\bGLU[-\s]?AC\b|\bAC\s*(?:sugar|glucose)\b|(?:glucose|sugar)\s*[-(]?\s*AC\b|"
            r"fasting\s+(?:plasma\s+)?glucose|空腹血糖"),
    ("ast", r"\bAST\b|\bS?GOT\b|草醋酸轉胺"),
    ("alt", r"\bALT\b|\bS?GPT\b|丙酮酸轉胺"),
    ("platelets", r"\bPLT\b|platelets?|血小板"),
    ("hdl", r"(?<!non[-\s])\bHDL(?:-?C(?:hol\w*)?)?\b|高密度"),
    ("ldl", r"\bLDL(?:-?C(?:hol\w*)?)?\b|低密度"),
    ("triglycerides", r"\bTG\b|triglycerides?|三酸甘油"),
    ("total_cholesterol", r"\bT-?CHO(?:L)?\b|total\s+cholesterol|總膽固醇|^\s*cholesterol\b"),
    ("creatinine", r"\bcreatinine\b|\bCREA?\b|\bCr\b|肌酸酐"),
    ("potassium", r"potassium|鉀|\bK\b(?=\s*[:：=]?\s*\d)"),
    ("sbp", r"\bSBP\b|systolic|收縮壓"),
    ("dbp", r"\bDBP\b|diastolic|舒張壓"),
    ("weight_kg", r"\bweight\b|\bBW\b|體重"),
    ("height_cm", r"\bheight\b|\bBH\b|身高"),
    ("bmi", r"\bBMI\b|身體質量"),
    ("qrs_ms", r"\bQRS\b"),
]
_COMPILED = [(f, re.compile(p, _I)) for f, p in _NUMERIC_LABELS]
_URINE = re.compile(r"urine|\bU[-\s]?CRE|尿", _I)
_BP = re.compile(r"(?:\bBP\b|血壓|SBP\s*/\s*DBP)[^0-9]{0,12}(\d{2,3})\s*/\s*(\d{2,3})", _I)
_RANGE = re.compile(r"\d+(?:\.\d+)?\s*[-~～]\s*\d+(?:\.\d+)?")
_NEG = re.compile(r"\b(no|not|denie[sd]|never|non|negative|without|none)\b|無|否|未|沒有|陰性|\(-\)", _I)


@dataclass
class Found:
    value: Any
    source: str
    line: int
    unit: str | None = None
    note: str | None = None
    warnings: list[str] = field(default_factory=list)


def _norm(text: str) -> str:
    # NFKC folds full-width digits, letters and punctuation (common in HIS exports).
    return unicodedata.normalize("NFKC", text or "").replace("μ", "µ")


def _first_number(rest: str) -> tuple[float, str] | None:
    """First number in `rest` that is not part of a reference range."""
    cleaned = _RANGE.sub(" ", re.sub(r"\[[^\]]*\]", " ", rest))
    m = re.search(_NUM, cleaned)
    if not m:
        return None
    return float(m.group(1)), cleaned[m.end(): m.end() + 24]


def _parse_date(y: str, m: str, d: str) -> str | None:
    year = int(y)
    if year < 200:  # ROC (民國) year
        year += 1911
    try:
        return date(year, int(m), int(d)).isoformat()
    except ValueError:
        return None


def _convert(fld: str, value: float, after: str, line: str) -> tuple[float, str | None, str | None]:
    """Return (value in canonical unit, unit seen, conversion note)."""
    unit_text = (after + " " + line).lower()
    if fld == "creatinine" and re.search(r"[uµ]mol", unit_text):
        return round(value / 88.4, 2), "µmol/L", "µmol/L ÷ 88.4 → mg/dL"
    if fld in ("fpg",) and "mmol" in unit_text:
        return round(value * 18.0, 0), "mmol/L", "mmol/L × 18 → mg/dL"
    if fld in ("total_cholesterol", "ldl", "hdl") and "mmol" in unit_text:
        return round(value * 38.67, 0), "mmol/L", "mmol/L × 38.67 → mg/dL"
    if fld == "triglycerides" and "mmol" in unit_text:
        return round(value * 88.57, 0), "mmol/L", "mmol/L × 88.57 → mg/dL"
    if fld == "uacr" and "mg/mmol" in unit_text:
        return round(value * 8.84, 1), "mg/mmol", "mg/mmol × 8.84 → mg/g"
    if fld == "hba1c" and ("mmol/mol" in unit_text or value > 20):
        return round(value / 10.929 + 2.15, 1), "mmol/mol", "IFCC mmol/mol → NGSP % (÷10.929 + 2.15)"
    if fld == "platelets":
        if re.search(r"10\^?4|10⁴|萬", unit_text):
            return round(value * 10, 0), "10⁴/µL", "10⁴/µL × 10 → 10³/µL"
        if value > 1500:
            return round(value / 1000, 0), "/µL", "/µL ÷ 1000 → 10³/µL"
    if fld == "height_cm" and value < 3:
        return round(value * 100, 1), "m", "m × 100 → cm"
    if fld == "qrs_ms" and value < 1:
        return round(value * 1000, 0), "s", "s × 1000 → ms"
    return value, None, None


def _bool_from(line: str, term: re.Pattern) -> bool | None:
    m = term.search(line)
    if not m:
        return None
    window = line[max(0, m.start() - 20): m.end() + 12]
    return not bool(_NEG.search(window))


def parse_text(text: str) -> dict:
    """Extract reviewable values from pasted HIS text. Deterministic; nothing stored."""
    lines = [_norm(raw).strip() for raw in (text or "").splitlines()]
    found: dict[str, list[Found]] = {}
    used: set[int] = set()

    def add(key: str, item: Found) -> None:
        found.setdefault(key, []).append(item)

    for i, line in enumerate(lines):
        if not line:
            continue
        src = line[:140]
        # Claim label spans in priority order; a lower-priority label inside a
        # claimed span is ignored (e.g. "Creatinine" inside "Alb/Creatinine").
        claims: list[tuple[str, int, int]] = []
        bp = _BP.search(line)
        if bp:
            add("sbp", Found(float(bp.group(1)), src, i + 1, "mmHg"))
            add("dbp", Found(float(bp.group(2)), src, i + 1, "mmHg"))
            claims.append(("bp", bp.start(), bp.end()))
            used.add(i)
        for fld, pat in _COMPILED:
            if fld == "creatinine" and _URINE.search(line):
                continue  # urine creatinine is not serum creatinine
            for m in pat.finditer(line):
                if any(m.start() < e and s < m.end() for _, s, e in claims):
                    continue
                claims.append((fld, m.start(), m.end()))
                break
        claims.sort(key=lambda c: c[1])
        for idx, (fld, s, e) in enumerate(claims):
            if fld == "bp":
                continue
            nxt = claims[idx + 1][1] if idx + 1 < len(claims) else len(line)
            got = _first_number(line[e:nxt])
            if not got:
                continue
            raw, after = got
            context = line[e:nxt] if len(claims) > 1 else line
            value, unit, note = _convert(fld, raw, after, context)
            add(fld, Found(value, src, i + 1, unit or UNITS.get(fld), note))
            used.add(i)

        # identity and history (independent of the numeric claim above)
        if m2 := re.search(r"(?:病歷號(?:碼)?|chart\s*(?:no|number)\.?|\bMRN\b)\s*[:：#]?\s*([A-Za-z0-9-]{3,20})", line, _I):
            add("chart_number", Found(m2.group(1), src, i + 1)); used.add(i)
        if m2 := re.search(r"姓名\s*[:：]?\s*([一-鿿○〇Ｏ]{2,4})", line) or \
                re.search(r"\bname\s*[:：]\s*([A-Za-z][A-Za-z .'-]{1,40})", line, _I):
            add("name", Found(m2.group(1).strip(), src, i + 1)); used.add(i)
        if m2 := re.search(r"(?:出生(?:日期)?|生日|\bDOB\b|birth\s*date|date\s+of\s+birth)\s*[:：]?\s*" + _DATE, line, _I):
            if d := _parse_date(*m2.groups()):
                add("date_of_birth", Found(d, src, i + 1)); used.add(i)
        if m2 := re.search(r"(?:年齡|\bage\b)\s*[:：]?\s*(\d{1,3})", line, _I) or \
                re.search(r"\b(\d{1,3})\s*(?:歲|y/?o\b|yrs?\b|y(?=\s*[/,]?\s*[MF]\b))", line, _I):
            add("age", Found(int(m2.group(1)), src, i + 1, "years")); used.add(i)
        if m2 := re.search(r"性別\s*[:：]?\s*(男|女)", line) or re.search(r"\bsex\s*[:：]\s*(male|female|m|f)\b", line, _I) or \
                re.search(r"\b\d{1,3}\s*(?:y/?o|歲|y)?\s*[/,]?\s*\b(M|F)\b", line) or re.search(r"\b(male|female)\b", line, _I):
            v = m2.group(1).lower()
            add("sex", Found("male" if v in ("男", "m", "male") else "female", src, i + 1)); used.add(i)
        if m2 := re.search(r"(?:診斷|diagnos\w*|DM\s+since|發病)\D{0,15}?((?:19|20)\d{2}|\d{2,3})\s*年?", line, _I):
            y = int(m2.group(1)); y = y + 1911 if y < 200 else y
            if 1930 <= y <= today().year:
                add("diagnosis_year", Found(y, src, i + 1)); used.add(i)
        elif m2 := re.search(r"(?:罹病|病程|糖尿病\s*史|DM\s+duration|duration)\D{0,10}?(\d{1,2})\s*(?:年|y)", line, _I):
            add("diabetes_duration_years", Found(int(m2.group(1)), src, i + 1, "years")); used.add(i)
        if re.search(r"第\s*1\s*型|type\s*1\b|\bT1D\b|\bT1DM\b", line, _I):
            add("diabetes_type", Found("T1D", src, i + 1)); used.add(i)
        elif re.search(r"第\s*2\s*型|type\s*2\b|\bT2D\b|\bT2DM\b", line, _I):
            add("diabetes_type", Found("T2D", src, i + 1)); used.add(i)
        for key, term in (
            ("current_smoker", re.compile(r"smok\w*|吸菸|抽菸|吸煙", _I)),
            ("prior_mi", re.compile(r"\bMI\b|myocardial\s+infarction|心肌梗塞", _I)),
            ("prior_cabg", re.compile(r"\bCABG\b|冠狀動脈繞道", _I)),
            ("ascvd", re.compile(r"\bASCVD\b|\bCAD\b|stroke|腦中風|中風|\bPAD\b|周邊動脈|冠心病", _I)),
        ):
            state = _bool_from(line, term)
            if state is None:
                continue
            if key == "current_smoker" and re.search(r"\bex-?|former|quit|戒", line, _I):
                state = False
            add(key, Found(state, src, i + 1, note="請確認 / please confirm")); used.add(i)
        if re.search(r"眼底|fundus|視網膜|retinopathy|\bN?PDR\b|\bDR\b", line, _I):
            low = line.lower()
            grade = None
            if re.search(r"macul|黃斑", low):
                grade = "maculopathy"
            elif re.search(r"severe\s*npdr|重度", low):
                grade = "severe_npdr"
            elif re.search(r"moderate\s*npdr|中度", low):
                grade = "moderate_npdr"
            elif re.search(r"mild\s*npdr|輕度", low):
                grade = "mild_npdr"
            elif re.search(r"(?<!n)pdr|增殖性", low) and not re.search(r"非增殖", low):
                grade = "pdr"
            elif re.search(r"no\s+(?:diabetic\s+)?(?:retinopathy|dr)\b|無.{0,4}(?:視網膜)?病變|normal|正常|\bNDR\b", low):
                grade = "none"
            if grade:
                add("fundus_result", Found(grade, src, i + 1)); used.add(i)
                if d := re.search(_DATE, line):
                    if iso := _parse_date(*d.groups()):
                        add("fundus_date", Found(iso, src, i + 1))
        if re.search(r"報告日期|採檢日期|檢驗日期|就診日期|collected|report\s*date|^\s*date\b|日期", line, _I) \
                and not re.search(r"出生|生日|DOB|birth", line, _I):
            if d := re.search(_DATE, line):
                if iso := _parse_date(*d.groups()):
                    add("encounter_date", Found(iso, src, i + 1)); used.add(i)

    fields: dict[str, dict] = {}
    for key, items in found.items():
        first = items[0]
        warnings = list(first.warnings)
        distinct = []
        for it in items:
            if it.value not in distinct:
                distinct.append(it.value)
        if len(distinct) > 1:
            warnings.append(
                f"找到 {len(distinct)} 個不同值（{', '.join(str(v) for v in distinct[:4])}），採用第一個，請確認是最新一筆 / "
                f"{len(distinct)} different values found; the first was used — check it is the latest"
            )
        if key in RANGES and isinstance(first.value, (int, float)) and not isinstance(first.value, bool):
            lo, hi = RANGES[key]
            if not lo <= first.value <= hi:
                warnings.append(f"超出合理範圍 {lo}–{hi}，請確認單位 / outside plausible range {lo}–{hi}; check the unit")
        fields[key] = {
            "value": first.value,
            "unit": UNITS.get(key) or first.unit,
            "unit_in": first.unit if first.note and first.unit != UNITS.get(key) else None,
            "note": first.note,
            "source": first.source,
            "line": first.line,
            "warnings": warnings,
        }
    unmatched = [
        {"line": i + 1, "text": line[:140]}
        for i, line in enumerate(lines)
        if line and i not in used and re.search(r"\d", line)
    ]
    return {
        "fields": fields,
        "unmatched_lines": unmatched[:30],
        "line_count": sum(1 for line in lines if line),
        "method": "deterministic label/unit rules (no LLM); every value must be reviewed",
    }


# --- parsed fields -> import CSV --------------------------------------------------

RECORD_TYPES = {
    "patients": ["chart_number", "name", "date_of_birth", "sex", "diabetes_type", "diagnosis_year", "height_cm"],
    "labs": ["chart_number", "encounter_date", *LAB_FIELDS, "note"],
    "screenings": ["chart_number", "screening_type", "performed_date", "result_code", "result_summary",
                   "is_normal", "next_due_date"],
    "conditions": ["chart_number", "code", "name", "onset_date", "active"],
    "ecg": ["chart_number", "exam_date", "qrs_ms", "rhythm", "interpretation"],
}


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _csv(columns: list[str], rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({c: _fmt(row.get(c)) for c in columns})
    return buf.getvalue()


def to_import_csv(parsed: dict, chart_number: str | None = None, encounter_date: str | None = None,
                  existing_charts: set[str] | None = None) -> dict:
    """CSV text per record type. A patients row only for a chart not in `existing_charts`."""
    f = {k: v["value"] for k, v in (parsed.get("fields") or {}).items()}
    chart = (chart_number or f.get("chart_number") or "").strip()
    encounter = encounter_date or f.get("encounter_date") or ""
    exists = bool(chart) and chart in (existing_charts or set())
    notes: list[str] = []
    out: dict[str, str] = {}
    if not chart:
        notes.append("No chart number found: fill in chart_number.")
    if chart and not exists:
        diagnosis_year = f.get("diagnosis_year")
        if diagnosis_year is None and f.get("diabetes_duration_years") is not None:
            diagnosis_year = today().year - int(f["diabetes_duration_years"])
        out["patients"] = _csv(RECORD_TYPES["patients"], [{
            "chart_number": chart, "name": f.get("name"), "date_of_birth": f.get("date_of_birth"),
            "sex": f.get("sex"), "diabetes_type": f.get("diabetes_type") or "T2D",
            "diagnosis_year": diagnosis_year, "height_cm": f.get("height_cm"),
        }])
    labs = {k: f.get(k) for k in LAB_FIELDS if f.get(k) is not None}
    if labs:
        if not encounter:
            notes.append("No report date found: fill in encounter_date.")
        out["labs"] = _csv(RECORD_TYPES["labs"], [{"chart_number": chart, "encounter_date": encounter, **labs,
                                                   "note": "HIS paste"}])
    if f.get("qrs_ms") is not None:
        out["ecg"] = _csv(RECORD_TYPES["ecg"], [{"chart_number": chart, "exam_date": encounter,
                                                 "qrs_ms": f["qrs_ms"], "interpretation": "HIS paste"}])
    conditions = [{"chart_number": chart, "code": k, "name": CONDITION_NAMES[k], "active": f[k]}
                  for k in BOOL_FIELDS if f.get(k) is not None]
    if conditions:
        out["conditions"] = _csv(RECORD_TYPES["conditions"], conditions)
        notes.append("History flags were read from free text: confirm each row.")
    if f.get("fundus_result"):
        out["screenings"] = _csv(RECORD_TYPES["screenings"], [{
            "chart_number": chart, "screening_type": "fundus_photo", "performed_date": f.get("fundus_date"),
            "result_code": f["fundus_result"], "result_summary": "HIS paste",
            "is_normal": f["fundus_result"] == "none"}])
    return {"chart_number": chart, "patient_exists": exists, "csv": out, "notes": notes}


# --- self-test (synthetic data only) -------------------------------------------------

SAMPLE = "\n".join([
    "病歷號：TST-0001　姓名：測試員　性別：男　出生日期：1968/03/15",
    "診斷：第2型糖尿病，診斷年 2012 年",
    "報告日期：2026/11/10",
    "檢驗項目\t結果\t單位\t參考值",
    "HbA1c\t8.1\t%\t4.0-6.0\tH",
    "Glucose AC\t156\tmg/dL\t70-100\tH",
    "Creatinine\t106\tµmol/L\t62-106",
    "eGFR (CKD-EPI)\t68\tmL/min/1.73m2\t>60",
    "Microalbumin/Creatinine ratio\t45\tmg/g\t<30\tH",
    "U-Creatinine\t120\tmg/dL",
    "GOT(AST)\t32\tU/L\t<40",
    "GPT(ALT)\t41\tU/L\t<41",
    "PLT\t２２.５\t10^4/µL\t15-40",
    "T-CHO　182 mg/dL",
    "HDL-C 42 mg/dL；LDL-C 110 mg/dL",
    "TG 165 mg/dL",
    "BP 138/82 mmHg  BW 76 kg  BH 170 cm",
    "ECG: sinus rhythm, QRS 0.10 s",
    "吸菸：無；過去病史：否認心肌梗塞",
    "眼底檢查 2026/05/02：輕度非增殖性視網膜病變 (mild NPDR)",
])


def _selftest() -> int:
    r = parse_text(SAMPLE)
    v = {k: f["value"] for k, f in r["fields"].items()}
    expected = {
        "chart_number": "TST-0001", "sex": "male", "date_of_birth": "1968-03-15", "diagnosis_year": 2012,
        "encounter_date": "2026-11-10", "hba1c": 8.1, "fpg": 156, "creatinine": 1.2, "egfr": 68, "uacr": 45,
        "ast": 32, "alt": 41, "platelets": 225, "total_cholesterol": 182, "hdl": 42, "ldl": 110,
        "triglycerides": 165, "sbp": 138, "dbp": 82, "weight_kg": 76, "height_cm": 170, "qrs_ms": 100,
        "current_smoker": False, "prior_mi": False, "fundus_result": "mild_npdr", "fundus_date": "2026-05-02",
    }
    bad = {k: (v.get(k), e) for k, e in expected.items() if v.get(k) != e}
    checks = {
        "urine creatinine unmatched": any("U-Creatinine" in u["text"] for u in r["unmatched_lines"]),
        "HbA1c mmol/mol": parse_text("HbA1c 64 mmol/mol")["fields"]["hba1c"]["value"] == 8.0,
        "ROC date": parse_text("出生日期：057/03/15")["fields"]["date_of_birth"]["value"] == "1968-03-15",
        "CJK-glued label": parse_text("腎功能eGFR 55")["fields"]["egfr"]["value"] == 55,
        "range warning": bool(parse_text("Creatinine 106")["fields"]["creatinine"]["warnings"]),
        "existing patient -> no patients CSV":
            "patients" not in to_import_csv(r, existing_charts={"TST-0001"})["csv"],
    }
    failed = [k for k, ok in checks.items() if not ok]
    if bad or failed:
        print("FAIL", bad, failed)
        return 1
    print(f"selftest ok: {len(expected)} fields + {len(checks)} checks")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("file", nargs="?", help="text file with pasted HIS content (default: stdin)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--csv", action="store_true", help="print import CSV per record type")
    ap.add_argument("--chart")
    ap.add_argument("--date")
    ap.add_argument("--existing", default="", help="comma-separated chart numbers that already exist")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    text = open(a.file, encoding="utf-8").read() if a.file else sys.stdin.read()
    parsed = parse_text(text)
    if a.csv:
        existing = {c.strip() for c in a.existing.split(",") if c.strip()}
        out = to_import_csv(parsed, a.chart, a.date, existing)
        for note in out["notes"]:
            print("#", note, file=sys.stderr)
        for kind, body_csv in out["csv"].items():
            print(f"--- {kind}.csv ---\n{body_csv}")
    else:
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
