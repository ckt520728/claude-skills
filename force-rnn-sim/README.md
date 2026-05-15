# force-rnn-sim

Sussillo & Abbott 2009 *Neuron* FORCE algorithm 的最小可運行 demo,三個變體一網打盡。

## 三個版本

| Script | 演算法 | Target | 時間 | Paper Fig |
|---|---|---|---|---|
| `force_sinusoid.py` | FORCE-Output | 4 sinusoid 混合 | ~30 秒 | Fig 2 |
| `force_lorenz.py` | FORCE-Output | Lorenz attractor x 分量 | ~30 秒 | (Fig 3 弱化版) |
| `force_internal.py` | **FORCE-Internal-RLS-N** | Lorenz attractor x 分量 | 2-5 分鐘 | **Fig 3** |

## 安裝

```bash
# 建立 conda env (推薦)
conda create -n force python=3.11 numpy matplotlib scipy -y
conda activate force

# 或用現有 Python ≥ 3.9 環境
pip install numpy matplotlib scipy
```

## 跑

```bash
python force_sinusoid.py
python force_lorenz.py
python force_internal.py
```

每個 script 跑完會在當前目錄產出對應的 PNG。

## 修改參數

**所有可調參數寫死在每個 `.py` 檔頂端的 const 區塊**。常用調整:

```python
N            = 1000     # 網路 unit 數 (force_internal 為 800)
g            = 1.5      # chaos gain (>1 進入 chaotic regime)
tau          = 10.0     # 時間常數 (ms)
alpha        = 1.0      # RLS regularization
n_train_cyc  = 15       # 訓練 cycle 數
LORENZ_SLOWDOWN = 200   # (Lorenz 版專屬) Lorenz 時間 vs 真實時間的比
```

用編輯器改檔(`notepad`、`code`、VS Code 任選),**不要**在 terminal 直接打 Python 賦值——那是 Python 語法,cmd 看不懂。

## 為什麼有 sinusoid vs lorenz vs internal 三個

- **sinusoid**: 證明 FORCE-Output 在週期 target 上可完美收斂(test MSE < 0.005)
- **lorenz** (FORCE-Output on chaos): 揭露 FORCE-Output 的天花板(70-80% 品質)
- **internal** (FORCE-Internal-RLS-N): paper Fig 3 真正的 Lorenz 蝴蝶,per-neuron RLS

跑完三個會對 FORCE algorithm 的「演算法選擇 ↔ target 性質」對應關係有清楚體會。

## 結果判讀

### Sinusoid

完美的長相:
- 紅線(network output)整段覆蓋灰線(target)
- 下半 error 振幅 < 0.05

### Lorenz (output 或 internal)

正確的判讀方式:
- **時間序列前 ~200 ms 貼合,後段 phase divergence 是正常**(混沌本性)
- **看 delay embedding 相圖的 attractor 形狀**,不是 point-by-point 重合
- 紅色蝴蝶愈接近黑色蝴蝶愈好,FORCE-Internal 會明顯比 FORCE-Output 乾淨

## 踩坑紀錄

完整 debugging 過程見 `PITFALLS.md`——6 個 failure mode + 環境設置坑 + 元教訓。

## 引用

Sussillo D, Abbott LF. Generating coherent patterns of activity from chaotic neural networks. *Neuron*. 2009;63(4):544-557. doi:[10.1016/j.neuron.2009.07.018](https://doi.org/10.1016/j.neuron.2009.07.018)

## 不是 bug,是 feature

`np.random.seed(42)` 寫死是故意的——讓所有跑出來的結果可重現。要看「隨機性敏感度」就把 seed 移掉重跑幾次。
