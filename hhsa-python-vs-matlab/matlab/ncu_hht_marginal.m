function [h, per] = ncu_hht_marginal(imfs, dt, f_edges, edge_trim, norm_kind)
% NCU_HHT_MARGINAL  Conventional Hilbert marginal spectrum, energy vs carrier f.
  if nargin < 4 || isempty(edge_trim), edge_trim = 0; end
  if nargin < 5 || isempty(norm_kind), norm_kind = 'natural'; end
  nf = numel(f_edges) - 1;
  h = zeros(1, nf); per = zeros(size(imfs,1), nf);
  for j = 1:size(imfs,1)
    [A, f] = ncu_ifreq(imfs(j,:), dt, 4, 2, norm_kind);
    n = numel(f); s = (1+edge_trim):(n-edge_trim);
    A = A(s); f = f(s);
    good = isfinite(f) & (f > 0);
    idx = lookup(f_edges, f(good));
    v = (A(good).^2) * dt;
    ok = idx >= 1 & idx <= nf;
    ii = idx(ok); vv = v(ok);
    c = accumarray(ii(:), vv(:), [nf 1])';
    h = h + c; per(j,:) = c;
  end
end
