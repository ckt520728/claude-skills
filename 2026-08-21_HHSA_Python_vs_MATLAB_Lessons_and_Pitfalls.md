# 專案收尾 — Python 版與 MATLAB 版 HHSA 比較：踩過的坑與可重用做法

**專案：** 2026 CGMS × HHSA — 用模擬腦波與真實 CGM 紀錄，比較 HHSA 的 Python 實作與 MATLAB 參考規格
**日期：** 2026-08-21（單一工作階段）
**成果：** 一份可歸因的比較報告 + 一套 Octave/MATLAB 版 HHSA 核心 + `hhsa-python-vs-matlab/` 資料夾
**環境：** Windows 11、Git Bash / PowerShell 5.1、Python 3.11.15（專屬 venv）、GNU Octave 11.3.0、Claude Code

> **語言說明：** 本檔採繁中撰寫（同 `CLAUDE.md`），檔名沿用 repo 既有的
> `YYYY-MM-DD_*_Lessons_and_Pitfalls.md` 命名慣例。

> **去識別化聲明：** 本 repo 為公開。CGM 個案的姓名、裝置序號、報告編號與確切日期
> 一律不出現；**原始 PDF 與還原後的 CSV 不進 repo**，`data/` 全部排除。IMF 圖與
> 統計量沿用 `2026-08-20` 那次的判準（以「recording day/hour」為時間軸，不用日曆日期）。

---

## 零、一句話總結

**「MATLAB 版和 Python 版一不一樣？」問成一個數字是沒有答案的。** 兩者同時差在五個
地方，任何單一相似度都無法解讀。真正有用的做法是把它拆成**一次只改一件事的階梯**，
然後才發現：影響最大的那一項，**原始論文根本沒有寫**。

| # | 發現 | 證據等級 |
|---|---|---|
| 1 | 兩套程式碼實作的是同一個 EMD——設定對齊後 98.4–100 % 變異數落在 \|r\| ≥ 0.9 的對應模態 | `observed` |
| 2 | 影響最大的單一因素是 amplitude normalisation 用哪種 spline——**未被任何文獻指定** | `observed`，4.25 × 10⁶ 倍振幅膨脹 |
| 3 | 乾淨模擬訊號兩者一致；真實 CGM 上**沒有任何一個模態一致** | `observed`，能量加權匹配率 0.0 % |
| 4 | Python 版的 `holo_spectrum()` 沒有時間軸，是**功能缺口**不是數值差異 | `derived` |

---

## 一、產出了什麼

- `hhsa-python-vs-matlab/matlab/` — 15 個 `.m` 檔，依 Nguyen 2019 supplement + `neuroholo_bak.m`
  規格寫成的 HHSA 核心：masking EMD、natural spline、normalized Hilbert、二層 holo-spectrum。
  Octave 與 MATLAB 皆可執行。
- `hhsa-python-vs-matlab/work/compare.py` — attribution ladder、IMF 對應、ground-truth 回收率。
- `hhsa-python-vs-matlab/assets/` — 6 張圖；`results/` — 全部數字的機器可讀版本。
- 完整報告（英文，含出處表與限制）：Google Drive 工作資料夾
  `Working/PyMatlab_HHSA_comparison_20260821/HHSA_Python_vs_MATLAB_comparison.md`。

---

## 二、最重要的一件事

**先證明兩套程式一樣，才有資格說兩套方法不同。**

第一輪比較出來的 cosine similarity 有一半是 0.000。看起來像 bug，也可能是真的發散，
但**當下無法區分**——因為兩邊同時差在 masking EMD、spline 家族、envelope 建法、
admissibility、格線五件事。

解法是先做「同構驗證」：把 MATLAB 端的 sifting spline 與 normalisation 都設成
Python 的做法，然後比對 layer-1 IMF。結果 CGM 的 6 個模態全部對應到 r = 0.962–1.000，
EEG 模擬 98.4–99.9 %。到這一步才能寫下那句關鍵的話：

> 以下所有差異都是**方法**的差異，不是任何一邊寫錯。

沒有這一步，整份報告就只是「兩個數字不一樣」。

---

## 三、遇到的坑（以及各自換來的規則）

### A. 環境與前置

