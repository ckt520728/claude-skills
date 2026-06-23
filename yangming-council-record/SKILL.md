---
name: yangming-council-record
description: >
  陽明醫院（地區醫院）院務會議全流程處理 skill：整合 PPT 簡報、錄音逐字稿（.docx）、健保公文（PDF/圖片）等多種輸入，
  產出結構化會議紀錄（Meeting Minutes）與健保春節加成獎勵金院內分配說明文件，並轉檔為 Word。
  觸發詞：「整理陽明會議」「幫我做院務會議記錄」「春節獎勵金分配」「健保春節加成」「NHI 春節獎勵」
  「整理會議逐字稿」「幫我轉 Word」「陽明醫院會議」「院務會議記錄」「健保署公文解讀」。
  不適用：其他醫院的院務會議（需另外調整人名與科室）、一般企業會議（用 [[meeting-minutes]] skill）、
  非健保春節加成類的財務文件（需另外調整公文格式）。
  先決條件：
    - 會議 PPT（.pptx）
    - 錄音逐字稿（.docx，AI 自動轉錄格式如 Truley/Otter.ai 匯出）
    - 春節獎勵金相關公文（健保署 PDF 公告 + 撥付公文 JPG/圖片）
    - Python 環境含 python-docx（`pip install python-docx`）
---

# Yangming Council Record Skill

整合 [[meeting-minutes]] 與 [[maybe-finance]] 兩個 skill 的院務會議全流程處理 skill。
專為陽明醫院（地區醫院）設計，處理每月院務會議紀錄及健保相關財務文件。

---

## 目的

把每月院務會議的多種原始素材（PPT 簡報、AI 錄音逐字稿、健保公文）
整合成：
1. **結構化 Meeting Minutes**（基於 [[meeting-minutes]] 格式）
2. **健保春節加成獎勵金院內分配說明**（基於 [[maybe-finance]] 健保財務知識）
3. **Word 輸出檔**（.docx，供存檔與發佈）

---

## 輸入素材清單

| 素材 | 格式 | 說明 |
|------|------|------|
| 院務會議 PPT | .pptx | 含統計數據、上次決議追蹤、各科業務報告 |
| 錄音逐字稿 | .docx | AI 自動轉錄（含 Speaker 1/2/3 標籤） |
| 健保春節加成公告 | .pdf | 健保醫字公告，含加成方式與撥付規範 |
| 健保撥付公文 | .jpg/.pdf | 健保署函文，含實際撥付金額 |

---

## Step 1：讀取素材

### 1-1 讀取 PPT（提取文字）

PPT 為 OOXML 格式，直接用 `Read` 工具無法讀取 .pptx binary，改用 PowerShell：

```powershell
Add-Type -AssemblyName WindowsBase
$pkg = [System.IO.Packaging.Package]::Open($pptxPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read)
$slides = $pkg.GetParts() | Where-Object { $_.Uri.ToString() -match "^/ppt/slides/slide\d+\.xml$" } |
    Sort-Object { [int]($_.Uri.ToString() -replace '.*slide(\d+)\.xml','$1') }
# ... 逐頁讀取 XML，strip tags 取純文字
```

> ⚠️ PPT 的圖表與圖片無法透過 XML 文字擷取——只能讀到文字框內容，圖表數字需對照原始 PPT 確認。

### 1-2 讀取逐字稿（.docx）

.docx 為 binary，`Read` 工具會報錯。改用 PowerShell：

```powershell
Add-Type -AssemblyName WindowsBase
$pkg = [System.IO.Packaging.Package]::Open($docxPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read)
$part = $pkg.GetPart([System.Uri]::new("/word/document.xml", [System.UriKind]::Relative))
# ... 讀取 XML strip tags
```

> 輸出可能超過 context 限制（>90KB），工具會自動儲存到 tool-results 檔案，用 `Read` 帶 offset 分段讀取。

### 1-3 讀取 PDF 公告

`Read` 工具支援 PDF，直接讀取即可：

```
Read(file_path="...公告.pdf")
```

### 1-4 讀取公文圖片（JPG）

`Read` 工具支援圖片（OCR + 視覺辨識），直接讀取：

```
Read(file_path="...公文.jpg")
```

---

## Step 2：識別講者（Speaker Mapping）

AI 逐字稿使用 Speaker 1/2/3 標籤。結合上下文推斷：

| Speaker | 身份 | 判斷依據 |
|---------|------|---------|
| Speaker 2 | 院長 | 「院長」直稱、主導決策、「我要請醫生發言」「從你的口袋扣掉」 |
| Speaker 3 | 張主任（行政）| 報告統計數字、「主任跟我講」、承諾提供班表與明細 |
| Speaker 1 | 護理主任 | 提出護理異常事件、「護理長提出」、討論病房人力 |

> 若逐字稿講者標籤無法對應，在 Action Items 寫 `?? (需確認)` 不要猜測。

