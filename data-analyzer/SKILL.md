---
name: data-analyzer
description: 對結構化資料(CSV、Excel、JSON、Parquet、SQLite)做嚴謹的探索性分析——載入、剖析、計算、視覺化、寫報告。**所有數字一律來自實際 pandas/numpy/scipy 計算,絕不靠 LLM 直覺**。觸發詞:「分析這份資料」「analyze this dataset」「跑一下這份 CSV」「看一下這份 Excel 有什麼洞察」「找出 anomalies」「這份資料有什麼趨勢」「描述性統計」「explore this data」「畫個圖看一下」「這幾欄的相關性」「outliers 在哪」「我想知道 X 跟 Y 的關係」。處理:臨床研究資料、商業 KPI、問卷、財務、實驗數據、個人記錄(支出/時間/健康)。輸出:含計算數值、視覺化圖表、限制聲明的 Markdown 報告。不適用:資料清理 / ETL(那是工程任務,本 skill 假設資料已大致乾淨)、機器學習模型訓練(那是 ml-modeling 範疇)、產出投影片或對外簡報(改用 article-writer 或 soil-teaching-deck)。
---

# Data Analyzer

## 🚨 鐵則:零數字捏造(Zero-Hallucinated-Number Rule)

報告裡的**每一個**數字、百分比、p-value、相關係數、平均值、anomaly threshold,都必須來自一段實際跑過的程式碼。**不可以**:

- 看 `describe()` 摘要憑感覺說「mean 看起來很高」
- 沒跑相關性檢驗就說「兩欄看起來有關」
- 沒定 threshold 就指認哪些是 outlier
- 「大約 30%」「明顯偏高」「remarkably correlated」之類含糊表述

每個聲稱要有對應的 code + 算出來的數字 + 適當的 caveat(樣本數、p-value、confidence interval)。

報告中**每一段 finding** 結尾要附引用,格式:

```
(computed: code_block_1, n=247, p=0.003)
```

讀者順著引用可以回頭找到產生這個數字的程式碼。

## 環境檢查

第一次使用先確認:

```bash
python --version 2>&1 || python3 --version 2>&1
python -c "import pandas, numpy, scipy, matplotlib" 2>&1
```

缺少套件就提示:「需要安裝 pandas, numpy, scipy, matplotlib——要我幫你跑 `pip install` 嗎?」**問了再裝**,不自己 pip。

## 觸發後的工作流程

### Step 1:載入 + 快速剖析(Profile)

依檔案類型載入:

| 格式 | 工具 |
|------|------|
| `.csv` / `.tsv` | `pd.read_csv` |
| `.xlsx` / `.xls` | `pd.read_excel`(若多 sheet,先列 sheet 名問使用者要哪一個) |
| `.json` / `.jsonl` | `pd.read_json` 或手動 |
| `.parquet` | `pd.read_parquet` |
| `.sqlite` / `.db` | `sqlite3` + `pd.read_sql`,先列 table 名 |

**強制輸出 profile 給使用者確認**:

```markdown
## 資料載入確認

- 來源:<path>
- Shape:1247 列 × 8 欄
- 時間範圍(如有 datetime 欄):2023-01-01 → 2024-12-31
- 欄位與型別:
  | 欄位 | 型別 | 缺失率 | 唯一值數 | 範例 |
  |------|------|--------|---------|------|
  | order_id | int64 | 0% | 1247 | 1001, 1002 |
  | customer_id | int64 | 0% | 312 | 50, 51 |
  | amount | float64 | 0.2% | 894 | 23.5, 47.0 |
  | category | object | 0% | 5 | A, B, C |
  | order_date | datetime | 0% | 730 | 2023-01-01 |

- 前 3 列(sanity check):
  | order_id | customer_id | amount | category | ... |
  ...

請確認:
- 資料是否如預期?
- 有沒有欄位該是 datetime 卻被讀成字串?
- 有沒有「-1」「999」「N/A」這種 sentinel 值需要轉成 NaN?
```

