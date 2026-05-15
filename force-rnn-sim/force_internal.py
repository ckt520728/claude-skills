"""
force_internal.py  (Stage 3 任務 3) — v2 (修正 feedback bug)
==============================================================

FORCE-Internal-RLS-N: 訓練 J 矩陣 (每個 neuron 獨立 RLS) + 同時訓練 W。
對應 Sussillo & Abbott 2009 Fig 3 的乾淨 Lorenz 蝴蝶。

v2 修正自 v1 的關鍵 bug:
    v1 把 explicit feedback w_fb*z 拿掉,以為 J 訓練後會自帶反饋。錯。
    結果:訓練期間網路 chaos 被 RLS 殺掉,坍縮成 fixed point,output 變成常數線。

    v2 修正:
    1. **保留 w_fb*z feedback** (Sussillo 原 MATLAB code FORCE_INTERNAL_ALL2ALL 的作法)
    2. **W 也訓練** (FORCE-Output 風格的 shared P_W,跟 J 的 per-neuron P 並行)
    3. W 初始化為 0,跟 J 一起從零學

關鍵 vs FORCE-Output (sinusoid / lorenz_output 版):
    1. W 訓練方式相同 (FORCE-Output RLS,單一 P_W)
    2. **多了訓練 J** — per-neuron RLS,N 個獨立 P_J
    3. Feedback (w_fb*z) 保留
    4. 訓練自由度從 N 增加到 N + p*N² (本程式 N=800, p=0.1 → 多 ~64,000 個自由度)

為什麼 FORCE-Internal 對 Lorenz (混沌 target) 大勝 FORCE-Output:
    - FORCE-Output 只訓練 W: 1 個 vector,N 個自由度
    - FORCE-Internal 同時訓練 W + J: N + p·N² 自由度
    - 多 N 倍的自由度 → 能精準刻畫 Lorenz vector field 細節

執行:
    python force_internal.py

預期執行時間: 3-5 分鐘 (per-neuron RLS 是慢但必要)
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint
import time

np.random.seed(42)

# ---------------------------------------------------------------------------
# 1. 網路與訓練參數
# ---------------------------------------------------------------------------
N               = 800       # per-neuron RLS 很耗時,從 1000 降到 800
g               = 1.5
p_conn          = 0.1
tau             = 10.0
dt              = 1.0
alpha           = 1.0
T_cycle         = 1440
n_train_cyc     = 15
n_test_cyc      = 1
update_every    = 2
LORENZ_SLOWDOWN = 200

T_total     = (n_train_cyc + n_test_cyc) * T_cycle
n_steps     = int(T_total / dt)
chunk       = int(T_cycle / dt)
train_steps = n_train_cyc * chunk

# ---------------------------------------------------------------------------
# 2. 初始化 J, W, w_fb, P 矩陣
# ---------------------------------------------------------------------------
# J: 稀疏 chaotic regime (跟 FORCE-Output 一樣的 init)
J = np.random.randn(N, N) * (g / np.sqrt(p_conn * N))
mask = np.random.rand(N, N) < p_conn
J *= mask
np.fill_diagonal(J, 0)

# 每個 neuron 的 presynaptic 索引
presyn = [np.where(J[i] != 0)[0] for i in range(N)]
n_pre_avg = np.mean([len(p) for p in presyn])
print(f"  Network: N={N}, p={p_conn}, avg presynaptic per neuron = {n_pre_avg:.1f}")

# W: readout — 初始化為 0,訓練過程跟 J 一起學
W = np.zeros(N)

# Feedback weights — **訓練期間必須保留!** (這是 v1 的 bug:當時拿掉造成 chaos 死掉)
# Sussillo 原版 MATLAB code 在 FORCE-Internal 訓練時也保留 wf*z
# 沒有 feedback → 網路喪失 chaotic regime → RLS 把網路推到 fixed point → 完全失敗
w_fb = (np.random.rand(N) - 0.5) * 2

# P 矩陣:一個 N×N 給 W (FORCE-Output 風格),N 個 per-neuron 給 J
P_W = np.eye(N) / alpha
P_J_list = [np.eye(len(idx)) / alpha for idx in presyn]
total_P_entries = N * N + sum(len(idx) ** 2 for idx in presyn)
print(f"  Memory: P_W ({N}x{N}) + N 個 P_J,共 {total_P_entries:,} entries ≈ {total_P_entries*8/1e6:.1f} MB")

# ---------------------------------------------------------------------------
# 3. Lorenz target (跟 lorenz_output 版相同)
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
# 4. 主迴圈:per-neuron RLS 訓練 J + standard RLS 訓練 W,**保留 feedback**
# ---------------------------------------------------------------------------
x = 0.5 * np.random.randn(N)
r = np.tanh(x)
z = float(W @ r)

z_log   = np.zeros(n_steps)
err_log = np.zeros(n_steps)

print(f"\n  開始 FORCE-Internal-v2 訓練 ({n_train_cyc} train cycles + {n_test_cyc} test cycle)")
print(f"  注意:per-neuron RLS 是慢的,別中斷,等候 console cycle 印出\n")

t_start = time.time()

for i in range(n_steps):
    # 前向動力學 — **保留 feedback w_fb · z** (v1 bug 修正點)
    x = x + (dt / tau) * (-x + J @ r + w_fb * z)
    r = np.tanh(x)
    z = float(W @ r)

    # RLS 更新 (W 用標準 FORCE-Output,J 用 per-neuron FORCE-Internal)
    if i < train_steps and (i % update_every == 0) and i > 0:
        error = z - target_all[i]

        # (a) 更新 W (FORCE-Output 風格,單一 P_W)
        Pr_W = P_W @ r
        c_W = 1.0 / (1.0 + r @ Pr_W)
        P_W -= c_W * np.outer(Pr_W, Pr_W)
        W -= c_W * error * Pr_W

        # (b) 更新 J 每一列 (per-neuron RLS,N 個獨立 P_J)
        for cell in range(N):
            idx = presyn[cell]
            r_pre = r[idx]
            Pr_J = P_J_list[cell] @ r_pre
            c_J = 1.0 / (1.0 + r_pre @ Pr_J)
            P_J_list[cell] -= c_J * np.outer(Pr_J, Pr_J)
            J[cell, idx] -= c_J * error * Pr_J

    z_log[i]   = z
    err_log[i] = z - target_all[i]

    # 每個 cycle 結束印診斷
    if (i + 1) % chunk == 0:
        cyc       = (i + 1) // chunk
        chunk_mse = np.mean(err_log[i + 1 - chunk : i + 1] ** 2)
        W_norm    = np.linalg.norm(W)
        J_norm    = np.linalg.norm(J) / np.sqrt(p_conn * N * N)
        phase     = "test " if i >= train_steps else "train"
        elapsed   = time.time() - t_start
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
ax[0].plot(t_test, z_test, 'r', linewidth=1, label='RNN output (FORCE-Internal-v2)')
ax[0].set_xlabel('time (ms)')
ax[0].set_ylabel('signal')
ax[0].set_title('FORCE-Internal v2: test phase time series')
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
plt.savefig('force_internal_demo.png', dpi=120, bbox_inches='tight')
print(f"\n完成。輸出: force_internal_demo.png")
print(f"\n判讀重點:")
print(f"  ① Train MSE 應持續下降到 ~10^-4 級別 (不像 v1 卡在 ~3)")
print(f"  ② |W| 應收斂到 ~0.5-1.5,|J|_norm 應收斂到 ~1.5-2.5")
print(f"  ③ 紅線 (output) 應該不是常數線了,有明顯 Lorenz 形狀")
print(f"  ④ 右圖蝴蝶應該比 force_lorenz.py 版乾淨許多")
