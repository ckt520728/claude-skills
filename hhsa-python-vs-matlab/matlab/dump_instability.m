% dump_instability.m -- the one trace that explains the largest divergence.
% Takes the CGM record's first masking-EMD mode and normalises its amplitude
% two ways: natural cubic spline (what the reference method's wording implies)
% and PCHIP (what the Python side uses). Writes both traces for plotting.
x = load('data/sig_cgm_5min.txt')'; dt = 1/12;
imfs = ncu_masking_emd(x, 9, 0.2, 4, 1.0, 'natural');
c = imfs(1,:);
[A_nat, ~] = ncu_ifreq(c, dt, 4, 2, 'natural');
[A_pch, ~] = ncu_ifreq(c, dt, 4, 2, 'pchip');
M = [c; A_nat; A_pch];
save('-ascii', 'output/instability_trace.txt', 'M');
printf('IMF1: max|c| %.4g   maxA natural %.4g   maxA pchip %.4g   ratio %.3g\n', ...
       max(abs(c)), max(A_nat), max(A_pch), max(A_nat)/max(A_pch));