**例外**:如果使用者已經明確說「不要 profile,直接分析」,跳過確認,但在最終報告開頭加上「未經 profile 確認,以下假設資料已乾淨」。

### Step 2:**問業務問題**(必跑,除非使用者已明說)

LLM 在資料分析上最大的失敗模式就是被叫「找 patterns / insights」就開始亂猜。**不要這樣做**。

主動問:

```
這份資料你要回答什麼問題?幾個常見方向:

(a) 描述性:「整體長怎樣?分佈、趨勢、缺失模式」
(b) 比較性:「A 跟 B 群組有沒有差?哪個欄位區別最大?」
(c) 關聯性:「X 跟 Y 是否相關?強度多少?」
(d) 異常偵測:「哪些紀錄不正常?標準是什麼?」
(e) 預測性:「根據過往資料預測 Z?」(這個會建議轉去 ml 工具)
(f) 你心裡有個具體假設想驗證?直接告訴我
```

使用者答了之後**才**設計分析。沒答之前不開始跑分析。

**唯一例外**:使用者明說「先給我描述性概覽就好」,走 (a)。

### Step 3:計算(按 Step 2 問題類型)

依問題類型選分析手法。每跑一段分析,**寫成獨立 Python 區塊**並執行,把輸出寫到 stdout/檔案,然後解讀。

#### (a) 描述性

```python
# describe per dtype
print(df.describe(include='number'))
print(df.describe(include='object'))

# missing patterns
print(df.isna().sum())
print(df.isna().sum(axis=1).value_counts())  # 多少列有 0/1/2... 個缺失

# distribution of key numeric cols → histogram (Step 4 處理)
# distribution of categoricals
for col in categorical_cols:
    print(df[col].value_counts(dropna=False).head(20))
```

#### (b) 比較性(雙群組)

```python
from scipy import stats

# numeric outcome → t-test (or Mann-Whitney 若非常態)
group_a = df.loc[df['group']=='A', 'outcome'].dropna()
group_b = df.loc[df['group']=='B', 'outcome'].dropna()

# 常態性檢驗
print(stats.shapiro(group_a), stats.shapiro(group_b))

# t-test or Mann-Whitney
t, p = stats.ttest_ind(group_a, group_b, equal_var=False)  # Welch's
print(f't={t:.3f}, p={p:.4f}, n_a={len(group_a)}, n_b={len(group_b)}')
# 加上效應量 Cohen's d
```

報告時**不能只寫 p-value**——要附 n、效應量、信賴區間。

#### (c) 關聯性

```python
# 數值 vs 數值 → Pearson + Spearman
print(df[['x','y']].corr(method='pearson'))
print(df[['x','y']].corr(method='spearman'))
# significance test
r, p = stats.pearsonr(df['x'].dropna(), df['y'].dropna())

# 類別 vs 類別 → chi-square
ct = pd.crosstab(df['cat1'], df['cat2'])
chi2, p, dof, expected = stats.chi2_contingency(ct)
```

**強制**:相關性 ≠ 因果。在報告中明確標 `(correlation only, no causal claim)`。

#### (d) 異常偵測

threshold **必須明確定義並寫在報告**:

```python
# IQR method
Q1 = df['amount'].quantile(0.25)
Q3 = df['amount'].quantile(0.75)
IQR = Q3 - Q1
lower = Q1 - 1.5 * IQR
upper = Q3 + 1.5 * IQR
outliers = df[(df['amount'] < lower) | (df['amount'] > upper)]
print(f'IQR threshold: [{lower:.2f}, {upper:.2f}], outliers: {len(outliers)} / {len(df)}')
```

報告中要列出具體 outlier 列號或關鍵欄位內容(取前 10 筆 + 說明還有多少筆),不准用「有一些 outliers」這種模糊話。

### Step 4:視覺化(關鍵發現都要有圖)

