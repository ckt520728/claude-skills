function out = ncu_hhsa(x, dt, f_edges, w_edges, opts)
% NCU_HHSA  Two-layer Holo-Hilbert Spectral Analysis, MATLAB/NCU reference spec.
%
% Layer 1  masking EMD of x(t)          -> IMFs c_j,  carrier frequency f_j(t)
% Envelope natural spline through maxima of |c_j|   -> A_j(t)     [supp. step 2]
% Layer 2  masking EMD of each A_j(t)   -> a_jk,     AM frequency w_jk(t)
% Holo     energy B^2 dt binned in (f_c, f_am), summed marginally over time
%          [supp. step 5]
%
% OPTS fields (all optional)
%   method     'mask' | 'emd'        layer-1 and layer-2 decomposition
%   sift_kind  'natural'|'notaknot'|'pchip'   spline used inside sifting
%   norm_kind  'natural'|'notaknot'|'pchip'   spline used in amplitude normalisation
%   max_imf, max_imf2, sd_thresh, edge_trim, n_phase
%
% No admissibility constraint is applied: neither Nguyen et al.'s supplement
% nor the NCU neuroholo GUI imposes f_am < f_c. OUT.rejected_fraction reports
% how much of this spectrum the Python rule would have discarded, so the
% difference is measurable rather than merely stated.
  if nargin < 5, opts = struct(); end
  max_imf   = gfd(opts, 'max_imf',   9);
  max_imf2  = gfd(opts, 'max_imf2',  7);
  sd_thresh = gfd(opts, 'sd_thresh', 0.2);
  edge_trim = gfd(opts, 'edge_trim', 0);
  method    = gfd(opts, 'method',    'mask');
  n_phase   = gfd(opts, 'n_phase',   4);
  sift_kind = gfd(opts, 'sift_kind', 'natural');
  norm_kind = gfd(opts, 'norm_kind', 'natural');

  x = double(x(:).'); n = numel(x);
  tic;
  if strcmp(method, 'mask')
    [imfs, res, minfo] = ncu_masking_emd(x, max_imf, sd_thresh, n_phase, 1.0, sift_kind);
  else
    [imfs, res] = ncu_emd(x, max_imf, sd_thresh, sift_kind); minfo = [];
  end
  t_layer1 = toc;

  nf = numel(f_edges) - 1; nw = numel(w_edges) - 1;
  H = zeros(nf, nw);
  e_keep = 0; e_drop = 0; L2 = {};
  tic;
  for j = 1:size(imfs, 1)
    [~, f] = ncu_ifreq(imfs(j,:), dt, 4, 2, norm_kind);
    A = ncu_abs_envelope(imfs(j,:), 2, 'natural');     % pinned by the reference
    if strcmp(method, 'mask')
      a2 = ncu_masking_emd(A, max_imf2, sd_thresh, n_phase, 1.0, sift_kind);
    else
      a2 = ncu_emd(A, max_imf2, sd_thresh, sift_kind);
    end
    for k = 1:size(a2, 1)
      [B, w] = ncu_ifreq(a2(k,:), dt, 4, 2, norm_kind);
      s = (1+edge_trim):(n-edge_trim);
      ff = f(s); ww = w(s); BB = B(s);
      good = isfinite(ff) & isfinite(ww) & ff > 0 & ww > 0;
      adm  = good & (ww < ff);
      e_keep = e_keep + sum(BB(adm).^2)*dt;
      e_drop = e_drop + sum(BB(good & ~adm).^2)*dt;
      fi = lookup(f_edges, ff(good)); wi = lookup(w_edges, ww(good));
      v  = (BB(good).^2) * dt;
      ok = fi >= 1 & fi <= nf & wi >= 1 & wi <= nw;
      if any(ok)
        fo = fi(ok); wo = wi(ok); vo = v(ok);
        H = H + accumarray([fo(:) wo(:)], vo(:), [nf nw]);
      end
      % store the UNTRIMMED traces: the time-resolved read in ncu_roi_time
      % indexes by absolute sample, so trimmed copies would silently miss.
      L2{end+1} = struct('imf', j, 'sub', k, 'ff', f, 'ww', w, 'BB', B, ...
                         'edge_trim', edge_trim, 'energy', sum(a2(k,:).^2));
    end
  end
  t_layer2 = toc;

  out = struct();
  out.imfs = imfs; out.res = res; out.minfo = minfo; out.H = H;
  out.hht = ncu_hht_marginal(imfs, dt, f_edges, edge_trim, norm_kind);
  out.L2 = L2;
  out.recon_err = max(abs(sum(imfs,1) + res - x));
  tot = e_keep + e_drop;
  if tot > 0, out.rejected_fraction = e_drop/tot; else, out.rejected_fraction = 0; end
  out.t_layer1 = t_layer1; out.t_layer2 = t_layer2;
end

function v = gfd(s, f, d)
  if isstruct(s) && isfield(s, f), v = s.(f); else, v = d; end
end
