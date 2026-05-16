---
name: force-rnn-sim
description: "Use this skill to run FORCE algorithm RNN simulations from Sussillo & Abbott 2009 (Neuron) and Sussillo & Barak 2013 fixed-point analysis. Trigger whenever the user mentions 'FORCE algorithm', 'FORCE 演算法', 'FORCE simulation', 'Sussillo FORCE', 'chaotic RNN training', 'RLS recurrent network', 'fixed point analysis', 'opening the black box', or wants to train a recurrent neural network to produce a target dynamical pattern (sinusoid mixture or Lorenz attractor). Also trigger for: 'demo FORCE', '跑 FORCE', 'computational neuroscience RNN demo', 'reservoir computing demo', 'Lorenz attractor RNN', 'Stage 3 computational neuroscience', 'Stage 4 fixed point', 'slow manifold analysis'. Skill produces PNG figures. Four variants: sinusoid (FORCE-Output, ~30s), lorenz-output (FORCE-Output on chaotic target, ~30s), lorenz-internal (FORCE-Internal v3 phase-split, ~6min, matches paper Fig 3 with clean butterfly), fixed-points (Sussillo & Barak 2013 fixed-point analysis on trained v3 network, ~45s, requires v3 to have run first). Do NOT trigger for general RNN/LSTM training, gradient descent, BPTT, transformer training — this skill is specifically for FORCE/RLS-based recurrent training and its dynamical-systems analysis."
---

# FORCE RNN Simulation

訓練 chaotic recurrent neural network 用 FORCE algorithm (Recursive Least Squares + closed-loop feedback) 產生目標動力學。對應 Sussillo & Abbott 2009 *Neuron* paper 的最小可運行 demo。

---

## 🚨 鐵則

1. **零外部 LLM API 依賴** — 純 `numpy + scipy + matplotlib`,沒有任何 LLM 呼叫
2. **零捏造結果** — 圖跟數字都是真實 RLS 訓練計算出來的,不偽造收斂曲線
3. **必須先確認 Python 環境** — 啟動 conda env 之後才跑(見 Step 2)
4. **長時間任務(FORCE-Internal)前要告知** — 那個版本需要 2-5 分鐘,別讓使用者誤以為當機

---

## Step 1 — 詢問使用者要哪一個 demo

| 選項 | 對應 paper figure | 訓練時間 | 學習目標 |
|---|---|---|---|
| `sinusoid` | Sussillo & Abbott 2009 Fig 2 | ~30 秒 | 證明 FORCE-Output 可完美學會週期性 target |
| `lorenz-output` | Sussillo & Abbott 2009 Fig 3 (FORCE-Output 變體) | ~30 秒 | 看 FORCE-Output 在混沌 target 上的天花板 (~70-80%) |
| `lorenz-internal` | Sussillo & Abbott 2009 Fig 3 (paper 主要結果) | ~6 分鐘 | per-neuron RLS v3 (phase-split),paper 的乾淨 Lorenz 蝴蝶 |
| `fixed-points` | Sussillo & Barak 2013 Fig 2 風格 | ~45 秒 | 對 trained v3 網路做 slow point + Jacobian 分析,看 RNN 怎麼「算」Lorenz |

如果使用者沒指定 → 先做 `sinusoid`(最快、最容易驗證 FORCE 運作)。

`fixed-points` **必須**先跑過 `lorenz-internal` v3(產生 `force_internal_v3_state.npz`)才能跑。

> v3 vs 早期 v1/v2: 早期版本會在 chaos target 上 chaos 坍縮輸出常數線,v3 用 phase-split 解決(前 10 cycle 只訓 W,後續才訓 J)。詳見 PITFALLS 失敗模式 9 + 10。

---

## Step 2 — 確認執行環境

**首選: `uv venv` (跨平台、最乾淨,Anaconda 壞掉時的 fallback,實測 2026-05-16 OK)**

```cmd
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe numpy scipy matplotlib
```

跑 script 時:
```cmd
set PYTHONIOENCODING=utf-8
.venv\Scripts\python.exe force_internal.py
```

