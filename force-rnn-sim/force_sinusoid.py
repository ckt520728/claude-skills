"""
minimal_force_sinusoid.py  (Stage 3 任務 1)
============================================

最小可運行 FORCE-Output 演算法,target 為 4 個 sinusoid 的混合 (週期性、可預測)。
對應 Sussillo & Abbott 2009 (Neuron) Fig 2。

執行:
    python minimal_force_sinusoid.py

預期輸出:
    force_sinusoid_demo.png  — 上半:test target vs output 重疊;下半:test 誤差
    成功條件:test MSE < 0.005,紅線整段覆蓋灰線

設計改動筆記 (2026-05-16):
    上一版用「multi-epoch」結構,結果 RLS 在 epoch 邊界發散——因為網路狀態 x 跨 epoch
    延續、但 target 重置回 t=0,RLS 看到同 target 對應不同 r 的矛盾訊號。
    Sussillo 原版是「單一長訓練 + 單一測試」,沒有 epoch 概念。已重寫為這個結構。

任務(按順序做):
    1. 跑通這份程式 → 看到 test 階段 output 完美貼合 target (~5 分鐘)
    2. 把 target 改成 Lorenz attractor 的 x 分量 → 訓練後關掉 input,網路自己跑類 Lorenz 軌跡
    3. 改寫成 FORCE-Internal (訓練 J 矩陣) → 理解 P 矩陣為什麼變 per-neuron

讀完 Sussillo & Abbott 2009 後,試著回答:
    Q1: 為什麼 update_every = 2 而不是每步都更新? (Hint: stability vs learning speed)
    Q2: P 矩陣初始化的 alpha 改成 100 會怎樣? (Hint: regularization 強度)
    Q3: 把 feedback weights w_fb 全設為 0 會發生什麼? (Hint: closed-loop 才是 FORCE 的精髓)
"""

import numpy as np
import matplotlib.pyplot as plt

np.random.seed(42)  # 重現性

# ---------------------------------------------------------------------------
# 1. 網路參數 (Sussillo & Abbott 2009 的典型設定)
# ---------------------------------------------------------------------------
N            = 1000     # recurrent units 數
g            = 1.5      # gain — g > 1 進入 chaotic regime (FORCE 必須條件)
p_conn       = 0.1      # 連接稀疏度 (10% 連通)
tau          = 10.0     # 神經元時間常數 (ms)
dt           = 1.0      # 數值積分步長 (ms) — 配合 tau,dt/tau = 0.1 等同 Sussillo 用 dt=0.1, tau=1
alpha        = 1.0      # RLS regularization (P = I/alpha)
T_cycle      = 1440     # 一個訓練/測試「週期」的時長 (ms) — 涵蓋 4 個 sinusoid 週期 (LCM = 480 × 3)
n_train_cyc  = 15       # 訓練週期數 (慢 target 需要更多 cycle 才能 imprint 進 W)
n_test_cyc   = 1        # 測試週期數 (RLS 關閉)
update_every = 2        # RLS 更新頻率 (Sussillo 原值)

T_total = (n_train_cyc + n_test_cyc) * T_cycle
n_steps = int(T_total / dt)
chunk   = int(T_cycle / dt)
train_steps = n_train_cyc * chunk

# ---------------------------------------------------------------------------
# 2. 初始化矩陣
# ---------------------------------------------------------------------------
# Recurrent connectivity J: 稀疏 + 標準差 g/sqrt(p*N) 的常態分布
J = np.random.randn(N, N) * (g / np.sqrt(p_conn * N))
J *= (np.random.rand(N, N) < p_conn)   # sparsity mask
np.fill_diagonal(J, 0)                  # 無自連接

# Feedback weights: output z 回饋進網路 — Sussillo & Abbott 2009 的關鍵設計
w_fb = (np.random.rand(N) - 0.5) * 2    # uniform [-1, 1]

# Readout weights: FORCE-Output 唯一訓練的對象,初始化為 0
W = np.zeros(N)

