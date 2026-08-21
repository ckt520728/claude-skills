function [imax, imin] = ncu_extrema(x)
% NCU_EXTREMA  Indices of local maxima and minima, plateaux collapsed to midpoint.
%
% Plateau handling matches the Python implementation deliberately: it is not
% pinned by any of the source documents, so leaving it different would put a
% confound in the comparison. CGM values sit on a 0.1 mmol/L lattice, so flat
% runs are common and a naive detector would return every sample of a flat peak.
  x = x(:).';
  d = diff(x);
  nz = find(d ~= 0);
  imax = []; imin = [];
  if numel(nz) < 2, return; end
  s = sign(d(nz));
  turn = find(diff(s) ~= 0);
  for k = turn(:).'
    i0 = nz(k) + 1; i1 = nz(k+1);
    c = floor((i0 + i1) / 2);
    if s(k) > 0, imax(end+1) = c; else, imin(end+1) = c; end
  end
end
