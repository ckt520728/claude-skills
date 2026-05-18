# kwota-daily-stack — 安裝說明

這份說明告訴你怎麼把 `kwota-daily-stack` skill 裝到一台電腦上(macOS / Windows 通用)。

## 1. 找到本機 Cowork skills 資料夾

**macOS**
```
~/Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin/<random-uuid>/<random-uuid>/skills/
```

**Windows**
```
%APPDATA%\Claude\local-agent-mode-sessions\skills-plugin\<random-uuid>\<random-uuid>\skills\
```

打開檔案總管 / Finder,你會看到 `dashboard-builder/`、`email-assistant/`、`article-writer/` 等現有 skill 資料夾,證明你找對地方。

> 路徑中那兩段 `<random-uuid>` 是你本機的工作階段識別碼,**每台電腦不同**——以實際資料夾名為準。

## 2. 建立 skill 資料夾並放入 SKILL.md

在上面那個 `skills/` 資料夾底下:

```
skills/
├── dashboard-builder/
├── email-assistant/
├── article-writer/
├── ...(其他既有 skill)
└── kwota-daily-stack/        ← 新建這個資料夾
    └── SKILL.md              ← 把 kwota-daily-stack-SKILL.md 改名放進來
```

**具體步驟**:
1. 在 `skills/` 底下新建空資料夾 `kwota-daily-stack`
2. 把 `kwota-daily-stack-SKILL.md`(從這個 outputs 資料夾複製)
3. 放進 `kwota-daily-stack/` 並重新命名為 `SKILL.md`(去掉前綴)

## 3. 重啟 Cowork

關掉 Cowork 完全離開,再重新打開——skill 載入器會在啟動時掃描 `skills/`。

## 4. 驗證 skill 已安裝

在 Cowork 對話裡輸入:
```
/kwota-daily-stack
```
如果有自動補全/出現該 skill,就裝好了。

或直接觸發:
```
跑我的每日 stack
```

## 5. 確認 MCP 依賴

這台電腦必須安裝並連好以下四個 MCP server:

| MCP | 用途 | 若缺少 |
|-----|------|--------|
| **Gmail MCP** | Email triage + Scholar alert 解析 | Email 與 Scholar 區塊跳過 |
| **Google Calendar MCP** | 今日行程 + 空檔識別 | 行程區塊跳過 |
| **NotebookLM MCP** | 最近 3 個 notebook 摘要 | **整個 skill 直接 halt** |
| **Google Drive MCP** | Dashboard 寫入第二大腦 `/一個知識庫/kwota-daily-stack/` | **整個 skill 直接 halt** |

WebSearch / WebFetch 是 Cowork 內建,不需另裝(用於 AI 主流四家媒體新聞)。

## 6. 確認 Google Drive 預備資料夾

在 Google Drive 上事先建立:
```
/一個知識庫/                ← 你的 Obsidian 第二大腦根目錄(應該已存在)
```
`/kwota-daily-stack/` 子資料夾不用手動建,skill 第一次跑時會自動建。

## 7.(選用)設定排程

如果想每天早上自動跑,在 Cowork 對話裡:
```
幫我設定每天早上 7 點跑 kwota-daily-stack
```

Cowork 會用 `create_scheduled_task` 建一個 cron `0 7 * * *` 的排程。

---

## 卸載

刪掉 `skills/kwota-daily-stack/` 整個資料夾,重啟 Cowork 即可。
排程要另外去 Cowork 側邊欄「Scheduled」區塊手動刪除。

## 升級

把新版 `SKILL.md` 覆蓋進 `skills/kwota-daily-stack/SKILL.md`,重啟 Cowork。
