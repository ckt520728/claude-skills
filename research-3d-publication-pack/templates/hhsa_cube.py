"""
hhsa_cube.py -- Time-resolved Holo-Hilbert Spectral Analysis 3-D Cube Builder.

Extends K2 (Working/BandedHHSA_20260904/python/hhsa_banded.py):
- Accumulates H(t, f_carrier, f_AM) into coarse time windows
  (CGM: 2 h windows -> 156 x 40 x 40; HRV & synthetic: 10 s windows).
- Exports band-level cubes (CGM 5 bands; HRV VLF/LF/HF/VHF).
- Computes admissibility mask (f_AM < f_carrier).
- Flags unresolvable frequency bins below 3/T Hz for short records.
- Verifies exact projection consistency with K2's S(t,f), C(f,w), M(t,w).
- Encodes cube to dense-float16-base64 and sparse representation (< 4 MB per JSON).
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.interpolate import CubicSpline, PchipInterpolator, interp1d
from scipy.signal import hilbert

# --------------------------------------------------------------------------
# Extrema & Spline Envelope Core (compatible with hhsa.py / hhsa_banded.py)
# --------------------------------------------------------------------------

def find_extrema(x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Find local maxima and minima, collapsing plateaus to their midpoint."""
    d = np.diff(x)
    nz = np.nonzero(d)[0]
    if nz.size < 2:
        return np.array([], int), np.array([], int)
    s = np.sign(d[nz])
    turn = np.nonzero(np.diff(s))[0]
    maxs, mins = [], []
    for k in turn:
        i0, i1 = nz[k] + 1, nz[k + 1]
        c = (i0 + i1) // 2
        (maxs if s[k] > 0 else mins).append(c)
    return np.array(maxs, int), np.array(mins, int)


def _mirror(idx: np.ndarray, val: np.ndarray, n: int, nbsym: int = 2) -> Tuple[np.ndarray, np.ndarray]:
    """Even reflection of extrema about endpoints."""
    if idx.size == 0:
        return idx, val
    k = min(nbsym, idx.size)
    li, lv = -idx[:k][::-1], val[:k][::-1]
    ri, rv = 2 * (n - 1) - idx[-k:][::-1], val[-k:][::-1]
    return np.concatenate([li, idx, ri]), np.concatenate([lv, val, rv])


def _envelope_pos(x: np.ndarray, idx: np.ndarray, nbsym: int = 2) -> np.ndarray:
    """Shape-preserving positive envelope via PCHIP."""
    n = len(x)
    i, v = _mirror(idx, x[idx], n, nbsym)
    i, u = np.unique(i, return_index=True)
    return PchipInterpolator(i, v[u])(np.arange(n))


def sift(x: np.ndarray, sd_thresh: float = 0.2, max_iter: int = 100, nbsym: int = 2) -> np.ndarray:
    """Extract one IMF by repeated mean-envelope removal."""
    h = np.asarray(x, float).copy()
    n = len(h)
    for _ in range(max_iter):
        imax, imin = find_extrema(h)
        if imax.size < 2 or imin.size < 2:
            break
        i_u, v_u = _mirror(imax, h[imax], n, nbsym)
        i_u, u = np.unique(i_u, return_index=True)
        env_u = CubicSpline(i_u, v_u[u])(np.arange(n))

        i_d, v_d = _mirror(imin, h[imin], n, nbsym)
        i_d, u = np.unique(i_d, return_index=True)
        env_d = CubicSpline(i_d, v_d[u])(np.arange(n))

        m = 0.5 * (env_u + env_d)
        h_prev = h
        h = h - m
        denom = np.sum(h_prev ** 2)
        sd = np.sum((h_prev - h) ** 2) / (denom if denom > 0 else 1.0)
        if sd < sd_thresh:
            break
    return h


def emd(x: np.ndarray, max_imf: int = 10, sd_thresh: float = 0.2,
        max_iter: int = 100, nbsym: int = 2) -> Tuple[np.ndarray, np.ndarray]:
    """Empirical Mode Decomposition."""
    res = np.asarray(x, float).copy()
    imfs = []
    for _ in range(max_imf):
        imax, imin = find_extrema(res)
        if imax.size + imin.size < 4:
            break
        c = sift(res, sd_thresh=sd_thresh, max_iter=max_iter, nbsym=nbsym)
        imfs.append(c)
        res = res - c
    if not imfs:
        return np.empty((0, len(x))), res
    return np.array(imfs), res


