"""
make_figures.py -- figures for the Python/MATLAB HHSA comparison.

Every panel is drawn from the artefacts in output/; nothing is recomputed here
except the raw signals, which are read back from data/.
"""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

plt.rcParams.update({
    'figure.dpi': 130, 'savefig.dpi': 130, 'font.size': 9,
    'axes.titlesize': 10, 'axes.labelsize': 9, 'axes.grid': True,
    'grid.alpha': 0.25, 'axes.spines.top': False, 'axes.spines.right': False,
    'figure.facecolor': 'white', 'savefig.facecolor': 'white',
})

MAT = '#c1440e'      # MATLAB / NCU reference
PY = '#1f6feb'       # Python
MID = '#6b7280'

man = json.load(open('data/manifest.json'))
R = json.load(open('output/comparison.json'))
CFGS = ['mat_mask', 'mat_mask_pchip', 'mat_emd', 'mat_emd_pchip',
        'mat_emd_nak_pchip', 'py', 'py_noadm']
LADDER_LABELS = ['1  normalisation\nspline', '2  masking EMD\n-> plain EMD',
                 '3  sifting spline', '4  layer-2\nenvelope', '5  admissibility\ncut']


def centers(e):
    e = np.asarray(e)
    return np.sqrt(e[:-1] * e[1:])


def path(cfg, nm, what):
    if cfg.startswith('mat'):
        return 'output/mat_%s_%s_%s.txt' % (nm, cfg[4:], what)
    if what in ('H',):
        return 'output/py_%s_%s_%s.txt' % (nm, cfg, what)
    return 'output/py_%s_%s.txt' % (nm, what)


def L(cfg, nm, what):
    a = np.loadtxt(path(cfg, nm, what))
    return np.atleast_2d(a) if what == 'imfs' else a


# ---------------------------------------------------------------- figure 1
def fig1():
    nm = 'nguyen_s1'
    S = man['signals'][nm]
    G = man['grids']['eeg']
    fc, wc = centers(G['f_edges']), centers(G['w_edges'])
    x = np.loadtxt('data/sig_%s.txt' % nm)
    t = np.arange(len(x)) / S['fs']

    fig = plt.figure(figsize=(11, 6.4))
    gs = fig.add_gridspec(2, 3, height_ratios=[0.8, 1.25], hspace=0.42, wspace=0.28)

    ax = fig.add_subplot(gs[0, :])
    ax.plot(t[:2000], x[:2000], color='#111', lw=0.7)
    ax.set(xlabel='time (s)', ylabel='amplitude',
           title='Nguyen et al. 2019 Supplementary Fig. S1 test signal   '
                 r'$0.5\sin(2\pi\,2t)+\sin(2\pi\,1.5t)\sin(2\pi\,14t)$'
                 '   (first 2 s of 6 s shown)')

    ax = fig.add_subplot(gs[1, 0])
    for cfg, col, lab in (('mat_mask', MAT, 'MATLAB reference (masking EMD)'),
                          ('py', PY, 'Python as shipped')):
        h = L(cfg, nm, 'hht').ravel()
        ax.semilogx(fc, h / h.max(), color=col, lw=1.3, label=lab)
    for f0 in (2.0, 14.0):
        ax.axvline(f0, color=MID, ls=':', lw=0.9)
    ax.set(xlabel='carrier frequency (Hz)', ylabel='normalised energy',
           xlim=(1, 60), title='HHT marginal spectrum\nboth find 2 Hz and 14 Hz')
    ax.legend(fontsize=7, loc='upper right')

    for k, (cfg, ttl) in enumerate([('mat_mask_pchip', 'MATLAB reference'),
                                    ('py', 'Python as shipped')]):
        ax = fig.add_subplot(gs[1, 1 + k])
        H = L(cfg, nm, 'H')
        Hp = np.where(H > 0, H, np.nan)
        vmax = np.nanmax(Hp)
        m = ax.pcolormesh(fc, wc, Hp.T, norm=LogNorm(vmax * 1e-5, vmax),
                          cmap='magma', shading='auto')
        ax.plot(14, 3, 'o', mfc='none', mec='#39d353', mew=1.6, ms=11)
        ax.set(xscale='log', yscale='log', xlim=(2, 60), ylim=(0.7, 20),
               xlabel=r'carrier $f_c$ (Hz)',
               ylabel=r'modulation $f_{am}$ (Hz)' if k == 0 else '',
               title='%s\nholo-spectrum, truth $\\langle 3|14\\rangle$ circled' % ttl)
        fig.colorbar(m, ax=ax, fraction=0.046, pad=0.02)
    fig.savefig('figs/fig1_nguyen_s1.png', bbox_inches='tight')
    plt.close(fig)


