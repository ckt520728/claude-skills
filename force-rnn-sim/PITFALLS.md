# FORCE Algorithm 實作踩坑全紀錄

> 整理自 2026-05-16 一次從零實作 FORCE algorithm 的 debugging 過程。
> 6 個 failure mode + 1 個成功收斂的完整路徑。
> 讀完這份比讀十遍 paper 還有用——這是用時間與挫折換來的。

---

## TL;DR — 致 future 的我

要實作 Sussillo & Abbott 2009 FORCE,必須同時滿足以下:

| # | 條件 | 為什麼 |
|---|---|---|
| 1 | **單一連續訓練,沒有 epoch boundary** | epoch 邊界讓 target 重置但網路狀態延續,RLS 看到矛盾訊號 |
| 2 | **target 週期 ≥ 10·tau** | tau = 神經元時間常數,target 變化比這快網路追不到 |
| 3 | **`update_every` × dt/tau ≈ 0.1-0.2** | Sussillo 原值是這個,維持 RLS 相對更新頻率 |
| 4 | **適度的 `n_train_cyc`(週期性 target ~15,混沌 target ~10)** | 過度訓練在混沌 target 下反而讓 W 飄遠 |
| 5 | **`alpha ≥ 1`** | RLS regularization,太小 W 會暴增 |
| 6 | **FORCE-Internal for 混沌 target** | FORCE-Output 對混沌 target 有 70-80% 天花板 |

---

## 失敗模式 1 — Multi-epoch 結構讓 RLS 追逐 moving target

### 現象

訓練 MSE **先降後升**:
```
Cycle 1  MSE = 0.000561   |W| = 0.240
Cycle 2  MSE = 0.000258   |W| = 0.281  ← 最低
Cycle 7  MSE = 0.001387   |W| = 0.531  ← 不正常上升
```

### 病因

把訓練拆成多個 epoch 時,每個 epoch:
- 網路狀態 `x` **跨 epoch 延續**(沒重置)
- Target `t` **重置回 0**(periodic)
- RLS 看到「同一個 target 值對應到不同 r」 → 追逐一個會跑的目標 → W 永遠不收斂

### 修法

**單一連續訓練,沒有 epoch 結構**。Sussillo paper 原版根本沒有 multi-epoch 概念。

```python
# ❌ 錯誤:
for epoch in range(n_epochs):
    for i in range(steps_per_epoch):
        x = step_dynamics(x, ...)
        if rls_active:
            W = rls_update(W, ...)

# ✓ 正確:
for i in range(total_steps):
    x = step_dynamics(x, ...)
    if i < train_end:
        W = rls_update(W, ...)
```

---

## 失敗模式 2 — Target 時間尺度錯配(週期 < 10·tau)

### 現象

Output 鎖在高頻振盪,振幅持續放大:
```
Test 階段紅線在 60-80 ms 週期狂震,振幅從 0.5 滾到 1.5
網路被 feedback 路徑推進「自己的高頻 limit cycle」
```

### 病因

`tau` 是神經元時間常數,**target 變化比 tau 快很多時,網路根本追不到**。FORCE 試圖補,W 在錯方向長大,feedback `w_fb · z` 變成主導訊號,鎖進高頻 limit cycle。

### 修法

Target 最快週期至少要 `10·tau`,理想是 `30·tau` 以上。

Sussillo & Abbott 2009 原 demo:
```python
# tau = 1 (in Sussillo's units), target 最快週期 = 30
# → 等效於 30·tau
freq = 1.0 / 60.0
target = (amp/1.0) * sin(1π·freq·t) + (amp/2.0) * sin(2π·freq·t) + ...
```

translated to my dt=1 ms, tau=10 ms:
```python
freq = 1.0 / 600.0           # 1 Lorenz unit = 600 ms 真實時間
# 4 個成分週期: 1200, 600, 400, 300 ms (= 120, 60, 40, 30 tau,夠慢)
```

