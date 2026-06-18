# DDM Simulator · 開發踩坑與設計決策

> 把 Ratcliff DDM 從學術論文（離散公式 + 統計推論）移植成瀏覽器互動 demo 時，
> 數學上幾個必須要做的決策，跟容易被忽略的失敗模式。

---

## 坑 1 — 縮放屬性的歧義

**症狀**：教學時學生問「為什麼 a = 0.12，不是 1？」、「v = 0.2 是什麼單位？」

**根因**：DDM 有 mathematical redundancy——把 `(a, v, s)` **同時等比例放大**，
RT 分布跟 accuracy 預測完全不變。所以絕對數值沒有物理意義，是被縮放參數 `s` 決定的。

**解法**：
- **固定 `s = 0.1`** 作為縮放參數（Ratcliff 慣例）
- 所有其他參數的數值都是「相對 s = 0.1」
- README 與教學時要明說：「a = 0.12 是 1.2 × s 的距離」

如果使用者把 `s` 從 0.1 改到 0.2，**預期 a 也要相應放大才能維持同樣的 accuracy**——
這 simulator 把 s 留做可調是讓學生「直接踩這個坑」教學用的，不是建議生產時改。

---

## 坑 2 — dt 太大導致邊界擊中時間被高估

**症狀**：把 dt 從 1 ms 改到 5 ms，RT 整體變慢 30-50 ms，accuracy 也不對。

**根因**：Euler-Maruyama 法在 SDE 邊界吸收問題上有 O(√dt) 偏差。dt 越大，
模擬的 x(t) 越粗糙，撞邊界的「真正時間」被高估。

**解法**：
- 預設 `dt = 0.001 s`（Ratcliff 推薦）
- range cap 在 0.005 s
- 如果還想更精確，可以做 Brownian bridge correction，但對教學需求是 overkill

教學重點：dt 是**數值方法的細節**，不是模型參數——和 v / a / Ter 那種「有心理意義」的參數性質不同。

---

## 坑 3 — Box-Muller vs `randn` 的隱形錯誤

**症狀**：第一版用 `Math.random() - 0.5` 當隨機數，結果 RT 分布尾巴看起來「正常但太對稱」。

**根因**：`Math.random()` 是 uniform，不是 normal。DDM 的 SDE 需要 **Wiener process 增量**，
也就是 `dW ~ N(0, dt)`。用 uniform 會讓 RT 分布形狀錯誤（kurtosis 不對）。

**解法**：
- 用 **Box-Muller transform** 從兩個 uniform 產生一個 normal
- 注意 `Math.log(u)` 在 u = 0 時會炸——加 `while (u === 0) u = Math.random()`

```js
function randn() {
  let u = 0, v = 0;
  while (u === 0) u = Math.random();
  while (v === 0) v = Math.random();
  return Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
}
```

如果效能瓶頸（單檔 JS 不太可能），可以改 Ziggurat 算法，但對 1500 trials × 1000 step
的負載，Box-Muller 完全夠用。

---

## 坑 4 — Across-trial 變異性的順序錯誤

**症狀**：把 v / z / Ter 的抽樣放在「每步」而不是「每 trial」——RT 分布變得**過度平滑**，
失去 DDM 的特徵右偏。

**根因**：Ratcliff 的數學是 **trial-level mixture**——同一個 trial 內 v 不變、z 不變、Ter 不變，
變的是試驗之間。錯誤地放在 step level 等同於把雜訊「漂白」。

**解法**：
- 在 `simulateTrial()` 函式**最開頭**抽樣 `v_i / z_i / Ter_i`
- 然後整個 while loop 都用這組固定值
- across-trial 跟 within-trial noise（s · dW）是**兩個獨立的雜訊源**

這個 bug 不會 crash，只會讓視覺化變「太漂亮」——必須對照 Ratcliff 論文的 RT 分布形狀才會發現。

---

## 坑 5 — sz 太大導致 z 超出 (0, a) 範圍

**症狀**：用 `bias` preset（z/a = 0.7）再把 sz 拉到極大值（0.08），偶爾出現「trial 0 ms 就終止」的詭異 path。

**根因**：`z_i ~ Uniform(z − sz/2, z + sz/2)` 可能 sample 出 `z_i ≤ 0` 或 `z_i ≥ a`，
那 trial 在 t = 0 就直接「撞邊界」，RT 退化成純 Ter。

**解法**：
```js
const z_i = Math.min(p.a - 1e-4, Math.max(1e-4, z_mu + (Math.random() - 0.5) * p.sz));
```

加 clip 到 `(ε, a - ε)`。教學上要說明：**sz 應該 < min(z, a - z)**，否則 z 分布會 truncated。
Ratcliff 論文裡 sz 通常是 a 的 30-40% 上限。

---

## 坑 6 — Canvas DPI 沒設導致圖糊

**症狀**：Retina 螢幕 / 高 DPR Windows 機器上文字跟線條都糊掉。

**根因**：HTML 預設 `canvas.width = 300` 是 **CSS pixel**，不是 device pixel。
在 DPR = 2 的螢幕上，每個 CSS pixel 是 2×2 個物理 pixel，Canvas 內容會被瀏覽器
雙線性放大。

