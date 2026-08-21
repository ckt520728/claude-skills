"""
run_python_side.py -- the Python HHSA over the same shared signals.

Run from the project root:
    python python/run_python_side.py

Two configurations, mirroring the MATLAB side's two:
  py        the implementation exactly as it ships in Working/hhsa.py
            (plain EMD both layers, PCHIP-normalised envelope, admissibility
             f_am < f_c enforced pointwise)
  py_noadm  identical except the admissibility cut is disabled, so that the
            holo-spectra can be compared against the MATLAB reference matrix
            without that one rule confounding everything else
"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from hhsa import emd, inst_freq, hilbert_marginal, holo_spectrum

man = json.load(open('data/manifest.json'))
os.makedirs('output', exist_ok=True)

MAX_IMF, MAX_IMF2 = 9, 7

for nm, S in man['signals'].items():
    x = np.loadtxt(f'data/sig_{nm}.txt')
    dt = 1.0 / S['fs']
    G = man['grids'][S['grid']]
    f_edges = np.array(G['f_edges']); w_edges = np.array(G['w_edges'])
    et = S['edge_trim']

    t0 = time.time(); imfs, res = emd(x, max_imf=MAX_IMF); t_l1 = time.time() - t0
    hht, _ = hilbert_marginal(imfs, dt, f_edges, edge_trim=et)

    for cfg, ratio in (('py', 1.0), ('py_noadm', 1e9)):
        t0 = time.time()
        H, detail, diag = holo_spectrum(imfs, dt, f_edges, w_edges, n_imf2=MAX_IMF2,
                                        ensemble=1, edge_trim=et,
                                        admissible_ratio=ratio)
        t_l2 = time.time() - t0
        tag = f'output/py_{nm}_{cfg}'
        np.savetxt(tag + '_H.txt', H)
        if cfg == 'py':
            np.savetxt(f'output/py_{nm}_imfs.txt', imfs)
            np.savetxt(f'output/py_{nm}_res.txt', res[None, :])
            np.savetxt(f'output/py_{nm}_hht.txt', hht[None, :])

        tv = np.var(x); rows = []
        for j, c in enumerate(imfs):
            zc = int(np.sum(np.diff(np.signbit(c)) != 0))
            A, f = inst_freq(c, dt)
            fp = f[np.isfinite(f) & (f > 0)]
            rows.append(dict(imf=j + 1,
                             period_zc=(2 * len(c) * dt / zc) if zc else float('nan'),
                             period_if=float(1.0 / np.median(fp)) if fp.size else float('nan'),
                             energy=float(np.sum(c ** 2)),
                             var_pct=float(100 * np.var(c) / tv),
                             mean_amp=float(np.mean(A))))
        summ = dict(signal=nm, method=cfg, n=int(len(x)), fs=S['fs'],
                    n_imf=int(imfs.shape[0]),
                    recon_err=float(np.max(np.abs(imfs.sum(0) + res - x))),
                    rejected_fraction=float(diag['rejected_fraction']),
                    t_layer1=t_l1, t_layer2=t_l2, wall=t_l1 + t_l2,
                    imf_stats=rows)
        json.dump(summ, open(tag + '_summary.json', 'w'))
        print(f'[{nm} / {cfg}] {imfs.shape[0]} IMFs, '
              f'L1 {t_l1:.1f}s L2 {t_l2:.1f}s, recon {summ["recon_err"]:.2e}, '
              f'rejected {100*diag["rejected_fraction"]:.4f}%')

print('\nPython side complete.')
