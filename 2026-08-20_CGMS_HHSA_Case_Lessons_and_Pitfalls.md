# 專案收尾 — 踩過的坑與可重用做法

**專案：** 2026 CGMS × HHSA — 用真實 CGM 個案資料實作 Holo-Hilbert Spectral Analysis
**日期：** 2026-08-20（單一工作階段）
**成果：** 從 PDF 還原 13 天血糖時間序列 + 兩層 HHSA + 三種虛無假設檢定 + 一頁 dashboard + 可重用 skill（`hhsa-clinical-timeseries`）
**環境：** Windows 10、PowerShell 5.1 / Git Bash、Python 3.14、Claude Code

本文寫給**未來的自己與其他 agent**。重點不是這個個案的臨床內容，而是**哪些地方會踩坑、以及怎麼繞過**。

> **去識別化聲明：** 本 repo 為公開。以下所有內容已移除姓名、CGM 裝置序號、報告編號、電話與確切日期，僅保留分析方法與去識別化的統計結果。原始 PDF 與還原後的 CSV **一律不進 repo**。

---

## 零、一句話總結

三件事，證據強度**完全不同**，收尾時最重要的就是不要把它們混在一起講：

| # | 發現 | 證據等級 |
|---|---|---|
| 1 | 原始時間序列**可以從 PDF 完整還原**，並用報告自己印的 12 個統計量驗證 | `observed`，誤差 ≤0.25 pp |
| 2 | 夜間低血糖，且**鎖定在時鐘時間上** | `observed`，p = 0.0002 |
| 3 | Holo-spectrum 的跨尺度結構**大多可被 phase-randomised surrogate 重現** | `derived` — 這是**負面結果**，照實寫 |

第 2 點根本不需要 HHSA 就看得到。第 3 點才是這次真正學到的方法學教訓。

---

## 一、資料取得的坑

### 1. 「只有報告 PDF、沒有原始 CSV」不等於做不了

**症狀：** 工作資料夾只有廠商的 AGP 報告 PDF，看起來只能拿到摘要數字。

**解法：** 先確認 PDF 是不是**向量圖**。這份是 100% 向量、零張點陣圖，每一天的血糖曲線是一條 stroked cubic-Bézier polyline，而**Bézier 的 anchor 點就是原始取樣點**。

```python
import fitz
d = fitz.open('report.pdf')
for i, dr in enumerate(d[0].get_drawings()):
    print(i, dr['type'], len(dr['items']), dr['rect'], dr.get('color'))
# 找 type == 's'（stroked）、橫跨整個繪圖區寬度的長路徑
```

**要點：** `get_drawings()` 回傳的 `items` 若全是 `'c'`，就是 Bézier；取每段的起點加上最後一段的終點，就是完整的取樣序列。

### 2. 還原後**一定要驗證**，而且要用報告自己印的數字

只做座標換算就宣稱還原成功是不夠的。這次用了三重驗證：

1. **對照印出來的統計量** — 平均血糖、CV、TIR/TAR/TBR 共 12 項，全部誤差 ≤0.25 個百分點。
2. **量化格點（lattice）檢定** — 校正後數值精準落在 **0.1 mmol/L 格點**上（offset 分數 0.0095，0.25 = 隨機）。測 0.099 與 0.101 都得到 0.22，代表這個極小值**極度銳利**；只要刻度差 0.5% 就會糊掉。順帶排除了 mg/dL 整數格點 → 裝置原生就存 mmol/L。
3. **跨日連續性** — 13 天是分開畫的 13 個 panel，但午夜接縫的跳動 ≤0.2 mmol/L，和日內正常的 1 分鐘變化（中位數 0.05）無法區分 → 確認是**同一段連續紀錄**，可以直接串接。

### 3. 校正要用「多錨點回歸」，不要只靠格線

**症狀：** 只用 6 條 y 軸格線做最小平方，殘差 ≤0.05 mmol/L 看似很好，但**13 天每一天**的日均值都固定高出 **+0.035 mmol/L**。

**解法：** 用報告在其他頁印的 13 個「每日平均血糖（MBG）」對還原值做回歸，得到 affine 修正。最大誤差從 0.042 降到 **0.006 mmol/L**。

