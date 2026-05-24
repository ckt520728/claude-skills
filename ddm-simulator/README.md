# DDM Simulator · Ratcliff Drift Diffusion Model

> 互動式網頁版漂移擴散模型，two-choice one-selection decision-making
> 全部 10 個參數可調，4 panel Canvas 即時視覺化，無依賴單檔 HTML

**線上 demo**：https://ckt520728.github.io/claude-skills/ddm-simulator/ddm_simulator.html

---

## 它是什麼

把 Ratcliff (2008, 2014, 2022) 系列論文裡的 DDM 數學，做成可以即時操控的瀏覽器互動模擬器：

1. 你拉動滑桿（drift v、boundary a、starting point z、non-decision Ter、跨試驗變異 η / sz / st…）
2. 瀏覽器立刻跑 1500 次 Monte-Carlo 試驗
3. 看到四張即時圖：sample path、RT 分布、分位數機率圖、心理測量函數
4. 旁邊顯示 accuracy / mean RT / 計算耗時

對應的學術需求：教 cognitive neuroscience、demo speed-accuracy tradeoff、檢查「快錯誤 vs 慢錯誤」的機制、老化決策研究的快速 sanity check。

---

## 為什麼做這個

傳統 Ratcliff DDM 在 fitting 端（DMAT、HDDM、fast-dm）有大量工具，但**前向模擬端缺少教學友善的互動工具**——大部分學生第一次接觸 DDM 是看靜態 path 圖或 MATLAB 老腳本。

這個 skill 想填的 gap：

- **零安裝**：丟個 URL 就能玩，學生不用裝 R / Python / MATLAB
- **參數即時對應視覺化**：拉 a 立刻看到 RT 拉長、accuracy 上升
- **內建 6 個 preset**：對應 Ratcliff 經典實驗條件（Easy / Hard / Speed / Accuracy / Bias / Aging）
- **顯式區分 η 與 sz**：兩個變異性參數的效應在 RT 分布上看得到差異（這是大部分課本不會展示的）

---

## 數學

### 核心 SDE（Stochastic Differential Equation）

```
dx = v · dt + s · √dt · ε   (ε ~ N(0,1))
```

- `x` 是累積證據，從 `z` 出發
- `a` 是上邊界（hit → correct），`0` 是下邊界（hit → error）
- `v` 是 drift rate（訊號強度）
- `s` 是 within-trial noise scaling（傳統固定 `s = 0.1`）

決策時間 = 撞邊界前的累積 t；總 RT = 決策時間 + Ter（非決策時間，編碼 + 運動）。

### 跨試驗變異性（across-trial）

每一個 trial **開始前**重抽：

```
v_i  ~ Normal(v, η)
z_i  ~ Uniform(z − sz/2, z + sz/2)
Ter_i ~ Uniform(Ter − st/2, Ter + st/2)
```

Ratcliff (2008) 證明：
- 沒有 η → 模型無法解釋「錯誤 RT > 正確 RT」
- 沒有 sz → 模型無法解釋「錯誤 RT < 正確 RT」
- 兩者並存 → 模型可同時解釋兩種錯誤速度模式

這就是為什麼 EZ-DDM 那種「沒變異性」的簡化版會擬合失敗的原因。

### 數值方法

用 **Euler-Maruyama 法**離散積分 SDE。每步 `dt = 1 ms`，標準 Ratcliff 設定。
Normal 隨機數用 **Box-Muller transform** 從 `Math.random()` 產生（pure JS，無依賴）。

```js
let x = z_i, t = 0;
const sqdt = Math.sqrt(dt);
while (t < maxT) {
  x += v_i * dt + s * sqdt * randn();
  t += dt;
  if (x >= a) return { rt: t + Ter_i, correct: true };
  if (x <= 0) return { rt: t + Ter_i, correct: false };
}
```

### 縮放唯一性

DDM 有 redundancy：同時放大 `(a, v, s)` 預測不變。所以**必須固定一個參數**才能比較。
本 simulator 把 `s` 留做可調，但**強烈建議固定 s = 0.1**（Ratcliff 慣例）。
所有 a / v / η 都是「相對於 s = 0.1」的數值。

---

## 可調參數一覽

