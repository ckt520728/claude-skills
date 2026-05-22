# force-rnn-sim

Sussillo & Abbott 2009 *Neuron* FORCE algorithm 的最小可運行 demo,加上 Sussillo & Barak 2013 fixed-point analysis,四個變體一網打盡。

## 四個版本

| Script | 演算法 | Target | 時間 | Paper |
|---|---|---|---|---|
| `force_sinusoid.py` | FORCE-Output | 4 sinusoid 混合 | ~30 秒 | Sussillo & Abbott 2009 Fig 2 |
| `force_lorenz.py` | FORCE-Output | Lorenz attractor x 分量 | ~30 秒 | (Fig 3 弱化版) |
| `force_internal.py` | **FORCE-Internal v3 (phase-split)** | Lorenz attractor x 分量 | ~6 分鐘 | **Fig 3 (paper 主結果)** |
| `stage4_fixed_points.py` | Fixed-point + Jacobian analysis | (讀 v3 訓練好的網路 state) | ~45 秒 | Sussillo & Barak 2013 |

## 互動網頁版 (純瀏覽器，免裝 Python)

`force_rnn_web_demo.html` — 單檔、零依賴、原生 JS 把 FORCE-Output 演算法做成瀏覽器端 60fps 即時互動：三任務 (1Hz 正弦 / 1+2.5Hz 雙頻 / ECG 節律)、時域誤差遮罩 + 隨機正交 2D 相位投影 + 神經元放電柵欄，可即時調 g / g_FB / N / α、注入脈衝擾動、切換 closed-loop。直接用瀏覽器開即可。

## 安裝

**首選 (Anaconda 壞掉時的 fallback,實測 OK):**
```cmd
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe numpy scipy matplotlib
```

**或用 conda:**
```bash
conda create -n force python=3.11 numpy matplotlib scipy -y
conda activate force
```

## 跑

```cmd
set PYTHONIOENCODING=utf-8
.venv\Scripts\python.exe force_sinusoid.py
.venv\Scripts\python.exe force_lorenz.py
.venv\Scripts\python.exe force_internal.py
:: 前面 force_internal.py 跑完會留 force_internal_v3_state.npz,fixed-point 需要它
.venv\Scripts\python.exe stage4_fixed_points.py
```

**Windows 必設 `PYTHONIOENCODING=utf-8`** — cmd 預設 cp950 編碼,script 裡的 `≈ ① ②` 之類字元會讓 `print` 直接炸。

每個 script 跑完會在當前目錄產出對應的 PNG。

## 修改參數

**所有可調參數寫死在每個 `.py` 檔頂端的 const 區塊**。常用調整:

```python
N            = 1000     # 網路 unit 數 (force_internal 為 800)
g            = 1.5      # chaos gain (>1 進入 chaotic regime)
tau          = 10.0     # 時間常數 (ms)
alpha        = 1.0      # RLS regularization
n_train_cyc  = 30       # 訓練 cycle 數 (v3: 30, 早期版本只用 15)
W_only_cyc   = 10       # (force_internal v3 專屬) Phase 1 只訓 W 的 cycle 數
LORENZ_SLOWDOWN = 400   # (Lorenz 版) Lorenz 時間 vs 真實時間的比
n_test_cyc   = 4        # 測試 cycle 數 (v3.1: 4,夠看到 lobe transition)
```

用編輯器改檔(`notepad`、`code`、VS Code 任選),**不要**在 terminal 直接打 Python 賦值——那是 Python 語法,cmd 看不懂。

## 為什麼有四個版本

- **sinusoid**: 證明 FORCE-Output 在週期 target 上可完美收斂 (test MSE < 0.005)
- **lorenz** (FORCE-Output on chaos): 揭露 FORCE-Output 的天花板 (70-80% 品質)
- **internal** (FORCE-Internal v3): paper Fig 3 真正的 Lorenz 蝴蝶,per-neuron RLS + phase split
- **fixed-points** (Sussillo & Barak 2013): 「打開黑箱」— 看 trained RNN 用什麼 attractor 結構編碼 Lorenz

跑完前三個會對「演算法選擇 ↔ target 性質」對應關係有清楚體會;再跑第四個會對「混沌 RNN 不用 isolated fixed points,而是用 slow manifold + saddles」有第一手實感。

## 結果判讀

### Sinusoid

完美的長相:
- 紅線(network output)整段覆蓋灰線(target)
- 下半 error 振幅 < 0.05

### Lorenz (output 或 internal)

正確的判讀方式:
- **時間序列前 ~1500 ms 貼合,後段 phase divergence 是正常**(混沌本性)
- **看 delay embedding 相圖的 attractor 形狀**,不是 point-by-point 重合
- 紅色蝴蝶愈接近黑色蝴蝶愈好,FORCE-Internal v3 會明顯比 FORCE-Output 乾淨
- **看不到蝴蝶之前先檢查 target 自己**:若 `n_test_cyc=1` 連 target 都沒跨 lobe,RNN 不可能有蝴蝶

### Fixed-points (Stage 4)

- 不會有 q < 10⁻⁷ 的真 fixed point — 這是 feature,RNN 用 slow manifold 編碼
- 多數 slow points: 2 unstable directions, max Re(λ) ~ 0.02-0.05 (manifold spiral)
- 少數 saddles: 8-26 unstable directions, max Re(λ) ~ 0.15-0.40 (lobe-switch triggers)
- Eigenvalue cloud 在 (Re≈-1, Im=0) 為中心,但跨過 Re=0 進入 unstable 區

## 踩坑紀錄

完整 debugging 過程見 [`PITFALLS.md`](./PITFALLS.md) — 累積 12 個 failure mode + 4 個環境坑 + 3 個 Stage 4 特殊踩坑 + 元教訓 10 條。

最重要的三個:
- **失敗模式 9 (v1 → v2)**: FORCE-Internal 拿掉 `w_fb·z` feedback 會殺死 chaos
- **失敗模式 10 (v2 → v3)**: W 跟 J 同時從 0 學 chaos target,J 被巨大初期 error 拉爆 → phase split 解決
- **失敗模式 12**: `n_test_cyc=1` 太短連 target 都沒跨 lobe,看不到蝴蝶不是訓練失敗

## 引用

- Sussillo D, Abbott LF. Generating coherent patterns of activity from chaotic neural networks. *Neuron*. 2009;63(4):544-557. doi:[10.1016/j.neuron.2009.07.018](https://doi.org/10.1016/j.neuron.2009.07.018)
- Sussillo D, Barak O. Opening the black box: low-dimensional dynamics in high-dimensional recurrent neural networks. *Neural Comput*. 2013;25(3):626-649. doi:[10.1162/NECO_a_00409](https://doi.org/10.1162/NECO_a_00409)

## 不是 bug,是 feature

`np.random.seed(42)` 寫死是故意的——讓所有跑出來的結果可重現。要看「隨機性敏感度」就把 seed 移掉重跑幾次。