**要點：** 那 13 個 MBG 是**用文字 span 座標抓出來、再和同一 panel 的日期標籤配對**的，不是用眼睛讀的。PDF 抽出的文字順序會亂到完全不能信（本例中軸標籤數字會黏進 MBG 數值，變成 `58.57` 這種東西）。

```python
# 用座標定位，不要用文字順序
for b in page.get_text('dict')['blocks']:
    for l in b.get('lines', []):
        for s in l['spans']:
            x0, y0, x1, y1 = s['bbox']   # 用 bbox 配對，不要用出現順序
```

---

## 二、方法學的坑（這幾條最貴）

> 全部可用 `hhsa-clinical-timeseries/scripts/validate_hhsa.py` 重現。合成訊號：
> `x(t) = [1 + 0.5·cos(2πt/24h)]·cos(2πt/3h) + 0.7·cos(2πt/12h)`
> 也就是「3 小時載波被 24 小時調幅」，真實包絡 SD = 0.354。

### 4. EEMD 的雜訊會**摧毀 HHSA 要量的那個調幅**

文獻慣例是兩層都用 EEMD。在有標準答案的合成訊號上，這對第二層是**錯的**。

第二層（對包絡做 EMD）24 小時 sub-IMF 的能量：

| 第二層方法 | 調幅能量 | 還原週期 |
|---|---|---|
| 純 EMD | **394.0** | 23.91 h |
| EEMD 0.05·SD | 385.4 | 23.97 h |
| EEMD 0.10·SD | 338.2 | 24.10 h |
| EEMD 0.20·SD | **104.8** | 24.39 h |

在最常被引用的 0.2·SD，**四分之三的調幅能量消失**。週期還在，「強度」沒了 — 如果你要報告調幅**強度**，EEMD 會讓你低估約 4 倍。

第一層也有兩種壞法（真值 0.354）：

| 第一層 | 2.2–4.2 h 帶內找到的載波 | 包絡 SD |
|---|---|---|
| 純 EMD | 3.00 h | **0.352** ✓ |
| EEMD 0.05 | 3.01 h | 0.391（被灌水） |
| EEMD 0.10 | 3.03 h | 0.476（被灌水） |
| EEMD 0.20 | 2.92 h **和** 3.02 h — 裂成兩條 | 0.356 / 0.121 |

低雜訊時**製造**出不存在的調幅；0.2·SD 時載波直接裂成自己的**調幅邊帶**（sideband）。

**規則：兩層都用純 EMD。** EEMD 只留作「敏感度分析」附錄。包絡本身很平滑、接近單一模態，不需要防 mode mixing。

> **一個要記下來的自我修正：** 稍早版本的分析曾宣稱「EEMD 第一層對 24 h 真值回報 257 h」。那個數字其實來自下面第 6 條的 spline bug，不是 EEMD 造成的。修掉之後 EEMD 第一層回到 22.17 h — 錯約 8%，不是災難性。**上面的邊帶分裂與第二層能量流失才是 EEMD 真正、可重現的問題。**

### 5. 調幅一定要比載波慢 — 強制 ω < f

沒有 admissibility mask 時，合成訊號的 holo-spectrum 峰值落在 **載波 2.79 h / 調幅 2.18 h** — 一個比被調變者還快的「調幅」，而且排名贏過真正的 24 h。

ω ≥ f 的點根本不是 AM，是**包絡估計的漣漪**：通過 |IMF| 極大值的 spline 必然在約半個載波週期上晃動，第二層就老實地把那個晃動分解出來。

要丟掉，而且要**回報丟掉的比例**才能被稽核。健康的分解只會丟幾個百分點；如果丟掉幾十個百分點，代表第一層的模態根本不夠振盪，做 AM 分析沒有意義。

### 6. 振幅正規化要用 **PCHIP**，不要用 natural cubic spline

**症狀：** 真實資料上 IMF3 的平均瞬時振幅跑到 **3 × 10⁶**（真實血糖振幅約 1 mmol/L）。

**原因：** Huang 的 normalized Hilbert 要反覆除以「通過 |IMF| 極大值的 spline」。間歇性模態上，相鄰極大值差好幾個數量級，cubic spline 會在中間**向下衝過頭逼近 0**，除四次就爆掉。

**解法：** 改用 **PCHIP**（保形，不會 overshoot/undershoot）。