**Windows + Anaconda** (如果已有 `force` env 且沒壞):
```powershell
conda activate force
$env:PYTHONIOENCODING = "utf-8"
python force_internal.py
```

**驗證**:
```bash
python -c "import numpy, scipy, matplotlib; print('OK')"
```

如果 Anaconda 報 `ImportError: DLL load failed while importing _multiarray_umath`,別硬修 base env,直接用上面的 `uv venv`。詳見 PITFALLS 坑 14。

### ⚠️ Windows 必設 PYTHONIOENCODING=utf-8

script 裡有 `≈ ① ②` 之類字元,Windows cmd 預設 cp950 編碼會直接讓 `print` 炸:
```
UnicodeEncodeError: 'cp950' codec can't encode character '≈'
```

設環境變數 `PYTHONIOENCODING=utf-8` 是最乾淨修法(別在 .py 內 wrap stdout,會破壞 IDE/Jupyter)。

---

## Step 3 — 跑 script

```cmd
cd <skill-dir>
set PYTHONIOENCODING=utf-8
.venv\Scripts\python.exe force_sinusoid.py         :: 對應 sinusoid 選項
:: 或
.venv\Scripts\python.exe force_lorenz.py           :: 對應 lorenz-output
:: 或
.venv\Scripts\python.exe force_internal.py         :: 對應 lorenz-internal (v3)
:: 或 (前提:force_internal.py 已跑完,有 .npz 落地)
.venv\Scripts\python.exe stage4_fixed_points.py    :: 對應 fixed-points
```

每個 script 是獨立可跑的(除了 `stage4_fixed_points.py` 依賴 `force_internal.py` 產出的 `.npz`),參數寫死在檔案頂端的 const 區塊。

### 修改參數的方式

絕對**不要**叫使用者「在 terminal 打 `n_train_cyc = 20`」(cmd 不認得 Python 語法)。
正確做法:用編輯器或 Edit tool 改 `.py` 檔頂端的 const 區塊。

### 長任務時 — 用背景執行

`force_internal.py` 跑 6 分鐘,建議用 background run + monitor 過濾「Cycle / 完成 / Traceback」line。別讓使用者以為當機。

---

## Step 4 — 顯示產出的 PNG

每個 script 產出對應的 PNG (在執行目錄):

| Script | 輸出 PNG | 內容 |
|---|---|---|
| `force_sinusoid.py` | `force_sinusoid_demo.png` | 上:target vs output 重疊 / 下:test error |
| `force_lorenz.py` | `force_lorenz_demo.png` | 時間序列 + delay embedding 相圖 |
| `force_internal.py` | `force_internal_v3_demo.png` (+`.npz` state) | 時序 + 蝴蝶,應比 lorenz_output 乾淨 |
| `stage4_fixed_points.py` | `stage4_fixed_points_demo.png` | 4-panel: PC1-PC2 / PC1-PC3 / Jacobian eigenvalues / q histogram |

打開圖檔:
- Windows: `ii force_<...>_demo.png`
- Mac: `open force_<...>_demo.png`
- Linux: `xdg-open force_<...>_demo.png`

---

## Step 5 — 結果判讀引導

### sinusoid 成功標準
- Train MSE **單調下降** 到 ~10⁻⁵
- |W| 收斂
- Test MSE < 0.005
- 視覺:紅線整段覆蓋灰線,error 振幅 < 0.05

### lorenz-output 成功標準
- 時間序列前 ~200 ms 貼合,**後段 phase divergence 是正常**(混沌本性)
- 相圖紅色形狀大致接近黑色 Lorenz 蝴蝶,但會比較鬆
- **不要追求 point-by-point 重合**,attractor 拓樸對就算成功

### lorenz-internal (v3) 成功標準
- 跟 lorenz-output 同類型判讀,但相圖蝴蝶**明顯更乾淨**(主要視覺差異)
- Phase 1 (W only) MSE 收斂到 ~10⁻⁴
- Phase 2 (W+J) MSE 在 ~10⁻⁴ 量級不再下太多,但 |W| 持續成長到 ~0.5
- `|J|_norm` 從 0.168 微調到 0.169(**只動 0.7%,代表 chaotic regime 被保留** — 這正是 v3 phase split 的設計目標)
- Test MSE 在 cycle 32+ 衝到 ~0.2-0.5 看起來嚇人,但這是混沌 phase divergence 必然,**判讀看 attractor 而非 point-by-point**

