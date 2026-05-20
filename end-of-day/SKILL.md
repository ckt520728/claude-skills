---
name: end-of-day
description: |
  每日收工流程。收集今日進度、儲存到 Firebase、GitHub repo 與 Obsidian 知識庫，
  並預備明天未完成的事項。觸發詞：「收工」、「end of day」、「wrap up」、「今日進度存檔」、「打包今天的進度」。
---

# End of Day — 每日收工流程

## 流程概要

1. **收集今日摘要** — 盤點今天做了什麼、完成什麼、卡住什麼
2. **儲存到 Firebase** — 寫入 Firestore `sessions` collection
3. **寫入 GitHub repo** — `ckt520728/2026Cordex` 的 session note
4. **同步到 Obsidian** — `知識庫/2026 OpenCode/` 資料夾 + 更新 index.md
5. **產生明日待辦** — 列出未完成事項，作為下一 session 的起點

## 參數

本 skill 接受兩種模式：

- 不帶參數：互動式詢問今天做了什麼
- 帶上今日摘要字串：直接處理

## 步驟

### Step 1: 取得今日摘要

如果使用者已附上摘要，直接使用。否則問：

> 今天做了什麼？請簡述（或貼上 session 記錄）。

### Step 2: 決定日期

```bash
$today = Get-Date -Format "yyyy-MM-dd"
$slug = "daily-$today"
```

### Step 3: 儲存到 Firebase

使用 Firebase MCP 將 session 記錄寫入 Firestore `sessions` collection：

- Collection: `sessions`
- Document ID: `$today`
- Fields:
  - `date`: `$today`
  - `summary`: 今日摘要
  - `completed`: 完成的項目列表（array）
  - `blocked`: 卡住 / 未完成的項目列表（array）
  - `next_actions`: 明天要接續的事項列表（array）
  - `tags`: `["daily-wrap"]`
  - `created_at`: Firebase timestamp

### Step 4: 產生 Markdown 記錄檔

產生一份完整的 session note，格式如下：

```markdown
# 每日進度記錄 — $today

## 今日完成
- [x] 事項 1
- [x] 事項 2

## 卡住 / 未完成
- [ ] 事項 3（原因：...）

## 明日待辦
- [ ] 事項 3 繼續
- [ ] 新事項

## 技術筆記
（任何值得記錄的踩坑或 learnings）
```

### Step 5: 寫入 GitHub repo

1. Clone / pull `ckt520728/2026Cordex`（暫存於 `$env:TEMP\2026Cordex`）
2. 將 Markdown 寫入 `<repo>/<slug>.md`
3. `git add`, `git commit -m "每日進度記錄 $today"`, `git push origin master`

### Step 6: 同步到 Obsidian

1. 複製同一份檔案到 `G:\我的雲端硬碟\Second Brain\知識庫\2026 OpenCode\<slug>.md`
2. 更新 `G:\我的雲端硬碟\Second Brain\知識庫\index.md`
   - 更新 `updated` frontmatter 日期
   - 在「OpenCode 與 gstack」表格新增一行

### Step 7: 產生明日待辦摘要

在完成後，回報給使用者：

```
✅ 今日進度已存檔：
- Firebase: sessions/$today
- GitHub: ckt520728/2026Cordex/$slug.md
- Obsidian: 知識庫/2026 OpenCode/$slug.md

明日待辦 (N 項)：
1. xxx
2. xxx
```

### Step 8: 如已設定 Windows 排程，觸發 /retro

如果當天是星期日，且 gstack 已安裝，建議執行 `/retro` 做週回顧。
