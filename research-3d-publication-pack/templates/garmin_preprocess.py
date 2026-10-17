"""
garmin_preprocess.py -- Port of MATLAB Garmin data preprocessing (G4) and HRV feature extraction (G3).

Reference MATLAB pipeline:
- G4: Garmin_data_preprocessing_mlx.pdf:
    1. Parse JSON Lines records (~50 Hz) and timestamp strings.
    2. Drop non-positive / missing values (<= 0 -> NaN).
    3. Filter physiological IBI range: 300 - 2000 ms.
    4. Interpolate IBI to uniform 50 Hz grid (linear extrapolation).
    5. Integrate instantaneous HR (1000 / IBI) to recover beat times via integrate-and-fire.
    6. Re-filter recovered IBIs (< 300 or > 2000 ms -> NaN) and fill missing linearly.
    7. Resample tachogram at 4 Hz using cubic spline for HHSA.
- G3: HRV_indexes.pdf:
    Time-domain features: MeanNN, SDNN, RMSSD, SDSD, CVNN, CVSD, MedianNN, MadNN, MCVNN, IQRNN,
    MinNN, MaxNN, Prc20NN, Prc80NN, pNN50, pNN20.

All outputs use neutral labels ('HRV session A', 'HRV session B') and relative seconds only.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import numpy as np
from scipy.interpolate import CubicSpline, interp1d


def preprocess_garmin_session(
    jsonl_path: str | Path,
    session_label: str = "HRV session A",
    target_fs: float = 4.0,
) -> Dict[str, Any]:
    """Preprocess one Garmin JSON Lines raw file and return cleaned 4 Hz tachogram and QC."""
    jsonl_path = Path(jsonl_path)
    raw_samples = 0
    records = []

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw_samples += 1
            rec = json.loads(line)
            ibi = float(rec.get("heartRateVariability", 0))
            hr = float(rec.get("heartRate", 0))
            stress = float(rec.get("stressLevel", 0))
            spo2 = float(rec.get("SPO2", 0))
            resp = float(rec.get("respiration", 0))
            t_str = rec.get("time", "")

            # Non-positive values coded as NaN
            ibi = ibi if ibi > 0 else np.nan
            hr = hr if hr > 0 else np.nan
            stress = stress if stress > 0 else np.nan
            spo2 = spo2 if spo2 > 0 else np.nan
            resp = resp if resp > 0 else np.nan

            records.append({
                "time_str": t_str,
                "ibi": ibi,
                "hr": hr,
                "stress": stress,
                "spo2": spo2,
                "resp": resp,
            })

    # Parse timestamps
    parsed_times = []
    valid_recs = []
    for r in records:
        try:
            dt_val = datetime.strptime(r["time_str"], "%Y-%m-%d %H-%M-%S-%f")
            parsed_times.append(dt_val)
            valid_recs.append(r)
        except Exception:
            pass

    if not parsed_times:
        raise ValueError(f"No valid timestamps parsed from {jsonl_path}")

    t0 = parsed_times[0]
    time_sec = np.array([(pt - t0).total_seconds() for pt in parsed_times])

    # Remove non-increasing time points (keep first t=0)
    valid_time_mask = np.ones(len(time_sec), dtype=bool)
    for i in range(1, len(time_sec)):
        if time_sec[i] <= 0:
            valid_time_mask[i] = False

    time_sec = time_sec[valid_time_mask]
    valid_recs = [valid_recs[i] for i in range(len(valid_recs)) if valid_time_mask[i]]

    # Stable unique timestamps
    _, unique_idx = np.unique(time_sec, return_index=True)
    unique_idx = np.sort(unique_idx)
    time_sec = time_sec[unique_idx]
    valid_recs = [valid_recs[i] for i in unique_idx]

    ibi_raw = np.array([r["ibi"] for r in valid_recs], dtype=float)
    hr_raw = np.array([r["hr"] for r in valid_recs], dtype=float)

    # Filter physiological IBI range: 300 to 2000 ms
    valid_ibi_mask = np.isfinite(ibi_raw) & (ibi_raw >= 300.0) & (ibi_raw <= 2000.0)
    ibis_kept = int(np.sum(valid_ibi_mask))
    ibis_rejected = int(len(ibi_raw) - ibis_kept)

    time_clean = time_sec[valid_ibi_mask]
    ibi_clean = ibi_raw[valid_ibi_mask]
    hr_clean = hr_raw[valid_ibi_mask]

    # Resample to uniform 50 Hz grid
    fs_50hz = 50.0
    t_uniform = np.arange(time_clean[0], time_clean[-1], 1.0 / fs_50hz)
    interp_fn = interp1d(time_clean, ibi_clean, kind="linear", fill_value="extrapolate")
    ibi_uniform = interp_fn(t_uniform)

    # Compute instantaneous HR in Hz and cumulative beat count
    inst_hr_hz = 1000.0 / ibi_uniform
    beat_counter = np.cumsum(inst_hr_hz) / fs_50hz

    # Recover beat times when beat counter crosses integer thresholds; the crossing time is
    # interpolated inside the 20 ms sample so recovered IBIs are not quantised to the 50 Hz grid
    k = np.nonzero(np.floor(beat_counter[1:]) > np.floor(beat_counter[:-1]))[0]
    level = np.floor(beat_counter[k + 1])
    frac = (level - beat_counter[k]) / (beat_counter[k + 1] - beat_counter[k])
    beat_times = t_uniform[k] + frac / fs_50hz
    recovered_beats = int(len(beat_times))

    # Recovered IBIs in ms
    ibi_ms = np.diff(beat_times) * 1000.0
    ibi_times = beat_times[1:]

    # Artifact correction on recovered IBIs
    bad_rec = (ibi_ms < 300.0) | (ibi_ms > 2000.0)
    ibi_ms_corr = ibi_ms.copy()
    ibi_ms_corr[bad_rec] = np.nan
    nans = np.isnan(ibi_ms_corr)
    if np.any(nans):
        not_nans = ~nans
        if np.sum(not_nans) >= 2:
            ibi_ms_corr[nans] = np.interp(ibi_times[nans], ibi_times[not_nans], ibi_ms_corr[not_nans])
        elif np.sum(not_nans) == 1:
            ibi_ms_corr[nans] = ibi_ms_corr[not_nans][0]

    # Resample tachogram at 4 Hz with cubic spline for HHSA
    t_tachogram = np.arange(ibi_times[0], ibi_times[-1], 1.0 / target_fs)
    cs = CubicSpline(ibi_times, ibi_ms_corr)
    tachogram_4hz = cs(t_tachogram)

    # QC calculation
    duration_s = float(time_clean[-1] - time_clean[0])
    valid_hr = hr_clean[np.isfinite(hr_clean) & (hr_clean > 0)]
    median_hr = float(np.median(valid_hr)) if valid_hr.size else float(60000.0 / np.median(ibi_ms_corr))
    expected_beats = float(duration_s * median_hr / 60.0)
    error_pct = float(abs(recovered_beats - expected_beats) / expected_beats * 100.0)
    error_pass = bool(error_pct <= 2.0)

    # Time-domain features (G3 formulas)
    diff_ibi = np.diff(ibi_ms_corr)
    mean_nn = float(np.mean(ibi_ms_corr))
    sdnn = float(np.std(ibi_ms_corr, ddof=1))
    rmssd = float(np.sqrt(np.mean(diff_ibi ** 2)))
    sdsd = float(np.std(diff_ibi, ddof=1))
    cvnn = float(sdnn / mean_nn)
    cvsd = float(rmssd / mean_nn)  # CVSD = RMSSD / MeanNN (G3)
    median_nn = float(np.median(ibi_ms_corr))
    mad_nn = float(np.median(np.abs(ibi_ms_corr - median_nn)))
    mcv_nn = float(mad_nn / median_nn)
    iqr_nn = float(np.percentile(ibi_ms_corr, 75) - np.percentile(ibi_ms_corr, 25))
    min_nn = float(np.min(ibi_ms_corr))
    max_nn = float(np.max(ibi_ms_corr))
    prc20_nn = float(np.percentile(ibi_ms_corr, 20))
    prc80_nn = float(np.percentile(ibi_ms_corr, 80))
    pnn50 = float(np.sum(np.abs(diff_ibi) > 50.0) / len(diff_ibi) * 100.0)
    pnn20 = float(np.sum(np.abs(diff_ibi) > 20.0) / len(diff_ibi) * 100.0)

    qc = {
        "session": session_label,
        "duration_seconds": round(duration_s, 2),
        "raw_samples": raw_samples,
        "ibis_kept": ibis_kept,
        "ibis_rejected": ibis_rejected,
        "recovered_beats": recovered_beats,
        "median_hr_bpm": round(median_hr, 2),
        "expected_beats": round(expected_beats, 2),
        "beat_count_relative_error_pct": round(error_pct, 4),
        "beat_count_acceptance_pass": error_pass,
    }

    time_domain_features = {
        "MeanNN_ms": round(mean_nn, 3),
        "SDNN_ms": round(sdnn, 3),
        "RMSSD_ms": round(rmssd, 3),
        "SDSD_ms": round(sdsd, 3),
        "CVNN": round(cvnn, 6),
        "CVSD": round(cvsd, 6),
        "MedianNN_ms": round(median_nn, 3),
        "MadNN_ms": round(mad_nn, 3),
        "MCVNN": round(mcv_nn, 6),
        "IQRNN_ms": round(iqr_nn, 3),
        "MinNN_ms": round(min_nn, 3),
        "MaxNN_ms": round(max_nn, 3),
        "Prc20NN_ms": round(prc20_nn, 3),
        "Prc80NN_ms": round(prc80_nn, 3),
        "pNN50_pct": round(pnn50, 3),
        "pNN20_pct": round(pnn20, 3),
    }

    return {
        "session": session_label,
        "t_tachogram": t_tachogram,
        "tachogram_4hz": tachogram_4hz,
        "duration_seconds": duration_s,
        "target_fs": target_fs,
        "qc": qc,
        "time_domain_features": time_domain_features,
    }
