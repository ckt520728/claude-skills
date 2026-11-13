"""The `local` provider: a calibrated decision layer with no key and no network.

## Why this ships

`13-portability.md` has always documented `local` as "a callable you register", and shipped
nothing. That left a reader without a `TYPESAFE_API_KEY` with two options, both bad: the `llm`
provider, which is a network call to a frontier model and therefore reintroduces the exact
cost the layer exists to remove, or a stub, which is not a decision layer at all.

Neither is necessary. The argument in `SKILL.md` for a separate decision layer is about the
**KV-cache tax** -- control returning to the large model rebuilds the cache, and that term
dominates. What deletes it is that the decision happens *beside* the loop and returns a typed
value your code branches on. That property is architectural. It does not name a vendor.

So: a decision layer that is a function call. ~0.1ms, zero cost, offline, and calibrated
against your own labels, which is the only data that can make confidence mean anything for
your questions.

## How it scores

Rule 1 says *meaning lives in the instructions* -- the question id never reaches the model,
and each option must carry criteria text that actually describes it. This provider takes that
literally and scores the state against **each option's own criteria**. There is no lexicon
baked in here; the vocabulary comes from the spec you already had to write.

A term appearing in only one option's criteria is discriminative and weighs 1.0. A term
appearing in every option's criteria is noise and weighs 1/n. That is all the cleverness
there is, and it is deliberately little: the scorer is meant to be read and argued with.

## What it is honestly not

A language model. It has no world knowledge, no synonymy, no negation handling. On input whose
wording does not overlap its criteria it will be wrong. **That is survivable only because of
`calibration.py`**: the layer measures how often it is right per confidence band and reports
accordingly, so an untuned or badly-performing band escalates instead of acting. A mediocre
calibrated layer is safe; a strong uncalibrated one is not.

Treat it as the thing you run during rule 7's shadow period, and keep whatever it earns.

Configure:
    JEV_PROVIDER=local
    JEV_CALIBRATION=/path/to/calibration.json   # optional; without it nothing is remembered
"""

from __future__ import annotations

import math
import os
import re
from typing import Any, Mapping, Sequence

from .. import calibration
from ..client import register_provider
from ..types import Choice, Noul, Question, Score

__all__ = ["local_provider", "tokenize", "score_options", "entropy_confidence"]

MODEL_NAME = "jev-local-0.1"

# Softmax temperature. 1.0 keeps distributions humble. Sharpening raises raw confidence
# without raising accuracy, which calibration then simply undoes -- so there is nothing to
# gain by tuning it. Named rather than inline (rule: thresholds live in named constants).
TEMPERATURE = 1.0

_LATIN = re.compile(r"[a-z0-9][a-z0-9'\-]{1,}", re.I)
_CJK = re.compile(r"[一-鿿぀-ヿ]")

# Terms too common to discriminate anything.
_STOP = frozenset(
    """the a an and or of to in on for with is are be been it its this that these those
    as at by from not no than then so if when while any all each which who whom whose
    do does did done can could should would may might must have has had you your i we
    our they their he she them us me my""".split()
)


def tokenize(text: str) -> set[str]:
    """Latin word tokens plus CJK character bigrams.

    Bigrams rather than characters for CJK because single Han characters are far too
    ambiguous to discriminate between options, and there is no stdlib word segmenter.
    """
    text = text or ""
    tokens = {t.lower() for t in _LATIN.findall(text) if t.lower() not in _STOP}
    chars = _CJK.findall(text)
    # Bigrams over the CJK run, which is a crude but serviceable segmentation.
    tokens.update(chars[i] + chars[i + 1] for i in range(len(chars) - 1))
    tokens.update(chars)
    return tokens


def _weights(criteria: Mapping[str, str]) -> dict[str, dict[str, float]]:
    """Per-option term weights, discounted by how many options share the term."""
    per_option = {opt: tokenize(text) for opt, text in criteria.items()}
    document_freq: dict[str, int] = {}
    for terms in per_option.values():
        for term in terms:
            document_freq[term] = document_freq.get(term, 0) + 1
    return {
        opt: {term: 1.0 / document_freq[term] for term in terms}
        for opt, terms in per_option.items()
    }


def score_options(state: str, criteria: Mapping[str, str]) -> dict[str, float]:
    """Raw score per option: summed discriminative weight of its criteria terms present."""
    state_terms = tokenize(state)
    weighted = _weights(criteria)
    return {
        opt: sum(w for term, w in terms.items() if term in state_terms)
        for opt, terms in weighted.items()
    }