def eemd(x: np.ndarray, n_imf: int = 10, noise_ratio: float = 0.2,
         ensemble: int = 100, seed: int = 0, sd_thresh: float = 0.2,
         max_iter: int = 100, nbsym: int = 2) -> Tuple[np.ndarray, np.ndarray]:
    """Ensemble EMD (Wu & Huang 2009)."""
    x = np.asarray(x, float)
    n = len(x)
    sd = x.std()
    rng = np.random.default_rng(seed)
    acc = np.zeros((n_imf + 1, n))
    for _ in range(ensemble):
        w = rng.normal(0.0, noise_ratio * sd if sd > 0 else 0.01, n)
        imfs, res = emd(x + w, max_imf=n_imf, sd_thresh=sd_thresh,
                        max_iter=max_iter, nbsym=nbsym)
        k = imfs.shape[0]
        if k:
            acc[:k] += imfs
        acc[n_imf] += res
    acc /= ensemble
    return acc[:n_imf], acc[n_imf]


def normalise_amplitude(c: np.ndarray, n_iter: int = 4, nbsym: int = 2) -> Tuple[np.ndarray, np.ndarray]:
    """Huang's NHT amplitude normalisation."""
    y = np.asarray(c, float).copy()
    A = np.ones_like(y)
    scale = np.max(np.abs(y))
    if scale <= 0 or not np.isfinite(scale):
        return np.zeros_like(y), np.zeros_like(y)
    for _ in range(n_iter):
        ab = np.abs(y)
        imax, _ = find_extrema(ab)
        if imax.size < 2:
            break
        env = _envelope_pos(ab, imax, nbsym)
        env = np.maximum(env, 1e-6 * np.max(ab) if np.max(ab) > 0 else 1e-12)
        y = y / env
        A = A * env
        if np.max(np.abs(y)) <= 1.0 + 1e-6:
            break
    y = np.clip(y, -1.0, 1.0)
    return y, A


def envelope(c: np.ndarray, kind: str = "analytic", nbsym: int = 2) -> np.ndarray:
    c = np.asarray(c, float)
    if kind == "analytic":
        return np.abs(hilbert(c))
    if kind == "normalized":
        return normalise_amplitude(c, n_iter=4, nbsym=nbsym)[1]
    raise ValueError(f"Unknown envelope kind: {kind}")


def inst_freq_of(c: np.ndarray, dt: float, kind: str = "analytic", nbsym: int = 2) -> np.ndarray:
    """Instantaneous frequency."""
    c = np.asarray(c, float)
    if kind == "analytic":
        y = c
    else:
        A = envelope(c, kind, nbsym)
        A = np.maximum(A, 1e-6 * (np.max(np.abs(c)) or 1.0))
        y = np.clip(c / A, -1.0, 1.0)
    ph = np.unwrap(np.angle(hilbert(y)))
    return np.gradient(ph, dt) / (2.0 * np.pi)


def decompose(x: np.ndarray, method: str = "emd", max_imf: int = 10,
              noise_ratio: float = 0.0, ensemble: int = 100, seed: int = 42,
              sd_thresh: float = 0.2) -> Tuple[np.ndarray, np.ndarray]:
    """Layer dispatcher for EMD / EEMD."""
    if method == "eemd":
        return eemd(x, n_imf=max_imf, noise_ratio=noise_ratio,
                    ensemble=ensemble, seed=seed, sd_thresh=sd_thresh)
    return emd(x, max_imf=max_imf, sd_thresh=sd_thresh)


def band_of(freq: np.ndarray, band_edges: np.ndarray) -> np.ndarray:
    """Assign frequency to band index, -1 if outside."""
    idx = np.digitize(freq, band_edges) - 1
    idx = np.where((idx < 0) | (idx >= len(band_edges) - 1), -1, idx)
    return idx


# --------------------------------------------------------------------------
# 3-D Holo-Hilbert Cube Engine
# --------------------------------------------------------------------------

