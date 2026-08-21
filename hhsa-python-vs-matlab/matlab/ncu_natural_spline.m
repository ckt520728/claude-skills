function y = ncu_natural_spline(xi, yi, xq)
% NCU_NATURAL_SPLINE  Cubic spline with the NATURAL end condition (y'' = 0).
%
% Pinned by Nguyen et al. 2019 Supplementary Methods, step 2:
%   "Assemble the envelope by employing a natural spline through all the maxima."
% Octave's core SPLINE and scipy's CubicSpline both default to NOT-A-KNOT, so
% neither stock routine implements what the reference method specifies. Solved
% here as a tridiagonal system in the second derivatives (Moler, Ch. 3).
  xi = xi(:); yi = yi(:); n = numel(xi);
  if n == 1, y = repmat(yi, size(xq)); return; end
  if n == 2
    y = yi(1) + (yi(2)-yi(1)) .* (xq - xi(1)) ./ (xi(2)-xi(1));
    return;
  end
  h = diff(xi);
  A = sparse(n, n); r = zeros(n, 1);
  A(1,1) = 1; A(n,n) = 1;                      % natural: M(1) = M(n) = 0
  for i = 2:n-1
    A(i,i-1) = h(i-1);
    A(i,i)   = 2*(h(i-1)+h(i));
    A(i,i+1) = h(i);
    r(i)     = 6*((yi(i+1)-yi(i))/h(i) - (yi(i)-yi(i-1))/h(i-1));
  end
  M = A \ r;
  xq = xq(:);
  k = min(max(lookup(xi, xq), 1), n-1);        % interval index for each query
  dx = xq - xi(k); hk = h(k);
  y = yi(k) ...
      + dx .* ((yi(k+1)-yi(k))./hk - hk.*(2*M(k)+M(k+1))/6) ...
      + dx.^2 .* M(k)/2 ...
      + dx.^3 .* (M(k+1)-M(k))./(6*hk);
  y = y.';
end