def _softmax(scores: Mapping[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    mx = max(scores.values())
    exps = {k: math.exp((v - mx) / max(1e-6, TEMPERATURE)) for k, v in scores.items()}
    total = sum(exps.values()) or 1.0
    return {k: v / total for k, v in exps.items()}


def entropy_confidence(probabilities: Mapping[str, float]) -> float:
    """1 - H(p)/log(n). SKILL.md: concentrated means confident, spread means uncertain.

    Entropy rather than top-1 margin because it uses the whole distribution: 0.34/0.33/0.33
    and 0.5/0.5 are both maximally uncertain, and a margin measure would rank them
    differently for no defensible reason.
    """
    values = [p for p in probabilities.values() if p > 0]
    n = len(probabilities)
    if n <= 1:
        return 0.0
    entropy = -sum(p * math.log(p) for p in values)
    return max(0.0, min(1.0, 1.0 - entropy / math.log(n)))


def _answer_choice(state: str, qid: str, q: Choice, cal: calibration.Calibrator) -> dict[str, Any]:
    scores = score_options(state, q.criteria)
    probabilities = _softmax(scores)

    if not any(v > 0 for v in scores.values()):
        # Nothing in the state matched any option's criteria. That is precisely what the
        # exit option is for (rule 4) -- it keeps uncertainty honest rather than letting an
        # arbitrary option win a tie.
        pick = q.exit_option
    else:
        pick = max(probabilities, key=lambda k: probabilities[k])

    raw = entropy_confidence(probabilities)
    return {
        "type": "choice",
        "choice": pick,
        "confidence": cal.calibrate(qid, raw),
        "probabilities": probabilities,
        "raw_confidence": raw,
        "warm": cal.is_warm(qid, raw),
    }


def _answer_score(state: str, qid: str, q: Score, cal: calibration.Calibrator) -> dict[str, Any]:
    levels: Sequence[str] = q.criteria
    indexed = {str(i): text for i, text in enumerate(levels)}
    scores = score_options(state, indexed)
    probabilities = _softmax(scores)
    # Expected value over the level distribution, not argmax: a Score is ordered, so the
    # mass between two adjacent levels is meaningful rather than a tie to be broken.
    value = sum(float(i) * probabilities.get(str(i), 0.0) for i in range(len(levels)))
    raw = entropy_confidence(probabilities)
    return {
        "type": "score",
        "score": value,
        "confidence": cal.calibrate(qid, raw),
        "probabilities": probabilities,
        "raw_confidence": raw,
        "warm": cal.is_warm(qid, raw),
    }


def _answer_noul(state: str, qid: str, q: Noul) -> dict[str, Any]:
    """A Noul returns a probability and, by design, no confidence field.

    Without criteria there is nothing to match, so it returns exactly 0.5 -- which is not a
    failure but the documented escalation signal: the state does not separate the two cases.
    """
    if not q.criteria:
        return {"type": "noul", "noul": 0.5}
    scores = score_options(state, dict(q.criteria))
    yes = scores.get("yes", scores.get("true", 0.0))
    no = scores.get("no", scores.get("false", 0.0))
    if yes == 0.0 and no == 0.0:
        return {"type": "noul", "noul": 0.5}
    return {"type": "noul", "noul": 1.0 / (1.0 + math.exp(-(yes - no)))}


@register_provider("local")
def local_provider(
    state: str,
    questions: Mapping[str, Question],
    model: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """The provider contract from 13-portability.md. No network, no key, no tokens."""
    cal = calibration.Calibrator.load(os.environ.get("JEV_CALIBRATION"))
    answers: dict[str, Any] = {}
    for qid, q in (questions or {}).items():
        if isinstance(q, Choice):
            answers[qid] = _answer_choice(state, qid, q, cal)
        elif isinstance(q, Score):
            answers[qid] = _answer_score(state, qid, q, cal)
        elif isinstance(q, Noul):
            answers[qid] = _answer_noul(state, qid, q)
        else:
            raise TypeError(f"local provider cannot answer {type(q).__name__} for {qid!r}")
    return {
        "model": model or MODEL_NAME,
        "answers": answers,
        # Zero rather than absent, so cost-accounting code upstream keeps working.
        "usage": {"input_tokens": 0, "output_tokens": 0},
    }


def observe(question_id: str, raw_confidence: float, was_correct: bool, path: str | None = None) -> str:
    """Record one resolved escalation. This is how the layer earns its thresholds.

    Call it whenever a human resolves a decision the gate escalated: their answer is the
    label. Without this the layer stays cold forever and escalates everything, which is safe
    but useless.
    """
    target = path or os.environ.get("JEV_CALIBRATION")
    cal = calibration.Calibrator.load(target)
    cal.observe(question_id, raw_confidence, was_correct)
    cal.save()
    return cal.report(question_id)