**解法**：
```js
const dpr = window.devicePixelRatio || 1;
const r = cv.getBoundingClientRect();
cv.width  = Math.floor(r.width  * dpr);
cv.height = Math.floor(r.height * dpr);
ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
```

額外加 `resize` 監聽器，視窗縮放時重畫。

---

## 坑 7 — 心理測量函數讓主執行緒卡死

**症狀**：第一版每改一次參數，掃描 v ∈ [−0.4, 0.4] 共 11 個點 × 200 trials × 1000 step，
瀏覽器卡 3-5 秒不能動。

**根因**：JS 是單執行緒，密集 for loop 會 block 整個 event loop。

**解法兩種**：
1. **降低樣本數**：心理測量函數每點只跑 200 trial（不像主圖跑 1500）
2. **`setTimeout(step, 0)` 拆批**：每跑完一個 v 就讓出主執行緒，讓 UI 有機會重繪

```js
function step() {
  if (myToken !== psyToken) return;   // newer request superseded us
  if (i >= vs.length) { drawPsy(...); return; }
  // run one v
  setTimeout(step, 0);
}
```

注意要 `myToken !== psyToken` 檢查——如果使用者快速連點 Run，舊的掃描要早退。

未來如果想撐更大 sweep，可以改 Web Worker，但對 200 × 11 = 2200 trial 用不到。

---

## 坑 8 — 隨機種子的取捨

**症狀**：使用者問「為什麼按 Run 兩次結果不一樣？」

**根因**：沒有 fix `Math.random()` 的 seed——JS 標準庫的 `Math.random()` 不能 seed。

**設計決策**：
- **不 seed**：教學情境下我們**要**讓學生看到 Monte-Carlo 的試驗變異——
  「即使參數一樣，每次 1500 trial 跑出來 accuracy 也會差 ±1-2%」
- 如果要 seed，可以引入 sfc32 / xoshiro128++ 等 PRNG 第三方算法（純 JS，~30 行），
  但會讓單檔變大且增加複雜度

教學時直接告訴使用者「按 Run 三次取趨勢，別追求單次重現」。

---

## 坑 9 — RT 分布 bin 太細 / 太粗

**症狀**：bin 寬 = 5 ms → 高度跳動劇烈，看起來像雜訊；bin 寬 = 100 ms → 整個分布變方塊圖。

**解法**：固定 25 ms bin（典型認知心理學報告的最小單位）。
未來可以做 adaptive bin width（Freedman-Diaconis 或 Scott's rule），但 25 ms 對 N = 1500 是好折衷。

---

## 坑 10 — GitHub Pages 路徑大小寫

**症狀**：本機 file:// 開可以，GitHub Pages 開 404。

**根因**：GitHub Pages（Linux 後端）區分大小寫。資料夾名 `DDM-simulator` vs URL `ddm-simulator` 會 fail。

**解法**：
- 資料夾、檔名**全小寫**（`ddm-simulator/`、`ddm_simulator.html`）
- URL 用 hyphen 連接，避免空白與底線混用

本 skill 一律 `ddm-simulator/ddm_simulator.html`，跟 force-rnn-sim 的 `force_rnn_web_demo.html` 風格一致。

---

## 設計決策速查

| 決策 | 選擇 | 為什麼 |
|---|---|---|
| 縮放參數 | 固定 s = 0.1（可調但建議鎖死） | Ratcliff 慣例 |
| 預設 N | 1500 trials | accuracy SE ≈ 1.3%，足夠教學 |
| dt | 1 ms 預設、5 ms 上限 | 平衡精度與速度 |
| 隨機種子 | 不 seed | 讓學生看 Monte-Carlo 變異 |
| RT bin | 25 ms 固定 | 認知心理學最小報告單位 |
| 心理測量點數 | 11 點 × 200 trial（拆 batch） | UI 不卡 |
| 視覺化框架 | 純 Canvas 2D（無 d3 / chart.js） | 零依賴 + 單檔交付 |
| 樣本路徑展示數 | 12 條 | 看得清楚但不混亂 |
| 老化 preset | a + Ter + st 同步上調 | 對應 Ratcliff 2022 driving paper |

---

## 還沒做但想做的擴充

1. **LBA 模式切換**：Brown & Heathcote (2008) 的多選項替代架構（4 panel 都要重畫）
2. **真實資料 overlay**：上傳 CSV，疊在 quantile probability plot 上對照
3. **參數對 RT 分布的 sensitivity heatmap**：在 v / a 平面上掃描，畫 accuracy 等高線
4. **Web Worker**：把 batch simulation 丟到 worker thread，UI 永不卡
5. **CSS dark/light mode 切換**：目前只有 dark
6. **fit-from-data**：給一組 RT，反推 v / a / Ter（這個會破壞「純教學 demo」的定位，慎重）

---

## 對照 force-rnn-sim 學到的事

1. **單檔 HTML 是最強的交付物**：不用 build、不用 server、雙擊就跑、可放 GitHub Pages
2. **Canvas 2D 對 4-panel 教學圖完全夠**：不用 d3 或 chart.js（依賴會讓單檔變幾百 KB）
3. **DPI 處理一定要先做**：不然 Retina 螢幕看起來像低解析度截圖
4. **GitHub Pages 路徑要全小寫 + hyphen**：跨平台一致最安全
5. **教學 preset 比文字說明有效 10 倍**：直接給 6 個 button 比寫 6 段文字好
