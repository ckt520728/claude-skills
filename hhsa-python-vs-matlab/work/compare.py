"""
compare.py -- put the two implementations side by side on identical inputs.

Everything here reads artefacts already written to output/ by
matlab/run_matlab_side.m and python/run_python_side.py. Nothing is recomputed
from memory; if a number appears in the report it comes from this file.

Configurations compared
-----------------------
  mat_mask   MATLAB/NCU reference : masking EMD, natural spline, |IMF|-maxima
             envelope, no admissibility cut
  mat_emd    same, but plain EMD  : isolates what masking EMD alone changes
  py         Python as shipped    : plain EMD, PCHIP normalisation, f_am < f_c
  py_noadm   Python, cut disabled : isolates the admissibility rule
"""
import json, os, sys
import numpy as np
sys.path.insert(0, 'python')
from hhsa import emd, inst_freq

man = json.load(open('data/manifest.json'))
SIGS = list(man['signals'])
CFGS = ['mat_mask', 'mat_mask_pchip', 'mat_emd', 'mat_emd_pchip',
        'mat_emd_nak_pchip', 'py', 'py_noadm']

# the attribution ladder: each step changes exactly one thing
LADDER = [('mat_mask', 'mat_mask_pchip', 'amplitude-normalisation spline: natural -> PCHIP'),
          ('mat_mask_pchip', 'mat_emd_pchip', 'decomposition: masking EMD -> plain EMD'),
          ('mat_emd_pchip', 'mat_emd_nak_pchip', 'sifting spline: natural -> not-a-knot'),
          ('mat_emd_nak_pchip', 'py_noadm', 'layer-2 envelope: |IMF|-maxima spline -> 4x PCHIP normalisation'),
          ('py_noadm', 'py', 'admissibility cut f_am < f_c: off -> on')]


def centers(edges):
    e = np.asarray(edges)
    return np.sqrt(e[:-1] * e[1:])


def load(cfg, nm, what):
    if cfg.startswith('mat'):
        base = 'output/mat_%s_%s' % (nm, cfg[4:])
    elif what in ('H', 'summary'):
        base = 'output/py_%s_%s' % (nm, cfg)
    else:
        base = 'output/py_%s' % nm
    if what == 'summary':
        return json.load(open(base + '_summary.json'))
    a = np.loadtxt(base + '_' + what + '.txt')
    return np.atleast_2d(a) if what == 'imfs' else a


def cell_energy(H, fc, wc, f_c, w_c, rel=0.18):
    fm = (f_c >= fc * (1 - rel)) & (f_c <= fc * (1 + rel))
    wm = (w_c >= wc * (1 - rel)) & (w_c <= wc * (1 + rel))
    return float(H[np.ix_(fm, wm)].sum())


def band_peak(v, c, lo, hi):
    m = (c >= lo) & (c <= hi)
    if not m.any() or v[m].max() <= 0:
        return float('nan')
    return float(c[m][int(np.argmax(v[m]))])


def holo_peak(H, f_c, w_c, flim, wlim):
    fm = (f_c >= flim[0]) & (f_c <= flim[1])
    wm = (w_c >= wlim[0]) & (w_c <= wlim[1])
    roi = H[np.ix_(fm, wm)]
    i, j = np.unravel_index(int(np.argmax(roi)), roi.shape)
    return float(f_c[fm][i]), float(w_c[wm][j]), float(roi.sum())


def cos_sim(A, B):
    a, b = A.ravel(), B.ravel()
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a @ b / (na * nb)) if na > 0 and nb > 0 else float('nan')


R = {'structure': {}, 'imf_match': {}, 'spectra': {}, 'ground_truth': {}, 'cgm': {}}

# ------------------------------------------------------------------ 1. structure
for nm in SIGS:
    row = {}
    for cfg in CFGS:
        s = load(cfg, nm, 'summary')
        row[cfg] = dict(
            n_imf=s['n_imf'], recon_err=s['recon_err'], wall=s.get('wall'),
            t_layer1=s.get('t_layer1'), t_layer2=s.get('t_layer2'),
            rejected=s.get('rejected_fraction',
                           s.get('rejected_fraction_if_admissibility_applied')))
    R['structure'][nm] = row