---

## 失敗模式 3 — Target 振幅權重均等(harmonic content 太強)

### 現象

即使週期改慢了,還是收斂得慢。

### 病因

我用 `(sin(60) + sin(120) + sin(240) + sin(480)) / 4` 給每個頻率**均等振幅**。但 Sussillo 原 demo 用 **`(1, 1/2, 1/6, 1/3)` 的非均等權重**——高頻成分振幅較小,target 更平滑。

### 修法

```python
amp = 1.3
target = ((amp/1.0) * sin(1π·freq·t) +
          (amp/2.0) * sin(2π·freq·t) +
          (amp/6.0) * sin(3π·freq·t) +
          (amp/3.0) * sin(4π·freq·t)) / 1.5
```

---

## 失敗模式 4 — `update_every` 跟 `dt/tau` 不匹配

### 現象

訓練 MSE 看起來在學,但 W 怎麼調都不太對。

### 病因

Sussillo 原 paper 用 `dt = 0.1 (in tau units)` + `update_every = 2`,等效每 0.2 tau 更新一次 RLS。

如果你用 `dt = 1 ms, tau = 10 ms`(等效 `dt/tau = 0.1`),`update_every = 2` → 每 2 ms 才更新(每 0.2 tau),維持了 Sussillo 的相對更新頻率,**對的**。

如果你改成 `update_every = 1` → 每 0.1 tau 更新,**過頻繁**,RLS 反而不穩。

### 修法

保持 `update_every × (dt/tau)` 在 0.1-0.2 範圍。

---

## 失敗模式 5 — 訓練不足(Lorenz)

### 現象

Test 階段前 600 ms 紅線完美貼合灰線,**後段慢慢漂走**。

### 病因

FORCE 算法本身 work,但 `n_train_cyc` 太少,W 還沒完全 imprint 慢時間尺度的 dynamics。

### 修法

對 sinusoid mixture target(週期 1200 ms 為最慢):
- `n_train_cyc = 5` → 部分成功,後段漂
- `n_train_cyc = 15` → 完美 ✓
- `n_train_cyc = 30+` → 沒幫助,可能讓 W 緩慢退化

---

## 失敗模式 6 — FORCE-Output 對混沌 target 的天花板

### 現象

`n_train_cyc = 40` 反而比 `n_train_cyc = 20` **更糟**:
```
Cycle 2   MSE = 0.000004   |W| = 0.106   ← 最低
Cycle 20  MSE = 0.000207   |W| = 0.420
Cycle 40  MSE = 0.001068   |W| = 0.629   ← MSE 比最低時惡化 250 倍
```

### 病因

**這是 FORCE-Output + 混沌 target 的本質限制,不是 bug**:

- 對 sinusoid(週期性): 存在「完美的 W」,RLS 越訓練越接近
- 對 Lorenz(混沌): **根本不存在「完美的 W」**——任何 W 都只能近似 Lorenz vector field 的某個切片。RLS 永遠在切片之間飄移,訓練越久飄越遠

### 修法

**不要訓練太久**(`n_train_cyc ≈ 15-20`),接受 70-80% 品質。

或:**升級到 FORCE-Internal**(per-neuron RLS,訓練 J 而非 W),解析 vector field 的能力是 FORCE-Output 的 N 倍。

---

## 失敗模式 9 — FORCE-Internal 拿掉 feedback 會殺死 chaos ⭐⭐

### 現象 (v1 force_internal.py 的 bug)

執行 FORCE-Internal,console 顯示:
```
Cycle  1 (train)  MSE = 4.636738   |J|_norm = 0.7944   elapsed = 15s
Cycle  5 (train)  MSE = 2.508332   |J|_norm = 0.9973   elapsed = 73s
Cycle 15 (train)  MSE = 3.794889   |J|_norm = 1.1253   elapsed = 219s
Cycle 16 (test)   MSE = 3.068353   |J|_norm = 1.1253   elapsed = 219s
```

