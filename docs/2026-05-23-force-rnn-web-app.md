# 2026-05-23 · 從 NotebookLM 到互動網頁：FORCE RNN 即時模擬平台

> 一次 session 的完整紀錄：把 Sussillo & Abbott (2009) 的 FORCE 演算法，
> 從 `force-rnn-sim` skill 的 Python/matplotlib 離線模擬，移植成**純原生 JS、
> 瀏覽器端 60fps 即時運行的單檔互動網頁**。
> 產出：[`force-rnn-sim/force_rnn_web_demo.html`](../force-rnn-sim/force_rnn_web_demo.html)
> **線上 demo（GitHub Pages）**：https://ckt520728.github.io/claude-skills/force-rnn-sim/force_rnn_web_demo.html

---

## 任務脈絡

使用者要求：
1. 用 notebooklm-mcp 開啟 NotebookLM 中 David Sussillo 的 notebook
2. 以一段詳細提示詞，建一個「具學術精度 + 視覺衝擊力」的互動式單檔網頁，
   即時模擬含 N 個非線性神經元的 chaotic RNN，展示 FORCE 演算法如何用 RLS 馴服混沌

關鍵差異點：skill 既有的是 **Python 離線模擬產 PNG**；這次要的是
**瀏覽器端即時互動**——兩者交付物完全不同，但**演算法核心必須一致**。

---

## 採用的方程式與參數（對齊 `force_sinusoid.py`）

```
前向動力學（Euler 積分）：
    x ← x + (dt/τ)·(−x + J·r + g_FB·w_fb·z)
    r = tanh(x)
    z = wᵀr

RLS 線上學習（每 2 步更新一次）：
    e⁻ = z − f(t)
    k  = P·r / (1 + rᵀ·P·r)
    P  ← P − k·(P·r)ᵀ
    w  ← w − e⁻·k
```

| 參數 | 值 | 來源 |
|---|---|---|
| τ（時間常數） | 10 ms | Sussillo 典型值 |
| dt（積分步長） | 1 ms | dt/τ = 0.1 |
| 連接稀疏度 p | 0.1 | 10% 連通 |
| J 標準差 | g/√(pN) | chaotic regime 縮放 |
| update_every | 2 | dt/τ × 2 ≈ 0.2，維持 Sussillo 相對更新頻率 |
| seed | 42 | 可重現 |

---

## 三個目標任務（皆週期性 → FORCE-Output 適用）

| 任務 | 目標訊號 | 意義 |
|---|---|---|
| ① 單一正弦 (1 Hz) | sin(2π·t/1000) | 動力系統基準 |
| ② 雙頻疊加 (1 + 2.5 Hz) | 0.8·sin1Hz + 0.5·sin2.5Hz | 多頻率高階動力學 |
| ③ ECG 節律 | P-QRS-T 五高斯合成，週期 1000 ms | 高非線性、不對稱、尖銳波峰 |

---

## 視覺化（原生 Canvas 2D）

1. **時域波形追蹤器**：target（灰）vs 輸出 z（青），兩者間以半透明紅色遮罩
   填滿瞬時誤差——直觀呈現一階誤差控制
2. **吸引子相位投影**：隨機正交投影矩陣（Gram-Schmidt）把 N 維 r 投到 2D，
   漸變褪色軌跡呈現混沌坍縮成極限環
3. **神經元放電柵欄圖**：前 20 個神經元 r∈[−1,1] 的滾動熱圖

**互動控制**：g (0.5–2.5)、g_FB、N、α；脈衝擾動鈕、解鉗 (closed-loop) 切換、重置。

---

## 踩到的坑 / 關鍵決策

### 坑 A — NotebookLM `notebook_query` 連續逾時
`mcp__notebooklm-mcp__notebook_query` 兩次都 `Request timed out`（120s / 300s）。
**決策**：不死等線上查詢，改以本地 `force-rnn-sim` skill 的
`force_sinusoid.py` + `PITFALLS.md` 作為演算法的權威來源。
→ 教訓：當 MCP 線上查詢不穩，手邊已驗證過的 skill 程式碼是更可靠的 ground truth。

### 決策 B — 用 FORCE-Output（只訓 W），不是 FORCE-Internal
三個任務都是**週期性** target，存在「完美的 W」，FORCE-Output 即可完美收斂。
依 `PITFALLS.md` 失敗模式 6：FORCE-Internal（訓 J）是為**混沌** target 設計的，
對週期 target 是殺雞用牛刀，且實作複雜度（per-neuron P 矩陣）高出 N 倍。

### 坑 C — 瀏覽器 60fps 的算力天花板 → N 上限
RLS 的 P 矩陣更新是 **O(N²)/步**。skill 用 N=1000（Python 離線可接受），
但純 JS 要維持 60fps 必須收斂規模。
**決策**：N 預設 220、上限 500。每幀跑 5 個積分步，P 更新每 2 步一次。

### 沿用 skill 的正確性鐵則（避免重蹈 PITFALLS 覆轍）
- **單一連續線上訓練，無 epoch boundary**（失敗模式 1）：網頁的 target 是
  「當前 simTime 代入 f(t)」，狀態與 target 永遠同步，不會出現 RLS 追逐 moving target。
- **target 週期 ≥ 10·τ**（失敗模式 2）：1Hz=1000ms=100τ、2.5Hz=400ms=40τ，皆遠 > 10τ。
- **feedback w_fb·z 必須保留**（失敗模式 9）：closed-loop 是 FORCE 精髓；
  「解鉗」按鈕只關 RLS 訓練，feedback 路徑保留，驗證網路能否自持續。
- **α ≥ 1**（TL;DR 條件 5）：α 滑桿下限設 0.25 並提示「過小會讓 |W| 暴增」。

---

## 成功判讀

- 任務①：紅/青線應在數秒內完全覆蓋灰線，即時 MSE 掉到 ~10⁻⁴ 量級，|W| 收斂
- 注入脈衝擾動後：相位軌跡被踢離流形，但應在數百 ms 內幾何收斂回吸引子（CTD 強韌性）
- 切到「解鉗」：訓練關閉後，網路僅靠 feedback 仍維持已學會的波形 = 自主閉環動力骨架成立

---

## 關聯

- skill：[`force-rnn-sim`](../force-rnn-sim/)（Python 離線版本 + 完整 PITFALLS）
- NotebookLM：`Neuro_David_Sussillo_大腦皮層動力學`（46 sources）
- 論文：Sussillo & Abbott (2009) *Neuron* — Generating Coherent Patterns of Activity from Chaotic Neural Networks