# ------------------------------------------------------------ 2. IMF correspondence
for nm in SIGS:
    P = load('py', nm, 'imfs')
    out = {}
    for cfg in ('mat_mask', 'mat_mask_pchip', 'mat_emd', 'mat_emd_pchip',
                'mat_emd_nak_pchip'):
        M = load(cfg, nm, 'imfs')
        C = np.zeros((M.shape[0], P.shape[0]))
        for i in range(M.shape[0]):
            for j in range(P.shape[0]):
                a = M[i] - M[i].mean()
                b = P[j] - P[j].mean()
                d = np.linalg.norm(a) * np.linalg.norm(b)
                C[i, j] = (a @ b / d) if d > 0 else 0.0
        best = []
        for i in range(M.shape[0]):
            j = int(np.argmax(np.abs(C[i])))
            best.append(dict(mat_imf=i + 1, py_imf=j + 1, r=float(C[i][j]),
                             mat_var_pct=float(100 * np.var(M[i]) / np.var(M.sum(0)))))
        # A raw "worst matched mode" statistic is dominated by the last one or
        # two IMFs, which carry a fraction of a percent of the variance and
        # always diverge -- EMD's tail is chaotic in both languages. The honest
        # statistic is how much VARIANCE sits in modes that do correspond.
        ev = np.array([np.var(M[i]) for i in range(M.shape[0])])
        good = np.array([np.max(np.abs(C[i])) >= 0.9 for i in range(M.shape[0])])
        out[cfg] = dict(corr=C.tolist(), best=best,
                        max_abs_r_per_py_imf=[float(np.max(np.abs(C[:, j])))
                                              for j in range(P.shape[0])],
                        matched_var_fraction=float(ev[good].sum() / ev.sum())
                        if ev.sum() > 0 else float('nan'),
                        n_matched=int(good.sum()))
    R['imf_match'][nm] = out

# --------------------------------------------------------------- 3. spectra
for nm in SIGS:
    G = man['grids'][man['signals'][nm]['grid']]
    f_c, w_c = centers(G['f_edges']), centers(G['w_edges'])
    Hs = {cfg: load(cfg, nm, 'H') for cfg in CFGS}
    norm = {k: (v / v.sum() if v.sum() > 0 else v) for k, v in Hs.items()}
    pairs = [(a, b) for a, b, _ in LADDER] + [
        ('mat_mask', 'py'), ('mat_emd', 'py'), ('mat_mask', 'py_noadm'),
        ('mat_emd', 'py_noadm'), ('mat_mask', 'mat_emd'),
        ('mat_mask_pchip', 'py_noadm'), ('py', 'py_noadm')]
    R['spectra'][nm] = dict(
        total_energy={k: float(v.sum()) for k, v in Hs.items()},
        cosine={a + '|' + b: cos_sim(norm[a], norm[b]) for a, b in pairs},
        peak={k: dict(zip(('fc', 'fam', 'energy'),
                          holo_peak(v, f_c, w_c, (f_c[0], f_c[-1]), (w_c[0], w_c[-1]))))
              for k, v in Hs.items()})

# ---------------------------------------------------------- 4. EEG ground truth
G = man['grids']['eeg']
f_c, w_c = centers(G['f_edges']), centers(G['w_edges'])
gt = {}

nm = 'nguyen_s1'
gt[nm] = {}
for cfg in CFGS:
    H = load(cfg, nm, 'H')
    hht = load(cfg, nm, 'hht').ravel()
    fc_pk, fam_pk, e = holo_peak(H, f_c, w_c, (11.0, 17.0), (2.4, 3.6))
    fm = (f_c >= 11) & (f_c <= 17)
    band = H[fm].sum(axis=0)
    conc = float(band[(w_c >= 2) & (w_c <= 4)].sum() / band.sum()) if band.sum() > 0 else float('nan')
    gt[nm][cfg] = dict(hht_peak_2hz=band_peak(hht, f_c, 1.6, 2.4),
                       hht_peak_14hz=band_peak(hht, f_c, 11.0, 17.0),
                       holo_carrier=fc_pk, holo_am=fam_pk, roi_energy=e,
                       am_band_concentration_2_4hz=conc)

gt['juan_fig4'] = {}
for cfg in CFGS:
    es = [cell_energy(load(cfg, 'juan_f4_b' + b, 'H'), 32.0, 4.0, f_c, w_c)
          for b in ('00', '04', '10')]
    gt['juan_fig4'][cfg] = dict(
        energy_beta0=es[0], energy_beta04=es[1], energy_beta1=es[2],
        monotonic=bool(es[0] < es[1] < es[2]),
        ratio_b04_b0=float(es[1] / es[0]) if es[0] > 0 else float('inf'),
        ratio_b1_b0=float(es[2] / es[0]) if es[0] > 0 else float('inf'))

for nm, cells, ctrls in (('juan_f6a', [(32, 4), (64, 4)], [(32, 8), (64, 8)]),
                         ('juan_f6b', [(32, 4), (32, 8)], [(64, 4), (16, 4)])):
    gt[nm] = {}
    for cfg in CFGS:
        H = load(cfg, nm, 'H')
        te = {'%dx%d' % (a, b): cell_energy(H, a, b, f_c, w_c) for a, b in cells}
        ce = {'%dx%d' % (a, b): cell_energy(H, a, b, f_c, w_c) for a, b in ctrls}
        mc = min(ce.values())
        gt[nm][cfg] = dict(target=te, control=ce,
                           min_specificity_ratio=(float(min(te.values()) / mc)
                                                  if mc > 0 else float('inf')))
R['ground_truth'] = gt