# RLS state
P = np.eye(N) / alpha

# ---------------------------------------------------------------------------
# 3. Target signal: Sussillo & Abbott 2009 原始 demo 的 target
#    關鍵:週期要遠 > tau (= 10 ms),且高頻成分振幅要小
#    Sussillo 原值是 freq=1/60 in tau units,本程式 tau=10 ms 所以 freq=1/600 in ms
# ---------------------------------------------------------------------------
t_all = np.arange(n_steps) * dt
amp   = 1.3
freq  = 1.0 / 600.0     # 等同 Sussillo 1/60 in tau units (本程式 tau=10 → 600 ms)
target_all = (
    (amp / 1.0) * np.sin(1.0 * np.pi * freq * t_all) +
    (amp / 2.0) * np.sin(2.0 * np.pi * freq * t_all) +
    (amp / 6.0) * np.sin(3.0 * np.pi * freq * t_all) +
    (amp / 3.0) * np.sin(4.0 * np.pi * freq * t_all)
) / 1.5
# 這版 target 的週期: 1200, 600, 400, 300 ms (都遠 > tau=10 ms,網路追得到)

# ---------------------------------------------------------------------------
# 4. 主迴圈:單一長訓練 + 單一測試 (沒有 epoch 結構!)
# ---------------------------------------------------------------------------
x = 0.5 * np.random.randn(N)
r = np.tanh(x)
z = float(W @ r)

z_log   = np.zeros(n_steps)
err_log = np.zeros(n_steps)

print(f"開始: N={N}, g={g}, alpha={alpha}, update_every={update_every}")
print(f"       訓練 {n_train_cyc} cycles × {T_cycle} ms,測試 {n_test_cyc} cycle\n")

for i in range(n_steps):
    # 前向動力學 (Euler 積分)
    x = x + (dt / tau) * (-x + J @ r + w_fb * z)
    r = np.tanh(x)
    z = float(W @ r)

    # RLS 更新 (只在訓練階段)
    if i < train_steps and (i % update_every == 0) and i > 0:
        error = z - target_all[i]
        Pr = P @ r
        k = Pr / (1.0 + r @ Pr)
        P = P - np.outer(k, Pr)
        W = W - error * k

    z_log[i]   = z
    err_log[i] = z - target_all[i]

    # 每個 cycle 結束時印一次診斷
    if (i + 1) % chunk == 0:
        cyc       = (i + 1) // chunk
        chunk_mse = np.mean(err_log[i + 1 - chunk : i + 1] ** 2)
        w_norm    = np.linalg.norm(W)
        phase     = "test " if i >= train_steps else "train"
        print(f"  Cycle {cyc} ({phase})  MSE = {chunk_mse:.6f}   |W| = {w_norm:.3f}")

# ---------------------------------------------------------------------------
# 5. 視覺化 (只畫 test 階段)
# ---------------------------------------------------------------------------
t_test      = t_all[train_steps:] - t_all[train_steps]
target_test = target_all[train_steps:]
z_test      = z_log[train_steps:]
err_test    = err_log[train_steps:]

fig, ax = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

ax[0].plot(t_test, target_test, 'k', alpha=0.4, linewidth=2.5, label='target')
ax[0].plot(t_test, z_test, 'r', linewidth=1, label='RNN output')
ax[0].set_ylabel('signal')
ax[0].set_title(f'FORCE-Output (test phase): N={N}, g={g}, {n_train_cyc} train cycles')
ax[0].legend(loc='upper right')

ax[1].plot(t_test, err_test, 'b', linewidth=0.5)
ax[1].set_xlabel('time (ms)')
ax[1].set_ylabel('error (z − target)')
ax[1].set_title('test error')

plt.tight_layout()
plt.savefig('force_sinusoid_demo.png', dpi=120, bbox_inches='tight')
print(f"\n完成。輸出: force_sinusoid_demo.png")
print(f"預期: test cycle 的 MSE 應 < 0.005,紅線幾乎完全覆蓋灰線")
