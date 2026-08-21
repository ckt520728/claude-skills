function A = ncu_abs_envelope(c, nbsym, kind)
% NCU_ABS_ENVELOPE  The layer-2 input envelope, exactly as the reference states.
%
% Nguyen et al. 2019, Supplementary Methods, step 2:
%   "Obtain the absolute value of the IMFs. Identify all the absolute-valued
%    function of IMF maxima. Assemble the envelope by employing a natural
%    spline through all the maxima."
% One pass, no iteration. The Python side instead feeds layer 2 with the
% amplitude from a four-iteration PCHIP normalisation, which is a smoother and
% strictly shape-preserving estimate of the same quantity. KIND stays 'natural'
% in every MATLAB configuration -- this is the pinned part of the spec.
  if nargin < 2 || isempty(nbsym), nbsym = 2; end
  if nargin < 3 || isempty(kind), kind = 'natural'; end
  a = abs(c(:).');
  [imax, ~] = ncu_extrema(a);
  if numel(imax) < 2, A = repmat(mean(a), 1, numel(a)); return; end
  A = ncu_envelope(a, imax, nbsym, kind);
end
