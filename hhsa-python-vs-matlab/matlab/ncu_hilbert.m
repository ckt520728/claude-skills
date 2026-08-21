function z = ncu_hilbert(x)
% NCU_HILBERT  Analytic signal by the standard FFT construction.
% Written out rather than taken from Octave's signal package so that the run
% has no package dependency and the transform is identical in form to the one
% scipy uses on the Python side (differences must come from the METHOD, not
% from which library happened to be installed).
  x = x(:).'; n = numel(x);
  X = fft(x);
  h = zeros(1, n);
  if mod(n, 2) == 0
    h(1) = 1; h(n/2+1) = 1; h(2:n/2) = 2;
  else
    h(1) = 1; h(2:(n+1)/2) = 2;
  end
  z = ifft(X .* h);
end