**1. 「有 skill 資料夾」不等於「有可以跑的程式」。**
`Working/NCU_Neuroholo/` 看起來是完整的 MATLAB skill，實際上只有 6623 行 GUIDE
GUI；它呼叫的四個核心函式（`eemd2layer_tf`、`holo_eeg_tf`、`eemd1_tf`、`hht_eeg_tf`）
整台機器都找不到。
*規則：拿到 MATLAB 專案，第一件事是 grep 出「被呼叫但不存在」的函式。*

```bash
grep -oE "\b[a-z_0-9]+\(" *.m | sort -u   # 再逐一比對有沒有對應的 .m
```

**2. MATLAB 裝著不等於能跑。**
`D:\Matlab` 有 R2022b，`matlab -batch` 直接吐 *License Manager Error -10（授權過期）*。
*規則：任何「跑 MATLAB 版」的任務，先 `matlab -batch "disp(1)"` 確認能啟動，再規劃工作。*
這兩件事合起來讓「執行原作者程式」從一開始就不可能——**及早發現，就有時間換方法論**。

**3. winget 下載失敗 ≠ 套件拿不到。**
`winget install GNU.Octave` 從 `ftpmirror.gnu.org` 抓檔回 **502 Bad Gateway**，而且
**exit code 仍然是 0**。改成直接抓 `https://ftp.gnu.org/gnu/octave/windows/...`（567 MB）
再用 NSIS 靜默安裝就成功。
*規則：winget 失敗先換 mirror，不要換方案。另外，winget 的 exit code 不可信，要看輸出。*