### lorenz-internal 失敗的早期警訊
- **output 是水平線停在 ~1.66** → chaos 被殺死,確認 phase split 是否啟動(看 console 是否有 "P1 W" → "P2 WJ" 階段轉換)
- **看不到蝴蝶但時序紅綠對齊** → test window 太短,把 `n_test_cyc` 從 1 提到 4

### fixed-points 成功標準 (Sussillo & Barak 2013 風格)
- L-BFGS 多數能收斂到 q < 10⁻³ (slow points),**少數能到 10⁻⁵** (準 fixed)
- 但 **不會有 q < 10⁻⁷ 的真 fixed point** — 這是 feature,RNN 用 slow manifold 編碼混沌
- Slow points 多數有 **2 unstable directions, max Re(λ) ~ 0.02-0.05** (manifold 上的 weakly-unstable spiral)
- 少數有 **8-26 unstable directions, max Re(λ) ~ 0.15-0.40** (真 saddle, 候選 lobe-switch trigger)
- Top 3 PC 應解釋變異 ~ 80% (RNN trajectory 落在低維 manifold)
- Eigenvalue cloud 集中在 (Re≈-1, Im=0) (因為 F = -x + ... 主導項是 -x),但**有可觀 mass 跨過 Re=0 進入 unstable 區**

### fixed-points 失敗 / 不對勁的訊號
- **只找到 1 個 unique slow point** → cluster `d_thresh` 太鬆 (2.0 → 0.5),或 `n_init` 太少 (50 → 200,加 perturbation)
- **找到 100+ 個 unique** → cluster `d_thresh` 太緊或 manifold 在 RNN state space 真的很延伸 — 看 eigenvalue stability pattern 是否分群即可,別硬追離散答案

---

## Step 6 (選用) — 引導調參

常見問題見 `PITFALLS.md`。重點口訣:

- **Target 太快** → output 鎖高頻爆炸 → 把 target 週期改長到 ≥ 10·tau
- **訓練太久** → train MSE 反升 → 適度減少 `n_train_cyc`
- **混沌 target 加 FORCE-Output** → 永遠卡在 70-80% → 換 FORCE-Internal
- **|W| 或 |J| 失控** → 提高 `alpha` (RLS regularization)

---

## 跟其他 skill 的協作

- **knowledge-base**:結果與調參經驗可以寫進 Obsidian 第二大腦
- **article-writer**:結果可以擴寫成科普 / 教學文章
- **soil-teaching-deck**:可拿來做 computational neuroscience 課程簡報

---

## 不要做的事

1. **不要把 N 改超過 1500** — 會 OOM,FORCE-Internal 尤其
2. **不要在 PowerShell 直接打 `n_train_cyc = 20`** — 那是 Python 語法,cmd 會說「不是內部或外部命令」
3. **不要修改 RLS 更新公式** — 那是 paper 的核心,改了就不是 FORCE 了
4. **不要刪掉 `np.random.seed(42)`** — 重現性是這個 demo 的核心價值
5. **不要對 chaotic target(Lorenz)期待 point-by-point 重合** — 混沌系統理論上不可能
6. **不要把 v3 的 phase split 拿掉** — 移除 `W_only_cyc` 立刻 regress 回 v2 的 chaos 坍縮 bug
7. **不要硬修壞掉的 Anaconda** — 直接 `uv venv` 起乾淨環境,別花半天 debug MKL DLL
8. **不要在 fixed-point analysis 上畫單位圓 |λ|=1** — 連續時間 Jacobian 的 stability boundary 是虛軸 Re=0,不是單位圓
9. **不要追求 fixed-point analysis 找到 N 個 "unique" 點** — 混沌 RNN 的 slow manifold 在 N 維空間是連續的,離散答案是錯問題
