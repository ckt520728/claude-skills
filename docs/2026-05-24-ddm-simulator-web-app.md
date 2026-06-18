# 2026-05-24 · 從 Ratcliff 論文到瀏覽器互動 DDM 模擬器

> 一次 session 的完整紀錄：把 Ratcliff (2008/2014/2022) 系列的 Drift Diffusion Model，
> 從學術 SDE 公式移植成**單檔 HTML、瀏覽器即時跑 Monte-Carlo、4 panel Canvas 視覺化**
> 的互動 demo。
> 產出：[`ddm-simulator/ddm_simulator.html`](../ddm-simulator/ddm_simulator.html)
> **線上 demo（GitHub Pages）**：https://ckt520728.github.io/claude-skills/ddm-simulator/ddm_simulator.html

---

## 任務脈絡

使用者輸入：4 份 PDF（Ratcliff 2008 / 2014 / 2022 + Brown & Heathcote 2008 LBA）
+ 1 份合併文字摘要（已先把 DDM 數學、實驗、SDE 公式、scaling parameter、LCA 擴充
都萃取整理過）。

需求：
1. 做一個 two-choice, one-selection DDM 互動模擬器
2. 全部參數可調
3. 互動式網頁 + 部署到公開網站
4. 包成 skill 放進 GitHub `ckt520728/claude-skills`
5. Obsidian 第二大腦記錄踩坑

直接套既有 `force-rnn-sim` 的模式：skill 資料夾 + 單檔 HTML + GitHub Pages
serve + Obsidian 筆記。

---

## 採用的方程式（對齊 Ratcliff 2008）

### 核心 SDE
```
dx = v · dt + s · √dt · ε    (ε ~ N(0,1))
```
- 上邊界 a → correct，下邊界 0 → error
- 起始點 z = (z/a) · a
- RT = decision_time + Ter

### 跨試驗變異性（trial 開頭抽樣一次）
```
v_i  ~ Normal(v, η)
z_i  ~ Uniform(z − sz/2, z + sz/2)
Ter_i ~ Uniform(Ter − st/2, Ter + st/2)
```

### 數值方法
- Euler-Maruyama 法，dt = 1 ms
- Box-Muller transform 從 `Math.random()` 產生 normal（純 JS，零依賴）

| 參數 | 預設 | 來源 |
|---|---|---|
| v | 0.20 | Ratcliff 典型中等難度 |
| a | 0.12 | Ratcliff 2008 Exp 2 中位 |
| z/a | 0.50 | 無偏好基準 |
| Ter | 0.30 s | 年輕成人 dot-motion typical |
| η | 0.08 | Ratcliff 慣用範圍 |
| sz | 0.04 | a 的 33% |
| st | 0.10 s | typical |
| s | 0.10 | 縮放常數（Ratcliff 慣例） |
| dt | 1 ms | dt/τ relationships |
| N | 1500 | accuracy SE ≈ 1.3% |

---

## 6 個教學 preset（對應 Ratcliff 經典實驗）

| Preset | 主要改動 | 對應論文情境 |
|---|---|---|
| Easy stim | v = 0.35 | 高一致性點刺激 |
| Hard stim | v = 0.08 | 5% 一致性 |
| Speed instr | a = 0.08, sz = 0.06 | 2008 Exp 2 速度指令 → 看「快錯誤」反轉 |
| Accuracy instr | a = 0.18 | 2008 Exp 2 準確指令 |
| Prob. bias | z/a = 0.7 | probability manipulation |
| Aging | a = 0.18, Ter = 0.42, st = 0.14 | 2022 driving paper 老化 pattern |

---

## 視覺化（原生 Canvas 2D）

四個 panel 並列：

1. **證據累積路徑**：12 條 sample path，綠 = correct、紅 = error
2. **RT 分布鏡像 histogram**：上半綠 correct / 下半紅 error，25 ms bin
3. **分位數機率圖**：Ratcliff 標準 fitting 圖，.1 .3 .5 .7 .9 quantile
4. **心理測量函數**：sweep v ∈ [−0.4, 0.4]，每點 200 trial 即時計算

統計列表：accuracy / mean correct RT / mean error RT / 計算耗時（ms）。

---