**要點：** 這個 bug 很難發現，因為**週期看起來都還很正常**，只有振幅爆炸。所以每個 IMF 都要印 `A.mean()` 並對照物理單位檢查。

### 7. 極值偵測要**把平台（plateau）縮成一點**

臨床數值是量化過的（CGM 0.1 mmol/L），平坦區到處都是 — 本個案 **34% 的 1 分鐘差分剛好等於 0**。用 `x[i-1] < x[i] > x[i+1]` 這種寫法會把平坦峰頂的每一個取樣點都當成極值，下游每一條包絡都會壞掉。

做法：在**非零**差分的正負號上找轉折，然後把極值放在平台的中點。

### 8. EMD 是 dyadic filter bank — 找到 24 小時的 IMF **不等於**有日夜節律

對任何這種長度的紅雜訊跑 EMD，都會有一條 IMF **依結構必然**落在 24 小時附近。實測：對真實紀錄做 AAFT surrogate（完全沒有節律），「circadian」IMF 出現在 **21.9 ± 1.9 h**，變異解釋 38 ± 8%。

所以需要**兩種不同的虛無假設**，而且它們回答的問題不一樣：

| 虛無假設 | 破壞什麼 | 能檢定什麼 |
|---|---|---|
| **AAFT surrogate** | 相位關係，保留功率頻譜 | 載波–調幅的**聯合結構**是否超越線性過程 |
| **循環旋轉（rotation）** | 對外部時鐘的對齊，保留週期內動態 | 節律是否真的**被授時（entrained）** |

**AAFT 沒辦法告訴你「有沒有節律」** — 它保留頻譜，所以本來就含有 24 小時的峰，問它是循環論證。本個案 rotation test 給 p = 0.0002、時鐘相位解釋 56.8% 變異；而 AAFT 對週期、變異、相位集中度全都給 p > 0.35。

### 9. 分解之前先確定**有效解析度**

儲存頻率 ≠ 資訊頻率。本個案存成每分鐘一點，但：

- 量化步階（0.1）**大於** 1 分鐘差分的 SD（0.095）；
- 抽稀到 5 分鐘再 spline 回來，RMSE 只有約一個量化步階；
- PSD 斜率從 −1.97（20–240 分鐘）**變陡**到 −2.56（2–10 分鐘）。

**變陡**代表廠商已經做過低通濾波；真正的量測雜訊底噪應該是平的。結論：15 分鐘以下沒有生理訊息，分析改在 5 分鐘 cadence。

這條很重要，因為 EMD 會把內插與量化的假結構做成 IMF，而沒檢查的人就會把它寫成「快速震盪」。

### 10. 該報的醜數字要報

- **變異佔比總和** — 本個案 101.9%、合成 demo 118.6%。EMD 模態近似但**不完全**正交。報成剛好 100% 的 pipeline 是在偷偷正規化。
- **重建誤差** — 純 EMD 應該到機器精度（3.6 × 10⁻¹⁵）。**EEMD 不會完全重建**，用了就要講。
- **反方向顯著也是發現** — 本個案 AM depth 0.229 vs 虛無 0.437 ± 0.094、MODD 2.28 vs 2.48 ± 0.08，都**低於**虛無。天真解讀是「不顯著」；正確解讀是這段紀錄**比頻譜相符的線性過程還規律**，符合固定的用藥與作息時間表。

---

## 三、環境的坑

### 11. Console 是 cp950 — 印 `ω` 這種字元會出事

**症狀：** `log(f'admissibility ω < f ...')` 在 cp950 console 印出來變亂碼；換個 codepage 就是 `UnicodeEncodeError` 直接把跑到一半的分析炸掉。

**解法：** **所有會被 print 的字串一律 ASCII**，Unicode 只留在寫入 UTF-8 檔案的內容裡。驗證方式是掃描原始碼：

```python
bad = [(i+1, l) for i, l in enumerate(src.splitlines())
       if 'log(' in l and any(ord(c) > 127 for c in l)]
```

（延續 `console-encoding-cp950` 這條老教訓：**寫檔用 UTF-8，用 Read 讀回來驗證，不要用 print 驗證**。）

### 12. Python 的 text-mode 寫檔會偷偷把 LF 換成 CRLF

