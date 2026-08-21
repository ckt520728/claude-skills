function h = ncu_sift(x, sd_thresh, max_iter, nbsym, kind)
% NCU_SIFT  One IMF by repeated removal of the mean envelope.
% Stopping rule is Huang's normalised squared difference SD < sd_thresh, with
% sd_thresh = 0.2 chosen to MATCH the Python implementation, so that the
% sifting criterion is not a confound in the headline comparison.
  if nargin < 2 || isempty(sd_thresh), sd_thresh = 0.2; end
  if nargin < 3 || isempty(max_iter), max_iter = 100; end
  if nargin < 4 || isempty(nbsym), nbsym = 2; end
  if nargin < 5 || isempty(kind), kind = 'natural'; end
  h = double(x(:).');
  for it = 1:max_iter
    [imax, imin] = ncu_extrema(h);
    if numel(imax) + numel(imin) < 3, break; end
    m = 0.5*(ncu_envelope(h, imax, nbsym, kind) + ncu_envelope(h, imin, nbsym, kind));
    hn = h - m;
    den = sum(h.^2);
    if den > 0, sd = sum((h - hn).^2)/den; else, sd = 0; end
    h = hn;
    if sd < sd_thresh, break; end
  end
end
