"""
hhsa.py -- Holo-Hilbert Spectral Analysis, written out in full.

Reference method: N.E. Huang et al., "On Holo-Hilbert spectral analysis: a full
informational spectral representation for nonlinear and non-stationary data",
Phil. Trans. R. Soc. A 374:20150206 (2016).

Why implement rather than import: the point of this exercise is to be able to
state every parameter that a reviewer would ask for (ensemble size, noise
amplitude, sifting criterion, boundary treatment, how instantaneous frequency
is obtained). A black-box call cannot do that.

Structure of HHSA
-----------------
Layer 1   EMD of x(t)               -> IMFs c_j(t)      carrier frequency f_j(t)
          normalised Hilbert        -> envelope A_j(t)
Layer 2   EMD of each A_j(t)        -> sub-IMFs a_jk(t) modulation freq w_jk(t)
Holo      energy of a_jk binned jointly in (f_j, w_jk), keeping only w < f

A conventional Hilbert spectrum collapses layer 2 away; that is precisely the
amplitude-modulation information HHSA is built to keep.

Note on EEMD. The literature convention is to use EEMD in both layers. eemd() is
provided and used for sensitivity analysis, but test_hhsa_synthetic.py shows on
known ground truth that the added noise splits an AM carrier into sidebands and
destroys the modulation HHSA is measuring (layer-2 modulation energy fell
389 -> 98 as noise went 0 -> 0.2 x SD). Plain EMD is therefore the default in
both layers here, and that choice is reported rather than assumed.
"""
import numpy as np
from scipy.interpolate import CubicSpline, PchipInterpolator
from scipy.signal import hilbert

# --------------------------------------------------------------------------
# extrema, with plateau handling
# --------------------------------------------------------------------------
def find_extrema(x):
    """Indices of local maxima and minima.

    CGM values are stored on a 0.1 mmol/L grid, so flat runs are common. A
    naive comparison-based detector would return every sample of a flat peak.
    Each plateau is collapsed to its midpoint instead.
    """
    d = np.diff(x)
    nz = np.nonzero(d)[0]
    if nz.size < 2:
        return np.array([], int), np.array([], int)
    s = np.sign(d[nz])
    turn = np.nonzero(np.diff(s))[0]
    maxs, mins = [], []
    for k in turn:
        i0, i1 = nz[k] + 1, nz[k + 1]        # plateau spans i0..i1
        c = (i0 + i1) // 2
        (maxs if s[k] > 0 else mins).append(c)
    return np.array(maxs, int), np.array(mins, int)


def _mirror(idx, val, n, nbsym=2):
    """Even reflection of the extrema set about the two end samples.

    Cubic-spline envelopes are undefined outside the extrema hull, so without
    this the first and last partial cycles of every IMF are garbage. Reflection
    about the endpoint is the standard remedy; it is not perfect, which is why
    the driver script reports how many cycles at each end are edge-affected.
    """
    if idx.size == 0:
        return idx, val
    k = min(nbsym, idx.size)
    li, lv = -idx[:k][::-1], val[:k][::-1]                  # about sample 0
    ri, rv = 2 * (n - 1) - idx[-k:][::-1], val[-k:][::-1]   # about sample n-1
    return np.concatenate([li, idx, ri]), np.concatenate([lv, val, rv])


def _envelope(x, idx, nbsym=2):
    n = len(x)
    i, v = _mirror(idx, x[idx], n, nbsym)
    i, u = np.unique(i, return_index=True)
    return CubicSpline(i, v[u])(np.arange(n))


def _envelope_pos(x, idx, nbsym=2):
    """Envelope of a strictly positive quantity, without overshoot.

    A natural cubic spline through the maxima of |IMF| can undershoot to near
    zero (or overshoot far above the data) wherever a mode is intermittent and
    successive maxima differ by orders of magnitude. Dividing by such an
    envelope, four times over, sends the amplitude to 1e6 and up. PCHIP is
    shape-preserving, so the amplitude normalisation stays bounded.
    """
    n = len(x)
    i, v = _mirror(idx, x[idx], n, nbsym)
    i, u = np.unique(i, return_index=True)
    return PchipInterpolator(i, v[u])(np.arange(n))


# --------------------------------------------------------------------------
# sifting / EMD
# --------------------------------------------------------------------------
def sift(x, sd_thresh=0.2, max_iter=100, nbsym=2):
    """Extract one IMF by repeated mean-envelope removal."""
    h = x.astype(float).copy()
    for _ in range(max_iter):
        imax, imin = find_extrema(h)
        if imax.size + imin.size < 3:
            break
        m = 0.5 * (_envelope(h, imax, nbsym) + _envelope(h, imin, nbsym))
        h_new = h - m
        denom = np.sum(h ** 2)
        sd = np.sum((h - h_new) ** 2) / denom if denom > 0 else 0.0
        h = h_new
        if sd < sd_thresh:
            break
    return h


