function [A, f] = ncu_ifreq(c, dt, n_iter, nbsym, kind)
% NCU_IFREQ  Instantaneous amplitude and frequency by the normalised Hilbert
% transform (Huang et al. 2009).
%
% KIND is the interpolant used for the amplitude normalisation. None of the
% source documents pins it, and it turns out to be the single most consequential
% unpinned choice in the whole pipeline: a natural (or not-a-knot) cubic spline
% through the maxima of |c| can dip toward zero between widely spaced maxima,
% and dividing by that four times over drives the amplitude up by six orders of
% magnitude. PCHIP cannot undershoot, so it stays bounded. Both are provided so
% the effect is measured rather than argued about.
  if nargin < 3 || isempty(n_iter), n_iter = 4; end
  if nargin < 4 || isempty(nbsym), nbsym = 2; end
  if nargin < 5 || isempty(kind), kind = 'natural'; end
  y = double(c(:).'); n = numel(y);
  A = ones(1, n);
  sc = max(abs(y));
  if ~(sc > 0) || ~isfinite(sc), A = zeros(1,n); f = zeros(1,n); return; end
  for it = 1:n_iter
    ab = abs(y);
    [imax, ~] = ncu_extrema(ab);
    if numel(imax) < 2, break; end
    env = ncu_envelope(ab, imax, nbsym, kind);
    mx = max(ab);
    if mx > 0, fl = 1e-6*mx; else, fl = 1e-12; end
    env = max(env, fl);
    y = y ./ env;
    A = A .* env;
    if max(abs(y)) <= 1 + 1e-6, break; end
  end
  y = min(max(y, -1), 1);
  ph = unwrap(angle(ncu_hilbert(y)));
  f = gradient(ph, dt) / (2*pi);
end
