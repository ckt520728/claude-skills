function [imfs, res] = ncu_emd(x, max_imf, sd_thresh, kind)
% NCU_EMD  Plain empirical mode decomposition.
  if nargin < 2 || isempty(max_imf), max_imf = 10; end
  if nargin < 3 || isempty(sd_thresh), sd_thresh = 0.2; end
  if nargin < 4 || isempty(kind), kind = 'natural'; end
  r = double(x(:).'); imfs = [];
  while size(imfs,1) < max_imf
    [imax, imin] = ncu_extrema(r);
    if numel(imax) + numel(imin) < 3, break; end
    c = ncu_sift(r, sd_thresh, 100, 2, kind);
    imfs(end+1, :) = c;
    r = r - c;
  end
  res = r;
end
