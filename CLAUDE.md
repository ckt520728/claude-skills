# CLAUDE.md

此 repo 用於 **Claude Code Skill 開發**。

通用行為準則(簡潔優先、外科手術式變更、目標驅動執行、語言偏好等)見全域 `~/.claude/CLAUDE.md`。本檔只記錄此 repo 的踩坑紀錄與硬性規則。

---

## Skill (.zip) 的四個上傳陷阱

製作或重新封裝 Skill 時必須**同時**滿足以下四點,否則 claude.ai 的 Upload skill 介面會擋下來。錯誤訊息常具誤導性(尤其 #3 與 #4 文字完全相同,但根因不同)。

| # | 規則 | 違反時的錯誤訊息 |
|---|------|----------------|
| 1 | zip 內必須有**單一根目錄**包住 `SKILL.md`(結構為 `<root>/SKILL.md`),不能巢狀過深,也不能裸放最外層 | `"SKILL.md file must be in the top-level folder"` |
| 2 | zip entry 路徑分隔符必須用 `/`。**禁用** PowerShell `Compress-Archive`(它寫 `\`),改用 `System.IO.Compression.ZipArchive` + 手動 `.Replace('\','/')` | `"Zip file contains path with invalid characters"` |
| 3 | zip 內**根目錄名**只能含 `[A-Za-z0-9_-]` | `"root directory name must contain only alphanumeric..."` |
| 4 | SKILL.md frontmatter `name:` 欄位也只能含 `[A-Za-z0-9_-]`,且**建議**與 zip 根目錄同名(Anthropic 把這個值當作安裝後的目錄 `~/.claude/skills/<name>/`) | 同 #3(訊息一字不差,但根因不同) |

H1 標題、`description`、正文**可保留中文**。**只有** `name:` 與目錄名必須 ASCII。

## 編碼:UTF-8 無 BOM

SKILL.md 一律用 **UTF-8 無 BOM**。PowerShell 的 `Set-Content` / `Out-File` 預設寫 UTF-16 LE with BOM,會破壞中文。必須:

```powershell
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($path, $content, $utf8NoBom)
```

Claude Code 內建的 `Write` 工具預設 UTF-8 無 BOM,可直接用。

## 本地 Skill Loader 的 `description: |` 規則

本地安裝(`~/.claude/skills/`)時,`description` 欄位必須用 **literal block scalar(`|`)**,不能用 folded scalar(`>`)。

```yaml
# ✅ 正確
description: |
  第一行說明。
  第二行說明。

# ❌ 錯誤——loader 回報「Skill.md must start with YAML front matter」,但根因是這個
description: >
  第一行說明。
```

注意:上面四陷阱是 claude.ai **上傳介面**的規則;本節是**本地 loader** 的規則,兩者獨立。詳見 `docs/2026-05-09-install-pitfalls.md`。

## Skill 設計共同原則

新 skill 要遵守:

1. **零外部 LLM API 依賴**——不呼叫 OpenAI / Gemini / 其他 LLM API。
2. **零捏造**——每個 skill 在對應領域(數字、引用、承諾、技能、資料)都要有明確的零捏造規則寫入 SKILL.md。
3. **強制業務問題前置**——長流程開跑前讓使用者確認「要回答什麼問題」。
4. **使用者干預點**——長流程一定有可暫停的位置改方向。
5. **反 LLM 陳腐用詞清單**——維護禁用詞庫(`delve into` / `leverage` / `祝商祺` / `In conclusion` ...)。
6. **協作整合**——輸出格式設計成可被其他 skill 消費(預設 Markdown)。

## SKILL.md 標準結構

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

## 命名與輸出慣例

- skill 目錄:`<skill-name>/`,內含 `SKILL.md`
- 上傳檔:`<skill-name>.skill`(實為 zip)
- 輸出檔案編碼:UTF-8 無 BOM
- 日期格式:`YYYY-MM-DD`

## SOIL 三件套圖檔命名(不可協商)

跨工具圖檔命名:`page_NN_<role>.png`(NN 補零)。`pack_pptx.py` 依此排序。

完整跨工具協作流程見 `docs/cross-tool-image-sop.md`;SOIL 六引擎流水線詳見各 skill 的 SKILL.md。

## 安裝 Skill 到本地

```powershell
# Windows
xcopy /E /I <skill-name> "C:\Users\User\.claude\skills\<skill-name>"

# Mac/Linux
cp -r <skill-name> ~/.claude/skills/
```

---

Skill 清單與架構說明見 `README.md`,或直接 `ls *.skill`。
