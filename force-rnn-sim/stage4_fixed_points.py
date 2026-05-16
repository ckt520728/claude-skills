"""
stage4_fixed_points.py  (Stage 4 任務 1)
==========================================

Sussillo & Barak 2013 "Opening the Black Box" — 對 FORCE-Internal v3 訓練好的
網路做 fixed/slow point analysis。

核心想法:
    訓練好的 RNN 是個高維非線性動力系統。它怎麼「算」Lorenz attractor?
    Sussillo & Barak 的回答:**找出動力系統的 fixed points (q=0) 跟 slow points
    (q 很小但不為 0)**,看它們在 state space 怎麼組織。這些「不動的位置」往往
    對應運算上有意義的結構:lobe centers、saddle points、limit cycles 的骨架等。

數學定義:
    動力方程:tau * dx/dt = -x + J @ tanh(x) + w_fb * (W @ tanh(x))
    定義 F(x) = -x + J @ tanh(x) + w_fb * (W @ tanh(x))     (蛻去 1/tau)
    目標函數:q(x) = 0.5 * ||F(x)||²
        - q(x*) = 0       → x* 是 fixed point
        - q(x*) 很小      → x* 是 slow point (準 fixed)
    對每個 found point 計算 Jacobian dF/dx,看 eigenvalues 判 stability:
        - 所有 |λ| < 1  (蛻 dt/tau 之後)  → stable attractor
        - 至少一個正實部 → unstable / saddle

策略 (Sussillo & Barak 2013 standard):
    1. 從 test trajectory 上 sample 多個初始 guess(網路真的去過的地方)
    2. 對每個 guess,L-BFGS-B 最小化 q(x)
    3. 過濾:q < threshold 才算 found
    4. 對 found points cluster(避免重複計算同一個 fixed point)
    5. 每個 unique point 算 Jacobian eigenvalues
    6. PCA 把 trajectory + fixed points 投影到 top 3 PC,視覺化

執行 (需要 minimal_force_internal_v3.py 先跑出 force_internal_v3_state.npz):
    python stage4_fixed_points.py

預期輸出:
    stage4_fixed_points_demo.png 三聯圖:
        - 左:  PC1-PC2 平面,trajectory + fixed points 顏色標 stability
        - 中:  PC1-PC3 平面 (從另一個角度看)
        - 右:  fixed points 的 Jacobian eigenvalues 在 complex plane

對應 Sussillo & Barak 2013 Fig 2 的 Lorenz analysis,預期結果:
    - 每個 lobe 中心附近有 1-3 個 unstable spiral fixed points (對應 Lorenz 的 C+/C-)
    - lobe 之間可能有 saddle point (對應 Lorenz 原點)
    - eigenvalue spectrum 應該大部分在 unit circle 內,但有少數 |λ|>1 在 ±i 附近
      (對應 oscillatory unstable modes,負責驅動 lobe-switch)
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
import time

np.random.seed(42)

# ---------------------------------------------------------------------------
# 1. 載入訓練好的網路狀態
# ---------------------------------------------------------------------------
state = np.load('force_internal_v3_state.npz', allow_pickle=True)
J          = state['J']
W          = state['W']
w_fb       = state['w_fb']
x_test     = state['x_test']       # shape (n_test_steps, N)
z_test     = state['z_test']
target_test = state['target_test']
tau        = float(state['tau'])
dt         = float(state['dt'])
N          = int(state['N'])

print(f"  載入 v3 state: N={N}, x_test shape={x_test.shape}")
print(f"  |W|={np.linalg.norm(W):.3f}, |J|={np.linalg.norm(J):.2f}")

# ---------------------------------------------------------------------------
# 2. 動力方程 F(x), 損失 q(x) = 0.5 ||F||², 與 gradient
# ---------------------------------------------------------------------------
def F(x):
    """RNN 動力方程的「速度」 (純向量場,蛻去 1/tau)。"""
    r = np.tanh(x)
    z = W @ r
    return -x + J @ r + w_fb * z

def q(x):
    """目標函數: q(x) = 0.5 * ||F(x)||²"""
    f = F(x)
    return 0.5 * f @ f

def grad_q(x):
    """解析 gradient:
        F(x) = -x + J @ tanh(x) + w_fb * (W @ tanh(x))
        ∂F_i/∂x_j = -δ_ij + (J_ij + w_fb_i * W_j) * (1 - tanh²(x_j))
        ∇q = J^T @ F  (where J = dF/dx, the Jacobian)
    """
    r = np.tanh(x)
    sech2 = 1.0 - r ** 2
    f = F(x)
    # Jacobian-vector product 形式:dF/dx^T @ f = (-I + (J + w_fb·W^T)·diag(sech²))^T @ f
    #                                          = -f + diag(sech²) @ (J^T + W·w_fb^T) @ f
    # 攤平:                                    = -f + sech² * (J.T @ f + W * (w_fb @ f))
    return -f + sech2 * (J.T @ f + W * (w_fb @ f))

# ---------------------------------------------------------------------------
# 3. 初始 guess pool: trajectory sample + random perturbation
#    v1 只用 trajectory 50 點,只找到 1 個 slow point → trajectory 上的鄰近點
#    被 L-BFGS 全推向同一個 attractor basin。
#    v2:加 perturbation 跳出局部 basin,讓搜尋探索更廣的 state space。
# ---------------------------------------------------------------------------
n_traj = 100   # 從 trajectory 等距 sample
n_pert = 100   # 從 trajectory 額外 sample 後加高斯擾動 (跳出鄰近 basin)
n_init = n_traj + n_pert

traj_idx = np.linspace(0, x_test.shape[0] - 1, n_traj).astype(int)
traj_guesses = x_test[traj_idx]

pert_idx = np.random.choice(x_test.shape[0], n_pert, replace=False)
# 擾動量 ~ 訓練後 x 的標準差,讓 perturbation 顯著但不離譜
x_std = x_test.std(axis=0).mean()
pert_guesses = x_test[pert_idx] + np.random.randn(n_pert, N) * x_std

initial_guesses = np.vstack([traj_guesses, pert_guesses])
print(f"\n  初始 guess pool: {n_traj} traj-sample + {n_pert} traj+perturbation = {n_init} 總點")
print(f"  perturbation 標準差 = {x_std:.3f} (= x_test 平均 std)")

found_points = []
found_q     = []
print(f"  L-BFGS-B 開始搜尋 (每個 guess maxiter=500)...")
t0 = time.time()
for k, x0 in enumerate(initial_guesses):
    res = minimize(q, x0, jac=grad_q, method='L-BFGS-B',
                   options={'maxiter': 500, 'gtol': 1e-10})
    found_points.append(res.x)
    found_q.append(res.fun)
    if (k + 1) % 10 == 0:
        elapsed = time.time() - t0
        print(f"    [{k+1:>2}/{n_init}] q_med={np.median(found_q):.2e}, "
              f"q_min={min(found_q):.2e}, elapsed={elapsed:.1f}s")

found_points = np.array(found_points)
found_q     = np.array(found_q)
print(f"  搜尋完成 ({time.time()-t0:.1f}s)。q 分布: "
      f"min={found_q.min():.2e}, median={np.median(found_q):.2e}, max={found_q.max():.2e}")

# ---------------------------------------------------------------------------
# 4. 篩選 + cluster (避免同一 fixed point 算多次)
# ---------------------------------------------------------------------------
# v2 修改:q_thresh 放寬到 5e-3 收 slow points;cluster d_thresh 縮到 0.5 避免合併
q_thresh = 5e-3

valid_mask = found_q < q_thresh
valid_points = found_points[valid_mask]
valid_q     = found_q[valid_mask]
print(f"\n  q < {q_thresh:.0e} 的點: {valid_mask.sum()}/{n_init}")

# 簡單 cluster:兩兩距離 < cluster_d 視為同一 point
def cluster(points, qs, d_thresh=1.0):
    """貪心 cluster:依 q 排序,每個 unique point 吸收附近的 duplicate"""
    if len(points) == 0:
        return points, qs
    order = np.argsort(qs)
    keep = []
    keep_q = []
    used = np.zeros(len(points), dtype=bool)
    for i in order:
        if used[i]:
            continue
        keep.append(points[i])
        keep_q.append(qs[i])
        for j in range(len(points)):
            if not used[j] and np.linalg.norm(points[i] - points[j]) < d_thresh:
                used[j] = True
    return np.array(keep), np.array(keep_q)

unique_pts, unique_q = cluster(valid_points, valid_q, d_thresh=0.5)
print(f"  cluster 後 unique slow/fixed points (d_thresh=0.5): {len(unique_pts)}")

# ---------------------------------------------------------------------------
# 5. 對每個 unique point 算 Jacobian + eigenvalues
# ---------------------------------------------------------------------------
def jacobian(x):
    """dF/dx,用解析公式避開 numerical Jacobian:
       J_F[i,j] = -δ_ij + (J[i,j] + w_fb[i] * W[j]) * (1 - tanh²(x_j))
    """
    sech2 = 1.0 - np.tanh(x) ** 2          # shape (N,)
    M = J + np.outer(w_fb, W)              # shape (N, N)
    return -np.eye(N) + M * sech2          # broadcasting on j-axis

all_eigs = []
for k, x_star in enumerate(unique_pts):
    Jx = jacobian(x_star)
    eigs = np.linalg.eigvals(Jx)
    all_eigs.append(eigs)
    n_unstable = np.sum(np.real(eigs) > 0)
    print(f"  fixed point #{k}: q={unique_q[k]:.2e}, "
          f"{n_unstable} unstable directions (max Re={np.real(eigs).max():.3f})")

# ---------------------------------------------------------------------------
# 6. PCA 投影 + 視覺化
# ---------------------------------------------------------------------------
# PCA 用 test trajectory 算主成分 (centred)
traj = x_test
mu = traj.mean(axis=0)
traj_c = traj - mu
# SVD-based PCA:traj_c = U S V^T,top PC = V[:, :k]
U, S, Vt = np.linalg.svd(traj_c, full_matrices=False)
V = Vt.T   # shape (N, N)
PC = V[:, :3]   # top 3 PC,shape (N, 3)
explained = (S[:3] ** 2) / (S ** 2).sum()
print(f"\n  PCA: top 3 PC 解釋變異 = {explained[0]:.1%}, {explained[1]:.1%}, {explained[2]:.1%}")

traj_proj = traj_c @ PC                      # shape (n_test_steps, 3)
fp_proj   = (unique_pts - mu) @ PC if len(unique_pts) > 0 else np.zeros((0, 3))

# Stability colour: 紅 = unstable (≥1 個 Re(λ)>0), 藍 = stable
fp_colors = []
for eigs in all_eigs:
    if np.real(eigs).max() > 0:
        fp_colors.append('red')
    else:
        fp_colors.append('blue')

# 大小編碼 q 品質: 越小越接近真 fixed point,點越大
fp_sizes = np.clip(-np.log10(unique_q + 1e-12) * 30, 30, 300) if len(unique_q) > 0 else []

fig, ax = plt.subplots(2, 2, figsize=(13, 11))

# (a) PC1-PC2
ax[0, 0].plot(traj_proj[:, 0], traj_proj[:, 1], 'k', alpha=0.3, linewidth=0.5, label='test trajectory')
if len(fp_proj) > 0:
    ax[0, 0].scatter(fp_proj[:, 0], fp_proj[:, 1], c=fp_colors, s=fp_sizes,
                     edgecolors='black', linewidths=1.5, zorder=10, alpha=0.8,
                     label='slow points (size = -log10(q))')
ax[0, 0].set_xlabel(f'PC1 ({explained[0]:.0%})')
ax[0, 0].set_ylabel(f'PC2 ({explained[1]:.0%})')
ax[0, 0].set_title('State space PC1-PC2')
ax[0, 0].legend(loc='upper right', fontsize=9)

# (b) PC1-PC3
ax[0, 1].plot(traj_proj[:, 0], traj_proj[:, 2], 'k', alpha=0.3, linewidth=0.5)
if len(fp_proj) > 0:
    ax[0, 1].scatter(fp_proj[:, 0], fp_proj[:, 2], c=fp_colors, s=fp_sizes,
                     edgecolors='black', linewidths=1.5, zorder=10, alpha=0.8)
ax[0, 1].set_xlabel(f'PC1 ({explained[0]:.0%})')
ax[0, 1].set_ylabel(f'PC3 ({explained[2]:.0%})')
ax[0, 1].set_title('State space PC1-PC3 (orthogonal view)')

# (c) Eigenvalue spectrum
if len(all_eigs) > 0:
    all_eigs_flat = np.concatenate(all_eigs)
    ax[1, 0].scatter(np.real(all_eigs_flat), np.imag(all_eigs_flat),
                     s=10, alpha=0.5, color='purple')
ax[1, 0].axhline(0, color='gray', linestyle='--', linewidth=0.8)
ax[1, 0].axvline(0, color='red', linestyle='--', linewidth=1.0, label='Re(λ)=0 (stability boundary)')
ax[1, 0].set_xlabel('Re(λ)')
ax[1, 0].set_ylabel('Im(λ)')
ax[1, 0].set_title('Jacobian eigenvalues (continuous-time)')
ax[1, 0].legend(loc='upper right', fontsize=9)
ax[1, 0].set_aspect('equal', adjustable='datalim')

# (d) q convergence distribution: 看是否 multi-modal,代表多個 basin
ax[1, 1].hist(np.log10(found_q + 1e-12), bins=40, color='steelblue', edgecolor='black', alpha=0.7)
ax[1, 1].axvline(np.log10(q_thresh), color='red', linestyle='--', linewidth=1.5,
                 label=f'q_thresh = {q_thresh:.0e}')
ax[1, 1].set_xlabel('log10(q) after L-BFGS')
ax[1, 1].set_ylabel('count')
ax[1, 1].set_title(f'q-landscape: {n_init} L-BFGS minima distribution')
ax[1, 1].legend(loc='upper left', fontsize=9)

plt.suptitle(f'Stage 4 (refined): {len(unique_pts)} unique slow points  |  '
             f'{n_init} initial guesses ({n_traj} traj + {n_pert} perturbed)',
             fontsize=12, y=1.00)
plt.tight_layout()
plt.savefig('stage4_fixed_points_demo.png', dpi=120, bbox_inches='tight')
print(f"\n完成。輸出: stage4_fixed_points_demo.png")
print(f"\n判讀重點 (對照 Sussillo & Barak 2013 Fig 2):")
print(f"  ① PC1-PC2 應該看到 Lorenz 蝴蝶在低維投影下的雙 lobe 結構")
print(f"  ② Fixed/slow points 應該聚在 lobe 中心附近 (對應 Lorenz C+/C-)")
print(f"  ③ Eigenvalue spectrum:大部分 |λ|<1,但有少數 |λ|>1 的 unstable mode")
print(f"     (帶共軛複數 → oscillatory instability → 驅動 lobe-switch)")
