"""
minimal_force_internal_v3.py  (Stage 3 任務 3) — v3 (修正 chaos 坍縮)
========================================================================

FORCE-Internal-RLS-N: 訓練 J 矩陣 (每個 neuron 獨立 RLS) + 同時訓練 W。
對應 Sussillo & Abbott 2009 Fig 3 的乾淨 Lorenz 蝴蝶。

v3 修正自 v2 的根因 bug:
    v2 結果:test 階段 RNN output 卡在 z ≈ 1.66 的常數線 → chaos 被殺死、
            網路坍縮到 fixed point、輸出 saturate。

    v2 為什麼失敗 (不是 v1 的 feedback 缺失,feedback 已經補回去了):
        - W 與 J 同時從 0 開始學一個 chaos target
        - 前 ~100 步 error magnitude ~ O(1.7) (target 振幅範圍)
        - per-neuron RLS 把這個 O(1.7) 的 error 灌進 J 的每一 row
        - J 被快速推離 chaotic regime → reservoir 失去 ergodicity
        - 一旦 chaos 死,RLS 看到的 r 不再 explore state space,W 也學不起來
        - 最終網路收斂到 fixed point,readout saturate 在 ~1.66

    v3 修正三點 (跟 Sussillo 原 paper Section "Learning the internal dynamics" 一致):
    1. **Two-phase training** (核心修正):
       - Phase 1 (前 W_only_cyc = 10 cycle): 只訓練 W,J 不動
         → 等同 FORCE-Output,讓 W 先把網路 imprint 出 Lorenz vector field
       - Phase 2 (後續 cycle): 才開始同時訓練 W + J
         → 此時 error 已經 ~10^-2 級別,J 不會被拉爆
    2. **LORENZ_SLOWDOWN 200 → 400** 對齊 lorenz_output 成功版的 target 速度
    3. **n_train_cyc 15 → 30** 自由度從 N 增加到 N+p·N²,需要更多 cycle 收斂

關鍵 vs FORCE-Output (lorenz_output 版):
    1. Phase 1 等同 lorenz_output 訓練 W
    2. Phase 2 加上 per-neuron RLS 訓練 J (多 ~p·N² ≈ 64000 自由度)
    3. Feedback (w_fb · z) 全程保留

執行:
    python minimal_force_internal_v3.py

預期執行時間: N=800、30 cycle、per-neuron RLS → 約 6-12 分鐘
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint
import time

np.random.seed(42)

# ---------------------------------------------------------------------------
# 1. 網路與訓練參數
# ---------------------------------------------------------------------------
N               = 800
g               = 1.5
p_conn          = 0.1
tau             = 10.0
dt              = 1.0
alpha           = 1.0
T_cycle         = 1440
W_only_cyc      = 10        # v3 新增: 前 10 cycle 只訓 W
n_train_cyc     = 30        # v2: 15 → v3: 30
n_test_cyc      = 4         # v3.1: 1 → 4 (~14 Lorenz time units,涵蓋多次 lobe transition)
update_every    = 2
LORENZ_SLOWDOWN = 400       # v2: 200 → v3: 400 (對齊 lorenz_output 成功版)

T_total       = (n_train_cyc + n_test_cyc) * T_cycle
n_steps       = int(T_total / dt)
chunk         = int(T_cycle / dt)
train_steps   = n_train_cyc * chunk
w_only_steps  = W_only_cyc * chunk  # Phase 1 結束的 step index

# ---------------------------------------------------------------------------
# 2. 初始化 J, W, w_fb, P 矩陣
# ---------------------------------------------------------------------------
J = np.random.randn(N, N) * (g / np.sqrt(p_conn * N))
mask = np.random.rand(N, N) < p_conn
J *= mask
np.fill_diagonal(J, 0)

presyn = [np.where(J[i] != 0)[0] for i in range(N)]
n_pre_avg = np.mean([len(p) for p in presyn])
print(f"  Network: N={N}, p={p_conn}, avg presynaptic per neuron = {n_pre_avg:.1f}")

W = np.zeros(N)

# Feedback weights 全程保留 (v1→v2 已修正,v3 維持)
w_fb = (np.random.rand(N) - 0.5) * 2

# RLS state
P_W = np.eye(N) / alpha
P_J_list = [np.eye(len(idx)) / alpha for idx in presyn]
total_P_entries = N * N + sum(len(idx) ** 2 for idx in presyn)
print(f"  Memory: P_W ({N}x{N}) + N 個 P_J,共 {total_P_entries:,} entries ≈ {total_P_entries*8/1e6:.1f} MB")

# ---------------------------------------------------------------------------
# 3. Lorenz target
# ---------------------------------------------------------------------------
def lorenz_deriv(state, t, sigma=10.0, rho=28.0, beta=8.0/3.0):
    x, y, z = state
    return [sigma * (y - x), x * (rho - z) - y, x * y - beta * z]

t_all = np.arange(n_steps) * dt
t_lorenz = t_all / LORENZ_SLOWDOWN
print(f"\n  生成 Lorenz target ({t_lorenz[-1]:.1f} Lorenz time units)...")
sol = odeint(lorenz_deriv, [1.0, 1.0, 1.0], t_lorenz, rtol=1e-8, atol=1e-10)
target_all = sol[:, 0] / 15.0
print(f"  target 振幅範圍: [{target_all.min():.2f}, {target_all.max():.2f}]")

# ---------------------------------------------------------------------------
# 4. 主迴圈 — Two-phase training
#    Phase 1 (step < w_only_steps):     只更新 W (FORCE-Output)
#    Phase 2 (w_only_steps ≤ step < train_steps): 更新 W + J (FORCE-Internal)
#    Phase 3 (step ≥ train_steps):      測試,RLS 全關
# ---------------------------------------------------------------------------
x = 0.5 * np.random.randn(N)
r = np.tanh(x)
z = float(W @ r)

z_log   = np.zeros(n_steps)
err_log = np.zeros(n_steps)
# Stage 4 需要:test 階段每 dt 的 x(t) 全部存下來,作為 fixed-point search 的初始 guess pool
x_test_log = np.zeros((n_steps - n_train_cyc * chunk, N))  # shape: (n_test_steps, N)

print(f"\n  Two-phase FORCE-Internal 訓練:")
print(f"    Phase 1 (W only):  cycle 1 ~ {W_only_cyc}")
print(f"    Phase 2 (W + J):   cycle {W_only_cyc+1} ~ {n_train_cyc}")
print(f"    Phase 3 (test):    cycle {n_train_cyc+1}\n")

t_start = time.time()

for i in range(n_steps):
    # 前向動力學 (feedback 全程保留)
    x = x + (dt / tau) * (-x + J @ r + w_fb * z)
    r = np.tanh(x)
    z = float(W @ r)

    # RLS 更新
    if i < train_steps and (i % update_every == 0) and i > 0:
        error = z - target_all[i]

        # (a) 更新 W — Phase 1 & 2 都做
        Pr_W = P_W @ r
        c_W = 1.0 / (1.0 + r @ Pr_W)
        P_W -= c_W * np.outer(Pr_W, Pr_W)
        W -= c_W * error * Pr_W

        # (b) 更新 J — 只在 Phase 2 做
        if i >= w_only_steps:
            for cell in range(N):
                idx = presyn[cell]
                r_pre = r[idx]
                Pr_J = P_J_list[cell] @ r_pre
                c_J = 1.0 / (1.0 + r_pre @ Pr_J)
                P_J_list[cell] -= c_J * np.outer(Pr_J, Pr_J)
                J[cell, idx] -= c_J * error * Pr_J

    z_log[i]   = z
    err_log[i] = z - target_all[i]
    if i >= train_steps:
        x_test_log[i - train_steps] = x

    # 每 cycle 結束印診斷
    if (i + 1) % chunk == 0:
        cyc       = (i + 1) // chunk
        chunk_mse = np.mean(err_log[i + 1 - chunk : i + 1] ** 2)
        W_norm    = np.linalg.norm(W)
        J_norm    = np.linalg.norm(J) / np.sqrt(p_conn * N * N)
        if i >= train_steps:
            phase = "test "
        elif i >= w_only_steps:
            phase = "P2 WJ"
        else:
            phase = "P1 W "
        elapsed = time.time() - t_start
        print(f"  Cycle {cyc:2d} ({phase})  MSE = {chunk_mse:.6f}   "
              f"|W| = {W_norm:.3f}  |J|_norm = {J_norm:.4f}   elapsed = {elapsed:5.0f}s")

# ---------------------------------------------------------------------------
# 5. 視覺化
# ---------------------------------------------------------------------------
t_test      = t_all[train_steps:] - t_all[train_steps]
target_test = target_all[train_steps:]
z_test      = z_log[train_steps:]

fig, ax = plt.subplots(1, 2, figsize=(13, 5))

ax[0].plot(t_test, target_test, 'k', alpha=0.4, linewidth=2.5, label='target (Lorenz x)')
ax[0].plot(t_test, z_test, 'r', linewidth=1, label='RNN output (FORCE-Internal v3)')
ax[0].set_xlabel('time (ms)')
ax[0].set_ylabel('signal')
ax[0].set_title('FORCE-Internal v3: test phase time series')
ax[0].legend(loc='upper right')

tau_d = 50
if len(z_test) > tau_d * 2:
    ax[1].plot(target_test[:-tau_d], target_test[tau_d:],
               'k', alpha=0.3, linewidth=0.7, label='target attractor')
    ax[1].plot(z_test[:-tau_d], z_test[tau_d:],
               'r', alpha=0.7, linewidth=0.7, label='RNN output attractor')
ax[1].set_xlabel('z(t)')
ax[1].set_ylabel(f'z(t + {tau_d} ms)')
ax[1].set_title('Attractor: should be much tighter Lorenz butterfly')
ax[1].legend(loc='upper right')
ax[1].set_aspect('equal', adjustable='box')

plt.tight_layout()
plt.savefig('force_internal_v3_demo.png', dpi=120, bbox_inches='tight')

# Stage 4 用:存出訓練好的網路狀態 + test 軌跡
# presyn 是不規則長度的 list,存成 object array
presyn_obj = np.empty(N, dtype=object)
for i_cell in range(N):
    presyn_obj[i_cell] = presyn[i_cell]
np.savez('force_internal_v3_state.npz',
         J=J, W=W, w_fb=w_fb, presyn=presyn_obj,
         x_test=x_test_log, z_test=z_test, target_test=target_test,
         tau=tau, dt=dt, N=N)
print(f"完成。輸出: force_internal_v3_demo.png + force_internal_v3_state.npz")
print(f"\n判讀重點:")
print(f"  ① Phase 1 MSE 應下降到 ~10^-2 (W only,跟 lorenz_output 版同等水準)")
print(f"  ② Phase 2 啟動後 MSE 應再降一個量級到 ~10^-3 ~ 10^-4")
print(f"  ③ |W| 應收斂到 ~0.5-1.5,|J|_norm 應從 ~1.0 微調 (不應大幅偏離 chaotic regime)")
print(f"  ④ 紅線應有明顯 Lorenz lobe-switch 行為,不是常數線")
print(f"  ⑤ 右圖 attractor 應該是清晰的 Lorenz 蝴蝶,比 lorenz_output 版更乾淨")
