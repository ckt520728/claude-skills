"""
test_hhsa_synthetic.py -- Ground-truth validation of the HHSA implementation.

Build a signal whose carrier and modulation frequencies are known exactly, then
check that (a) EMD separates the components, (b) instantaneous frequency comes
back right, and (c) the holo-spectrum puts energy at the correct (f, w) cell --
the last being the whole point of HHSA and the thing a plain Hilbert spectrum
gets wrong.

Ground truth
    x(t) = [1 + 0.5 cos(2 pi t / 24h)] * cos(2 pi t / 3h)   AM component
         + 0.7 cos(2 pi t / 12h)                            pure tone
    carrier periods present : 3 h and 12 h
    the 3 h carrier is amplitude-modulated at period 24 h
So the holo-spectrum must show a peak at (f = 1/3h, w = 1/24h) that a
conventional Hilbert marginal spectrum cannot express at all.
"""
import numpy as np, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hhsa import emd, eemd, inst_freq, holo_spectrum, find_extrema

dt = 5 / 60.0                       # 5 min, expressed in hours
n = 3744                            # same length as the real series
t = np.arange(n) * dt

am = (1 + 0.5 * np.cos(2 * np.pi * t / 24.0)) * np.cos(2 * np.pi * t / 3.0)
tone = 0.7 * np.cos(2 * np.pi * t / 12.0)
x = am + tone

print('=== 1. extrema detector, incl. plateau handling ===')
p = np.array([0, 1, 2, 2, 2, 1, 0, -1, -1, 0, 1])
mx, mn = find_extrema(p)
print(f'  plateau signal {p.tolist()}')
# plateau 2,2,2 spans idx 2-4 -> midpoint 3;  plateau -1,-1 spans 7-8 -> midpoint 7
print(f'  maxima at {mx.tolist()} (expect [3]), minima at {mn.tolist()} (expect [7])')
assert mx.tolist() == [3] and mn.tolist() == [7], 'plateau handling broken'
print('  OK')

print('\n=== 2. instantaneous frequency of a known tone ===')
pure = np.cos(2 * np.pi * t / 3.0)
A, f = inst_freq(pure, dt)
core = slice(200, n - 200)
print(f'  true period 3.000 h ->  recovered median {1/np.median(f[core]):.4f} h, '
      f'IQR {1/np.percentile(f[core],75):.4f}-{1/np.percentile(f[core],25):.4f}')
print(f'  envelope should be 1.0 -> mean {A[core].mean():.4f} (sd {A[core].std():.4f})')

print('\n=== 3. EMD separation ===')
imfs, res = emd(x, max_imf=8)
print(f'  {imfs.shape[0]} IMFs; reconstruction max error = '
      f'{np.abs(imfs.sum(axis=0) + res - x).max():.3e}')
for j, c in enumerate(imfs):
    A, f = inst_freq(c, dt)
    fp = f[core][np.isfinite(f[core]) & (f[core] > 0)]
    T = 1 / np.median(fp) if fp.size else np.nan
    print(f'   IMF{j+1}: median period {T:8.3f} h   var {100*np.var(c)/np.var(x):5.1f}%'
          f'   env sd {A[core].std():.3f}')

print('\n=== 4. holo-spectrum: does the (3h carrier, 24h modulation) cell light up? ===')
f_edges = np.geomspace(1 / 200.0, 1 / 0.4, 41)      # cycles per hour
w_edges = np.geomspace(1 / 400.0, 1 / 2.0, 31)
fc = np.sqrt(f_edges[:-1] * f_edges[1:])
wc = np.sqrt(w_edges[:-1] * w_edges[1:])


def report(tag, imf_set):
    H, det, diag = holo_spectrum(imf_set, dt, f_edges, w_edges, n_imf2=5,
                                 ensemble=1, edge_trim=200)
    i, j = np.unravel_index(np.argmax(H), H.shape)
    band = (1 / fc > 2.2) & (1 / fc < 4.2)
    col = H[band].sum(axis=0)
    cen = np.exp(np.sum(col * np.log(1 / wc)) / np.sum(col)) if col.sum() else np.nan
    print(f'  [{tag}]')
    print(f'    peak cell: carrier {1/fc[i]:6.2f} h, modulation {1/wc[j]:7.2f} h')
    print(f'    2.2-4.2 h carrier band -> energy-weighted modulation {cen:.2f} h')
    print(f'    inadmissible (w >= f) energy rejected: '
          f'{100*diag["rejected_fraction"]:.1f}%')
    return cen


print('  ground truth: carrier 3 h, modulation 24 h\n')
cen_emd = report('plain EMD layer 1', imfs)

ee, trend = eemd(x, n_imf=8, noise_ratio=0.2, ensemble=30, seed=0)
print('\n  EEMD layer-1 carrier periods (noise shifts the IMF index):')
for j, c in enumerate(ee):
    A, f = inst_freq(c, dt)
    fp = f[core][np.isfinite(f[core]) & (f[core] > 0)]
    T = 1 / np.median(fp) if fp.size else np.nan
    print(f'    IMF{j+1}: {T:8.3f} h  var {100*np.var(c)/np.var(x):5.1f}%')
cen_ee = report('EEMD layer 1', ee)

ok = abs(cen_emd - 24) / 24 < 0.15
print(f'\n  VERDICT: plain-EMD modulation period within 15% of 24 h -> {ok}')
assert ok, 'holo-spectrum failed to localise the known modulation'
