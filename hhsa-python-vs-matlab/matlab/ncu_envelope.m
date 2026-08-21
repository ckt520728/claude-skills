function e = ncu_envelope(x, idx, nbsym, kind)
% NCU_ENVELOPE  Spline envelope through the extrema at IDX.
%
% KIND selects the interpolant, so that the choice can be varied one factor at
% a time instead of being buried in the code:
%   'natural'   cubic spline with y''=0 at both ends  (Nguyen et al. supplement)
%   'notaknot'  cubic spline, not-a-knot ends         (what Octave SPLINE and
%                                                      scipy CubicSpline default to)
%   'pchip'     shape-preserving piecewise cubic      (what the Python side uses
%                                                      for amplitude normalisation)
% Endpoints are handled by even reflection of the outermost NBSYM extrema in
% every case, matching the Python side, so reflection is never the confound.
  if nargin < 3 || isempty(nbsym), nbsym = 2; end
  if nargin < 4 || isempty(kind), kind = 'natural'; end
  n = numel(x);
  if isempty(idx), e = zeros(1, n); return; end
  k = min(nbsym, numel(idx));
  li = -idx(k:-1:1);                  lv = x(idx(k:-1:1));
  ri = 2*(n-1) - idx(end:-1:end-k+1); rv = x(idx(end:-1:end-k+1));
  xv = x(idx);
  ii = [li(:); idx(:)-1; ri(:)];      vv = [lv(:); xv(:); rv(:)];   % 0-based abscissa
  [ii, u] = unique(ii);               vv = vv(u);
  xq = 0:n-1;
  switch kind
    case 'natural',  e = ncu_natural_spline(ii, vv, xq);
    case 'notaknot', e = spline(ii, vv, xq);
    case 'pchip',    e = pchip(ii, vv, xq);
    otherwise, error('ncu_envelope: unknown kind %s', kind);
  end
  e = e(:)';
end