# ---------------------------------------------------------------- figure 2
def fig2():
    sigs = list(man['signals'])
    M = np.array([[R['spectra'][nm]['cosine']['%s|%s' % p]
                   for p in [('mat_mask', 'mat_mask_pchip'),
                             ('mat_mask_pchip', 'mat_emd_pchip'),
                             ('mat_emd_pchip', 'mat_emd_nak_pchip'),
                             ('mat_emd_nak_pchip', 'py_noadm'),
                             ('py_noadm', 'py')]] for nm in sigs])
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    im = ax.imshow(M, cmap='RdYlGn', vmin=0, vmax=1, aspect='auto')
    ax.set_xticks(range(5), LADDER_LABELS, fontsize=8)
    ax.set_yticks(range(len(sigs)), sigs, fontsize=8)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, '%.2f' % M[i, j], ha='center', va='center',
                    fontsize=8, color='#111')
    ax.set_title('How much of the holo-spectrum survives each single change\n'
                 'cosine similarity, 1.00 = the change made no difference',
                 fontsize=10)
    ax.grid(False)
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    fig.savefig('figs/fig2_attribution_ladder.png', bbox_inches='tight')
    plt.close(fig)


# ---------------------------------------------------------------- figure 3
def fig3():
    tr = np.loadtxt('output/instability_trace.txt')
    c, A_nat, A_pch = tr[0], tr[1], tr[2]
    t = np.arange(len(c)) * 5 / 60.0
    fig, axs = plt.subplots(2, 1, figsize=(9.5, 5.0), sharex=True,
                            gridspec_kw=dict(hspace=0.2))
    axs[0].plot(t, c, color='#111', lw=0.5)
    axs[0].plot(t, A_pch, color=PY, lw=1.2, label='PCHIP normalisation (Python)')
    axs[0].set(ylabel='mmol/L',
               title='CGM record, first masking-EMD mode: the amplitude of the same '
                     'mode, normalised two ways')
    axs[0].legend(fontsize=8)
    axs[1].semilogy(t, np.maximum(A_nat, 1e-3), color=MAT, lw=0.8,
                    label='natural cubic spline (reference wording)')
    axs[1].semilogy(t, np.maximum(A_pch, 1e-3), color=PY, lw=1.2,
                    label='PCHIP (Python)')
    axs[1].set(xlabel='time (h)', ylabel='instantaneous amplitude (log)',
               xlim=(0, t[-1]))
    axs[1].legend(fontsize=8, loc='upper left')
    axs[1].set_title('same trace, log scale: max %.3g vs %.3g  '
                     '(a %.2g-fold inflation from the interpolant alone)'
                     % (A_nat.max(), A_pch.max(), A_nat.max() / A_pch.max()),
                     fontsize=9)
    fig.savefig('figs/fig3_normalisation_instability.png', bbox_inches='tight')
    plt.close(fig)


# ---------------------------------------------------------------- figure 4
def fig4():
    nm = 'cgm_5min'
    x = np.loadtxt('data/sig_%s.txt' % nm)
    t = np.arange(len(x)) * 5 / 60.0
    Mm = L('mat_mask', nm, 'imfs')
    Pp = L('py', nm, 'imfs')
    pm = R['cgm']['mat_mask']['periods_h']
    pp = R['cgm']['py']['periods_h']
    vm = R['cgm']['mat_mask']['var_pct']
    vp = R['cgm']['py']['var_pct']

    rows = max(len(Mm), len(Pp)) + 1
    fig, axs = plt.subplots(rows, 2, figsize=(11.5, 1.05 * rows), sharex=True,
                            gridspec_kw=dict(hspace=0.35, wspace=0.12))
    for col, (M, per, var, ttl, col_c) in enumerate(
            [(Mm, pm, vm, 'MATLAB reference — masking EMD', MAT),
             (Pp, pp, vp, 'Python as shipped — plain EMD', PY)]):
        axs[0, col].plot(t, x, color='#111', lw=0.5)
        axs[0, col].set_title('%s\n13-day CGM record, 5-min cadence' % ttl, fontsize=9)
        axs[0, col].set_ylabel('mmol/L', fontsize=8)
        for i in range(rows - 1):
            ax = axs[i + 1, col]
            if i < len(M):
                ax.plot(t, M[i], color=col_c, lw=0.6)
                ax.text(0.995, 0.86, 'IMF%d   T=%.2f h   %.1f%% var'
                        % (i + 1, per[i], var[i]), transform=ax.transAxes,
                        ha='right', va='top', fontsize=7.5, color=col_c)
            else:
                ax.axis('off')
            ax.set_yticks([])
        axs[rows - 1, col].set_xlabel('time (h)')
    for ax in axs.ravel():
        ax.set_xlim(0, t[-1])
    fig.suptitle('Same record, same sampling, same stopping rule — different modes',
                 fontsize=11, y=0.995)
    fig.savefig('figs/fig4_cgm_imfs.png', bbox_inches='tight')
    plt.close(fig)


