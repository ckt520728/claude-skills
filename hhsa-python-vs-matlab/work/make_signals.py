"""
make_signals.py -- generate the shared inputs for the Python/MATLAB comparison.

Both implementations must see byte-identical samples, otherwise any divergence
downstream is uninterpretable. So the signals are generated once, here, written
as plain text at full double precision (%.17g), and read back by both sides.

Outputs
-------
data/sig_<name>.txt      one sample per line, %.17g
data/manifest.json       fs, n, ground truth, and the shared spectral grids
"""
import json, numpy as np, pandas as pd, os

FS = 1000.0
os.makedirs('data', exist_ok=True)

def tvec(dur, fs=FS):
    return np.arange(round(dur * fs), dtype=float) / fs

sig = {}
meta = {}

# ---------------------------------------------------------------- EEG side
# Nguyen 2019 Supplementary Fig. S1: 2 Hz additive + 14 Hz carrier, 3 Hz AM
t = tvec(6.0)
sig['nguyen_s1'] = 0.5*np.sin(2*np.pi*2.0*t) + np.sin(2*np.pi*1.5*t)*np.sin(2*np.pi*14.0*t)
meta['nguyen_s1'] = dict(fs=FS, dur=6.0, truth=dict(additive_hz=2.0, carrier_hz=14.0, am_hz=3.0),
                         note='S2 = sin(2pi 1.5 t) sin(2pi 14 t); |envelope| is 3 Hz')

# Juan 2021 Fig. 4: fixed coupling strength beta = 0, 0.4, 1.0
t = tvec(4.0)
for b in (0.0, 0.4, 1.0):
    env = 1.0 + b*np.cos(2*np.pi*4.0*t)
    sig[f'juan_f4_b{int(b*10):02d}'] = np.sin(2*np.pi*4.0*t) + env*np.sin(2*np.pi*32.0*t)
    meta[f'juan_f4_b{int(b*10):02d}'] = dict(fs=FS, dur=4.0, truth=dict(carrier_hz=32.0, am_hz=4.0, beta=b))

# Juan 2021 Fig. 5: beta ramps 0 -> 1 across the 4 s
beta = t/t[-1]
sig['juan_f5_tv'] = np.sin(2*np.pi*4.0*t) + (1.0 + beta*np.cos(2*np.pi*4.0*t))*np.sin(2*np.pi*32.0*t)
meta['juan_f5_tv'] = dict(fs=FS, dur=4.0, truth=dict(carrier_hz=32.0, am_hz=4.0, beta='linear 0->1'),
                          probe_times=[0.5, 1.5, 2.5, 3.5])

# Juan 2021 Fig. 6: two carriers by one modulator / one carrier by two modulators
t = tvec(6.0)
slow = np.sin(2*np.pi*4.0*t)
sig['juan_f6a'] = (slow + (1.0+0.8*np.cos(2*np.pi*4.0*t))*np.sin(2*np.pi*32.0*t)
                        + (1.0+0.8*np.cos(2*np.pi*4.0*t))*np.sin(2*np.pi*64.0*t))
meta['juan_f6a'] = dict(fs=FS, dur=6.0, truth=dict(cells=[[32.0,4.0],[64.0,4.0]],
                                                   controls=[[32.0,8.0],[64.0,8.0]]))
sig['juan_f6b'] = slow + (2.0+0.8*np.cos(2*np.pi*4.0*t)+0.8*np.cos(2*np.pi*8.0*t))*np.sin(2*np.pi*32.0*t)
meta['juan_f6b'] = dict(fs=FS, dur=6.0, truth=dict(cells=[[32.0,4.0],[32.0,8.0]],
                                                   controls=[[64.0,4.0],[16.0,4.0]]))

# ---------------------------------------------------------------- CGMS side
# The patient series is deliberately absent from the public repository. When
# data/cgm_1min.csv is missing, everything above still runs: the seven published
# EEG simulations carry their own ground truth and need no patient data.
if os.path.exists('data/cgm_1min.csv'):
    df = pd.read_csv('data/cgm_1min.csv')
    g = df['glucose_mmol_L'].to_numpy()
    DEC = 5                              # analysis cadence 5 min
    x = g[::DEC]
    sig['cgm_5min'] = x
    meta['cgm_5min'] = dict(fs=12.0,      # samples per hour
                            dur=len(x)/12.0,
                            unit='mmol/L', dt_h=5/60.0,
                            truth=dict(expect_circadian_h=24.0),
                            note='13-day CGM, digitised from a vendor AGP PDF, '
                                 'decimated 1 min -> 5 min')
else:
    print('data/cgm_1min.csv not found -- EEG simulations only.')

# edge trim, identical on both sides: 0.25 s for the 1 kHz EEG simulations,
# 2 h for the 5-min CGM cadence. Edge-affected cycles are excluded rather than
# left in to contaminate the spectra.
for k in meta:
    meta[k]['edge_trim'] = 250 if meta[k]['fs'] == 1000.0 else 24
    meta[k]['grid'] = 'cgm' if k.startswith('cgm') else 'eeg'

for k, v in sig.items():
    np.savetxt(f'data/sig_{k}.txt', np.asarray(v, float), fmt='%.17g')
    meta[k]['n'] = int(len(v))
    print(f'{k:16s} n={len(v):6d}  fs={meta[k]["fs"]}  range [{np.min(v):.4f}, {np.max(v):.4f}]')

# shared spectral grids -- geometric, as in the 2026-08-21 Python validation run
grids = dict(
    eeg=dict(f_edges=np.geomspace(0.5, 128.0, 193).tolist(),
             w_edges=np.geomspace(0.5, 32.0, 145).tolist()),
    cgm=dict(f_edges=np.geomspace(1/24.0, 6.0, 97).tolist(),     # cycles/hour
             w_edges=np.geomspace(1/240.0, 1.0, 97).tolist()),
)
json.dump(dict(signals=meta, grids=grids), open('data/manifest.json','w'), indent=1)
print('\nwrote data/sig_*.txt and data/manifest.json')
