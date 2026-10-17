"""
demo_facts.py -- Summary numbers for the worked demonstrations, read only from the cube JSON
files that run_cubes.py writes. Every demo figure quoted in the paper, deck, blog and site
should be traceable to demo_facts.json; re-run this after run_cubes.py.
"""

import base64
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def load(name):
    d = json.loads((HERE / f"{name}_cube.json").read_text(encoding="utf-8"))
    H = np.frombuffer(base64.b64decode(d["H"]), dtype=np.float16).astype(float).reshape(d["shape"])
    return d, H


def band_summary(d, H):
    fc = np.array(d["axes"]["fc"])
    fam = np.array(d["axes"]["fam"])
    total = H.sum()
    C = H.sum(axis=0)
    out = {"carrier_band_energy_pct": {}, "dominant_am_band_per_carrier_band": {}}
    for b in d["bands"]:
        fi = (fc >= b["lo"]) & (fc < b["hi"])
        e = C[fi].sum()
        out["carrier_band_energy_pct"][b["name"]] = round(100 * e / total, 1)
        if e > 0:
            am_e = {bb["name"]: C[np.ix_(fi, (fam >= bb["lo"]) & (fam < bb["hi"]))].sum() for bb in d["bands"]}
            top = max(am_e, key=am_e.get)
            out["dominant_am_band_per_carrier_band"][b["name"]] = {"am_band": top, "share_pct": round(100 * am_e[top] / e, 1)}
    i, j = np.unravel_index(C.argmax(), C.shape)
    out["C_peak"] = {"fc": round(float(fc[i]), 4), "fam": round(float(fam[j]), 4)}
    S = H.sum(axis=(0, 2))
    out["fc_marginal_peak"] = round(float(fc[S.argmax()]), 4)
    inadm = fam[None, :] >= fc[:, None]
    out["energy_at_or_above_fam_eq_fc_pct"] = round(100 * C[inadm].sum() / total, 1)
    lim = d["resolvability"]["unresolvable_below_hz"]
    unres = (fc[:, None] < lim) | (fam[None, :] < lim)
    out["energy_in_bins_below_3_over_T_pct"] = round(100 * C[unres].sum() / total, 1)
    out["three_over_T"] = lim
    out["units_f"] = d["units"]["f"]
    return out


facts = {}

d, H = load("synthetic")
val = json.loads((HERE / "cube_validation.json").read_text(encoding="utf-8"))
rec = val["criteria_checks"]["synthetic_argmax_recovery"]
fc = np.array(d["axes"]["fc"]); fam = np.array(d["axes"]["fam"]); t = np.array(d["axes"]["t"])
grid = np.geomspace(0.01, 2.0, 41)
misses = []
for w in range(H.shape[0]):
    fce = 0.50 + 0.15 * np.cos(2 * np.pi * t[w] / 300.0)
    fame = 0.05 + 0.02 * np.sin(2 * np.pi * t[w] / 300.0)
    ei, ej = np.digitize(fce, grid) - 1, np.digitize(fame, grid) - 1
    ri, rj = np.unravel_index(H[w].argmax(), H[w].shape)
    if abs(ri - ei) > 1 or abs(rj - ej) > 1:
        misses.append({"window": w, "t_s": float(t[w]), "fc_bin_off": int(ri - ei), "fam_bin_off": int(rj - ej)})
facts["synthetic"] = {
    "signal": d["truth"]["function"], "fc_formula": d["truth"]["fc_formula"], "fam_formula": d["truth"]["fam_formula"],
    "duration_s": d["record"]["duration"], "fs_hz": 1 / d["record"]["dt"], "n": d["record"]["n"],
    "windows": int(H.shape[0]), "window_s": 10.0,
    "recovery_pct": round(rec["recovery_rate_pct"], 1), "recovery_target_pct": rec["target_threshold_pct"],
    "recovery_status": rec["status"], "missed_windows": misses,
    **band_summary(d, H),
}

d, H = load("cgm")
facts["cgm"] = {"duration_h": d["record"]["duration"], "n": d["record"]["n"], "window_h": 2.0, **band_summary(d, H)}

qc = json.loads((HERE / "garmin_qc.json").read_text(encoding="utf-8"))
for key, label in (("hrv_sessionA", "HRV session A"), ("hrv_sessionB", "HRV session B")):
    d, H = load(key)
    facts[key] = {"qc": qc[label]["qc"], "time_domain": qc[label]["time_domain_features"], **band_summary(d, H)}

d, H = load("hrv_synthetic")
S = H.sum(axis=(0, 2)); fcax = np.array(d["axes"]["fc"])
peaks = [int(i) for i in np.argsort(S)[::-1] if 0 < i < len(S) - 1 and S[i] >= S[i - 1] and S[i] >= S[i + 1]][:2]
facts["hrv_synthetic"] = {"truth": d["truth"], "fc_marginal_local_peaks_hz": sorted(round(float(fcax[i]), 4) for i in peaks),
                          **band_summary(d, H)}

params = json.loads((HERE / "synthetic_cube.json").read_text(encoding="utf-8"))["params"]
facts["pipeline"] = {**params, "layer2_max_imf": 7, "layer1_max_imf": 10, "sd_stop": 0.2, "grid_bins": 40,
                     "garmin": "IBI 300-2000 ms, linear interpolation to 50 Hz, integrate-and-fire beats "
                               "(sub-sample crossing), 4 Hz cubic-spline tachogram"}

(HERE / "demo_facts.json").write_text(json.dumps(facts, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(facts, indent=1, ensure_ascii=False))
