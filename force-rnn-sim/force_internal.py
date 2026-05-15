"""
minimal_force_internal.py  (Stage 3 任務 3)
==============================================

FORCE-Internal-RLS-N: **訓練 J 矩陣** (每個 neuron 獨立 RLS),W 固定。
對應 Sussillo & Abbott 2009 (Neuron) Fig 3 的乾淨 Lorenz 蝴蝶。

關鍵改動 vs FORCE-Output (sinusoid / lorenz_output 版):
    1. W (readout) **FIXED random**,不訓練
    2. J (recurrent matrix) **訓練**——每個 post-synaptic neuron 有自己的 P 矩陣
       (這就是 "per-neuron RLS",所以叫 RLS-N)
    3. 沒有 explicit feedback w_fb——J 的訓練本身已內建反饋路徑
    4. 算法複雜度: 從 O(N²) 變 O(N²) × N neurons = O(N³) 每 update step
       為了能在 2-4 分鐘內跑完,N 從 1000 降到 800

為什麼 FORCE-Internal 對 Lorenz (混沌 target) 大勝 FORCE-Output:
    - FORCE-Output 只訓練 W (1 個 vector,N 自由度)
    - FORCE-Internal 訓練 J 的所有非零項 (~N × p·N = p·N² 自由度,本程式 ~64,000)
    - **多 N 倍的自由度** → 能精準刻畫 Lorenz vector field 細節
    - 視覺證據:右圖 delay-embedding 蝴蝶會明顯「收緊」、雙葉乾淨

執行:
    python minimal_force_internal.py

預期執行時間: 2-5 分鐘 (per-neuron RLS 是慢但必要的代價)

預期結果:
    - Train MSE 應收斂 (不像 FORCE-Output on Lorenz 那樣中途反升)
    - 右圖蝴蝶結構比 FORCE-Output 乾淨許多
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint
import time

np.random.seed(42)

# ---------------------------------------------------------------------------
# 1. 網路與訓練參數
# ---------------------------------------------------------------------------
N               = 800       # 從 1000 降到 800,平衡 per-neuron RLS 的速度
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
# 2. 初始化 J, W, per-neuron P 矩陣
# ---------------------------------------------------------------------------
# J: 稀疏 chaotic regime (跟 FORCE-Output 一樣的 init)
J = np.random.randn(N, N) * (g / np.sqrt(p_conn * N))
mask = np.random.rand(N, N) < p_conn
J *= mask
np.fill_diagonal(J, 0)

# 每個 neuron 的 presynaptic 索引 (J[i, j] != 0 的 j)
presyn = [np.where(J[i] != 0)[0] for i in range(N)]
n_pre_avg = np.mean([len(p) for p in presyn])
print(f"  Network: N={N}, p={p_conn}, avg presynaptic per neuron = {n_pre_avg:.1f}")

# W: 固定隨機 readout (不訓練) — scale 讓 |z| 初始 ~ 0.5
W = np.random.randn(N) / np.sqrt(N)

# Per-neuron P 矩陣:每個 P_i 大小 = neuron i 的 presynaptic 數
# 這是 FORCE-Internal-RLS-N 的核心:N 個獨立 RLS state
P_list = [np.eye(len(idx)) / alpha for idx in presyn]
total_P_entries = sum(len(idx) ** 2 for idx in presyn)
print(f"  Memory: {N} 個 P 矩陣,共 {total_P_entries:,} entries ≈ {total_P_entries*8/1e6:.1f} MB")

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
# 4. 主迴圈:per-neuron RLS 訓練 J (沒有 explicit feedback!)
# ---------------------------------------------------------------------------
x = 0.5 * np.random.randn(N)
r = np.tanh(x)
z = float(W @ r)

z_log   = np.zeros(n_steps)
err_log = np.zeros(n_steps)

print(f"\n  開始 FORCE-Internal 訓練 ({n_train_cyc} train cycles + {n_test_cyc} test cycle)")
print(f"  注意:per-neuron RLS 是慢的,別中斷,等候 console cycle 印出\n")

t_start = time.time()

for i in range(n_steps):
    # 前向動力學 — **沒有 w_fb · z!**
    # J 訓練後本身就承載了「需要的反饋路徑」
    x = x + (dt / tau) * (-x + J @ r)
    r = np.tanh(x)
    z = float(W @ r)

    # FORCE-Internal RLS 更新 (per-neuron)
    if i < train_steps and (i % update_every == 0) and i > 0:
        error = z - target_all[i]

        for cell in range(N):
            idx = presyn[cell]
            r_pre = r[idx]                      # 只取此 neuron 的 presynaptic 活動

            Pr = P_list[cell] @ r_pre
            c = 1.0 / (1.0 + r_pre @ Pr)
            P_list[cell] -= c * np.outer(Pr, Pr)
            J[cell, idx] -= c * error * Pr      # 只更新此 row 的非零項

    z_log[i]   = z
    err_log[i] = z - target_all[i]

    # 每個 cycle 結束時印診斷
    if (i + 1) % chunk == 0:
        cyc       = (i + 1) // chunk
        chunk_mse = np.mean(err_log[i + 1 - chunk : i + 1] ** 2)
        # |J|_norm 用 Frobenius / sqrt(p·N²) 標準化
        J_norm    = np.linalg.norm(J) / np.sqrt(p_conn * N * N)
        phase     = "test " if i >= train_steps else "train"
        elapsed   = time.time() - t_start
        print(f"  Cycle {cyc:2d} ({phase})  MSE = {chunk_mse:.6f}   "
              f"|J|_norm = {J_norm:.4f}   elapsed = {elapsed:5.0f}s")

# ---------------------------------------------------------------------------
# 5. 視覺化:時間序列 + delay embedding
# ---------------------------------------------------------------------------
t_test      = t_all[train_steps:] - t_all[train_steps]
target_test = target_all[train_steps:]
z_test      = z_log[train_steps:]

fig, ax = plt.subplots(1, 2, figsize=(13, 5))

# 左:時間序列
ax[0].plot(t_test, target_test, 'k', alpha=0.4, linewidth=2.5, label='target (Lorenz x)')
ax[0].plot(t_test, z_test, 'r', linewidth=1, label='RNN output (FORCE-Internal)')
ax[0].set_xlabel('time (ms)')
ax[0].set_ylabel('signal')
ax[0].set_title('FORCE-Internal: test phase time series')
ax[0].legend(loc='upper right')

# 右:delay embedding (attractor 真正的判讀工具)
tau_d = 50
if len(z_test) > tau_d * 2:
    ax[1].plot(target_test[:-tau_d], target_test[tau_d:],
               'k', alpha=0.3, linewidth=0.7, label='target attractor')
    ax[1].plot(z_test[:-tau_d], z_test[tau_d:],
               'r', alpha=0.7, linewidth=0.7, label='RNN output attractor')
ax[1].set_xlabel('z(t)')
ax[1].set_ylabel(f'z(t + {tau_d} ms)')
ax[1].set_title('Attractor shape: should be tighter Lorenz butterfly than FORCE-Output')
ax[1].legend(loc='upper right')
ax[1].set_aspect('equal', adjustable='box')

plt.tight_layout()
plt.savefig('force_internal_demo.png', dpi=120, bbox_inches='tight')
print(f"\n完成。輸出: force_internal_demo.png")
print(f"\n判讀重點:")
print(f"  ① 對比 FORCE-Output 版的 |J|_norm 應收斂、不再無限長大")
print(f"  ② Train MSE 應該單調下降到 10^-5 級別")
print(f"  ③ 右圖蝴蝶比 FORCE-Output 乾淨 → 證明 per-neuron RLS 的威力")
