% run_matlab_side.m -- MATLAB/NCU-reference HHSA over every shared signal.
%
% Run from the project root:
%   octave-cli --no-gui --path matlab --eval "run_matlab_side"
%
% Five configurations, arranged so that the distance between the MATLAB
% reference and the Python implementation can be walked one factor at a time:
%
%   mask           masking EMD, natural spline everywhere      <- the reference
%   mask_pchip     ... amplitude normalisation switched to PCHIP
%   emd            plain EMD, natural spline everywhere
%   emd_pchip      plain EMD, PCHIP normalisation
%   emd_nak_pchip  plain EMD, not-a-knot sifting spline, PCHIP normalisation
%                  -- differs from the Python side only in how the layer-2
%                     input envelope is built, and in the admissibility rule
%
% Held fixed in all five: the |IMF|-maxima natural-spline layer-2 envelope
% (pinned by Nguyen et al.'s supplement), SD < 0.2 sifting stop, 2-point
% mirror endpoints, the shared frequency grids, and the shared edge trim.

more off;
manifest = jsondecode(fileread('data/manifest.json'));
names = fieldnames(manifest.signals);
if ~exist('output', 'dir'), mkdir('output'); end

CFG = { ...
  'mask',          'mask', 'natural',  'natural';  ...
  'mask_pchip',    'mask', 'natural',  'pchip';    ...
  'emd',           'emd',  'natural',  'natural';  ...
  'emd_pchip',     'emd',  'natural',  'pchip';    ...
  'emd_nak_pchip', 'emd',  'notaknot', 'pchip'};

for i = 1:numel(names)
  nm = names{i};
  S  = manifest.signals.(nm);
  x  = load(sprintf('data/sig_%s.txt', nm))';
  dt = 1.0 / S.fs;
  G  = manifest.grids.(S.grid);
  f_edges = G.f_edges(:)'; w_edges = G.w_edges(:)';

  for ci = 1:size(CFG, 1)
    tagname = CFG{ci,1};
    opts = struct('max_imf', 9, 'max_imf2', 7, 'sd_thresh', 0.2, ...
                  'edge_trim', S.edge_trim, 'method', CFG{ci,2}, ...
                  'sift_kind', CFG{ci,3}, 'norm_kind', CFG{ci,4}, 'n_phase', 4);
    printf('[%s / %s] n=%d fs=%g ... ', nm, tagname, numel(x), S.fs); fflush(stdout);
    tstart = tic;
    out = ncu_hhsa(x, dt, f_edges, w_edges, opts);
    wall = toc(tstart);
    printf('%d IMFs, %.1f s, maxA %.3g\n', size(out.imfs,1), wall, max(out.hht)); fflush(stdout);

    tag = sprintf('output/mat_%s_%s', nm, tagname);
    imfs = out.imfs; res = out.res; H = out.H; hht = out.hht;
    save('-ascii', [tag '_imfs.txt'], 'imfs');
    save('-ascii', [tag '_res.txt'],  'res');
    save('-ascii', [tag '_H.txt'],    'H');
    save('-ascii', [tag '_hht.txt'],  'hht');

    tv = var(x); rows = {};
    for j = 1:size(imfs,1)
      c = imfs(j,:);
      zc = sum(diff(c >= 0) ~= 0);
      if zc > 0, T_zc = 2*numel(c)*dt/zc; else, T_zc = NaN; end
      [A, f] = ncu_ifreq(c, dt, 4, 2, CFG{ci,4});
      fp = f(isfinite(f) & f > 0);
      if numel(fp), T_if = 1/median(fp); else, T_if = NaN; end
      rows{end+1} = struct('imf', j, 'period_zc', T_zc, 'period_if', T_if, ...
                           'energy', sum(c.^2), 'var_pct', 100*var(c)/tv, ...
                           'mean_amp', mean(A), 'max_amp', max(A));
    end
    summ = struct('signal', nm, 'method', tagname, 'n', numel(x), 'fs', S.fs, ...
                  'decomposition', CFG{ci,2}, 'sift_spline', CFG{ci,3}, ...
                  'norm_spline', CFG{ci,4}, ...
                  'n_imf', size(imfs,1), 'recon_err', out.recon_err, ...
                  'rejected_fraction_if_admissibility_applied', out.rejected_fraction, ...
                  't_layer1', out.t_layer1, 't_layer2', out.t_layer2, 'wall', wall, ...
                  'imf_stats', {rows});
    if strcmp(CFG{ci,2}, 'mask') && ~isempty(out.minfo)
      mf = zeros(1, numel(out.minfo));
      for q = 1:numel(out.minfo), mf(q) = out.minfo(q).mask_freq_cyc_per_sample * S.fs; end
      summ.mask_freq_hz = mf;
    end
    if strcmp(nm, 'juan_f5_tv')
      probes = [0.5 1.5 2.5 3.5];
      summ.roi_probe_times = probes;
      summ.roi_energy = ncu_roi_time(out.L2, dt, numel(x), ...
                                     [32*0.82 32*1.18], [4*0.82 4*1.18], probes, 0.15);
    end
    fid = fopen([tag '_summary.json'], 'w');
    fputs(fid, jsonencode(summ)); fclose(fid);
  end
end
printf('\nMATLAB side complete.\n');