def emd(x, max_imf=10, sd_thresh=0.2, max_iter=100, nbsym=2):
    """Empirical Mode Decomposition. Returns (imfs, residual)."""
    r = np.asarray(x, float).copy()
    imfs = []
    while len(imfs) < max_imf:
        imax, imin = find_extrema(r)
        if imax.size + imin.size < 3:       # residual is monotonic / trend
            break
        c = sift(r, sd_thresh, max_iter, nbsym)
        imfs.append(c)
        r = r - c
    return np.array(imfs) if imfs else np.zeros((0, len(x))), r


def eemd(x, n_imf=10, noise_ratio=0.2, ensemble=100, seed=0,
         sd_thresh=0.2, max_iter=100, nbsym=2):
    """Ensemble EMD (Wu & Huang 2009).

    White noise of amplitude `noise_ratio` x SD(x) is added to each realisation
    and the IMFs are averaged. This populates the whole time-frequency plane so
    that sifting cannot mode-mix, at the cost of exact reconstruction: the
    ensemble mean of the IMFs does not sum exactly back to x. The driver
    reports that reconstruction residual rather than hiding it.
    """
    x = np.asarray(x, float)
    n = len(x)
    sd = x.std()
    rng = np.random.default_rng(seed)
    acc = np.zeros((n_imf + 1, n))          # +1 row for the trend/residual
    for _ in range(ensemble):
        w = rng.normal(0.0, noise_ratio * sd, n)
        imfs, res = emd(x + w, max_imf=n_imf, sd_thresh=sd_thresh,
                        max_iter=max_iter, nbsym=nbsym)
        k = imfs.shape[0]
        if k:
            acc[:k] += imfs                  # rows beyond k contribute 0
        acc[n_imf] += res                    # trend of this realisation
    acc /= ensemble
    return acc[:n_imf], acc[n_imf]


# --------------------------------------------------------------------------
# normalised Hilbert transform -> instantaneous amplitude and frequency
# --------------------------------------------------------------------------
def normalise_amplitude(c, n_iter=4, nbsym=2):
    """Split an IMF into envelope A(t) and unit-amplitude carrier y(t).

    Applying the Hilbert transform straight to an AM-FM signal violates the
    Bedrosian identity whenever amplitude and carrier spectra overlap. Huang's
    normalisation scheme divides out the envelope first (iterating on the
    spline through the maxima of |c|), so the Hilbert transform only ever sees
    a signal of near-constant amplitude.
    """
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
        # Floor the envelope RELATIVE to the mode's own scale. An absolute
        # floor lets a near-zero envelope blow the amplitude up by many orders
        # of magnitude on modes that are numerically empty (pure EEMD residue).
        env = np.maximum(env, 1e-6 * np.max(ab) if np.max(ab) > 0 else 1e-12)
        y = y / env
        A = A * env
        if np.max(np.abs(y)) <= 1.0 + 1e-6:
            break
    y = np.clip(y, -1.0, 1.0)
    return y, A


def inst_freq(c, dt, n_iter=4, nbsym=2):
    """Instantaneous amplitude A(t) and frequency f(t) [cycles per unit time]."""
    y, A = normalise_amplitude(c, n_iter, nbsym)
    phase = np.unwrap(np.angle(hilbert(y)))
    f = np.gradient(phase, dt) / (2 * np.pi)
    return A, f


# --------------------------------------------------------------------------
# spectra
# --------------------------------------------------------------------------
def hilbert_marginal(imfs, dt, f_edges, edge_trim=0):
    """Conventional Hilbert marginal spectrum: energy vs carrier frequency."""
    h = np.zeros(len(f_edges) - 1)
    per_imf = []
    for c in imfs:
        A, f = inst_freq(c, dt)
        sl = slice(edge_trim, len(c) - edge_trim if edge_trim else None)
        A, f = A[sl], f[sl]
        good = np.isfinite(f) & (f > 0)
        idx = np.digitize(f[good], f_edges) - 1
        ok = (idx >= 0) & (idx < len(h))
        contrib = np.zeros(len(h))
        np.add.at(contrib, idx[ok], (A[good][ok] ** 2) * dt)
        h += contrib
        per_imf.append(contrib)
    return h, np.array(per_imf)


