"""Life OS's handle on the jev-engineering decision layer.

**Corrected 2026-09-30.** Sessions 1-4 built `decide.py` + `calibrate.py`: a private copy of
the skill's ideas with its own API (`backend.choice(state, qid, options, "one line")`). That
was the skill's *shape* without the skill. Its questions broke the skill's own rules — bare
option names with no criteria (rule 1), an unlabelled 5-level Score (rule 3), four separate
calls per capture (rule 5) — and none of the skill's validation could catch it, because the
skill was never imported.

Now Life OS imports the skill. `lifeos/jev/` is a verbatim, hash-pinned copy of
`jev-engineering/assets/jev` (see `scripts/sync_jev.py`). Every GTD question is a real
`jev.Choice` / `jev.Score` / `jev.Noul`, validated by the skill's types, answered by the
skill's `local` provider in one `decide()` call, and gated by the skill's `gate()`.

What this module adds on top is only what is Life-OS-specific:

- **where the calibration file lives** (inside the vault, so it travels with the data);
- **recalibration from raw**, so Life OS owns one calibrator for every primitive — the
  `local` provider calibrates Choice/Score but, per the spec, not Noul;
- **a deterministic stub provider** for the test suite.
"""

import os
from contextlib import contextmanager

from . import jev
from .jev import calibration

__all__ = ["Layer", "DEFAULT_CALIBRATION", "make_stub", "COLD_CONFIDENCE"]

COLD_CONFIDENCE = calibration.COLD_CONFIDENCE

DEFAULT_CALIBRATION = os.path.join(
    "G:" + os.sep, "我的雲端硬碟", "Second Brain", "Life OS", "Meta", "calibration.json")


@contextmanager
def _no_env_calibration():
    """Run the provider without its own calibration file; Life OS recalibrates from raw.

    Two calibrators reading two files would let them disagree silently. One owner.
    """
    saved = os.environ.pop("JEV_CALIBRATION", None)
    try:
        yield
    finally:
        if saved is not None:
            os.environ["JEV_CALIBRATION"] = saved


class Layer(object):
    """Which jev provider answers, and which calibration file turns raw scores into belief.

    `calibrator` may be passed in-memory (tests); otherwise it is loaded from `path`.
    """

    def __init__(self, provider="local", path=None, calibrator=None):
        self.provider = provider
        self.path = path
        self.cal = calibrator if calibrator is not None else calibration.Calibrator.load(path)

    @property
    def name(self):
        return self.provider

    @property
    def live(self):
        """True when answers come from a real decision layer, not the test stub."""
        return not self.provider.startswith("lifeos-stub")

    def decide(self, state, questions):
        """One jev.decide() call. Every question shares the state (rule 5)."""
        with _no_env_calibration():
            return jev.decide(state, questions, provider=self.provider, retries=1)

    def raw_of(self, result, qid):
        """The uncalibrated score the provider produced, if it exposes one."""
        wire = (result.raw.get("answers") or {}).get(qid) or {}
        ans = result.answers[qid]
        if ans.type == "noul":
            # A Noul has no confidence field by design. Its raw score is decisiveness,
            # |p - 0.5| * 2 — the skill's own `Answer.certainty` definition.
            return ans.certainty if ans.noul is not None else None
        return wire.get("raw_confidence")

    def confidence_of(self, result, qid):
        """Calibrated belief for one answer: measured on this user's labels when possible."""
        raw = self.raw_of(result, qid)
        if raw is not None:
            return self.cal.calibrate(qid, raw), raw, self.cal.is_warm(qid, raw)
        # A provider with native calibrated confidence (the jev API) and no raw score.
        return result.answers[qid].certainty, None, None

    def record(self, qid, raw, correct, save=True):
        """One adjudicated outcome. The only way the layer learns anything."""
        if raw is None:
            return None
        self.cal.observe(qid, raw, bool(correct))
        if save and self.path:
            self.cal.save()
        return self.cal.report(qid)


_STUB_COUNT = [0]


def make_stub(confidence=0.34, picks=None, noul=0.5, score=0.0):
    """Register a deterministic provider for tests; return a Layer using it.

    Every Choice picks `picks[qid]` if given, else its first non-exit option, at
    `confidence`. No raw score is exposed, so the gate sees the native number unchanged.
    """
    _STUB_COUNT[0] += 1
    name = "lifeos-stub-%d" % _STUB_COUNT[0]
    picks = dict(picks or {})

    @jev.register_provider(name)
    def _stub(state, questions, model, timeout):
        answers = {}
        for qid, q in questions.items():
            if isinstance(q, jev.Choice):
                opts = [k for k in q.criteria if k != q.exit_option] or list(q.criteria)
                pick = picks.get(qid, opts[0])
                answers[qid] = {"type": "choice", "choice": pick, "confidence": confidence,
                                "probabilities": {pick: confidence}}
            elif isinstance(q, jev.Score):
                answers[qid] = {"type": "score", "score": score, "confidence": confidence,
                                "probabilities": {}}
            else:
                answers[qid] = {"type": "noul", "noul": picks.get(qid, noul)}
        return {"model": name, "answers": answers,
                "usage": {"input_tokens": 0, "output_tokens": 0}}

    return Layer(provider=name, calibrator=calibration.Calibrator())
