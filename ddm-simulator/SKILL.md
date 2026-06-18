---
name: ddm-simulator
description: "Use this skill to launch an interactive browser-based Drift Diffusion Model (DDM) simulator for two-choice, one-selection decision making. Trigger whenever the user mentions 'DDM', 'drift diffusion model', 'Ratcliff model', '漂移擴散模型', 'two-choice decision', 'sequential sampling model', 'response time distribution', 'speed-accuracy tradeoff', 'quantile probability plot', 'psychometric function from RT', or wants to demonstrate / teach how trial-by-trial noise + drift produces accuracy and RT distributions. Also trigger for: 'Ratcliff 2008', 'Ratcliff 2014 ceiling effects', 'Ratcliff 2022 aging driving', 'fast vs slow errors', 'how does drift rate affect RT', 'simulate decision making in browser'. Skill opens a single self-contained HTML page with sliders for v, a, z, Ter, η, sz, st, s, dt, N — and live Canvas plots of sample paths, mirror-RT histogram, quantile probability plot, and psychometric function. Already deployed on GitHub Pages — share the URL directly. Do NOT trigger for LBA-only multi-choice tasks, hierarchical Bayesian DDM fitting (HDDM), neural recordings analysis, or non-decision-making RT modeling."
---

# DDM Simulator · Ratcliff Drift Diffusion Model 互動模擬器

單檔 HTML（自含 CSS + JS），瀏覽器即時跑 Monte-Carlo 模擬，可調全部 10 個參數，
4 panel Canvas 視覺化。對應 Ratcliff 2008/2014/2022 系列論文的最小可操作 demo。

---

## 🚨 鐵則

1. **零外部依賴** — 純原生 JS，無 npm、無 build、無 framework，雙擊 HTML 就跑
2. **零數值偽造** — 所有圖跟數字都來自即時 Box-Muller + Euler-Maruyama 數值積分
3. **預設可重現** — 沒鎖 seed（教學需要看 noise），但同樣參數 N=1500 試驗下統計收斂良好
4. **不要把 dt 改超過 5 ms** — 邊界擊中精度會崩壞（Ratcliff 推薦 dt = 1 ms）

---

## Step 1 — 詢問使用者想看什麼

| 情境 | 建議 preset | 重點 |
|---|---|---|
| 我想看 DDM 怎麼跑 | `Easy stim` (預設) | 高 drift，看 path 衝上邊界 |
| 速度-準確權衡 | `Speed instr` vs `Accuracy instr` | 改的是 a，不是 v |
| 機率偏誤 | `Prob. bias (z↑)` | z/a > 0.5 → 偏好上邊界 |
| 老化 (2022 driving paper) | `Aging (a↑, Ter↑)` | 老人主要 a↑、Ter↑，v 不一定降 |
| 快錯誤 vs 慢錯誤 | 改 η vs sz | η↑ → 慢錯誤；sz↑ → 快錯誤 |

如果使用者沒指定 → 直接開預設（Easy stim），讓他自己玩。

---

## Step 2 — 開啟模擬器

**本機開啟**：
```powershell
ii ddm_simulator.html
```

**線上版（已部署）**：
https://ckt520728.github.io/claude-skills/ddm-simulator/ddm_simulator.html

雙擊就能用，不需要 dev server。任何瀏覽器（Chrome / Edge / Firefox / Safari）都支援，
推薦螢幕寬度 ≥ 1200px（兩欄 canvas 佈局）。

---

## Step 3 — 解讀四個 panel

| Panel | 內容 | 觀察重點 |
|---|---|---|
| 證據累積路徑 | 12 條 sample path | 綠 = 撞上邊界（correct）、紅 = 撞下邊界（error） |
| RT 分布 | 鏡像 histogram (25 ms bin) | 上半綠 = correct RT，下半紅 = error RT |
| 分位數機率圖 | .1 .3 .5 .7 .9 分位數 | X = response probability，Y = RT quantile |
| 心理測量函數 | sweep v ∈ [−0.4, 0.4] | 每點 200 trial，黃線 = 當前 v 位置 |

統計列出：accuracy / mean correct RT / mean error RT / N + 計算時間（ms）。

---

## Step 4 — 引導探索（核心教學點）

1. **drift rate v** — 唯一影響「知覺品質」的參數
   - v 加倍 → accuracy 飆升、RT 分布尾巴變短
   - Ratcliff 2014 重點：v 在天花板區仍持續上升，突破 SDT 的盲區

2. **boundary a** — 速度-準確權衡
   - a↑ → 更慢但更準（要累更多證據才下決定）
   - Ratcliff 2008 Exp 2：speed instruction 唯一改的就是 a

3. **starting point z** — probability bias
   - z/a 從 0.5 移到 0.7 → 偏好上邊界，error RT 變慢
   - 這對應「預期某邊機率高」的決策偏誤

4. **跨試驗變異 η, sz, st** — 解 RT 模型最棘手的問題
   - 只調 η：錯誤 RT 變慢（典型）
   - 只調 sz：錯誤 RT 變快（快錯誤反轉，常見於 speed 條件）
   - 兩者並存 → 解釋為什麼有時錯誤快、有時錯誤慢

5. **Ter** — 非決策時間（編碼 + 運動）
   - 純粹 shift 整個 RT 分布，不改變形狀
   - Ratcliff 2022：老化主要影響的不是 v，而是 Ter 與 a

---

## Step 5 — 跟其他 skill 的協作

- **knowledge-base / Obsidian**：把參數實驗心得寫進第二大腦
- **article-writer**：擴寫成科普文章或教學文
- **soil-teaching-deck**：拿截圖做 cognitive neuroscience 課程簡報
- **force-rnn-sim**：兩者都是「行為理論 → 即時瀏覽器互動」的範例

---

## 不要做的事

1. **不要把 dt 改超過 5 ms** — 邊界擊中精度崩壞，RT 會被高估
2. **不要把 N 改超過 5000** — 瀏覽器會卡 2-3 秒（純 JS 單執行緒）
3. **不要把 s 改超過 0.2** — 數值會炸（Ratcliff 慣例固定 s = 0.1）
4. **不要把 a 設得比 sz 還小** — z 抽樣會超出 (0, a) 範圍（程式有 clip，但會失真）
5. **不要對單次模擬下定論** — 即使 N = 1500，標準誤仍 ~ ±1.3% accuracy；要對比就連跑 3 次取趨勢
6. **不要在 GitHub Pages 連結直接展示「絕對 RT 數值符合某老化研究」** — DDM 是相對參數比較工具，絕對值依賴 s 縮放

---

## 數學參考

詳見 [README.md](README.md)；常見坑詳見 [PITFALLS.md](PITFALLS.md)。

論文鏈：
- Ratcliff (2008) *Psych Rev* — DDM 基礎 + speed-accuracy
- Ratcliff (2014) *Psych Rev* — DDM 突破 ceiling effects
- Ratcliff (2022) — aging on driving decisions
- Brown & Heathcote (2008) — LBA 替代架構（未實作於本 skill）