**症狀：** 用 `open(p, 'w').write(s)` 修補過的檔案，位元組數莫名比預期多出「行數」那麼多，做 checksum 比對時對不起來。

**解法：** 比對前先正規化 `b.replace(b'\r\n', b'\n')`，或寫檔時用 `newline='\n'`。這次上傳到 Drive 比對大小時就是被這個絆到。

### 13. Google Drive 的本地鏡像**不一定是同一個資料夾**

`G:\我的雲端硬碟\<專案名>` 存在，**不代表**它就是 Drive 上那個同名資料夾。本次實測：在本地資料夾建立的檔案**沒有**出現在 Drive 端，兩邊內容完全不同 → 它們是**同名但不同**的資料夾。

**要點：** 交付物要走 **Google Drive MCP**，不要假設本地鏡像會同步。另外 Drive MCP 的 `update_file` **只能改 metadata（標題、父資料夾），不能改內容** — 要換內容只能 `trash_file` + 重新 `create_file`。

### 14. 大檔不要走 `download_file_content`

那個工具會把 base64 塞進 context。1.4 MB 的 PDF ≈ 1.9 MB base64，非常浪費。**改用瀏覽器下載** `https://drive.google.com/uc?export=download&id=<FILE_ID>`，再從 Downloads 搬過去（順便改成 ASCII 檔名，避開 CJK 路徑問題）。

---

## 四、可重用產出

### Skill：`hhsa-clinical-timeseries`

把上面所有規則寫進程式碼的可重用 skill：

```
hhsa-clinical-timeseries/
├── SKILL.md                      入口與不可妥協的規則
├── references/
│   ├── pitfalls.md               上面第二節的完整量測版本
│   └── dashboard-spec.md         一頁 dashboard 的設計契約
├── scripts/
│   ├── hhsa.py                   EMD / EEMD / normalized Hilbert / holo / nulls
│   ├── hhsa_pipeline.py          ingest → 解析度稽核 → 第一層 → 虛無 → 第二層 → 檢定 → 圖 → HTML
│   ├── build_dashboard.py        results.json + figs → 單檔 HTML
│   ├── validate_hhsa.py          有標準答案的驗證，動分解前先跑這個
│   └── make_demo_data.py         合成資料，不用病人資料就能跑
└── assets/                       本個案的去識別化圖
```

一行跑完：

```bash
python scripts/make_demo_data.py --days 13 --out demo_cgm.csv
python scripts/hhsa_pipeline.py --input demo_cgm.csv \
    --time-col timestamp --value-col glucose --unit mmol/L \
    --resample 5 --cycle-h 24 --out out/
```

合成資料裡**故意埋了標準答案**（24 h 載波、被 24 h 調幅的 4 h 載波、72 h 漂移、0.1 量化格點），pipeline 跑完應該四個都找得回來 — 這樣才驗得出 pipeline 有沒有壞，而不是只能「看起來很合理」。

### 與既有 skill 的分工

| skill | 範圍 |
|---|---|
| `hhsa-closed-loop-prototyping` | **即時 / 閉迴路**：EEG、相位鎖定觸發、tACS/TMS、FPGA 移植 |
| `hhsa-clinical-timeseries`（本次新增） | **離線 / 單一病人**：CSV 或報告 PDF → 兩層 HHSA → 一頁 dashboard |

兩者的離線 HHSA 不變量是一致的（ω < f、包絡走 spline-through-extrema、邊界鏡射、對數分箱）。本次新增的是 **PCHIP 正規化**與**三種虛無假設檢定**。

---

## 五、下次要先問的問題

1. **記錄長度夠嗎？** 13 天 ≈ 13 個日週期，對 holo-spectrum 想解析的 >32 h 調幅頻率**根本不夠**。HHSA 的賣點需要數週到數月，不是兩週。先確認長度再決定要不要做第二層。
2. **有沒有共變量？** 沒有用藥時間、進食時間、睡眠，任何「這個 8.3 小時模態代表什麼」都只是描述，不是解釋。**這是這次最大的限制**，而且事後補不回來。
3. **這個發現需要 HHSA 嗎？** 本個案臨床上最重要的發現（夜間低血糖鎖定在時鐘時間）用一個 time-of-day 直方圖就看得出來。方法要配問題，不要為了用方法而用。