---

## Step 3：產出 Meeting Minutes

遵循 [[meeting-minutes]] skill 的七區塊格式，但加入以下醫院特定規則：

### 陽明醫院 Meeting Minutes 補充規則

**數據區塊**（每月固定）：

在 `## 7. 附錄` 加入當月主要指標表：

| 指標 | 本月值 | 備註 |
|------|--------|------|
| 門診件數 | | |
| 住診申報件數 | 含切帳/自家/安養分類 | |
| 洗腎人數/人次 | | |
| 呼吸器死亡率 | 計算公式：死亡人數/呼吸器>21天人次 | |
| 各病房占床率 | 二病房/護之家/5F/ICU 分別列出 | |
| 全院藥費占率 | 與去年同期比較 | |
| Q2 季度額度結餘 | | |

**病人名單敏感資訊處理**：
- 超過 30 日住院名單、14 日內再入院名單包含姓名與病歷號
- 會議記錄中保留（院內文件），但若需對外分享需遮罩
- 格式：姓名保留、病歷號保留（院內文件）

**決議格式強制規則**：
- 每條決議必須有「理由」欄——「逐字稿未明確說明」比空白好
- 護理異常事件必須有後續追蹤 Action

---

## Step 4：產出春節獎勵金分配文件

### 必要資訊對照

| 項目 | 來源 | 位置 |
|------|------|------|
| 加成方式（除夕/初三/初四初五/小年夜）| 健保署年度公告 PDF | 伍、支付方式 |
| 實際撥付金額 | 健保署函文（公文 JPG）| 主旨段 |
| 撥付比例（80%/20%）| 健保署公告 | 伍、四、獎勵金撥付規範 |
| 達標指標（餘20%條件）| 健保署公告 | 陸、預期效益之評估指標 |
| 院內分配比例 | 院務會議討論 | 逐字稿 |

### 春節加成關鍵數字（115年參考）

| 假別 | 日期 | 門診加成率 | 急診/住院加成 |
|------|------|-----------|-------------|
| 除夕至初三 | 2/16–2/19 | 100% | 100% |
| 初四至初五 | 2/20–2/21 | 50% | 100% |
| 小年夜及其餘連假 | 2/14、2/15、2/22 | 30% | 100% |
| 門診血液透析 | 全期 | +2% | — |

**撥付規則**：
- 第一次撥付：計算結果 × 80%（已直接入健保帳）
- 第二次撥付：計算結果 × 20%（需第 1 季評估指標達標）
- 院內強制分配：獎勵金的 **80% 以上** 須分配給相關人員

### 院內分配文件結構

```markdown
## 一、方案背景（引用健保公告）
## 二、健保署加成計算方式（表格）
## 三、本院實際撥付金額（含各部門明細）
## 四、評估指標達標獎勵（餘20%條件）
## 五、院內分配原則
  ### 法規強制規範（80%以上給人員）
  ### 討論中的分配比例（待定案）
  ### 分配對象範圍
  ### 所需資料清單（班表、費用明細）
## 六、後續時程
```

---

## Step 5：轉換為 Word（.docx）

`Read` 工具和 `Write` 工具只能處理文字，Word 轉換需用 Python + `python-docx`：

```python
# 先確認環境
python -c "import docx; print('OK')"

# 執行轉換
python convert_md_to_docx.py
```

> ⚠️ PowerShell heredoc（`@'...'@`）不能直接內嵌含 `**` 的 Python 程式碼——PowerShell 會把 `**` 解析為 `Remove-Item` 萬用字元導致錯誤。
> **解法**：先用 `Write` 工具把 Python 腳本存成 .py 檔，再用 PowerShell 執行。

---

## 定期會議 Checklist

每次院務會議後執行：

- [ ] 收集 PPT、逐字稿 .docx、健保公文
- [ ] 提取 PPT 數據（PowerShell XML）
- [ ] 提取逐字稿（PowerShell XML，分段讀取）
- [ ] 識別本月 Speaker 對應
- [ ] 完成 Meeting Minutes（含附錄數據表）
- [ ] 若有春節/連假獎勵金公文：完成分配說明文件
- [ ] 轉換 Word（python-docx）
- [ ] 存檔至 `D:\陽明醫院會議記錄\`

---

## 相關 Skill

- [[meeting-minutes]] — 會議紀錄七區塊格式規範（本 skill 的核心格式來源）
- [[maybe-finance]] — 健保財務架構與 NHI 申報邏輯參考（https://github.com/ckt520728/maybe）

## 參考文件位置

- 陽明醫院會議資料：`D:\陽明醫院會議記錄\`
- Google Drive：`G:\我的雲端硬碟\Second Brain\Yangming-council-skill\`
- GitHub Skill Repo：https://github.com/ckt520728/claude-skills/tree/master/yangming-council-record
