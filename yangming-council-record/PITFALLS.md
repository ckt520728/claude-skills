# 陽明醫院會議記錄 Session — 踩坑紀錄與解法

**Session 日期**：2026-06-23
**任務**：115年5月院務會議記錄 + 春節獎勵金發放方式說明 + Word 輸出

---

## Pitfall 1：`Read` 工具無法讀取 .docx / .pptx（Binary 檔案）

**現象**：
```
Error: This tool cannot read binary files. The file appears to be a binary .docx file.
```

**原因**：`.docx` 和 `.pptx` 都是 OOXML zip 格式（binary），`Read` 工具只能讀純文字或特定格式（PDF、圖片）。

**解法**：改用 PowerShell 透過 `WindowsBase` assembly 開啟 Open Packaging Convention（OPC），直接讀取內部 XML：

```powershell
Add-Type -AssemblyName WindowsBase
$pkg = [System.IO.Packaging.Package]::Open($path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read)
# .docx 主體：/word/document.xml
# .pptx 投影片：/ppt/slides/slide*.xml
```

**注意**：提取出的純文字會喪失：表格結構、圖表數值、圖片內容。需對照原始檔案補充。

---

## Pitfall 2：逐字稿輸出超過 Context 上限（92 KB）

**現象**：
```
Output too large (92.4KB). Full output saved to: C:\Users\User\.claude\...\tool-results\biqcjbu5g.txt
```

**原因**：長達 1h 46m 的錄音逐字稿，AI 轉錄後文字量龐大，超出工具單次輸出限制。

**解法**：
1. 工具自動存到 `tool-results/` 檔案，用 `Read` 工具讀取該檔案
2. `Read` 工具有 25,000 token 的 cap，若仍超過，用 `offset`/`limit` 分段讀取
3. 或先用 `Grep` 搜尋關鍵段落（決議、Action Items、春節獎金）

---

## Pitfall 3：PowerShell Heredoc 內嵌 Python 程式碼時 `**` 觸發錯誤

**現象**：
```
Remove-Item on system path 'r'\*\*' is blocked. This path is protected from removal.
```

**原因**：PowerShell 的 `@'...'@` heredoc 在某些情況下仍會解析 `**` 為萬用字元（glob pattern），導致 PowerShell 試圖執行 `Remove-Item **`。

**解法**：永遠不要在 PowerShell heredoc 裡放含 `**` 的 Python 程式碼（如正則的 `**bold**` pattern）。改用**先 Write 再 Execute**的兩步驟：

```
# Step 1：用 Write 工具把 .py 腳本存到磁碟
Write(file_path="C:\\Users\\User\\script.py", content="...")

# Step 2：用 PowerShell 執行
PowerShell: python "C:\Users\User\script.py"
```

---

## Pitfall 4：PowerShell 終端機顯示中文路徑亂碼

**現象**：
```
Saved: D:\������|�|ĳ�O��\meeting_2026-05-21...
```

**原因**：PowerShell 5.1 的 `[Console]::OutputEncoding` 預設為 CP950/Big5，Python `print()` 輸出 UTF-8 中文時亂碼。

**影響**：只是顯示問題，檔案本身正確儲存，路徑中文完全正常。

**確認方法**：執行後用 `Get-ChildItem` 列出實際檔案，中文名稱顯示正確即代表成功。

**若需修正顯示**（非必要）：
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

---

## Pitfall 5：`.skill` 檔是 ZIP Binary，不是 Markdown

**現象**：用 `gh api` 讀取 `meeting-minutes.skill` 得到的是 binary PK zip 格式，無法解析。

**原因**：`claude-skills` repo 裡的 `.skill` 檔案是壓縮打包的 zip 格式，不是純文字。

**解法**：讀取同名資料夾內的 `SKILL.md` 文字版本：
```bash
gh api repos/ckt520728/claude-skills/contents/meeting-minutes/SKILL.md --jq '.content' | base64 -d
```

---

## Pitfall 6：`maybe` Repo 是個人理財 App，不是「健保財務 Skill」

**現象**：用戶稱 `https://github.com/ckt520728/maybe` 為「Finance Skill」，但實際上是 Maybe 個人財務管理 Rails App（追蹤帳戶/交易/投資）。

**原因**：該 repo 為 fork 自 `maybe-finance/maybe`，是一個追蹤個人資產的 SaaS 應用，其 `CLAUDE.md` 是 Rails 開發規範，與健保財務/NHI 申報完全無關。

**解法**：
- 健保相關財務知識（春節加成、NHI 撥付規範）從健保署 PDF 公告直接取得
- `maybe` repo 的 CLAUDE.md 作為「Rails 開發最佳實踐」參考，不作為健保財務知識來源
- 本 skill 改為引用「maybe-finance」作為財務應用開發參考，而非健保申報知識

---

## Pitfall 7：PPTX 圖表數值無法透過 XML 擷取

**現象**：投影片 5、6、7（門診件數圖、住診件數圖、洗腎件數表）提取出的文字只有簡短說明，圖表內的年度比較折線圖數值無法取得。

**原因**：PPTX 圖表（`<c:chartSpace>`）儲存在 `/ppt/charts/chart*.xml`，與投影片 XML 是分開的，簡單的 strip-tags 無法取得。

**解法（本次採用）**：從投影片頁面文字中取得「本月值」的標記數字（如 `4 月份：2791`），並在文件附錄中標注「詳細圖表請見原始 PPT」。

**完整解法（若需要）**：讀取 `/ppt/charts/chart*.xml` 並解析 `<c:ser>` 系列資料。

---

## Pitfall 8：公文關鍵資訊在手機拍照的 JPG 裡

**現象**：健保署撥付函文（含實際金額 346,901 元）只有 `春节奖励金公文.jpg`，無文字版本。

**解法**：`Read` 工具支援圖片視覺辨識，直接讀取 .jpg 即可取得文字內容（OCR 結果）。

**注意**：圖片傾斜/對焦不清時 OCR 準確度會下降，重要金額需二次確認。

---

## Pitfall 9：Speaker 身份無法從逐字稿直接確認

**現象**：逐字稿全程使用 `Speaker 1`、`Speaker 2`、`Speaker 3`，沒有真實姓名。

**解法**：結合上下文線索推斷：
- Speaker 2 → 院長（頻繁決策、「從你的口袋扣掉」、全程主導）
- Speaker 3 → 張主任（「主任跟我講」、報告申報數字、承諾提供班表）
- Speaker 1 → 護理主任（提出護理異常事件、討論病房人力配置）

**原則**：若無法高信心對應，Action Items 負責人欄填 `?? (需確認)`，不猜測。

---

## 最佳實踐總結

| 情境 | 正確做法 |
|------|---------|
| 讀取 .docx/.pptx | PowerShell + WindowsBase OPC |
| 逐字稿太長 | Read tool-results 檔 + 分段 offset |
| Python 腳本含 `**` | Write 存 .py 檔 → PowerShell 執行 |
| 中文路徑顯示亂碼 | 用 Get-ChildItem 確認實際儲存成功 |
| 讀取 GitHub .skill 檔 | 讀資料夾內 SKILL.md，非 .skill zip |
| 圖表數值缺失 | 標注原始 PPT，或讀 chart*.xml |
| 公文只有圖片 | Read 工具直接讀 .jpg（支援 OCR） |
| Speaker 身份不明 | 上下文推斷 + `??(需確認)` 標記 |
