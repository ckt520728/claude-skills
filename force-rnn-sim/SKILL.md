---
name: force-rnn-sim
description: "Use this skill to run FORCE algorithm RNN simulations from Sussillo & Abbott 2009 (Neuron). Trigger whenever the user mentions 'FORCE algorithm', 'FORCE 演算法', 'FORCE simulation', 'Sussillo FORCE', 'chaotic RNN training', 'RLS recurrent network', or wants to train a recurrent neural network to produce a target dynamical pattern (sinusoid mixture or Lorenz attractor). Also trigger for: 'demo FORCE', '跑 FORCE', 'computational neuroscience RNN demo', 'reservoir computing demo', 'Lorenz attractor RNN', 'Stage 3 computational neuroscience'. Skill produces a PNG figure showing target vs trained network output. Three variants: sinusoid (FORCE-Output, ~30s), lorenz-output (FORCE-Output on chaotic target, ~30s), lorenz-internal (FORCE-Internal per-neuron RLS, ~3min, matches paper Fig 3). Do NOT trigger for general RNN/LSTM training, gradient descent, BPTT, transformer training — this skill is specifically for FORCE/RLS-based recurrent training."
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
| `sinusoid` | Fig 2 | ~30 秒 | 證明 FORCE-Output 可完美學會週期性 target |
| `lorenz-output` | Fig 3 (FORCE-Output 變體) | ~30 秒 | 看 FORCE-Output 在混沌 target 上的天花板 (~70-80%) |
| `lorenz-internal` | Fig 3 (paper 主要結果) | 2-5 分鐘 | per-neuron RLS,paper 的乾淨 Lorenz 蝴蝶 |

如果使用者沒指定 → 先做 `sinusoid`(最快、最容易驗證 FORCE 運作)。

---

## Step 2 — 確認執行環境

**Windows + Anaconda** (使用者已有 `force` env):
```powershell
conda activate force
```

**任何 Python ≥ 3.9 + 該 env 已有 numpy, matplotlib, scipy**:
```bash
python -c "import numpy, scipy, matplotlib; print('OK')"
```

如果環境不存在,引導使用者建立:
```
conda create -n force python=3.11 numpy matplotlib scipy -y
```

---

## Step 3 — 跑 script

```bash
cd <skill-dir>
python force_sinusoid.py      # 對應 sinusoid 選項
# 或
python force_lorenz.py        # 對應 lorenz-output
# 或
python force_internal.py      # 對應 lorenz-internal
```

每個 script 是獨立可跑的,參數寫死在檔案頂端的 const 區塊。

### 修改參數的方式

絕對**不要**叫使用者「在 terminal 打 `n_train_cyc = 20`」(cmd 不認得 Python 語法)。
正確做法:用編輯器或 Edit tool 改 `.py` 檔頂端的 const 區塊。

---

## Step 4 — 顯示產出的 PNG

每個 script 產出對應的 PNG (在執行目錄):

| Script | 輸出 PNG | 內容 |
|---|---|---|
| `force_sinusoid.py` | `force_sinusoid_demo.png` | 上:target vs output 重疊 / 下:test error |
| `force_lorenz.py` | `force_lorenz_demo.png` | 時間序列 + delay embedding 相圖 |
| `force_internal.py` | `force_internal_demo.png` | 同上,attractor 應更乾淨 |

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

### lorenz-internal 成功標準
- 跟 lorenz-output 同類型判讀,但相圖蝴蝶**明顯更乾淨**(主要視覺差異)
- Train MSE 不會像 FORCE-Output 那樣中途反升
- |J|_norm 應收斂

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