def holo_spectrum(imfs, dt, f_edges, w_edges, n_imf2=6, noise_ratio=0.2,
                  ensemble=50, seed=1, edge_trim=0, verbose=False,
                  admissible_ratio=1.0):
    """The 2-D holo-spectrum H(f, w).

    f = carrier frequency from layer 1, w = amplitude-modulation frequency from
    layer 2. Energy is the squared layer-2 sub-IMF amplitude, so H(f, w) reads
    'how much of the energy carried at rate f is being modulated at rate w'.

    Admissibility
    -------------
    Amplitude modulation is only physically meaningful when the modulation is
    slower than the thing it modulates: w < f. Points with w >= f are not AM at
    all -- they are either degenerate (w == f) or inverted (w > f), where the
    "envelope" varies faster than the carrier and the carrier/modulator roles
    have effectively swapped. Such points are envelope-estimation ripple, not
    physiology, and are excluded. `admissible_ratio` sets the cut as
    w < admissible_ratio * f; the discarded energy fraction is returned so the
    exclusion is auditable rather than silent.
    """
    H = np.zeros((len(f_edges) - 1, len(w_edges) - 1))
    detail = []
    e_keep = e_drop = 0.0
    for j, c in enumerate(imfs):
        A, f = inst_freq(c, dt)
        # Layer 2 defaults to plain EMD (ensemble <= 1). An amplitude envelope
        # is smooth and near-unimodal, so it does not need EEMD's mode-mixing
        # protection -- and the added noise actively destroys the modulation
        # energy being measured (validated in test_hhsa_synthetic.py).
        if ensemble <= 1:
            am_imfs, am_res = emd(A, max_imf=n_imf2)
        else:
            am_imfs, am_res = eemd(A, n_imf=n_imf2, noise_ratio=noise_ratio,
                                   ensemble=ensemble, seed=seed + j)
        for k, a in enumerate(am_imfs):
            B, w = inst_freq(a, dt)
            sl = slice(edge_trim, len(c) - edge_trim if edge_trim else None)
            ff, ww, BB = f[sl], w[sl], B[sl]
            good = np.isfinite(ff) & np.isfinite(ww) & (ff > 0) & (ww > 0)
            adm = good & (ww < admissible_ratio * ff)     # AM admissibility
            e_keep += float(np.sum(BB[adm] ** 2) * dt)
            e_drop += float(np.sum(BB[good & ~adm] ** 2) * dt)
            fi = np.digitize(ff[adm], f_edges) - 1
            wi = np.digitize(ww[adm], w_edges) - 1
            ok = ((fi >= 0) & (fi < H.shape[0]) & (wi >= 0) & (wi < H.shape[1]))
            np.add.at(H, (fi[ok], wi[ok]), (BB[adm][ok] ** 2) * dt)
            detail.append({'imf': j, 'sub': k,
                           'energy': float(np.sum(a ** 2)),
                           'mean_w_period': float(
                               1.0 / np.median(w[np.isfinite(w) & (w > 0)]))
                           if np.any(np.isfinite(w) & (w > 0)) else np.nan})
        if verbose:
            print(f'    layer-2 done for IMF{j+1}')
    tot = e_keep + e_drop
    diag = {'energy_admissible': e_keep, 'energy_rejected': e_drop,
            'rejected_fraction': (e_drop / tot) if tot > 0 else 0.0}
    return H, detail, diag


def noise_null_bounds(n, dt, n_imf=10, ensemble=100, seed=99, pct=(5, 95)):
    """Wu & Huang white-noise null for IMF energy.

    EEMD of pure white noise yields IMFs whose mean energy falls on a known
    decay with period. An IMF of the real signal is only worth interpreting if
    its energy sits above that null band -- otherwise it is indistinguishable
    from what the method produces from noise alone.
    Returns per-IMF (median period, energy percentiles) for unit-variance noise.
    """
    rng = np.random.default_rng(seed)
    E = np.zeros((ensemble, n_imf))
    T = np.zeros((ensemble, n_imf))
    for i in range(ensemble):
        w = rng.normal(0, 1, n)
        imfs, _ = emd(w, max_imf=n_imf)
        for j, c in enumerate(imfs):
            E[i, j] = np.mean(c ** 2)
            zc = np.sum(np.diff(np.signbit(c)) != 0)
            T[i, j] = (2 * n * dt / zc) if zc else np.nan
    out = []
    for j in range(n_imf):
        e = E[:, j][E[:, j] > 0]
        t = T[:, j][np.isfinite(T[:, j])]
        if e.size == 0:
            continue
        out.append({'imf': j + 1,
                    'period_h': float(np.median(t)) if t.size else np.nan,
                    'e_lo': float(np.percentile(e, pct[0])),
                    'e_med': float(np.median(e)),
                    'e_hi': float(np.percentile(e, pct[1]))})
    return out


def imf_stats(imfs, dt, total_var):
    """Per-IMF summary: energy share and characteristic period."""
    rows = []
    for j, c in enumerate(imfs):
        imax, imin = find_extrema(c)
        n_ext = imax.size + imin.size
        # zero-crossing period is robust for near-oscillatory modes
        zc = np.sum(np.diff(np.signbit(c)) != 0)
        T_zc = (2 * len(c) * dt / zc) if zc else np.nan
        A, f = inst_freq(c, dt)
        fp = f[np.isfinite(f) & (f > 0)]
        T_if = 1.0 / np.median(fp) if fp.size else np.nan
        rows.append({
            'imf': j + 1,
            'period_zc_h': T_zc,
            'period_if_h': T_if,
            'energy': float(np.sum(c ** 2)),
            'var_pct': 100.0 * np.var(c) / total_var,
            'mean_amp': float(np.mean(A)),
            'n_extrema': int(n_ext),
        })
    return rows