MSE 從沒掉到合理範圍 (理應 < 0.01),|J|_norm 長太慢 (理應到 ~2)。圖上 output 是**一條平直線** (z ≈ 1.65 常數),attractor 坍縮成一點。

### 病因

我寫 v1 時把 `w_fb · z` feedback 拿掉,以為 J 訓練後會自帶反饋。**這是錯的**。

對照 Sussillo 原 MATLAB code `FORCE_INTERNAL_ALL2ALL.m`:
```matlab
% Sussillo 原版 — 訓練期間 feedback 是保留的!
x = (1-dt)*x + M*(r*dt) + wf*(z*dt);   % wf*z 還在
```

**Feedback 不是 FORCE-Output 專屬**,它在 FORCE-Internal 訓練時**也是必要的**:
- 維持 chaotic regime,讓 RLS 有訊號可調
- 提供穩定的「驅動力」,網路才不會被 RLS 推進 fixed point
- J 是學「在 feedback 環境下產出 target」,**不是「取代 feedback」**

另一個 v1 缺陷:只訓 J 不訓 W。readout 從零開始 → 初始 z 太小 → error 太大 → RLS 用力修 J 把 chaos 滅了。

### 修法 (force_internal.py v2)

兩個修正同時做:
1. **保留 `x = x + (dt/tau) * (-x + J @ r + w_fb * z)` 的 feedback 項**
2. **同時訓練 W** (用 FORCE-Output 風格的 shared P_W 矩陣) + **訓練 J** (per-neuron P_J_list)

```python
# 保留 feedback
x = x + (dt/tau) * (-x + J @ r + w_fb * z)

# 訓練 W (FORCE-Output 風格)
Pr_W = P_W @ r
c_W = 1.0 / (1.0 + r @ Pr_W)
P_W -= c_W * np.outer(Pr_W, Pr_W)
W -= c_W * error * Pr_W

# 訓練 J 每一列 (FORCE-Internal 風格)
for cell in range(N):
    ... per-neuron RLS update ...
```

### 元教訓

**「演算法 X 的進階版」≠「移除演算法 X 的基本元件」**。
我直觀以為「FORCE-Internal 訓練 J 就不需要 feedback」,但這個直覺錯了。
正確理解:FORCE-Internal 是 FORCE-Output 的「**增量**」——把 J 訓練**加上去**,而不是**取代**任何東西。

---

## 失敗模式 10 — v2 仍然失敗:W 跟 J 同時從零學 chaos target ⭐⭐⭐

### 現象 (v2 跑下去之後,2026-05-16 凌晨那次)

`force_internal.py` v2 已經修了 v1 的 feedback bug,但 **test phase RNN output 仍然是一條水平線停在 z ≈ 1.66**。Target (Lorenz x) 標準化後振幅約 ±1.0,output 比 target 上界還高 → 網路正面 saturate、chaos 完全死掉。

訓練數字:
```
Cycle 15 (test)  MSE = 高,W 沒在動,J 被推離 chaotic regime
```

### 病因

**v1 → v2 的 fix(保留 feedback + 同時訓 W)沒解決根本問題。** 真正的根因:

- W 跟 J **同時從 0 開始學一個 chaos target**
- 前 ~100 步 error magnitude ~ O(1.7)(= target 振幅)
- per-neuron RLS 把這個 O(1.7) 的 error 灌進 J 的每一 row
- J 被快速推離 chaotic regime → reservoir 失去 ergodicity
- chaos 死後 RLS 看到的 r 不再 explore state space → W 也學不起來
- 最終網路收斂到 fixed point,readout saturate 在 ~1.66

Sussillo 原 paper Section "Learning the internal dynamics" 明確說: FORCE-Internal 的訓練起始條件是「W 已經被 FORCE-Output 訓練到網路會 generate target」,然後 J 才開始 fine-tune。v2 完全跳過這個前提。

