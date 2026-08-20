"""
hhsa_pipeline.py -- physiological time series -> two-layer HHSA -> one-page dashboard.

One entry point. Give it a CSV with a time column and a value column; it runs the
whole chain and writes a self-contained HTML dashboard plus every intermediate
number as CSV/JSON.

    python hhsa_pipeline.py --input cgm.csv --time-col timestamp --value-col glucose \
        --unit mmol/L --resample 5 --out out/ --label "13-day CGM"

Chain
-----
    1  ingest      parse, sort, check gaps, resample to a uniform grid
    2  audit       effective resolution: what cadence still carries information
    3  layer 1     EMD -> IMFs, instantaneous amplitude and frequency
    4  nulls       white-noise null (Wu & Huang) per IMF
    5  layer 2     EMD of each envelope -> holo-spectrum, admissibility ω < f
    6  surrogates  AAFT (is the joint structure real?) + rotation (clock-locked?)
    7  dashboard   figures + single-file HTML

Every step writes its numbers out. Nothing in the dashboard is asserted that is
not in one of those files.

Design rules this script enforces, and why, are in ../references/pitfalls.md.
The short version:
  - plain EMD in BOTH layers (EEMD noise destroys the AM that HHSA measures)
  - admissibility ω < f, with the rejected fraction reported
  - a ~24 h IMF proves nothing on its own -- EMD is a dyadic filter bank
  - never interpret below the effective resolution found in step 2
"""
import argparse, json, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from scipy.signal import welch
from scipy.interpolate import CubicSpline

from hhsa import (emd, eemd, inst_freq, imf_stats, hilbert_marginal,
                  holo_spectrum, noise_null_bounds)


# ------------------------------------------------------------------ 1. ingest
def ingest(path, time_col, value_col, resample_min, log):
    df = pd.read_csv(path)
    for c in (time_col, value_col):
        if c not in df.columns:
            raise SystemExit(f'column "{c}" not in {path}; found {list(df.columns)}')
    t = pd.to_datetime(df[time_col], errors='coerce')
    v = pd.to_numeric(df[value_col], errors='coerce')
    ok = t.notna() & v.notna()
    log(f'  rows read           : {len(df)}   usable: {int(ok.sum())}')
    t, v = t[ok].to_numpy(), v[ok].to_numpy(float)
    order = np.argsort(t)
    t, v = t[order], v[order]

    dt_s = np.diff(t).astype('timedelta64[s]').astype(float)
    med = float(np.median(dt_s)) if dt_s.size else np.nan
    log(f'  native cadence      : median {med/60:.2f} min '
        f'(min {dt_s.min()/60:.2f}, max {dt_s.max()/60:.2f})')
    gaps = dt_s > 3 * med
    if gaps.any():
        log(f'  GAPS                : {int(gaps.sum())} interval(s) > 3x median, '
            f'largest {dt_s.max()/3600:.1f} h -- these are interpolated across; '
            f'do not interpret modes shorter than the largest gap')

    step = resample_min * 60.0
    tsec = (t - t[0]).astype('timedelta64[s]').astype(float)
    grid = np.arange(0, tsec[-1] + step / 2, step)
    x = np.interp(grid, tsec, v)
    log(f'  resampled           : {resample_min} min grid, n = {len(x)}, '
        f'span {grid[-1]/3600:.1f} h = {grid[-1]/86400:.2f} days')
    return grid / 3600.0, x, pd.Timestamp(t[0]), med / 60.0


# ------------------------------------------------------------------- 2. audit
def _detect_lattice(x):
    """Find the storage quantum, if the values live on a grid.

    A blind linear scan over step sizes will walk straight past the true
    quantum unless it happens to land on it -- an earlier version scanned
    `arange(range/2000, range/20, range/2000)` and missed a planted 0.1 grid
    because 0.1 was not a multiple of its own step. So: test the smallest
    non-zero increment (which IS the quantum whenever any two adjacent samples
    differ by one step) plus round-number candidates, and prefer the LARGEST
    step that still fits, since every divisor of the true quantum also scores
    perfectly.
    """
    d = np.abs(np.diff(x))
    d = d[d > 1e-12]
    cands = set()
    if d.size:
        cands.add(round(float(d.min()), 12))
    span = float(np.ptp(x))
    for dec in range(-5, 2):
        for m in (1.0, 2.0, 2.5, 5.0):
            q = m * 10.0 ** dec
            if 1e-9 < q < max(span / 5.0, 1e-9):
                cands.add(round(q, 12))
    scored = []
    for q in sorted(cands):
        r = x / q
        scored.append((q, float(np.abs(r - np.round(r)).mean())))
    good = [(q, s) for q, s in scored if s < 0.02]
    if good:
        return max(good, key=lambda t: t[0])          # largest step that fits
    return min(scored, key=lambda t: t[1]) if scored else (None, 1.0)


