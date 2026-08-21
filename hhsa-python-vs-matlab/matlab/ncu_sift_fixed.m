function h = ncu_sift_fixed(x, n_sift, nbsym)
% NCU_SIFT_FIXED  RCADA convention: a fixed number of siftings (default 10).
  if nargin < 2, n_sift = 10; end
  if nargin < 3, nbsym = 2; end
  h = double(x(:).');
  for it = 1:n_sift
    [imax, imin] = ncu_extrema(h);
    if numel(imax) + numel(imin) < 3, break; end
    h = h - 0.5*(ncu_envelope(h, imax, nbsym) + ncu_envelope(h, imin, nbsym));
  end
end