### 修法 (v3 — phase split)

**Two-phase training:**

```python
W_only_cyc = 10   # 前 10 cycle 只訓 W (純 FORCE-Output)

for i in range(n_steps):
    x = x + (dt/tau) * (-x + J @ r + w_fb * z)
    r = np.tanh(x)
    z = float(W @ r)

    if i < train_steps and i % update_every == 0 and i > 0:
        error = z - target_all[i]

        # Phase 1 & 2 都更新 W
        Pr_W = P_W @ r
        c_W = 1.0 / (1.0 + r @ Pr_W)
        P_W -= c_W * np.outer(Pr_W, Pr_W)
        W -= c_W * error * Pr_W

        # Phase 2 才更新 J (i >= w_only_steps)
        if i >= w_only_steps:
            for cell in range(N):
                ... per-neuron RLS update ...
```

Phase 1 結束時 W 已 imprint 大部分 Lorenz vector field,error 降到 ~10⁻⁴,Phase 2 啟動 J 訓練時 error 已經很小,J 不會被拉爆。

### 元教訓

**「兩個學習機制都從 0 開始」≠「兩個學習機制協同」**。當 target 是混沌時,過大的初始 error 會讓 per-neuron RLS 主動破壞 reservoir 的 chaotic regime — 必須給 W 先機 warm-up,J 才能在小 error 下做 fine-tune。

---

## 失敗模式 11 — `LORENZ_SLOWDOWN` 太快,target 跑得比網路追得到的還快

### 現象

v2 用 `LORENZ_SLOWDOWN = 200` 對應 1 Lorenz time unit = 200 ms 真實時間。但 lorenz_output 版能跑出 70-80% 蝴蝶用的是 `LORENZ_SLOWDOWN = 400`。

問題疊加: v2 已經有 phase split 問題,**外加 target 比成功版快 2 倍**,訓練更難。

### 病因

跟失敗模式 2 同根: target 變化比 tau 快,網路追不到 → RLS 用更大力修 → J 偏離 chaotic regime 更快。

### 修法

對齊已知成功版:`LORENZ_SLOWDOWN = 400`(1 Lorenz time unit = 400 ms = 40 tau)。

---

## 失敗模式 12 — `n_test_cyc = 1` 太短,測試段沒跨 lobe 看不到蝴蝶

### 現象

v3 phase split 修好之後,左圖時序紅綠對齊得不錯(振幅 ±1 內),但右圖 attractor 只看到一個 lobe 在繞圈,**沒有蝴蝶結構**。

誤判: 以為訓練還是失敗。

### 病因

`n_test_cyc = 1` → 測試段只跑 1440 ms = 3.6 Lorenz time units。Lorenz lobe transition 平均間隔約 0.5-2 Lorenz time units,**3.6 個 Lorenz time units 不保證至少跨 lobe 一次**,尤其當初始相位剛好落在某個 lobe 的內部時。

更糟的是,你看時序圖 target (灰) 自己整段也只在單一 lobe 內振盪,所以連 target 都沒蝴蝶可看 — RNN 跟著 target 就也沒蝴蝶。**不是訓練失敗,是 test window 太短。**

### 修法

`n_test_cyc = 4` (~14 Lorenz time units),保證跨 lobe 多次。

### 判讀守則

> 看不到蝴蝶之前,先看 **target 自己** 在 test 段有沒有跨 lobe。target 沒跨,RNN 跨不出蝴蝶是物理必然,不是 RNN 的鍋。

---

## 環境設置坑

### 坑 7 — Anaconda base env DLL load failed

```
ImportError: DLL load failed while importing _multiarray_umath: 找不到指定的模組。
Python: Anaconda 3.9 from C:\Users\User\anaconda3\python.exe
NumPy: 1.21.5
```

**原因**: 用 PowerShell 直接打 `python` 沒先 `conda activate`,MKL DLLs 不在 PATH 裡。或 base env 本身受損。

