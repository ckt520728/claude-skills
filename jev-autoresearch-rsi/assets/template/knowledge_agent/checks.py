"""
Deterministic checks on every generated deliverable. The model's answer is never its own proof:
citations must point at collected evidence, figures must appear in the evidence they cite,
and privacy, terminology, placeholder and structure rules are checked by code.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Callable, Dict, List, Optional

from .config import CONFIG, LANGUAGE, PHI_FILE
from .sources import Evidence
from .specs import BLOG_DISCLAIMER, DECK_SECTIONS, DECK_SLIDES

BLOG_MIN_CJK = 900
KEY_GROUP = r"\[E\d+(?:\s*,\s*E\d+)*\]"
RAW_ID = re.compile(r"\b10\.\d{4,9}/\S+|\bPMID:?\s*\d{6,9}|\barXiv:\s*\d{4}\.\d{4,5}|\bNCT\d{8}\b", re.I)
LATEX = re.compile(r"\$[^$\n]{1,80}\$|\\text\{|\\frac\{|\\mathrm\{|\\underbrace|\\times\b|\\geq?\b|\\leq?\b")
NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w])")
PLACEHOLDERS = [re.compile(p, re.I) for p in (r"\bTODO\b", r"\bFIXME\b", r"\bTBD\b", r"lorem ipsum", r"<placeholder>", r"\[insert .{0,40}\]", r"\byour .{0,20} here\b", r"rest of the (code|file)")]


@dataclass
class Check:
    name: str
    passed: bool
    score: float
    message: str

    def to_dict(self) -> Dict:
        return asdict(self)


def load_phi_terms() -> List[str]:
    if not PHI_FILE.exists():
        return []
    return [t.strip() for t in PHI_FILE.read_text(encoding="utf-8").splitlines() if t.strip() and not t.startswith("#")]


def phi_hits(text: str, terms: Optional[List[str]] = None) -> int:
    """Number of known identifiers in the text. The terms themselves are never logged."""
    terms = load_phi_terms() if terms is None else terms
    return sum(text.count(term) for term in terms)


def cited_keys(text: str) -> List[str]:
    keys: List[str] = []
    for match in re.finditer(r"\[(E\d+(?:\s*,\s*E\d+)*)\]", text):
        keys.extend(k.strip() for k in match.group(1).split(","))
    return list(dict.fromkeys(keys))


def number_value(value) -> Optional[float]:
    """A chart value as a float, accepting strings like "63.6", "63.6%" or "63.6 [E4]"."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*%?\s*(?:\[E\d+(?:\s*,\s*E\d+)*\])?\s*", str(value))
    return float(match.group(1)) if match else None


