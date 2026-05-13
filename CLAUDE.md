# CLAUDE.md

行為準則 + 此工作區的硬性規則。改寫自 Andrej Karpathy 公開分享的 CLAUDE.md 模板,並合併個人踩坑紀錄。

**Tradeoff:** 這份規則偏向謹慎勝於速度。瑣碎任務自行判斷。

---

## 關於我

- 臨床醫師,專長腎臟病、糖尿病、複雜內科急症
- 認知神經科學博士
- 此資料夾 / repo 用於 **Claude Code Skill 開發**
- Obsidian 第二大腦另有獨立 CLAUDE.md 管理 vault 結構(知識庫 / 創作庫 / 每日筆記 / Templates),規則互不干擾

## 語言偏好

- 對話、文件、commit message、SKILL.md 正文一律**繁體中文**
- 技術專有名詞(API 名稱、變數、library 名)保留英文
- Skill `name:` 欄位、目錄名、檔名必須**純 ASCII**(見 §5)
- 回應力求簡潔,白話文,先給結論

---

## 1. 先思考再寫程式

**不假設、不掩飾困惑、把取捨擺出來。**

實作前:
- 把假設明說。不確定就問。
- 多種解讀並存時,逐一提出——不要默默選一個。
- 有更簡單做法,要說。該推回就推回。
- 不清楚就停下來。指明哪裡不清楚。問。

## 2. 簡潔優先

**用最少的程式碼解決問題。不投機。**

- 不加沒被要求的功能。
- 一次性程式碼不抽象化。
- 沒被要求的「彈性」或「配置」一律不做。
- 不為不可能發生的情境寫錯誤處理。
- 200 行能寫成 50 行,就重寫。

自問:「資深工程師會不會說這寫太複雜?」會 → 簡化。

## 3. 外科手術式變更

**只動該動的。只清自己的爛攤子。**

編輯既有檔案時:
- 不「順手改善」鄰近程式碼、註解、格式。
- 沒壞就不重構。
- 即使不認同既有風格,還是配合它。
- 看到不相關的死碼,**提一下**——但不要刪。

你的變更若產生孤兒:
- 移除**你的**變更使其變成未使用的 import / 變數 / function。
- 不要刪除預先存在的死碼,除非被明確要求。

測試:每一行變更都能直接對應使用者的請求。

## 4. 目標驅動的執行

**定義成功標準。迴圈直到驗證通過。**

把任務轉成可驗證的目標:
- 「加驗證」→「先寫測試,再讓測試通過」
- 「修 bug」→「先寫能重現 bug 的測試,再讓測試通過」
- 「重構 X」→「重構前後測試都通過」

多步驟任務先列計畫:
```
1. [步驟] → 驗證:[檢查]
2. [步驟] → 驗證:[檢查]
3. [步驟] → 驗證:[檢查]
```

明確的成功標準讓你可以獨立迴圈。模糊的標準(「讓它能動」)需要不斷被打斷確認。

---

## 5. Skill 開發的硬性規則(此工作區專屬)

### 5.1 Skill (.zip) 的四個上傳陷阱

製作或重新封裝 Skill 時必須**同時**滿足以下四點,否則 claude.ai 的 Upload skill 介面會擋下來。錯誤訊息常具誤導性(尤其 #3 與 #4 文字完全相同,但根因不同)。

| # | 規則 | 違反時的錯誤訊息 |
|---|------|----------------|
| 1 | zip 內必須有**單一根目錄**包住 `SKILL.md`(結構為 `<root>/SKILL.md`),不能巢狀過深,也不能裸放最外層 | `"SKILL.md file must be in the top-level folder"` |
| 2 | zip entry 路徑分隔符必須用 `/`。**禁用** PowerShell `Compress-Archive`(它寫 `\`),改用 `System.IO.Compression.ZipArchive` + 手動 `.Replace('\','/')` | `"Zip file contains path with invalid characters"` |
| 3 | zip 內**根目錄名**只能含 `[A-Za-z0-9_-]` | `"root directory name must contain only alphanumeric..."` |
| 4 | SKILL.md frontmatter `name:` 欄位也只能含 `[A-Za-z0-9_-]`,且**建議**與 zip 根目錄同名(Anthropic 把這個值當作安裝後的目錄 `~/.claude/skills/<name>/`) | 同 #3(訊息一字不差,但根因不同) |

H1 標題、`description`、正文**可保留中文**。**只有** `name:` 與目錄名必須 ASCII。

### 5.2 編碼

SKILL.md 一律用 **UTF-8 無 BOM**。PowerShell 的 `Set-Content` / `Out-File` 預設寫 UTF-16 LE with BOM,會破壞中文。必須:

```powershell
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($path, $content, $utf8NoBom)
```

Claude Code 內建的 `Write` 工具預設 UTF-8 無 BOM,可直接用。

### 5.3 Skill 設計的共同原則

此工作區內所有 skill 共享以下原則,新 skill 要遵守:

1. **零外部 LLM API 依賴**——不呼叫 OpenAI / Gemini / 其他 LLM API。Claude 本身就在執行,呼叫外部多一層失真且花錢。
2. **零捏造(Zero-Fabrication)**——每個 skill 在對應領域(數字、引用、承諾、技能、資料)都要有明確的零捏造規則寫入 SKILL.md。
3. **強制業務問題前置**——長流程開跑前讓使用者確認「要回答什麼問題」,避免空泛的「general observations」輸出。
4. **使用者干預點**——長流程一定有可暫停的位置改方向(outline review、gap 分析、triage 分類)。
5. **反 LLM 陳腐用詞清單**——每個 skill 維護對應領域的禁用詞庫(`delve into` / `leverage` / `祝商祺` / `In conclusion` ...)。
6. **協作整合**——輸出格式設計成可被其他 skill 消費(預設 Markdown)。

### 5.4 SKILL.md 標準結構

```
---
name: <ASCII kebab-case,與 root 同名>
description: <一段話含觸發詞,繁中為主>
---

# <Skill 標題>

## 目的
## 🚨 鐵則(該領域的零捏造規則)
## 觸發後的工作流程(分 Step)
## 重要的編輯原則
## 跟其他 skill 的協作(可選)
## 不要做的事
```

### 5.5 命名與輸出慣例

- skill 目錄:`<skill-name>/`,內含 `SKILL.md`
- 上傳檔:`<skill-name>.skill`(實為 zip,改副檔名以符合 repo 既有慣例)
- 輸出檔案編碼:UTF-8 無 BOM
- 日期格式:`YYYY-MM-DD`
- 路徑分隔符討論時用 `/`,實作時依平台
- 不主動加 emoji 到檔案內容,除非使用者明確要求

---

**這份規則有效的訊號:** diff 裡沒有多餘變動、不再因過度設計而重寫、釐清問題出現在實作之前而非錯誤之後。