**修法**: 別修 base env,直接建乾淨 env:
```
conda create -n force python=3.11 numpy matplotlib scipy -y
conda activate force
```

需要用 **Anaconda Prompt**(不是 PowerShell),除非 PowerShell 跑過 `conda init`。

### 坑 8 — Terminal 不是 Python REPL

使用者在 cmd 打:
```
n_train_cyc = 40
```
得到 `'n_train_cyc' 不是內部或外部命令`。

**原因**: cmd / PowerShell 是執行程式的地方,不是寫 Python 的地方。

**修法**: 改 `.py` 檔頂端的 const 區塊。用記事本/VS Code/Edit tool。

### 坑 13 — Windows cmd 預設 cp950 編碼,程式裡的 `≈` 直接讓 print 炸 ⭐

```
UnicodeEncodeError: 'cp950' codec can't encode character '≈' in position 54
```

**原因**: Windows 終端機預設用 cp950 (繁中 Big5),程式裡只要有 `≈ ° ① ② ...` 之類常見排版字元就會炸。

**修法**: 跑前設環境變數:
```cmd
set PYTHONIOENCODING=utf-8
python force_internal.py
```

或 PowerShell:
```powershell
$env:PYTHONIOENCODING = "utf-8"
python force_internal.py
```

或寫進 `.py` 開頭最早處:
```python
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

(本 skill 的所有 .py 不在程式內 wrap,因為這會破壞 IDE/Jupyter 行為。靠 `PYTHONIOENCODING` 環境變數最乾淨。)

### 坑 14 — Anaconda 壞了不要硬修,直接用 `uv venv` 起乾淨環境

```
ImportError: DLL load failed while importing _multiarray_umath: 找不到指定的模組。
```

Anaconda 的 numpy 經常因為 MKL 跟 OpenMP DLL 衝突而炸。**不要花時間修 base env**,直接:

```cmd
:: 安裝 uv (若沒有)
curl -LsSf https://astral.sh/uv/install.sh | sh

:: 在 skill 目錄起一個 venv
uv venv --python 3.12 .venv

:: 裝套件
uv pip install --python .venv\Scripts\python.exe numpy scipy matplotlib

:: 跑 script
set PYTHONIOENCODING=utf-8
.venv\Scripts\python.exe force_internal.py
```

uv 用 Astral 預先打包的 Python wheel,跟 Anaconda 完全獨立,不會撞 MKL DLL。

---

## Stage 4 fixed-point analysis 的特殊踩坑

Stage 4 (`stage4_fixed_points.py`) 對訓練好的 FORCE-Internal v3 做 Sussillo & Barak 2013 "Opening the Black Box" 分析。下面是這部分特有的坑。

### 坑 15 — 連續時間 vs 離散時間 eigenvalue 判讀 ⭐

`F(x) = -x + J·tanh(x) + w_fb·W·tanh(x)` 的 Jacobian eigenvalues 是 **連續時間** 的。

- **連續時間 stability boundary 是「虛軸 Re(λ)=0」**:Re(λ)>0 unstable, Re(λ)<0 stable
- **離散時間 stability boundary 是「單位圓 |λ|=1」**:|λ|>1 unstable

我第一版錯誤地在 eigenvalue plot 上畫了單位圓,這對 continuous-time Jacobian 是錯的判讀。

**修法**: 在 eigenvalue plot 上**只標 Re=0 的虛軸**,別畫單位圓。

### 坑 16 — Cluster `d_thresh` 取捨陷阱

L-BFGS 找到的 slow points cluster 半徑非常難調:

| d_thresh | 結果 | 問題 |
|---|---|---|
| 2.0 | 從 50 個搜尋只 cluster 成 1 個 unique | 太鬆,把不同 basin 的 slow points 都合併 |
| 0.5 | 從 200 個搜尋 cluster 成 124 個 unique | 太緊,同一個 slow manifold 上鄰近點被當不同點 |

**根因**: FORCE-Internal v3 學到的不是 isolated fixed points,而是 **slow manifold + 散布幾個強 saddle**。Slow manifold 上每個點 q 都很小,L-BFGS 把不同初始 guess 推到 manifold 上的不同位置,但這些都不是 "unique" fixed points。

**判讀守則**:
- 不要追求「找到 N 個 unique fixed points」這種離散答案
- 改看 **eigenvalue 結構**:多數 slow points 都有 2 unstable directions(spiral on manifold),少數有 8-26 unstable directions(true saddle,候選 lobe-switch trigger)
- 用 q histogram 看 q-landscape 是否 multi-modal (manifold 跟 saddle 對應不同峰)

### 坑 17 — RNN 沒有 isolated fixed points 是 feature,不是 bug

實測 FORCE-Internal v3 訓練後:
- 所有 L-BFGS 找到的「最低 q」都 ~10⁻⁵ ~ 10⁻⁶,**沒有真正 q < 10⁻⁷ 的純 fixed point**
- 這 **不是訓練不夠**,是 Sussillo & Barak 2013 對 Lorenz RNN 的核心觀察 — 混沌 task 的 RNN 用 **slow manifold + few saddles** 而非 isolated fixed points 編碼動力

**判讀守則**: 對混沌 target 的 RNN,把 `q_thresh` 從教科書 `1e-6` (fixed point) 放寬到 `5e-3` (slow point) 才看得到結構。

---

## 數字一張表

```
N=1000, g=1.5, p=0.1, tau=10ms, dt=1ms, alpha=1, update_every=2