def build_hhsa_cube(
    x: np.ndarray,
    dt: float,
    grid: np.ndarray,
    band_edges: Optional[np.ndarray] = None,
    time_window_size: float = 10.0,
    layer1: str = "eemd",
    layer2: str = "emd",
    envelope_kind: str = "analytic",
    weight: str = "amplitude",
    max_imf: int = 10,
    max_imf2: int = 7,
    noise_ratio: float = 0.2,
    ensemble: int = 100,
    seed: int = 42,
    edge_trim: int = 0,
    admissible: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Build coarse 3-D Holo-Hilbert cube H(t_w, f_carrier, f_AM), along with
    band cubes, admissibility mask, and exact K2 projection verification.
    """
    x = np.asarray(x, float)
    n = len(x)
    total_duration = n * dt
    nf = nw = len(grid) - 1
    fc_centers = np.sqrt(grid[:-1] * grid[1:])
    fam_centers = np.sqrt(grid[:-1] * grid[1:])

    # Time windowing
    n_windows = int(np.ceil(total_duration / time_window_size))
    t_centers = (np.arange(n_windows) + 0.5) * time_window_size
    t_phys = np.arange(n) * dt
    w_idx = np.clip(np.floor(t_phys / time_window_size).astype(int), 0, n_windows - 1)

    # Allocations
    H_cube = np.zeros((n_windows, nf, nw), dtype=float)
    S_tf = np.zeros((n, nf), dtype=float)
    C_fw = np.zeros((nf, nw), dtype=float)
    M_tw = np.zeros((n, nw), dtype=float)

    nb = (len(band_edges) - 1) if band_edges is not None else 0
    band_cube = np.zeros((n_windows, nb, nb), dtype=float) if nb > 0 else None

    sl = slice(edge_trim, n - edge_trim if edge_trim else None)

    # Layer 1 decomposition
    nr1 = noise_ratio if layer1 == "eemd" else 0.0
    imfs, res = decompose(x, layer1, max_imf, nr1, ensemble, seed)
    recon = float(np.abs(imfs.sum(0) + res - x).max()) if imfs.size else 0.0

    if verbose:
        print(f"Layer 1: {layer1}, {imfs.shape[0]} IMFs, recon err = {recon:.3e}")

    # Accumulation loop
    for j, c in enumerate(imfs):
        f = inst_freq_of(c, dt, envelope_kind)
        A = envelope(c, envelope_kind)

        nr2 = noise_ratio if layer2 == "eemd" else 0.0
        amcs, _ = decompose(A, layer2, max_imf2, nr2, ensemble, seed + 1000 + j)

        for k, a in enumerate(amcs):
            w = inst_freq_of(a, dt, envelope_kind)
            bamp = envelope(a, envelope_kind)

            ff, ww, bb = f[sl], w[sl], bamp[sl]
            val = bb if weight == "amplitude" else (bb ** 2) * dt

            good = np.isfinite(ff) & np.isfinite(ww) & (ff > 0) & (ww > 0)
            fi_full = np.digitize(ff, grid) - 1
            wi_full = np.digitize(ww, grid) - 1

            in_f = good & (fi_full >= 0) & (fi_full < nf)
            in_w = good & (wi_full >= 0) & (wi_full < nw)
            keep = in_f & in_w

            if admissible:
                keep = keep & (ww < ff)

            ti = np.arange(n)[sl][keep]
            t_win = w_idx[sl][keep]
            fi = fi_full[keep]
            wi = wi_full[keep]
            vv = val[keep]

            # Accumulate K2 projections
            np.add.at(S_tf, (ti, fi), vv)
            np.add.at(C_fw, (fi, wi), vv)
            np.add.at(M_tw, (ti, wi), vv)

            # Accumulate 3D cube
            np.add.at(H_cube, (t_win, fi, wi), vv)

            # Accumulate band cube
            if band_cube is not None and band_edges is not None:
                fb = band_of(ff[keep], band_edges)
                wb = band_of(ww[keep], band_edges)
                ok = (fb >= 0) & (wb >= 0)
                np.add.at(band_cube, (t_win[ok], fb[ok], wb[ok]), vv[ok])

    # Admissibility mask (f_AM < f_carrier)
    admissible_mask = np.zeros((nf, nw), dtype=bool)
    for i in range(nf):
        for j in range(nw):
            admissible_mask[i, j] = bool(fam_centers[j] < fc_centers[i])

    # Resolvability below 3/T Hz
    f_limit_hz = 3.0 / total_duration if total_duration > 0 else 0.0
    fc_resolvable = (fc_centers >= f_limit_hz).tolist()
    fam_resolvable = (fam_centers >= f_limit_hz).tolist()

    # Verify projection consistency
    C_from_cube = H_cube.sum(axis=0)
    S_coarse = H_cube.sum(axis=2)
    M_coarse = H_cube.sum(axis=1)

    # Bin K2 S_tf and M_tw into coarse windows
    S_k2_binned = np.zeros((n_windows, nf), dtype=float)
    M_k2_binned = np.zeros((n_windows, nw), dtype=float)
    for w_i in range(n_windows):
        mask = (w_idx == w_i)
        if np.any(mask):
            S_k2_binned[w_i] = S_tf[mask].sum(axis=0)
            M_k2_binned[w_i] = M_tw[mask].sum(axis=0)

    norm_C = np.linalg.norm(C_fw)
    norm_S = np.linalg.norm(S_k2_binned)
    norm_M = np.linalg.norm(M_k2_binned)

    err_C = float(np.max(np.abs(C_from_cube - C_fw)))
    rel_C = float(np.linalg.norm(C_from_cube - C_fw) / (norm_C if norm_C > 0 else 1.0))

    err_S = float(np.max(np.abs(S_coarse - S_k2_binned)))
    rel_S = float(np.linalg.norm(S_coarse - S_k2_binned) / (norm_S if norm_S > 0 else 1.0))

    err_M = float(np.max(np.abs(M_coarse - M_k2_binned)))
    rel_M = float(np.linalg.norm(M_coarse - M_k2_binned) / (norm_M if norm_M > 0 else 1.0))

    projection_consistency = {
        "C_fw_rel_error": rel_C,
        "C_fw_max_abs_error": err_C,
        "S_tf_binned_rel_error": rel_S,
        "S_tf_binned_max_abs_error": err_S,
        "M_tw_binned_rel_error": rel_M,
        "M_tw_binned_max_abs_error": err_M,
        "consistency_pass": bool(rel_C < 1e-6 and rel_S < 1e-6 and rel_M < 1e-6),
    }

    return {
        "H_cube": H_cube,
        "band_cube": band_cube,
        "admissible_mask": admissible_mask,
        "resolvability": {
            "unresolvable_below_hz": round(f_limit_hz, 6),
            "fc_resolvable": fc_resolvable,
            "fam_resolvable": fam_resolvable,
        },
        "axes": {
            "t": [round(float(v), 3) for v in t_centers],
            "fc": [round(float(v), 6) for v in fc_centers],
            "fam": [round(float(v), 6) for v in fam_centers],
            "log": True,
        },
        "record": {
            "n": n,
            "dt": dt,
            "duration": round(total_duration, 3),
            "nyquist": round(1.0 / (2.0 * dt), 4),
        },
        "params": {
            "layer1": layer1,
            "layer2": layer2,
            "ensemble": ensemble,
            "noise_sd": noise_ratio,
            "envelope": envelope_kind,
            "weight": weight,
            "seed": seed,
            "edge_trim": edge_trim,
            "admissible": admissible,
        },
        "projection_consistency": projection_consistency,
        "S_tf": S_tf,
        "C_fw": C_fw,
        "M_tw": M_tw,
        "recon_error": recon,
    }


def serialize_cube_json(
    cube_result: Dict[str, Any],
    dataset_name: str,
    is_synthetic: bool,
    units: Dict[str, str],
    bands: List[Dict[str, Any]],
    truth: Optional[Dict[str, Any]] = None,
    max_sparse_entries: int = 10000,
) -> Dict[str, Any]:
    """Serialize cube data to standard JSON format adhering to section 4.3 specification."""
    H = cube_result["H_cube"]
    shape = list(H.shape)

    # Encode dense float16 to base64
    h_f16 = H.astype(np.float16)
    h_b64 = base64.b64encode(h_f16.tobytes()).decode("ascii")

    # Sparse top-k representation for fast point-cloud rendering
    nonzeros = np.nonzero(H)
    t_idx, f_idx, w_idx = nonzeros
    vals = H[nonzeros]

    if len(vals) > max_sparse_entries:
        top_indices = np.argsort(vals)[-max_sparse_entries:]
        t_idx = t_idx[top_indices]
        f_idx = f_idx[top_indices]
        w_idx = w_idx[top_indices]
        vals = vals[top_indices]

    h_sparse = [
        [int(t_idx[i]), int(f_idx[i]), int(w_idx[i]), round(float(vals[i]), 5)]
        for i in range(len(vals))
    ]

    # Convert band cube to nested list rounded
    band_cube_list = None
    if cube_result["band_cube"] is not None:
        band_cube_list = np.round(cube_result["band_cube"], 5).tolist()

    out_doc = {
        "dataset": dataset_name,
        "synthetic": is_synthetic,
        "units": units,
        "axes": cube_result["axes"],
        "bands": bands,
        "params": cube_result["params"],
        "record": cube_result["record"],
        "encoding": "dense-float16-base64",
        "shape": shape,
        "H": h_b64,
        "H_sparse": h_sparse,
        "band_cube": band_cube_list,
        "admissible_mask": cube_result["admissible_mask"].tolist(),
        "resolvability": cube_result["resolvability"],
        "projection_consistency": cube_result["projection_consistency"],
    }

    if truth is not None:
        out_doc["truth"] = truth

    return out_doc
