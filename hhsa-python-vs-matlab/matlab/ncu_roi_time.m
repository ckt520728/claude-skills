function ts = ncu_roi_time(L2, dt, n, flim, wlim, probe_times, halfwin_s)
% NCU_ROI_TIME  Energy inside one (f_c, f_am) cell as a function of time.
% This is the part of the reference method the Python implementation does not
% have: the holo-spectrum is built over (f_am, f_c, TIME) and only then summed
% marginally, so a time-resolved read of one cell is available for free.
  if nargin < 7, halfwin_s = 0.1; end
  hw = round(halfwin_s / dt);
  ts = zeros(1, numel(probe_times));
  for p = 1:numel(probe_times)
    c = round(probe_times(p)/dt) + 1;
    s = max(1, c-hw):min(n, c+hw);
    e = 0;
    for q = 1:numel(L2)
      L = L2{q};
      if numel(L.ff) ~= n, continue; end
      fs_ = L.ff(s); ws_ = L.ww(s); bs_ = L.BB(s);
      m = fs_ >= flim(1) & fs_ <= flim(2) & ws_ >= wlim(1) & ws_ <= wlim(2);
      e = e + sum(bs_(m).^2) * dt;
    end
    ts(p) = e;
  end
end