Sinusoid target (週期 1200/600/400/300 ms, 振幅 1, 1/2, 1/6, 1/3)
    n_train_cyc = 15 → 完美 (test MSE < 0.005)

Lorenz target (FORCE-Output, SLOWDOWN=400)
    n_train_cyc = 40 → 70-80% (FORCE-Output 天花板)

Lorenz target (FORCE-Internal v3, N=800, SLOWDOWN=400)
    Phase 1 (W only, 10 cyc) + Phase 2 (W+J, 20 cyc) + Test (4 cyc)
    → 90%+ (paper Fig 3 品質,雙 lobe + saddle 結構)
    執行時間: ~6 分鐘
    輸出: force_internal_v3_state.npz (Stage 4 用)

Stage 4 fixed-point analysis (N=800, 200 個 L-BFGS 搜尋)
    執行時間: ~45 秒
    結果: ~120 unique slow points (manifold + ~20% saddle)
    Top 3 PC 解釋變異 ~ 81%
```

---

## 從這次 debugging 學到的元教訓

1. **不要相信「概念懂了」就「演算法懂了」**——讀過 paper 跟親手寫過差距巨大
2. **錯誤訊息常常誤導**,真正的病因往往在訊息描述的兩三層之上
3. **訓練 MSE 突然反升是強烈警訊**,不是隨機波動
4. **|W| 不收斂是診斷工具**,比 MSE 更早暴露問題
5. **混沌 target 的「成功」定義不同於週期 target**——attractor 拓樸符合 > point-by-point 重合
6. **FORCE 的真正創新在 RLS,不在 closed-loop feedback**——feedback 1980 年代就有了
7. **多階段學習機制不能同時從 0 啟動**——W 跟 J 要有先後 (v3 phase split),否則前期巨大 error 會自我破壞
8. **混沌系統不需要 isolated fixed points 來編碼**——slow manifold + saddle 就夠了,別硬找 q<1e-6 的點
9. **「output 是常數線」這個 signature 強指向「chaos 被殺死」**——別繼續調 RLS 參數,要回頭看 reservoir state
10. **看不到蝴蝶之前,先檢查 target 自己有沒有蝴蝶**——n_test_cyc 太短時 target 連 lobe 都沒跨,RNN 不可能有