## 踩到的坑 / 關鍵決策

### 坑 A — Across-trial 變異抽樣位置

第一直覺會想「在迴圈裡每步重抽 v」——但這違反 Ratcliff 數學。
**正解**：trial 開頭抽一次 `v_i, z_i, Ter_i`，整個 trial 用同一組。
within-trial 雜訊（`s · dW`）跟 across-trial 抽樣是**兩個獨立的雜訊源**。

### 坑 B — Box-Muller vs uniform

```js
// 錯：Math.random() - 0.5 ← 這是 uniform 不是 normal
// 對：Box-Muller
function randn() {
  let u = 0, v = 0;
  while (u === 0) u = Math.random();
  while (v === 0) v = Math.random();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}
```
注意 `Math.log(0)` 會 −∞，必須 `while (u === 0)` 重抽。

### 坑 C — sz 過大讓 z 超出 (0, a)

bias preset 加 sz 極大值時，`z_i` 可能 sample 出 ≤ 0 或 ≥ a，導致 trial 0 ms 就終止。
解法：`Math.min(a − ε, Math.max(ε, z_i))` clip。

### 坑 D — Canvas DPR

第一版在 Retina 螢幕上字糊。標準處方：
```js
const dpr = window.devicePixelRatio || 1;
cv.width = r.width * dpr;
cv.height = r.height * dpr;
ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
```

### 坑 E — 心理測量 sweep 卡 UI

11 點 × 200 trial 直接 for loop → 瀏覽器卡 3 秒。
解法：`setTimeout(step, 0)` 拆批 + token 機制讓舊掃描自動早退。

### 決策 F — 不 seed 隨機數

教學情境**故意**讓學生看 Monte-Carlo 變異。連點 Run 三次看趨勢，
而不是追求單次重現。

### 決策 G — 不實作 LBA / fitting

保持 single-purpose：純 DDM 教學 demo。
- Fitting 推薦 HDDM (Python) / DMAT (MATLAB) / fast-dm
- LBA 可考慮另開 skill（不在這次範疇）

### 決策 H — 縮放參數 s 留可調

知道 `s` 固定 0.1 是 Ratcliff 慣例。但**故意**留滑桿讓學生「親手踩 redundancy 坑」——
把 s 從 0.1 改到 0.2，會發現 accuracy 整個變——這正是 scaling property 的教學點。

---

## 跟 force-rnn-sim 的對照

| 面向 | force-rnn-sim | ddm-simulator |
|---|---|---|
| 領域 | RNN dynamical systems | Cognitive decision making |
| 演算法 | RLS + chaotic RNN | Euler-Maruyama + DDM |
| Paper figure 對齊 | Sussillo & Abbott 2009 Fig 2/3 | Ratcliff 2008 quantile prob plot |
| 即時互動 | 60 fps continuous training | 1500 trial 跑完 ~300 ms |
| 視覺化 | 時域 + 相圖 + 神經元 raster | sample path + RT histogram + QPP + psychometric |
| 教學 preset | 三任務切換 | 六種實驗條件 preset |
| 主要 pitfall | RLS 數值穩定性 | DDM 跨試驗變異性的位置 |

兩個 skill 共同模式：**「論文 SDE / RLS → 單檔 HTML + Canvas + GitHub Pages」**
已經是這個 repo 的標準工作流。

---

## 部署路徑

1. 建立 `ddm-simulator/` 資料夾，內含 `SKILL.md` / `README.md` / `PITFALLS.md` / `ddm_simulator.html`
2. `git add ddm-simulator/ docs/2026-05-24-ddm-simulator-web-app.md`
3. `git commit -m "feat(ddm-simulator): add Ratcliff DDM interactive simulator"`
4. `git pull --rebase origin master` → `git push origin master`
5. GitHub Pages 自動 serve → 線上 URL 立刻可用

---

## 開放問題

1. 要不要實作 LBA？需求出現再說，single-purpose 優先
2. 要不要做 csv upload + 真實資料 overlay？會偏離「教學 demo」定位
3. Web Worker 化？目前 N = 1500 的負載瀏覽器吃得下，先不做
4. Bayesian 後驗區間？同樣偏離教學定位，HDDM 已經處理得很好