def extract_json(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if match:
        return match.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("No JSON object in the answer")
    return text[start:end + 1]


def _flatten(output: str) -> str:
    """Slides and infographics are JSON; check the human-readable values, not the keys."""
    try:
        data = json.loads(extract_json(output))
    except (ValueError, TypeError):
        return output

    def flat(node) -> List[str]:
        if isinstance(node, dict):
            return [t for item in node.values() for t in flat(item)]
        if isinstance(node, list):
            return [t for item in node for t in flat(item)]
        return [str(node)] if isinstance(node, (str, int, float)) and not isinstance(node, bool) else []

    def walk(node) -> List[str]:
        if isinstance(node, str):
            return [node]
        if isinstance(node, (int, float)) and not isinstance(node, bool):
            return [str(node)]
        if isinstance(node, list):
            return [t for item in node for t in walk(item)]
        if isinstance(node, dict):
            # A stat or chart is one claim: its citation in the label or title covers its values.
            if "bars" in node or ("value" in node and "label" in node and "title" not in node and "points" not in node):
                return [" ".join(flat(node))]
            return [t for item in node.values() for t in walk(item)]
        return []

    return "\n".join(walk(data))


def _units(text: str) -> List[str]:
    """Units a citation must share with its figures: a whole table row, or one prose sentence."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    units: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or re.fullmatch(r"[|\s:-]+", line):
            continue
        if line.startswith("|"):
            units.append(line)
            continue
        units.extend(s.strip() for s in re.split(r"(?<=[。！？!?])\s*|(?<=\.)\s+(?=[A-Z一-鿿*])", line) if s.strip())
    return units


def _plain_numbers(unit: str) -> List[str]:
    cleaned = re.sub(KEY_GROUP, " ", unit)
    cleaned = re.sub(r"^\s*#*\s*\d+(?:\.\d+)*[.)、]?\s", " ", cleaned)
    numbers = []
    for raw in NUMBER.findall(cleaned):
        value = raw.replace(",", "")
        # Years, small counts and the 95 in "95% CI" are not findings; every other figure must be traceable.
        if re.fullmatch(r"(19|20)\d{2}", value) or (value.isdigit() and int(value) <= 10) or value == "95":
            continue
        numbers.append(value)
    return numbers


def check_citation_keys(text: str, evidence: Dict[str, Evidence], minimum: int) -> Check:
    flat = _flatten(text)
    keys = cited_keys(flat)
    unknown = [k for k in keys if k not in evidence]
    if unknown:
        return Check("CitationKeys", False, 0.2, f"Cites evidence that does not exist: {unknown[:8]}. Use only the supplied [E#] keys.")
    bare = re.findall(r"\bE\d{1,3}\b", re.sub(KEY_GROUP, " ", flat))
    if bare:
        return Check("CitationKeys", False, 0.5, f"Readers cannot see evidence keys. Remove {sorted(set(bare))[:6]} from the prose: name the study, and keep keys only inside citations like [E3].")
    raw = RAW_ID.findall(flat)
    if raw:
        return Check("CitationKeys", False, 0.4, f"Remove hand-typed identifiers {raw[:4]}. Cite with [E#]; the reference list is generated automatically.")
    if len(keys) < minimum:
        return Check("CitationKeys", False, round(0.5 * len(keys) / max(1, minimum), 3), f"Only {len(keys)} distinct sources cited; at least {minimum} are required.")
    return Check("CitationKeys", True, 1.0, f"{len(keys)} distinct sources cited, all from collected evidence.")


def check_numbers(text: str, evidence: Dict[str, Evidence], min_score: float = 0.95) -> Check:
    sources = {k: re.sub(r"[\s,]", "", e.text) for k, e in evidence.items()}
    total = supported = 0
    problems: List[str] = []
    for unit in _units(_flatten(text)):
        keys = cited_keys(unit)
        for number in _plain_numbers(unit):
            total += 1
            if any(number in sources.get(k, "") for k in keys):
                supported += 1
            elif len(problems) < 12:
                where = f"not found in {', '.join(keys)}" if keys else "no citation beside it"
                problems.append(f'{number} ({where}): "{unit[:90]}"')
    score = supported / total if total else 1.0
    if score < min_score:
        return Check("NumericGrounding", False, round(score, 3), f"{total - supported} of {total} figures are unsupported. Correct each from the cited evidence, cite the right source, or remove it: " + " | ".join(problems))
    return Check("NumericGrounding", True, round(score, 3), f"{supported} of {total} figures found in the evidence they cite.")


def check_claim_numbers(text: str, keys: List[str], evidence: Dict[str, Evidence]) -> Check:
    """
    Ground a model claim that carries its keys in a separate field. The keys are attached to *every* sentence,
    because check_numbers needs a citation beside each figure. Appending them once at the end made figures in an
    earlier sentence look uncited (two faithful claims were rejected in run 20261109-091620-b8f1c4).
    """
    cite = f" [{', '.join(keys)}]"
    plain = re.sub(r"\[E\d+(?:\s*,\s*E\d+)*\]", "", text)
    return check_numbers("\n".join(u + cite for u in _units(plain)), evidence)


# Labels only this engine produces. Topic words such as "pairwise tournament" stay allowed: a review may discuss them.
INTERNAL_LABELS = re.compile(r"(?i:Falcon[- ](?:verified|checked|findings?)|Crow swarm)|VERIFIED FINDINGS|RANKED HYPOTHESES")


def check_clean(text: str) -> Check:
    hits = phi_hits(text)
    if hits:
        return Check("CleanText", False, 0.0, f"Contains {hits} known identifier(s). Remove all personal and case identifiers.")
    latex = LATEX.findall(text)
    if latex:
        return Check("CleanText", False, 0.5, f"Replace raw LaTeX with plain Unicode: {latex[:3]}")
    wrong = [t for t in CONFIG.get("terms", {}).get("forbidden", []) if t in text]
    if wrong:
        preferred = "; ".join(f"{k} = {v}" for k, v in CONFIG["terms"].get("preferred", {}).items())
        return Check("CleanText", False, 0.6, f"Wrong terms {wrong[:3]}. Use: {preferred}")
    placeholders = [r.search(text).group(0) for r in PLACEHOLDERS if r.search(text)]
    if placeholders:
        return Check("CleanText", False, 0.5, f"Remove placeholders: {placeholders[:3]}")
    internal = sorted({m.group(0) for m in INTERNAL_LABELS.finditer(text)})
    if internal:
        return Check("CleanText", False, 0.6, f"Remove internal workflow labels; readers cannot see them: {internal[:3]}. Describe the sources instead.")
    return Check("CleanText", True, 1.0, "No known identifiers, raw LaTeX, wrong terms or placeholders.")


def _chinese(text: str) -> int:
    return len(re.findall(r"[一-鿿]", text))


def _paper(text: str) -> List[str]:
    problems = []
    low = text.lower()
    for section in ("abstract", "introduction", "methods", "results", "discussion", "limitations", "conclusion"):
        if not re.search(rf"^#+.*{section}", low, re.M):
            problems.append(f"Missing section heading: {section}")
    if LANGUAGE == "zh-TW" and not re.search(r"^#+.*摘要", text, re.M):
        problems.append("Missing a Traditional Chinese abstract heading (摘要)")
    words = len(re.findall(r"[A-Za-z]+", text)) + _chinese(text)
    if words < 900:
        problems.append(f"Too short: about {words} words; at least 900 are required")
    if re.search(r"^#+.*\breferences\b", low, re.M):
        problems.append("Do not write a references section; it is generated automatically")
    return problems


def _blog(text: str) -> List[str]:
    problems = []
    if len(re.findall(r"^# ", text, re.M)) != 1:
        problems.append("Needs exactly one # title")
    language = CONFIG.get("blog_language", "zh-TW")
    if language == "zh-TW":
        if _chinese(text) < BLOG_MIN_CJK:
            problems.append(f"Write in Traditional Chinese (keeping English technical terms), at least {BLOG_MIN_CJK} Chinese characters (found {_chinese(text)})")
        if BLOG_DISCLAIMER not in text:
            problems.append(f"Needs a closing note containing the sentence 「{BLOG_DISCLAIMER}」")
    else:
        if len(re.findall(r"[A-Za-z]+", text)) < 350:
            problems.append("Too short: at least 350 words are required")
        if not re.search(CONFIG.get("disclaimer_pattern", "does not replace|不能取代|諮詢"), text, re.I):
            problems.append("Needs a closing note that this does not replace professional advice")
    return problems


def _deck(text: str) -> List[str]:
    try:
        slides = json.loads(extract_json(text)).get("slides", [])
    except (ValueError, AttributeError) as e:
        return [f"Answer must be one valid JSON object: {e}"]
    if not isinstance(slides, list):
        return ["'slides' must be a list"]
    problems = []
    if len(slides) != DECK_SLIDES:
        problems.append(f"Needs exactly {DECK_SLIDES} slides, found {len(slides)}")
    sections = [str(s.get("section", "")).strip().lower() if isinstance(s, dict) else "" for s in slides]
    expected = [name for name, count in DECK_SECTIONS for _ in range(count)]
    if sections != expected:
        counts = {name: sections.count(name) for name, _ in DECK_SECTIONS}
        bad = [f'"{name}" needs {count} slides, found {counts[name]}' for name, count in DECK_SECTIONS if counts[name] != count]
        stray = sorted({s or "(missing)" for s in sections} - set(counts))
        if stray:
            bad.append(f"unknown or missing section values {stray}")
        if not bad:
            bad.append("sections are out of order")
        problems.append("Sections must run hook x2, concepts x5, evidence x5, misconceptions x1, conclusion x2 in that order: " + "; ".join(bad))
    for i, slide in enumerate(slides, 1):
        if not isinstance(slide, dict) or not slide.get("title") or not slide.get("bullets"):
            problems.append(f"Slide {i} needs a title and bullets")
        elif not isinstance(slide["bullets"], list) or len(slide["bullets"]) > 5:
            problems.append(f"Slide {i} has {len(slide['bullets']) if isinstance(slide['bullets'], list) else 'invalid'} bullets; at most 5 are allowed")
    return problems


def _infographic(text: str) -> List[str]:
    try:
        panels = json.loads(extract_json(text)).get("panels", [])
    except ValueError as e:
        return [f"Answer must be one valid JSON object: {e}"]
    problems = [f"Needs exactly 6 panels, found {len(panels)}"] if len(panels) != 6 else []
    for i, panel in enumerate(panels, 1):
        if not panel.get("title") or not panel.get("points"):
            problems.append(f"Panel {i} needs a title and points")
        for bar in (panel.get("chart") or {}).get("bars", []):
            if number_value(bar.get("value")) is None:
                problems.append(f'Panel {i} chart: value "{bar.get("value")}" must be a plain number such as 63.6, or remove that chart')
                break
    return problems


STRUCTURE: Dict[str, Callable[[str], List[str]]] = {"paper": _paper, "blog": _blog, "deck": _deck, "infographic": _infographic}
MIN_SOURCES = {"paper": 6, "deck": 4, "blog": 3, "infographic": 3}


def run_checks(kind: str, text: str, evidence: Dict[str, Evidence]) -> List[Check]:
    problems = STRUCTURE[kind](text)
    structure = Check("Structure", not problems, 0.4 if problems else 1.0, "; ".join(problems) or f"{kind} structure is complete.")
    return [
        structure,
        check_citation_keys(text, evidence, min(MIN_SOURCES[kind], max(1, len(evidence)))),
        check_numbers(text, evidence),
        check_clean(text),
    ]