| 參數 | 預設 | 範圍 | 意義 |
|---|---|---|---|
| `v` | 0.20 | [−0.5, 0.5] | drift rate（>0 偏好上邊界） |
| `a` | 0.12 | [0.05, 0.30] | boundary separation |
| `z/a` | 0.50 | [0.1, 0.9] | starting point 相對位置（0.5 = 無偏） |
| `Ter` | 0.30 s | [0.10, 0.60] | 非決策時間（編碼 + 運動） |
| `η` | 0.08 | [0, 0.20] | drift 跨試驗 SD |
| `sz` | 0.04 | [0, 0.08] | starting point 跨試驗 range |
| `st` | 0.10 s | [0, 0.30] | Ter 跨試驗 range |
| `s` | 0.10 | [0.05, 0.20] | within-trial noise scaling (固定建議) |
| `dt` | 1 ms | [0.5, 5] | 數值積分步長 |
| `N` | 1500 | [200, 5000] | 模擬試驗數 |

---

## 預設情境（Preset buttons）

- **Easy stim**：v = 0.35，高 drift，accuracy ~95%+
- **Hard stim**：v = 0.08，低 drift，accuracy ~60%
- **Speed instr**：a = 0.08，sz = 0.06，看「快錯誤」反轉
- **Accuracy instr**：a = 0.18，慢但準
- **Prob. bias**：z/a = 0.7，預期上邊界，error 變慢
- **Aging**：a = 0.18, Ter = 0.42, st = 0.14 — Ratcliff 2022 老化 driving paper 的核心參數 pattern（謹慎 + 動作慢，v 不一定降）

---

## 視覺化說明

### Panel 1 · 證據累積路徑
12 條 trial 的 x(t) 軌跡。綠線撞到上邊界 = correct，紅線撞到下邊界 = error。
水平虛黃線標示起始點 z，水平虛灰線標示上/下邊界。

### Panel 2 · RT 分布（mirror histogram）
上半部綠 = correct RT 分布，下半部紅 = error RT 分布（鏡像顯示）。
Bin 寬 25 ms。看尾巴的右偏（positive skew）就是 DDM 的招牌特徵。

### Panel 3 · 分位數機率圖（Quantile Probability Plot）
Ratcliff 的標準 fitting 圖。X 軸是 response probability，Y 軸是 RT 分位數。
每個 condition 在 X 軸上是兩根直線（correct = p，error = 1-p）。
五個分位數 .1 .3 .5 .7 .9 各畫一個點。

### Panel 4 · 心理測量函數
Sweep drift v ∈ [−0.4, 0.4]，每個 v 跑 200 trial，畫出 P(correct) vs v。
這對應 Ratcliff 2014 的天花板突破論點：當 v 大時 accuracy 飽和在 100%，
但 mean RT 仍持續下降——DDM 比 SDT 多測出一個維度。

---

## 三篇關鍵論文

| Paper | 對 simulator 的貢獻 |
|---|---|
| Ratcliff (2008) *Psychological Review* — A Theory of Memory Retrieval | DDM 主架構、speed-accuracy 設計、η + sz 必要性證明 |
| Ratcliff (2014) *Psychological Review* — Modeling response signal and response time data | DDM 突破 ceiling effects 的證據，validates psychometric function panel |
| Ratcliff (2022) | Aging on driving decisions — 提供 `Aging` preset 的參數依據 |
| Brown & Heathcote (2008) | LBA 替代方案（本 skill 未實作，預留擴充） |

---

## 不打算做的事

- **不做 fitting**：fitting 推薦用 HDDM (Python) / DMAT (MATLAB) / fast-dm
- **不做 LBA**：保持 single-purpose（DDM only），LBA 未來可考慮另開 skill
- **不做神經元層級擴充**：LCA / leaky accumulator 是另一個 skill 的範疇
- **不做 hierarchical Bayesian**：本 skill 是教學 demo，不是貝氏推論工具

---

## 致謝

- Roger Ratcliff（Ohio State）系列論文是整個 sequential sampling model 文獻的基石
- Scott Brown & Andrew Heathcote 的 LBA 是這個 simulator 未來的擴充方向
- 視覺化設計參考 Wagenmakers 實驗室常用的 quantile probability plot 風格

---

## License & 引用

如果你拿這個 simulator 上課或寫論文，請引用上述四篇論文。Simulator 本身採 MIT。
