"""
minimal_force_lorenz.py  (Stage 3 任務 2)
==========================================

把 target 從週期性 sinusoid 換成 **Lorenz attractor 的 x 分量** — 混沌、非週期、
有 strange attractor 幾何結構。對應 Sussillo & Abbott 2009 (Neuron) Fig 3。

為什麼這比 sinusoid 版難:
    - Sinusoid 有明確週期,網路只要「記住一個 cycle」就過關
    - Lorenz 永不重複,網路必須學會 **vector field 本身**,才能在 test 階段
      不靠 RLS 矯正、自己 generate 出 Lorenz-like 軌跡
    - 混沌系統對初始條件指數敏感,所以「target 跟 output 一模一樣」是不可能的
      正確的成功標準:output 軌跡應該停留在 Lorenz attractor 的 **幾何形狀** 上
      (兩個 lobe 之間反覆切換、振幅在合理範圍、不發散不收斂)

執行:
    python minimal_force_lorenz.py

預期輸出:
    force_lorenz_demo.png  — 上半:時間序列(早期應重合,後期會 phase divergent)
                             下半:test 階段網路輸出的「delay embedding」相圖
    成功條件:
    - 早期 ~200 ms:紅線貼著灰線
    - 後期:會偏離 (混沌本性),但振幅維持 ±1.3 之間、有 lobe-switch 行為
    - delay embedding 圖呈現 Lorenz 蝴蝶狀的「strange attractor」

讀完 Sussillo & Abbott 2009 Fig 3 後,試著回答:
    Q1: 為什麼成功標準從「point-by-point 重合」變成「attractor 幾何形狀」?
    Q2: 增加 n_train_cyc 到 30 會更好嗎?(Hint: 混沌訓練的 saturation)
    Q3: 把 LORENZ_SLOWDOWN 改成 50 會發生什麼?(Hint: target 速度 vs tau)
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint

np.random.seed(42)  # 重現性

# ---------------------------------------------------------------------------
# 1. 網路參數 (與 sinusoid 版相同,FORCE 核心不變)
# ---------------------------------------------------------------------------
N            = 1000     # recurrent units 數
g            = 1.5      # gain
p_conn       = 0.1      # 連接稀疏度
tau          = 10.0     # 神經元時間常數 (ms)
dt           = 1.0      # 數值積分步長 (ms)
alpha        = 1.0      # RLS regularization
T_cycle      = 1440     # logging 用 cycle 長度 (ms)
n_train_cyc  = 40       # 混沌 target 需要更多 cycle (從 20 → 40,給 W 更多時間 imprint vector field)
n_test_cyc   = 1
update_every = 2

# Lorenz 時間尺度:每 ms 真實時間 = 1/LORENZ_SLOWDOWN Lorenz time unit
# 400 → 1 Lorenz unit = 400 ms 真實 → lobe transition ~200-400 ms ~ 20-40 tau
# 從 200 → 400 (target 變慢,網路更容易追,attractor 應更精緻)
LORENZ_SLOWDOWN = 400

T_total = (n_train_cyc + n_test_cyc) * T_cycle
n_steps = int(T_total / dt)
chunk   = int(T_cycle / dt)
train_steps = n_train_cyc * chunk

# ---------------------------------------------------------------------------
# 2. 初始化網路
# ---------------------------------------------------------------------------
J = np.random.randn(N, N) * (g / np.sqrt(p_conn * N))
J *= (np.random.rand(N, N) < p_conn)
np.fill_diagonal(J, 0)

w_fb = (np.random.rand(N) - 0.5) * 2
W = np.zeros(N)
P = np.eye(N) / alpha

# ---------------------------------------------------------------------------
# 3. Target signal: Lorenz attractor 的 x 分量
# ---------------------------------------------------------------------------
def lorenz_deriv(state, t, sigma=10.0, rho=28.0, beta=8.0/3.0):
    x, y, z = state
    return [sigma * (y - x), x * (rho - z) - y, x * y - beta * z]

t_all = np.arange(n_steps) * dt
t_lorenz = t_all / LORENZ_SLOWDOWN          # Lorenz 內部時間
print(f"產生 Lorenz target ({t_lorenz[-1]:.1f} Lorenz time units)...")
sol = odeint(lorenz_deriv, [1.0, 1.0, 1.0], t_lorenz, rtol=1e-8, atol=1e-10)
target_all = sol[:, 0] / 15.0  # 標準化到 ~ [-1.5, 1.5]
print(f"  Lorenz x 範圍: [{target_all.min():.2f}, {target_all.max():.2f}]")

# ---------------------------------------------------------------------------
# 4. 主迴圈:單一長訓練 + 單一測試
# ---------------------------------------------------------------------------
x = 0.5 * np.random.randn(N)
r = np.tanh(x)
z = float(W @ r)

z_log   = np.zeros(n_steps)
err_log = np.zeros(n_steps)

print(f"\n開始 FORCE-Output 訓練: N={N}, g={g}, {n_train_cyc} cycles × {T_cycle} ms")
print(f"  混沌 target,訓練後網路須自己 generate Lorenz-like 軌跡\n")

for i in range(n_steps):
    x = x + (dt / tau) * (-x + J @ r + w_fb * z)
    r = np.tanh(x)
    z = float(W @ r)

    if i < train_steps and (i % update_every == 0) and i > 0:
        error = z - target_all[i]
        Pr = P @ r
        k = Pr / (1.0 + r @ Pr)
        P = P - np.outer(k, Pr)
        W = W - error * k

    z_log[i]   = z
    err_log[i] = z - target_all[i]

    if (i + 1) % chunk == 0:
        cyc       = (i + 1) // chunk
        chunk_mse = np.mean(err_log[i + 1 - chunk : i + 1] ** 2)
        w_norm    = np.linalg.norm(W)
        phase     = "test " if i >= train_steps else "train"
        print(f"  Cycle {cyc:2d} ({phase})  MSE = {chunk_mse:.6f}   |W| = {w_norm:.3f}")

# ---------------------------------------------------------------------------
# 5. 視覺化:時間序列 + delay embedding (相圖)
# ---------------------------------------------------------------------------
t_test      = t_all[train_steps:] - t_all[train_steps]
target_test = target_all[train_steps:]
z_test      = z_log[train_steps:]

fig, ax = plt.subplots(1, 2, figsize=(13, 5))

# 左:時間序列
ax[0].plot(t_test, target_test, 'k', alpha=0.4, linewidth=2.5, label='target (Lorenz x)')
ax[0].plot(t_test, z_test, 'r', linewidth=1, label='RNN output')
ax[0].set_xlabel('time (ms)')
ax[0].set_ylabel('signal')
ax[0].set_title(f'Test phase: time series (chaos → phase divergence is OK)')
ax[0].legend(loc='upper right')

# 右:delay embedding (相圖) — 把網路輸出畫成 (z(t), z(t+τ_d)) 看 attractor 結構
tau_d = 50  # delay (ms) — for Lorenz, ~τ/4 of slowest mode 看得到蝴蝶
if len(z_test) > tau_d * 2:
    ax[1].plot(target_test[:-tau_d], target_test[tau_d:], 'k', alpha=0.3, linewidth=0.7,
               label='target attractor')
    ax[1].plot(z_test[:-tau_d], z_test[tau_d:], 'r', alpha=0.7, linewidth=0.7,
               label='RNN output attractor')
ax[1].set_xlabel('z(t)')
ax[1].set_ylabel(f'z(t + {tau_d} ms)')
ax[1].set_title('Delay embedding: attractor shape')
ax[1].legend(loc='upper right')
ax[1].set_aspect('equal', adjustable='box')

plt.tight_layout()
plt.savefig('force_lorenz_demo.png', dpi=120, bbox_inches='tight')
print(f"\n完成。輸出: force_lorenz_demo.png")
print(f"判讀:")
print(f"  - 左圖前 ~200 ms:紅線應貼合灰線")
print(f"  - 左圖後段:phase divergence (混沌本性,正常)——但振幅須維持在 ±1.5 內")
print(f"  - 右圖:紅色 attractor 形狀應接近黑色 (Lorenz 蝴蝶)——這才是真正的成功標準")
