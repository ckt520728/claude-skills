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

---

## 數字一張表

```
N=1000, g=1.5, p=0.1, tau=10ms, dt=1ms, alpha=1, update_every=2

Sinusoid target (週期 1200/600/400/300 ms, 振幅 1, 1/2, 1/6, 1/3)
    n_train_cyc = 15 → 完美 (test MSE < 0.005)

Lorenz target (SLOWDOWN=200)
    n_train_cyc = 15-20 → 70-80% (FORCE-Output 天花板)
    n_train_cyc = 40   → 退步 (over-training,W 飄遠)
    
Lorenz target with FORCE-Internal (N=800)
    n_train_cyc = 15 → 預期 90%+ (paper Fig 3 品質)
```

---

## 從這次 debugging 學到的元教訓

1. **不要相信「概念懂了」就「演算法懂了」**——讀過 paper 跟親手寫過差距巨大
2. **錯誤訊息常常誤導**,真正的病因往往在訊息描述的兩三層之上
3. **訓練 MSE 突然反升是強烈警訊**,不是隨機波動
4. **|W| 不收斂是診斷工具**,比 MSE 更早暴露問題
5. **混沌 target 的「成功」定義不同於週期 target**——attractor 拓樸符合 > point-by-point 重合
6. **FORCE 的真正創新在 RLS,不在 closed-loop feedback**——feedback 1980 年代就有了