**4. NSIS 的 `/D=` 可能被忽略。**
指定 `/D=C:\Users\User\Octave`，實際裝到 `C:\Program Files\GNU Octave\Octave-11.3.0\`。
*規則：安裝後一律 `find` 確認實際路徑，不要用假設的路徑寫進腳本。*
可執行檔在 `mingw64/bin/octave-cli.exe`，不是資料夾根目錄那幾個 `.exe` / `.vbs`。

**5. Octave 沒有 `signal` package，`hilbert` 不存在。**
*規則：核心變換自己寫。* 十行 FFT 就有解析訊號，而且順便消掉「兩邊用了不同函式庫」
這個混淆因子——這反而讓比較更乾淨。

**6. venv 沒有 pip。**
`python -m pip` → `No module named pip`。*規則：* `python -m ensurepip --upgrade`。

**7. Anaconda base 的 NumPy/SciPy 配對是壞的。**
NumPy 2.0.2 對上要求 `<1.23` 的 SciPy，import 就警告加失敗。
*規則：這個專案一律用 `C:\Users\User\.venvs\hhsa-amfm\`（3.11.15 / NumPy 2.3.2 / SciPy 1.16.1）。*

**8. Git Bash 把 CJK 絕對路徑當參數傳會亂碼。**
`python -c "...open(r'/g/我的雲端硬碟/...')"` → `FileNotFoundError: '/g/?ڪ????ݵw??/...'`。
`cd "/g/我的雲端硬碟/..."` 本身沒問題，壞掉的是**當作參數傳進去**那一段。
*規則：先 `cd` 進目錄，再用相對路徑。*

**9. 用 shell heredoc 寫程式檔，跳脫序列會被吃掉。**
`print('... only.\n')` 寫進檔案變成真的換行 → `SyntaxError: unterminated string literal`。
同一輪還遇到 heredoc 整段莫名 `unexpected EOF`。
*規則：程式檔用 Write 工具寫，不要用 shell heredoc；heredoc 只留給不含跳脫序列的短片段。*

### B. 方法學（這幾條最貴）

**10. 一次只改一件事，否則無法歸因。**
第一版把 natural spline 用在**所有地方**（sifting、normalisation、envelope），
結果 cosine 掉到 0.000，但完全不知道是哪一項造成的。
*規則：把每個「文獻沒有釘死」的選擇做成參數，然後跑階梯。* 最後的排序是：

| 步驟 | 改動 | cosine | 判定 |
|---|---|---|---|
| 1 | amplitude normalisation 的 spline | 0.00 – 0.96 | **決定性，而且沒人寫過** |
| 4 | layer-2 envelope 建法 | 0.11 – 0.86 | 大，文獻有指定 |
| 2 | masking EMD ↔ plain EMD | 0.11 – 0.84 | 大，文獻有指定 |
| 3 | sifting spline 端點條件 | 0.96 – 1.00 | 可忽略 |
| 5 | admissibility `f_am < f_c` | 0.999 – 1.000 | 可忽略 |

這張表是整個專案的產出核心。沒有階梯，就只有「0.000」這個沒有意義的數字。

**11. natural cubic spline 做 amplitude normalisation 會炸掉六個數量級。**
同一個 IMF，`max|c| = 1.373`；PCHIP 正規化後 `max A = 1.373`，natural spline 正規化後
`max A = 5.84 × 10⁶`——**4.25 × 10⁶ 倍**，集中在四個局部爆點。那四個點接著主宰了整張
marginal spectrum（總能量 4.6 × 10¹¹ vs 1.7 × 10³）。
*規則：normalisation 用 shape-preserving 內插（PCHIP）；若堅持用 cubic spline，
必須報 `max A / max|IMF|` 這個比值當 sanity check。*
`hhsa.py` 的 `_envelope_pos` docstring 早就寫過這件事，這次是把它量化成數字。

**12. 沒被文獻指定的選擇，反而影響最大。**
Nguyen supplement 明確指定了 masking EMD 與 natural spline envelope，卻**完全沒提**
normalized Hilbert 內部用什麼內插——而那才是決定性的一項。
*規則：讀 method 時，把「有寫的」和「沒寫的」分兩欄列出來。沒寫的那一欄就是風險清單。*

**13. 「最差匹配模態」這個統計量會被垃圾模態綁架。**
`juan_f4_b04` 的最差 |r| = 0.07，看起來像實作不一致；實際上那是能量佔 0.007 % 的
最後一個殘餘模態，前兩個模態（99.9 % 能量）是 r = 1.000 與 0.983。
*規則：EMD 尾端在任何語言都是混沌的。匹配統計量一律用**能量加權**，並同時報「有幾個
模態被匹配到」。* 換成能量加權後是 98.8 %，故事完全反過來。

**14. masking EMD 的 dyadic descent 會一直製造模態。**
CGM 那筆 312 小時的紀錄，masking EMD 生出 52 h 與 104 h 兩個模態，各佔 5.6 % 與 4.7 %
變異數——但它們在紀錄裡只有 **6 個**和 **3 個**週期。
*規則：報週期時一定同時報「這個週期在紀錄裡有幾個循環」。少於約 10 個就寫成 trend，
不要寫成 rhythm。*

**15. runtime 比較要 like-for-like。**
第一眼「Octave 7.6 s vs Python 0.08 s ≈ 95 倍」是誤導：MATLAB 端跑的是 masking EMD
（每個模態 8 次 sifting，而且模態多 50 %）。同演算法對同演算法是 1.08 s vs 0.08 s。
*規則：跨語言計時，先把演算法對齊，再比較；兩個數字都要報。*

### C. 跨語言工程

**16. Octave 允許鏈式索引，MATLAB 不允許。**
`v(ok)(:)`、`L.BB(s)(m)` 在 Octave 沒問題，在真 MATLAB 是語法錯誤。
*規則：若宣稱 `.m` 檔 MATLAB 相容，就用暫存變數，不要用 Octave 專屬語法。*

**17. `jsondecode` 會改掉含 `.` 的欄位名。**
訊號取名 `juan_f4_b0.4`，Octave 讀進來欄位名被改寫，對不上檔名。
*規則：任何跨語言交換的 key，只用 `[A-Za-z0-9_]`。* 改成 `b04` 就沒事了。

**18. 共用輸入必須是同一份位元。**
兩邊各自 `sin(2*pi*4*t)` 生一次訊號，看起來一樣，但比較結果裡永遠有一份說不清的殘差。
*規則：輸入生成一次，以 `%.17g` 寫成純文字，兩邊都用讀的。* 格線、edge trim、
sifting 停止條件同理——**凡是可以對齊的，全部對齊**，剩下的差異才有意義。

**19. 被 trim 過的陣列用全長索引，會安靜地回傳 0。**
layer-2 的 `ff/ww/BB` 存的是 edge-trim 後的長度，`ncu_roi_time` 卻用絕對取樣點索引，
守衛條件 `numel(L.ff) < n` 直接 `continue` → **整組 ROI 時間序列都是 0，而且沒有任何錯誤**。
*規則：trim 過的陣列要嘛把 offset 一起存進結構，要嘛乾脆存全長。
守衛條件寫成 `~=` 而不是 `<`，讓不一致變成明顯的失敗而不是安靜的零。*
發現它的方法是：四個探測時間點全部是 0——**全 0 是訊號，不是結果**（同 08-19 那次
「所有分組同時為 0，是 schema 訊號」的教訓）。

**20. 不要留 placeholder 呼叫。**
`save('-ascii', [tag '_imfs.txt'], 'out')` 先寫了一行佔位（`out` 是 struct，Octave 會炸），
打算下面覆蓋掉——結果那一行還是會執行。
*規則：寫完立刻刪，不要靠「下面會蓋掉」。*

### D. 公開 repo 與可重現性

**21. 進 public repo 前一定要掃姓名、日期、原始檔名。**
報告裡有帶著個案姓氏的原始檔名（`Reference/CGMS_<姓名>_agp_report.pdf`）與確切日期區間，這兩樣都不能進 repo。
*規則：commit 前跑一次掃描；`data/` 全部排除。*

```bash
grep -rniE "<個案姓氏>|agp_report|20[0-9]{2}-[0-9]{2}-[0-9]{2}|cgm_1min" <資料夾>
```

判準沿用 08-20 那次：**IMF 圖、holo-spectrum、統計量可以公開**（時間軸用 recording
hour，不用日曆日期）；**原始 PDF 與還原 CSV 不行**。

**22. 「可重現」要真的在乾淨資料夾跑過。**
把 public 版複製到空資料夾、只放 `hhsa.py`、沒有任何病人資料，從頭跑一次
`make_signals → run_matlab_side → run_python_side → compare → make_figures`。
第一次就抓到第 9 條那個 SyntaxError，以及三個腳本硬寫死 `cgm_5min` 會 KeyError。
*規則：宣稱「無病人資料可執行」之前，先在乾淨資料夾跑完整條管線。*
現在缺 CGM 時會印 `skipped fig3 -- needs the CGM record, which is not public` 並正常結束。

---

## 四、可重用產出

### `hhsa-python-vs-matlab/`

| 檔案 | 用途 |
|---|---|
| `matlab/ncu_hhsa.m` | 二層 HHSA，所有爭議選擇都是 `opts` 開關（`method` / `sift_kind` / `norm_kind`） |
| `matlab/ncu_masking_emd.m` | Deering–Kaiser masking EMD，4 相位平均 + dyadic mask 遞降 |
| `matlab/ncu_natural_spline.m` | 明確的 natural cubic spline（Octave `spline` 與 scipy `CubicSpline` 預設都是 not-a-knot，**兩者都不是文獻寫的那個**） |
| `matlab/ncu_hilbert.m` | 十行 FFT 解析訊號，不依賴 signal package |
| `work/compare.py` | attribution ladder + 能量加權 IMF 對應 + ground-truth 回收率 |

### 可以直接搬去別的專案的三個做法

1. **Attribution ladder**：比較兩個多處相異的實作時，把差異拆成單步階梯，每步報一個
   相似度。適用於任何「舊管線 vs 新管線」的驗證。
2. **同構驗證前置**：先把兩邊設定對齊、證明結果一致，再談方法差異。
3. **共用輸入檔**：輸入生成一次寫成 `%.17g` 文字檔，兩邊都讀。

---

## 五、下次要先問的問題

1. **這個「MATLAB 版」到底存不存在？** 先確認核心函式在硬碟上、授權能啟動，再答應比較。
2. **文獻沒寫的選擇有哪些？** 開工前列成清單；這次證明它比有寫的還重要。
3. **有沒有辦法把兩邊設成一模一樣？** 如果不能，這個比較就沒有基準線。
4. **哪些輸出可以公開？** 個案資料的專案，在開始存檔前就決定 `data/` 的邊界，
   不要等到 commit 前才處理。
5. **Tsai et al. 2016 的 masking EMD 強化版拿得到嗎？** 拿得到才能把 MATLAB 端的
   保真度主張再收緊一級；這次只能用 Deering–Kaiser 原版並明講。

---

## 相關檔案

- `hhsa-python-vs-matlab/README.md` — 資料夾說明、出處表、執行方式
- `2026-08-20_CGMS_HHSA_Case_Lessons_and_Pitfalls.md` — 產生這筆 CGM 紀錄的那次個案
- `hhsa-clinical-timeseries/` — 被比較的 Python 實作與臨床管線
- `hhsa-clinical-timeseries/references/pitfalls.md` — 方法學層面的量化踩坑清單