def audit_resolution(x, dt_h, log):
    """How fine a cadence still carries information? Everything faster is noise,
    quantisation, or vendor smoothing -- and EMD will turn it into IMFs anyway."""
    out = {}
    d1 = np.diff(x)
    best_q, best_s = _detect_lattice(x)
    out['lattice_step'] = best_q
    out['lattice_score'] = best_s
    if best_s < 0.05:
        log(f'  quantisation        : values sit on a {best_q:.4g} grid '
            f'(score {best_s:.4f}; 0 = perfect, 0.25 = none)')
    else:
        log(f'  quantisation        : no clear lattice (best score {best_s:.3f}) -- '
            f'values look continuous')
    out['frac_zero_steps'] = float(np.mean(d1 == 0))
    out['sd_increment'] = float(d1.std())
    log(f'  1-step increments   : SD {d1.std():.4g}, '
        f'{100*np.mean(d1==0):.1f} % exactly zero')

    # decimate-and-restore
    log(f'  decimate-and-restore (thin by k, spline back, RMSE):')
    dec = {}
    for k in (2, 3, 5, 10, 20):
        if len(x) // k < 20:
            continue
        idx = np.arange(0, len(x), k)
        rec = CubicSpline(idx, x[idx])(np.arange(len(x)))
        e = float(np.sqrt(np.mean((rec - x) ** 2)))
        dec[k] = e
        flag = ''
        if best_q and e < best_q:
            flag = '  <- below one quantisation step: no information here'
        log(f'      k={k:>3}  ({k*dt_h*60:>6.1f} min)  RMSE {e:.4g}{flag}')
    out['decimate_rmse'] = dec

    # spectral roll-off, fast vs slow band
    f, P = welch(x - x.mean(), fs=1 / dt_h, nperseg=min(1024, len(x) // 4))
    per = 1 / f[1:]
    P = P[1:]
    def slope(lo, hi):
        m = (per >= lo) & (per <= hi)
        if m.sum() < 5:
            return np.nan
        return float(np.polyfit(np.log10(1 / per[m]), np.log10(P[m]), 1)[0])
    fast = slope(2 * dt_h, 10 * dt_h)
    slow = slope(20 * dt_h, 240 * dt_h)
    out['psd_slope_fast'], out['psd_slope_slow'] = fast, slow
    log(f'  PSD log-log slope   : fast band {fast:+.2f}, slow band {slow:+.2f}')
    if np.isfinite(fast) and np.isfinite(slow) and fast < slow - 0.3:
        log(f'      steepening at the fast end = smoothing/filtering, not a white '
            f'noise floor. Treat the fastest IMFs as instrument, not physiology.')
    return out


# ---------------------------------------------------------------- 6. surrogates
def aaft(y, rng):
    n = len(y)
    z = np.sort(rng.normal(size=n))[np.argsort(np.argsort(y))]
    Z = np.fft.rfft(z)
    ph = rng.uniform(0, 2 * np.pi, len(Z))
    ph[0] = 0.0
    if n % 2 == 0:
        ph[-1] = 0.0
    zs = np.fft.irfft(np.abs(Z) * np.exp(1j * ph), n=n)
    return np.sort(y)[np.argsort(np.argsort(zs))]


def surrogate_test(x, dt_h, target_period, n_sur, edge, log):
    """Does the record carry structure a spectrum-matched linear process would not?

    AAFT keeps the power spectrum, so it ALREADY contains any spectral peak:
    this cannot test whether a rhythm exists, only whether the joint
    carrier-modulation structure exceeds a linear null.
    """
    rng = np.random.default_rng(2026)
    n = len(x)
    core = slice(edge, n - edge)

    def stat(y):
        imfs, _ = emd(y, max_imf=11)
        per = np.array([_period(c, dt_h) for c in imfs])
        j = int(np.argmin(np.abs(per - target_period)))
        A, _ = inst_freq(imfs[j], dt_h)
        Ac = A[core]
        return {'period': per[j],
                'var_pct': 100 * np.var(imfs[j]) / np.var(y),
                'am_depth': Ac.std() / Ac.mean() if Ac.mean() > 0 else np.nan}

    obs = stat(x)
    sur = [stat(aaft(x, rng)) for _ in range(n_sur)]
    S = pd.DataFrame(sur)
    res = {}
    for k in obs:
        s = S[k].to_numpy()
        s = s[np.isfinite(s)]
        p = float((1 + np.sum(s >= obs[k])) / (1 + len(s)))
        res[k] = {'observed': float(obs[k]), 'sur_mean': float(s.mean()),
                  'sur_sd': float(s.std()), 'p_one_sided': p}
        verdict = ('above null' if p < 0.05 else
                   'BELOW null (more regular than linear)' if p > 0.95 else
                   'indistinguishable from null')
        log(f'      {k:<10} obs {obs[k]:8.3f}   null {s.mean():7.3f} +- {s.std():.3f}'
            f'   p={p:.3f}  {verdict}')
    return res


def rotation_test(x, dt_h, period_h, n_perm, log):
    """Is the rhythm locked to an external clock, or just a slow mode?

    Keeps each cycle's internal dynamics and destroys only its phase alignment.
    This is the test that actually licenses the word "circadian"/"diurnal".
    """
    per_n = int(round(period_h / dt_h))
    n_cyc = len(x) // per_n
    if n_cyc < 3:
        log('      too few full cycles for a rotation test -- skipped')
        return None
    m = x[:n_cyc * per_n].reshape(n_cyc, per_n)
    rng = np.random.default_rng(7)

    def stat(mm):
        prof = mm.mean(axis=0)
        ss_b = mm.shape[0] * np.sum((prof - mm.mean()) ** 2)
        ss_t = np.sum((mm - mm.mean()) ** 2)
        return {'profile_amplitude': float(np.ptp(prof)),
                'var_explained_pct': float(100 * ss_b / ss_t)}

    obs = stat(m)
    null = [stat(np.array([np.roll(m[i], rng.integers(per_n))
                           for i in range(n_cyc)])) for _ in range(n_perm)]
    N = pd.DataFrame(null)
    res = {}
    for k in obs:
        s = N[k].to_numpy()
        p = float((1 + np.sum(s >= obs[k])) / (1 + len(s)))
        res[k] = {'observed': obs[k], 'null_mean': float(s.mean()),
                  'p_one_sided': p}
        log(f'      {k:<20} obs {obs[k]:8.3f}   null {s.mean():7.3f}   p={p:.4f}')
    res['n_cycles'] = n_cyc
    res['period_h'] = period_h
    return res


def _period(c, dt_h):
    zc = np.sum(np.diff(np.signbit(c)) != 0)
    return (2 * len(c) * dt_h / zc) if zc else np.inf


# ------------------------------------------------------------------- pipeline
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--input', required=True, help='CSV file')
    ap.add_argument('--time-col', default='timestamp')
    ap.add_argument('--value-col', default='value')
    ap.add_argument('--unit', default='')
    ap.add_argument('--label', default='time series')
    ap.add_argument('--resample', type=float, default=5.0,
                    help='analysis cadence in minutes')
    ap.add_argument('--cycle-h', type=float, default=24.0,
                    help='candidate entrainment period for the rotation test')
    ap.add_argument('--max-imf', type=int, default=11)
    ap.add_argument('--surrogates', type=int, default=199)
    ap.add_argument('--permutations', type=int, default=4999)
    ap.add_argument('--edge-h', type=float, default=None,
                    help='hours trimmed at each end (default: one --cycle-h)')
    ap.add_argument('--bands', default='',
                    help='optional clinical bands, e.g. "3.9:10.0:in range"')
    ap.add_argument('--out', default='hhsa_out')
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    os.makedirs(os.path.join(a.out, 'figs'), exist_ok=True)
    lines = []
    def log(s=''):
        print(s)
        lines.append(s)

    R = {'label': a.label, 'unit': a.unit, 'input': os.path.basename(a.input)}

    log('=' * 74)
    log(f'HHSA  |  {a.label}')
    log('=' * 74)
    log('\n[1] INGEST')
    t_h, x, t0, native_min = ingest(a.input, a.time_col, a.value_col,
                                    a.resample, log)
    dt = a.resample / 60.0
    n = len(x)
    R['n'] = n
    R['dt_min'] = a.resample
    R['span_h'] = float(t_h[-1])
    R['native_cadence_min'] = native_min
    R['mean'] = float(x.mean())
    R['sd'] = float(x.std(ddof=1))
    log(f'  mean {x.mean():.3f} {a.unit}   SD {x.std(ddof=1):.3f}   '
        f'CV {100*x.std(ddof=1)/x.mean():.1f} %')

    log('\n[2] EFFECTIVE RESOLUTION AUDIT')
    R['audit'] = audit_resolution(x, dt, log)

    edge_h = a.edge_h if a.edge_h is not None else a.cycle_h
    EDGE = min(int(edge_h / dt), n // 4)
    core = slice(EDGE, n - EDGE)
    log(f'\n[3] LAYER 1 -- EMD   (edge policy: {EDGE*dt:.1f} h trimmed each end)')
    imfs, res = emd(x, max_imf=a.max_imf)
    recon = float(np.abs(imfs.sum(0) + res - x).max())
    log(f'  IMFs {imfs.shape[0]}   reconstruction error {recon:.2e}')
    tot = np.var(x)
    rows = imf_stats(imfs, dt, tot)
    log(f'  {"IMF":>4}{"period(h)":>11}{"var %":>8}{"mean amp":>11}{"AM depth":>10}')
    imf_tab = []
    for j, c in enumerate(imfs):
        A, _ = inst_freq(c, dt)
        Ac = A[core]
        amd = float(Ac.std() / Ac.mean()) if Ac.mean() > 0 else np.nan
        log(f'  {j+1:>4}{rows[j]["period_zc_h"]:>11.2f}{rows[j]["var_pct"]:>8.1f}'
            f'{Ac.mean():>11.3f}{amd:>10.2f}')
        imf_tab.append({'imf': j + 1, 'period_h': rows[j]['period_zc_h'],
                        'var_pct': rows[j]['var_pct'],
                        'mean_amp': float(Ac.mean()), 'am_depth': amd})
    var_sum = sum(r['var_pct'] for r in rows) + 100 * np.var(res) / tot
    log(f'  residual var {100*np.var(res)/tot:.1f} %   '
        f'(shares sum to {var_sum:.1f} %: EMD modes are not exactly orthogonal)')
    R['recon_error'] = recon
    R['var_sum_pct'] = float(var_sum)
    R['residual_var_pct'] = float(100 * np.var(res) / tot)

    log('\n[4] WHITE-NOISE NULL PER MODE  (Wu & Huang)')
    null = noise_null_bounds(n, dt, n_imf=a.max_imf, ensemble=100, seed=99)
    for j, c in enumerate(imfs):
        if j >= len(null):
            break
        e_obs = float(np.mean(c[core] ** 2))
        e_hi = null[j]['e_hi'] * tot
        ratio = e_obs / e_hi if e_hi > 0 else np.inf
        imf_tab[j]['null_ratio'] = float(ratio)
        imf_tab[j]['above_null'] = bool(ratio > 1)
        log(f'  IMF{j+1:<2} {rows[j]["period_zc_h"]:>8.2f} h   '
            f'obs/null95 = {ratio:6.2f}   '
            f'{"above noise" if ratio > 1 else "not above noise"}')
    log('  NOTE: this null is WHITE. A red signal is expected to fall below it at')
    log('  fast scales; that is not proof the fast modes are artefacts.')
    R['imfs'] = imf_tab

    log('\n[5] LAYER 2 -- HOLO-HILBERT SPECTRUM')
    f_edges = np.geomspace(1 / (4 * R['span_h']), 1 / (2 * dt), 61)
    w_edges = np.geomspace(1 / (4 * R['span_h']), 1 / (4 * dt), 41)
    fc = np.sqrt(f_edges[:-1] * f_edges[1:])
    wc = np.sqrt(w_edges[:-1] * w_edges[1:])
    H, _, diag = holo_spectrum(imfs, dt, f_edges, w_edges, n_imf2=6,
                               ensemble=1, edge_trim=EDGE)
    log(f'  layer 2 = plain EMD on each envelope (NOT EEMD -- see pitfalls.md)')
    log(f'  admissibility w < f : rejected {100*diag["rejected_fraction"]:.1f} % '
        f'of layer-2 energy')
    R['holo_rejected_frac'] = diag['rejected_fraction']
    hm, _ = hilbert_marginal(imfs, dt, f_edges, edge_trim=EDGE)

    # The point of HHSA: for each carrier, WHERE does its amplitude modulation
    # live? Without this the run is just an EMD with extra steps.
    log('  carrier -> dominant modulation (admissible cells only):')
    for j in range(imfs.shape[0]):
        A, fq = inst_freq(imfs[j], dt)
        fq = fq[core][np.isfinite(fq[core]) & (fq[core] > 0)]
        if fq.size == 0:
            continue
        fmed = float(np.median(fq))
        b = int(np.digitize([fmed], f_edges)[0]) - 1
        if not (0 <= b < H.shape[0]):
            continue
        col = H[max(0, b - 1):min(H.shape[0], b + 2)].sum(axis=0)
        if col.sum() <= 0:
            continue
        k = int(np.argmax(col))
        imf_tab[j]['carrier_h'] = 1 / fmed
        imf_tab[j]['dom_mod_h'] = float(1 / wc[k])
        imf_tab[j]['mod_share_pct'] = float(100 * col[k] / col.sum())
        log(f'    IMF{j+1:<2} carrier {1/fmed:7.2f} h  ->  modulated at '
            f'{1/wc[k]:8.1f} h  ({100*col[k]/col.sum():.0f} % of its layer-2 energy)')

    per = np.array([r['period_zc_h'] for r in rows])
    jc = int(np.argmin(np.abs(per - a.cycle_h)))
    R['cycle_imf'] = jc + 1
    R['cycle_period_h'] = float(per[jc])
    R['cycle_var_pct'] = float(rows[jc]['var_pct'])
    log(f'  mode nearest {a.cycle_h} h : IMF{jc+1} at {per[jc]:.2f} h '
        f'({rows[jc]["var_pct"]:.1f} % of variance)')

    log(f'\n[6] SURROGATES  ({a.surrogates} AAFT: is the joint structure real?)')
    R['aaft'] = surrogate_test(x, dt, a.cycle_h, a.surrogates, EDGE, log)
    log(f'\n    ROTATION TEST ({a.permutations} perms: is it locked to the clock?)')
    R['rotation'] = rotation_test(x, dt, a.cycle_h, a.permutations, log)

    # ---------------------------------------------------------------- bands
    bands = []
    for spec in filter(None, a.bands.split(',')):
        lo, hi, name = spec.split(':')
        pct = float(100 * np.mean((x >= float(lo)) & (x <= float(hi))))
        bands.append({'lo': float(lo), 'hi': float(hi), 'name': name, 'pct': pct})
    if bands:
        log('\n[7] BAND OCCUPANCY')
        for b in bands:
            log(f'  {b["name"]:<16} {b["lo"]}-{b["hi"]}  {b["pct"]:5.1f} %')
        total = sum(b['pct'] for b in bands)
        if total > 100.5:
            log(f'  WARNING: bands total {total:.1f} % -- edges are INCLUSIVE on both'
                f' sides, so adjacent bands sharing an edge double-count it.')
        elif total < 99.5:
            log(f'  NOTE: bands total {total:.1f} % -- they do not cover the record.')
    R['bands'] = bands

    # --------------------------------------------------------- cycle profile
    per_n = int(round(a.cycle_h / dt))
    n_cyc = n // per_n
    prof = None
    if n_cyc >= 2:
        m = x[:n_cyc * per_n].reshape(n_cyc, per_n)
        prof = m.mean(axis=0)
        ph = np.arange(per_n) * dt
        R['profile'] = {'phase_h': ph.tolist(), 'mean': prof.tolist()}
        R['profile_trough'] = {'value': float(prof.min()),
                               'at_h': float(ph[int(np.argmin(prof))])}
        R['profile_peak'] = {'value': float(prof.max()),
                             'at_h': float(ph[int(np.argmax(prof))])}
        log(f'\n[8] CYCLE-AVERAGED PROFILE over {n_cyc} cycles of {a.cycle_h} h')
        log(f'  trough {prof.min():.2f} at +{ph[np.argmin(prof)]:.1f} h, '
            f'peak {prof.max():.2f} at +{ph[np.argmax(prof)]:.1f} h, '
            f'swing {np.ptp(prof):.2f} {a.unit}')

    # ------------------------------------------------------------- figures
    make_figures(a, R, t_h, x, imfs, res, per, jc, fc, wc, H, hm, dt, prof, bands)

    # ------------------------------------------------------------- persist
    pd.DataFrame(imf_tab).to_csv(os.path.join(a.out, 'imf_table.csv'), index=False)
    np.savetxt(os.path.join(a.out, 'holo_matrix.csv'), H, delimiter=',')
    with open(os.path.join(a.out, 'results.json'), 'w', encoding='utf-8') as f:
        json.dump(R, f, indent=2, default=float)
    with open(os.path.join(a.out, 'hhsa_log.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    from build_dashboard import build
    html = build(R, a.out)
    with open(os.path.join(a.out, 'dashboard.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    log(f'\nwrote {a.out}/dashboard.html, results.json, imf_table.csv, '
        f'holo_matrix.csv, hhsa_log.txt, figs/')


def make_figures(a, R, t_h, x, imfs, res, per, jc, fc, wc, H, hm, dt, prof, bands):
    d = os.path.join(a.out, 'figs')
    plt.rcParams.update({'font.size': 8, 'figure.dpi': 130,
                         'axes.spines.top': False, 'axes.spines.right': False})
    cyc = a.cycle_h

    fig, ax = plt.subplots(figsize=(11, 3.2))
    for b in bands:
        ax.axhspan(b['lo'], b['hi'], color='#c8e6c9', alpha=.45, lw=0, label=b['name'])
    ax.plot(t_h / cyc, x, lw=.45, color='#1a237e')
    ax.plot(t_h / cyc, imfs[jc] + res, lw=1.5, color='#e65100',
            label=f'IMF{jc+1} ({per[jc]:.1f} h) + trend')
    ax.set_xlabel(f'cycle ({cyc:g} h) of recording')
    ax.set_ylabel(f'{a.label} ({a.unit})')
    ax.set_title(f'{a.label}: record and the {per[jc]:.1f} h mode')
    ax.legend(loc='upper right', fontsize=7, framealpha=.9)
    fig.tight_layout(); fig.savefig(f'{d}/series.png'); plt.close(fig)

    k = imfs.shape[0]
    fig, axes = plt.subplots(k + 2, 1, figsize=(11, 1.15 * (k + 2)), sharex=True)
    axes[0].plot(t_h / cyc, x, lw=.5, color='k')
    axes[0].set_ylabel('x(t)', rotation=0, ha='right', va='center')
    for j in range(k):
        axes[j+1].plot(t_h / cyc, imfs[j], lw=.6, color='#1565c0')
        axes[j+1].plot(t_h / cyc, inst_freq(imfs[j], dt)[0], lw=.8, color='#d84315')
        axes[j+1].set_ylabel(f'IMF{j+1}\n{per[j]:.1f} h', rotation=0, ha='right',
                             va='center', fontsize=7)
    axes[-1].plot(t_h / cyc, res, lw=1.2, color='#2e7d32')
    axes[-1].set_ylabel('residual', rotation=0, ha='right', va='center', fontsize=7)
    axes[-1].set_xlabel(f'cycle ({cyc:g} h)')
    axes[0].set_title('EMD; red = instantaneous amplitude envelope A(t)')
    fig.tight_layout(); fig.savefig(f'{d}/imfs.png'); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 5.2))
    Hm = np.ma.masked_where(H <= 0, H)
    pcm = ax.pcolormesh(1 / fc, 1 / wc, Hm.T, norm=LogNorm(), cmap='magma',
                        shading='auto')
    ax.set_xscale('log'); ax.set_yscale('log')
    ax.set_xlabel('carrier period  1/f  (h)')
    ax.set_ylabel('modulation period  1/ω  (h)')
    ax.set_title('Holo-Hilbert spectrum H(f, ω)\nadmissible AM only (ω < f)')
    lim = np.array([1 / fc.max(), 1 / fc.min()])
    ax.plot(lim, lim, color='w', ls='--', lw=.9)
    ax.axhline(cyc, color='#4dd0e1', ls=':', lw=1)
    fig.colorbar(pcm, ax=ax, label='energy density')
    fig.tight_layout(); fig.savefig(f'{d}/holo.png'); plt.close(fig)

    fig, ax = plt.subplots(1, 2, figsize=(10, 3.4))
    ax[0].loglog(1 / fc, hm, lw=1.2, color='#1a237e')
    ax[0].axvline(cyc, color='#e65100', ls='--', lw=.8)
    ax[0].set_xlabel('carrier period (h)'); ax[0].set_ylabel('Hilbert marginal energy')
    ax[0].set_title('Hilbert marginal spectrum')
    if prof is not None:
        ph = np.arange(len(prof)) * dt
        ax[1].plot(ph, prof, lw=1.4, color='#3949ab')
        ax[1].set_xlabel(f'phase within {cyc:g} h cycle')
        ax[1].set_ylabel(f'mean ({a.unit})')
        ax[1].set_title('Cycle-averaged profile')
    for q in ax: q.grid(alpha=.25, which='both')
    fig.tight_layout(); fig.savefig(f'{d}/spectra.png'); plt.close(fig)


if __name__ == '__main__':
    main()
