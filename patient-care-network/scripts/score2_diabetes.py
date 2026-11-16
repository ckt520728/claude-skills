"""Standalone SCORE2-Diabetes (10-year CVD risk). Stdlib only.

SCORE2-Diabetes Working Group. Eur Heart J 2023;44(28):2544-2556.
Coefficients cross-checked against RiskScorescvd (R/15_SCORE2-Diabetes_func.R).

Usage:
    python score2_diabetes.py --selftest
    python score2_diabetes.py --sex male --age 60 --smoker 0 --sbp 140 \
        --tc-mmol 5.5 --hdl-mmol 1.3 --age-dx 60 --hba1c-mmol 50 --egfr 90 --region low

Applicability: type 2 diabetes, age 40-69, no established ASCVD. Taiwan and most
of Asia are not SCORE2 calibration regions: always report the region used.
"""

from __future__ import annotations

import argparse
import math

COEF = {
    "male": dict(age=0.5368, smoking=0.4774, sbp=0.1322, diabetes=0.6457, tchol=0.1102, hdl=-0.1087,
                 smoking_age=-0.0672, sbp_age=-0.0268, diabetes_age=-0.0983, tchol_age=-0.0181, hdl_age=0.0095,
                 agediag=-0.0998, hba1c=0.0955, egfr=-0.0591, egfr2=0.0058, hba1c_age=-0.0134, egfr_age=0.0115,
                 s0=0.9605),
    "female": dict(age=0.6624, smoking=0.6139, sbp=0.1421, diabetes=0.8096, tchol=0.1127, hdl=-0.1568,
                   smoking_age=-0.1122, sbp_age=-0.0167, diabetes_age=-0.1272, tchol_age=-0.0200, hdl_age=0.0186,
                   agediag=-0.1180, hba1c=0.1173, egfr=-0.0640, egfr2=0.0062, hba1c_age=-0.0196, egfr_age=0.0169,
                   s0=0.9776),
}
REGION = {
    "low": {"male": (-0.5699, 0.7476), "female": (-0.7380, 0.7019)},
    "moderate": {"male": (-0.1565, 0.8009), "female": (-0.3143, 0.7701)},
    "high": {"male": (0.3207, 0.9360), "female": (0.5710, 0.9369)},
    "very_high": {"male": (0.5836, 0.8294), "female": (0.9412, 0.8329)},
}


def hba1c_percent_to_mmol(p: float) -> float:
    return (p - 2.15) * 10.929


def mgdl_to_mmol_chol(v: float) -> float:
    return v / 38.67


def score2_diabetes(sex: str, age: float, smoker: bool, sbp: float, tc_mmol: float, hdl_mmol: float,
                    age_dx: float, hba1c_mmol: float, egfr: float, region: str = "high") -> dict:
    if not 40 <= age <= 69:
        return {"status": "not_applicable", "reason": "age outside 40-69"}
    c = COEF[sex]
    cage = (age - 60) / 5
    csbp = (sbp - 120) / 20
    ctc = tc_mmol - 6
    chdl = (hdl_mmol - 1.3) / 0.5
    smk = 1.0 if smoker else 0.0
    cdx = (age_dx - 50) / 5
    ca1c = (hba1c_mmol - 31) / 9.34
    z = (math.log(egfr) - 4.5) / 0.15
    lp = (c["age"] * cage + c["smoking"] * smk + c["sbp"] * csbp + c["diabetes"] + c["tchol"] * ctc + c["hdl"] * chdl
          + c["smoking_age"] * smk * cage + c["sbp_age"] * csbp * cage + c["diabetes_age"] * cage
          + c["tchol_age"] * ctc * cage + c["hdl_age"] * chdl * cage + c["agediag"] * cdx + c["hba1c"] * ca1c
          + c["egfr"] * z + c["egfr2"] * z * z + c["hba1c_age"] * ca1c * cage + c["egfr_age"] * z * cage)
    uncal = 1 - c["s0"] ** math.exp(lp)
    s1, s2 = REGION[region][sex]
    risk = 1 - math.exp(-math.exp(s1 + s2 * math.log(-math.log(1 - uncal))))
    value = round(risk * 100, 1)
    band = "low" if value < 5 else "moderate" if value < 10 else "high" if value < 20 else "very_high"
    return {"status": "calculated", "risk_percent": value, "band": band, "region": region,
            "linear_predictor": round(lp, 4), "uncalibrated_percent": round(uncal * 100, 2)}


def selftest() -> None:
    r = score2_diabetes("male", 60, False, 140, 5.5, 1.3, 60, 50, 90, "low")
    assert r["risk_percent"] == 8.4 and r["band"] == "moderate", r
    lo, hi, vh = (score2_diabetes("male", 60, False, 140, 5.5, 1.3, 60, 50, 90, g)["risk_percent"]
                  for g in ("low", "high", "very_high"))
    assert lo < hi < vh
    assert score2_diabetes("male", 60, True, 140, 5.5, 1.3, 60, 50, 90, "low")["risk_percent"] > 8.4
    assert score2_diabetes("female", 72, False, 140, 5.5, 1.3, 60, 50, 90)["status"] == "not_applicable"
    assert abs(hba1c_percent_to_mmol(6.725) - 50) < 0.1
    print("selftest ok: worked example 8.4 % (low region), region ordering, smoking, applicability")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--sex", choices=["male", "female"])
    ap.add_argument("--age", type=float)
    ap.add_argument("--smoker", type=int, choices=[0, 1])
    ap.add_argument("--sbp", type=float)
    ap.add_argument("--tc-mmol", type=float)
    ap.add_argument("--hdl-mmol", type=float)
    ap.add_argument("--age-dx", type=float)
    ap.add_argument("--hba1c-mmol", type=float)
    ap.add_argument("--egfr", type=float)
    ap.add_argument("--region", default="high", choices=list(REGION))
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        print(score2_diabetes(a.sex, a.age, bool(a.smoker), a.sbp, a.tc_mmol, a.hdl_mmol, a.age_dx,
                              a.hba1c_mmol, a.egfr, a.region))