# ---------------------------------------------------------------- figure 5
def fig5():
    nm = 'cgm_5min'
    G = man['grids']['cgm']
    fc, wc = centers(G['f_edges']), centers(G['w_edges'])
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.2), gridspec_kw=dict(wspace=0.28))
    for ax, cfg, ttl in ((axs[0], 'mat_mask_pchip', 'MATLAB reference (masking EMD)'),
                         (axs[1], 'py', 'Python as shipped (plain EMD)')):
        H = L(cfg, nm, 'H')
        Hp = np.where(H > 0, H, np.nan)
        vmax = np.nanmax(Hp)
        m = ax.pcolormesh(1 / fc, 1 / wc, Hp.T, norm=LogNorm(vmax * 1e-4, vmax),
                          cmap='magma', shading='auto')
        ax.axvline(24, color='#39d353', ls='--', lw=1.1)
        ax.text(24, 1.05 * (1 / wc).min(), ' 24 h', color='#39d353', fontsize=8,
                rotation=90, va='bottom')
        ax.set(xscale='log', yscale='log',
               xlabel='carrier period (h)', ylabel='modulation period (h)',
               title=ttl)
        fig.colorbar(m, ax=ax, fraction=0.046, pad=0.02)
    fig.suptitle('Holo-spectrum of the same CGM record', fontsize=11)
    fig.savefig('figs/fig5_cgm_holo.png', bbox_inches='tight')
    plt.close(fig)


# ---------------------------------------------------------------- figure 6
def fig6():
    g4 = R['ground_truth']['juan_fig4']
    f5 = R['fig5_time_resolved']
    betas = [0.0, 0.4, 1.0]
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.0), gridspec_kw=dict(wspace=0.28))

    for cfg, col, mk, lab in (('mat_mask_pchip', MAT, 'o', 'MATLAB reference'),
                              ('mat_emd_pchip', MID, 's', 'MATLAB, plain EMD'),
                              ('py', PY, '^', 'Python as shipped')):
        e = [g4[cfg]['energy_beta0'], g4[cfg]['energy_beta04'], g4[cfg]['energy_beta1']]
        axs[0].semilogy(betas, np.maximum(e, 1e-12), marker=mk, color=col, lw=1.3,
                        label=lab, ms=5)
    axs[0].set(xlabel=r'coupling strength $\beta$',
               ylabel=r'energy in cell $\langle 4\,|\,32\rangle$',
               title='Juan et al. 2021 Fig. 4\nfixed coupling strength')
    axs[0].legend(fontsize=8)

    b2 = np.array(f5['beta_squared'])
    for cfg, col, mk, lab in (('mat_mask_pchip', MAT, 'o', 'MATLAB reference'),
                              ('mat_emd_pchip', MID, 's', 'MATLAB, plain EMD'),
                              ('py', PY, '^', 'Python as shipped')):
        y = np.array(f5['energy'][cfg], float)
        axs[1].plot(f5['probe_times'], y / y.max(), marker=mk, color=col, lw=1.3,
                    label='%s  (r=%.4f)' % (lab, f5['r'][cfg]), ms=5)
    axs[1].plot(f5['probe_times'], b2 / b2.max(), color='#39d353', ls='--', lw=1.2,
                label=r'theory $\beta^2$')
    axs[1].set(xlabel='time (s)', ylabel='normalised recovered AM power',
               title='Juan et al. 2021 Fig. 5\ntime-varying coupling')
    axs[1].legend(fontsize=7.5)
    fig.savefig('figs/fig6_coupling_recovery.png', bbox_inches='tight')
    plt.close(fig)


HAS_CGM = 'cgm_5min' in man['signals']
for f in (fig1, fig2, fig3, fig4, fig5, fig6):
    if f in (fig3, fig4, fig5) and not HAS_CGM:
        print('skipped', f.__name__, '-- needs the CGM record, which is not public')
        continue
    f()
    print('drew', f.__name__)
print('figures written to figs/')