# ------------------------------------------- 5. Juan Fig. 5, time-resolved cell
# The MATLAB side reads this straight off its (f_am, f_c, t) cube. The Python
# API has no time axis in holo_spectrum(), so the layer-2 loop has to be
# re-implemented here by hand -- which is itself one of the findings.
nm = 'juan_f5_tv'
S = man['signals'][nm]
dt = 1.0 / S['fs']
x = np.loadtxt('data/sig_%s.txt' % nm)
imfs, _ = emd(x, max_imf=9)
probes = [0.5, 1.5, 2.5, 3.5]
hw = int(round(0.15 / dt))
py_ts = []
for p in probes:
    c0 = int(round(p / dt))
    sl = slice(max(0, c0 - hw), min(len(x), c0 + hw))
    e = 0.0
    for c in imfs:
        A, f = inst_freq(c, dt)
        a2, _ = emd(A, max_imf=7)
        for a in a2:
            B, w = inst_freq(a, dt)
            m = ((f[sl] >= 32 * 0.82) & (f[sl] <= 32 * 1.18) &
                 (w[sl] >= 4 * 0.82) & (w[sl] <= 4 * 1.18))
            e += float(np.sum(B[sl][m] ** 2) * dt)
    py_ts.append(e)

mat_ts = {c: load(c, nm, 'summary').get('roi_energy')
          for c in CFGS if c.startswith('mat')}
beta2 = np.array([(p / 4.0) ** 2 for p in probes])


def corr(a):
    a = np.asarray(a, float)
    if a.size != beta2.size or not np.all(np.isfinite(a)) or a.std() == 0:
        return float('nan')
    return float(np.corrcoef(beta2, a)[0, 1])


def mono(a):
    return bool(np.all(np.diff(np.asarray(a, float)) > 0)) if a is not None else None


R['fig5_time_resolved'] = dict(
    probe_times=probes, beta_squared=beta2.tolist(),
    energy=dict(list(mat_ts.items()) + [('py', py_ts)]),
    r=dict([(k, corr(v)) for k, v in mat_ts.items()] + [('py', corr(py_ts))]),
    monotonic=dict([(k, mono(v)) for k, v in mat_ts.items()] + [('py', mono(py_ts))]))

# --------------------------------------------------------------------- 6. CGM
nm = 'cgm_5min'
Gc = man['grids']['cgm']
fcc, wcc = centers(Gc['f_edges']), centers(Gc['w_edges'])
cg = {}
for cfg in (CFGS if nm in SIGS else []):
    s = load(cfg, nm, 'summary')
    H = load(cfg, nm, 'H')
    per = [r['period_zc'] for r in s['imf_stats']]
    var = [r['var_pct'] for r in s['imf_stats']]
    circ = int(np.argmin([abs(p - 24.0) for p in per])) if per else -1
    fc_pk, fam_pk, _ = holo_peak(H, fcc, wcc, (fcc[0], fcc[-1]), (wcc[0], wcc[-1]))
    cg[cfg] = dict(periods_h=per, var_pct=var, n_imf=s['n_imf'],
                   circadian_imf=circ + 1,
                   circadian_period_h=per[circ] if circ >= 0 else float('nan'),
                   circadian_var_pct=var[circ] if circ >= 0 else float('nan'),
                   holo_peak_carrier_period_h=1.0 / fc_pk if fc_pk > 0 else float('nan'),
                   holo_peak_am_period_h=1.0 / fam_pk if fam_pk > 0 else float('nan'),
                   energy_24h_carrier=float(cell_energy(H, 1 / 24, 1 / 24, fcc, wcc, rel=0.30)))
R['cgm'] = cg

json.dump(R, open('output/comparison.json', 'w'), indent=1)
print('wrote output/comparison.json')

print('\n== IMF counts ==')
print('%-14s' % 'signal' + ''.join('%10s' % c for c in CFGS))
for nm in SIGS:
    print('%-14s' % nm + ''.join('%10d' % R['structure'][nm][c]['n_imf'] for c in CFGS))

print('\n== attribution ladder: cosine similarity across each single change ==')
print('%-16s' % 'signal' + ''.join('%9s' % ('step%d' % (i + 1))
                                   for i in range(len(LADDER))))
for nm in SIGS:
    c = R['spectra'][nm]['cosine']
    print('%-16s' % nm + ''.join('%9.3f' % c[a + '|' + b] for a, b, _ in LADDER))
print('\nsteps (each changes exactly one thing):')
for i, (a, b, d) in enumerate(LADDER):
    print('  step%d  %s' % (i + 1, d))

print('\n== reference (mat_mask) vs shipped Python (py) ==')
for nm in SIGS:
    sp = R['spectra'][nm]
    print('%-16s cosine %.3f   total holo energy: MATLAB %.4g   Python %.4g'
          % (nm, sp['cosine']['mat_mask|py'],
             sp['total_energy']['mat_mask'], sp['total_energy']['py']))
