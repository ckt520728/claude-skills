function [imfs, res, minfo] = ncu_masking_emd(x, max_imf, sd_thresh, n_phase, amp_ratio, kind)
% NCU_MASKING_EMD  Masking EMD -- the decomposition the reference method uses.
%
% Nguyen et al. 2019, Supplementary Methods:
%   "we employed an enhanced algorithm of masking EMD proposed by Tsai et al.
%    ... modified from the original masking EMD [Deering & Kaiser 2005] to
%    obtain each IMF."
%
% Per IMF, on the current residue r:
%   1. build a mask m(t) = a*cos(2*pi*fm*t + phi)
%   2. IMF candidate = ( sift(r+m) + sift(r-m) ) / 2      -> the mask cancels
%   3. average over N equally spaced phases phi
% Mask frequency starts from the zero-crossing rate of the plain-EMD first IMF
% and halves for each subsequent mode; mask amplitude is AMP_RATIO times the
% standard deviation of the previous mode.
%
% PROVENANCE. Deering & Kaiser (2005) is cited by name in the reference
% supplement and is what is implemented here. Tsai et al.'s specific
% enhancement was not obtainable offline in this session, so the phase-averaged
% dyadic schedule below follows standard mask-sift practice rather than that
% paper, and no claim of equivalence to Tsai et al. is made.
  if nargin < 2 || isempty(max_imf), max_imf = 10; end
  if nargin < 3 || isempty(sd_thresh), sd_thresh = 0.2; end
  if nargin < 4 || isempty(n_phase), n_phase = 4; end
  if nargin < 5 || isempty(amp_ratio), amp_ratio = 1.0; end
  if nargin < 6 || isempty(kind), kind = 'natural'; end
  x = double(x(:).'); n = numel(x);
  t = 0:n-1;                          % mask frequency carried in cycles/sample

  c1 = ncu_sift(x, sd_thresh, 100, 2, kind);
  zc = sum(diff(c1 >= 0) ~= 0);
  if zc < 2, fm = 0.25; else, fm = zc/(2*n); end
  amp = amp_ratio * std(x);

  imfs = []; r = x; minfo = [];
  for k = 1:max_imf
    [imax, imin] = ncu_extrema(r);
    if numel(imax) + numel(imin) < 3, break; end
    if fm <= 1/n || amp <= 0
      c = ncu_sift(r, sd_thresh, 100, 2, kind);
    else
      acc = zeros(1, n);
      for p = 0:n_phase-1
        m = amp * cos(2*pi*fm*t + 2*pi*p/n_phase);
        acc = acc + 0.5*(ncu_sift(r + m, sd_thresh, 100, 2, kind) + ...
                         ncu_sift(r - m, sd_thresh, 100, 2, kind));
      end
      c = acc / n_phase;
    end
    imfs(end+1, :) = c;
    minfo(end+1).mask_freq_cyc_per_sample = fm;
    minfo(end).mask_amp = amp;
    r = r - c;
    fm = fm / 2;
    amp = amp_ratio * std(c);
  end
  res = r;
end