- 用 matplotlib(預設)或 plotly(若需要互動)
- 圖**存成 PNG** 到工作目錄,在報告中用 `![](path)` 引用
- 檔名:`fig_<short-description>.png`,例:`fig_amount_by_month.png`
- 每張圖配一句 caption,**caption 要說圖在講什麼**,不是純標題

選圖標準:

| 任務 | 圖型 |
|------|------|
| 數值分佈 | histogram + boxplot |
| 時間趨勢 | line chart(必要時 + rolling mean) |
| 類別比較 | bar chart(横向若 label 多) |
| 雙變數關係(數值) | scatter + 趨勢線(`np.polyfit`) |
| 相關矩陣 | heatmap |
| 比例構成 | bar chart(**不要用 pie chart**——閱讀效率低) |

**不要做**的圖:
- ❌ 3D 圖(除非真的有三個連續維度,99% 場合 2D 就夠)
- ❌ 雙 y 軸(誤導性高,寧可拆兩張)
- ❌ Pie chart 超過 4 個分類

### Step 5:寫報告

固定六段結構。每段沒內容就**整段刪**(避免空殼)。

```markdown
# 資料分析報告:<業務問題的一句話>

- **資料來源**:<path>
- **分析期間**:<YYYY-MM-DD → YYYY-MM-DD>(若有時間維度)
- **樣本數**:N=<總筆數>(扣除缺失後 N=<X>)
- **分析日期**:<今天>
- **分析工具**:Python pandas <ver>, scipy <ver>, matplotlib <ver>

## 1. TL;DR

<3-5 句。最重要的 1-2 個發現,帶具體數字。讓決策者讀完就能下下一步動作。>

## 2. 業務問題與分析設計

<在 Step 2 抓到的問題,以及為了回答這個問題,跑了哪些分析。一段話。>

## 3. 主要發現

### 3.1 <發現 1 的一句話標題>

<2-3 句解釋,帶數字>

(computed: n=247, mean=23.4, 95% CI [21.1, 25.7])

![圖:<caption>](fig_xxx.png)

### 3.2 <發現 2>

...

(每個發現都附 computed 引用 + 圖,若適用)

## 4. 異常與資料品質問題

具體列出:
- 缺失資料:`amount` 有 0.2% NaN(共 3 筆),集中在 2024-Q4
- Outliers(IQR > 1.5):共 12 筆,例:
  - row 47, amount=8500(中位數 23.5,73 倍)
  - ...
- 可疑記錄(若有):`order_date` 有 5 筆是 1970-01-01,疑為 epoch 預設值

## 5. 限制(Limitations)

**這份分析不能回答什麼**:
- 樣本量太小:Q4 只有 47 筆,任何 Q4-specific 結論信心度低
- 相關性不是因果:第 3.2 節 X 與 Y 相關,**沒檢驗**是否有共同 confounder
- 抽樣偏誤(若有):資料只涵蓋付費用戶,免費用戶行為無法推論

## 6. 建議的下一步

具體可行動的:
- [ ] <例:把第 4 節 outlier 12 筆人工確認是真實交易還是錯記>
- [ ] <例:補抓 Q4 額外資料以增加樣本量>
- [ ] <例:對 X-Y 關聯做 multivariate regression 控制 Z>
```

### Step 6:檔案輸出

- 報告:`analysis_<dataset-slug>_<YYYY-MM-DD>.md`
- 圖檔:`fig_*.png`(放同目錄)
- 分析腳本:`analysis_<dataset-slug>.py`(把所有跑過的程式碼存成可重跑的腳本,讓使用者三個月後還能 reproduce)

回報只說:
- 報告路徑
- TL;DR 第一句
- 圖檔數量

**不要**把整份報告再貼一次到 chat。

## 隱私 / 敏感資料處理

讀進資料後**主動偵測**以下欄位類型,並提醒使用者:

| 偵測到 | 行動 |
|--------|------|
| 看起來像 email(`@` + 網域) | 提醒「資料含 email,要不要在報告中遮罩成 `***@domain.com`?」 |
| 身分證 / 健保卡號 / 信用卡格式 | 強制遮罩,不要原樣放進報告 |
| 姓名欄位(根據欄名 like `name`, `姓名`, `customer_name`) | 提醒「報告若要分享,姓名要不要替換成 ID?」 |
| 病歷 / 診斷碼 | 提醒「醫療資料注意 IRB / 隱私規範,確認分析用途已獲授權」 |

## 重要的分析原則

**先看分佈再看平均**:LLM 最愛報 mean,但 mean 對偏態分佈幾乎沒意義。每個數值欄位先看 histogram + median + IQR,再決定要不要報 mean。

**小樣本要謙虛**:n < 30 任何 p-value 都不可靠;n < 10 連描述性統計都要加 caveat。看到「Q4 only had 8 transactions but growth was 300%」這種敘述要立刻 flag。

**多重比較校正**:跑超過 3 個 hypothesis test,要套 Bonferroni 或 FDR。報告中明說有沒有做。

**Confounder 不能忽略**:看到「年收入 × 健康狀態」相關,要主動想「年齡」「教育」可能是共因。報告中要列出**沒控制**的 confounder。

**時間序列要看 seasonality**:有 datetime 欄位的話,在跑 trend 前先看 seasonal decomposition(週、月、季、年)。不然「上升趨勢」可能只是季節性。

**圖的字要看得清楚**:`plt.tight_layout()` 必跑,軸字 fontsize ≥ 10,旋轉長 label,千分位加逗號。圖的目的是讀者看得懂,不是 Skill 自我滿足。

## 反 LLM 資料分析陳腐用詞清單

看到就改:

- ❌ "remarkable" / "significant"(後者在統計語境有專門意義,口語請避免)
- ❌ "skyrocketed" / "plummeted"(改寫成「increased by X% over Y period」)
- ❌ "surprisingly" / "interestingly"(讀者自己會判斷有不有趣)
- ❌ "the data clearly shows"(資料從來不會 clearly 顯示什麼)
- ❌ "trending upward"(說「+3.2% per month, n=24 months, p=0.04」)
- ❌ 不附 caveat 的因果句「X causes Y」/「X 導致 Y」
- ❌ 每段都用「Analysis reveals that...」開頭

## 跟其他 skill 的協作

- **knowledge-base ← data-analyzer**:重要的分析報告可以 ingest 進個人知識庫,日後查「我之前看過 X 資料的結論」
- **article-writer ← data-analyzer**:把分析結果寫成對外發布文章 → article-writer 接手,但保留 data-analyzer 報告作為素材
- **meeting-minutes ← data-analyzer**:跨部門資料簡報後的會議紀錄,可附 data-analyzer 報告路徑

## 不要做的事

- ❌ 不要呼叫外部 LLM API——Claude 解讀統計結果,但**統計結果一定由 Python 計算**,不是 LLM 估算
- ❌ 不要看 `describe()` 字串就下結論(這是原 Python code 的失敗模式)
- ❌ 不要在沒做 Step 2(問業務問題)前就跑分析——會得到空泛的「general observations」垃圾報告
- ❌ 不要把分析結果用 pie chart 呈現超過 4 個分類
- ❌ 不要報告 p-value 卻不報 n、effect size
- ❌ 不要用 mean 描述偏態資料的中心(改用 median)
- ❌ 不要對 n<10 的子群組做 inference(只能描述)
- ❌ 不要從相關性跳到因果結論,即使「commonly assumed」
- ❌ 不要把 PII(姓名、email、身分證)原樣放進報告
- ❌ 不要在 chat 裡把整份報告再貼一次——使用者去開檔案
- ❌ 不要產出沒有 fig_*.png 引用的「主要發現」——關鍵發現必須可視覺化
