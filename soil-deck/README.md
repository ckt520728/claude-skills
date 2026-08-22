# soil-deck — SOIL 三合一簡報 Skill

> 給開發者 / 其他 agent 讀的快速說明。完整工作流請看 [`SKILL.md`](SKILL.md)。

---

## 這是什麼

把原本三個獨立的 SOIL 簡報 skill（`soil-image-deck` / `soil-teaching-deck` / `soil-html-deck`）合併成**單一 skill**，
共享 SOIL 六引擎 + 林長揚 30 原則的判斷邏輯，只在最終輸出階段（引擎 6）依模式分流。

| 模式 | 觸發詞 | 輸出 | 文字可編輯？ |
|------|-------|------|------------|
| **image** | 「純圖片簡報」、「全圖簡報」、「每頁都是 AI 圖」 | `.pptx`（每頁 1 張 1536×1024 滿版圖）| ❌ 文字燒在圖裡 |
| **teaching** | 「教學簡報」、「上課用投影片」、「文字可編輯的 .pptx」 | `.pptx`（底圖 + PowerPoint 文字物件）| ✅ 雙擊可改 |
| **html** | 「HTML 簡報」、「網頁版簡報」、「互動式簡報」、「可分享連結」 | 單一 `.html`（base64 內嵌圖）| ✅ HTML 編輯 |

---

## 檔案結構

```
soil-deck/
├── SKILL.md                # 主入口：模式判斷 + 引擎 1–5（共用）+ 林長揚 30 原則
├── modes/
│   ├── image-deck.md       # 引擎 6（image 版）+ baked / plate 子模式
│   ├── teaching-deck.md    # 引擎 6（teaching 版）+ visuals / geometry + 診斷修改
│   └── html-deck.md        # 引擎 6（html 版）+ 互動元件 + Chart.js
├── scripts/
│   └── pack_pptx.py        # image / plate 模式的打包腳本（python-pptx）
└── README.md               # 本檔
```

---

## 安裝

複製 `soil-deck/` 整個資料夾到 `~/.claude/skills/`（或對應作業系統路徑），重啟 Claude Code 即可。

```bash
# Linux / macOS
cp -r soil-deck ~/.claude/skills/

# Windows（PowerShell）
Copy-Item -Recurse soil-deck "$env:USERPROFILE\.claude\skills\"
```

⚠️ frontmatter 一律用 `description: |`（literal block），不要用 `>`（folded），避免 loader 解析失敗。

---

## 依賴

### 三模式共用
- **draw skill**（gpt-image-2 生圖）— 需 `OPENAI_API_KEY`、OpenAI 組織完成 Individual 驗證
- **Python**：`Pillow`、`PyYAML`

### image / teaching 模式
- **Python**：`python-pptx`、`openai`
- （teaching 進階）**Node**：`pptxgenjs`

### teaching 模式（diagnostic 子模式）
- **Python**：`markitdown[pptx]`
- **soffice**（LibreOffice）+ `pdftoppm`（poppler-utils）轉圖檢視

### teaching 模式（geometry 子模式）
- **Python**：`cairosvg`
- 外部腳本：`/mnt/skills/user/jh-math-geometry/scripts/geometry_renderer.py`

### html 模式
- 純前端：Chart.js（CDN）+ Google Fonts（CDN）
- 本地工具：`Pillow`（base64 內嵌前的 resize）

一鍵裝齊：

```bash
pip install openai python-pptx Pillow PyYAML cairosvg "markitdown[pptx]" --break-system-packages
npm install -g pptxgenjs
```

---

## 與原三個 skill 的關係

| 原 skill | 在新版的位置 |
|---------|-------------|
| `soil-image-deck/SKILL.md` | 拆成共用部分（→ `SKILL.md`）+ image 專屬（→ `modes/image-deck.md`）|
| `soil-teaching-deck/SKILL.md` | 拆成共用部分（→ `SKILL.md`）+ teaching 專屬（→ `modes/teaching-deck.md`）|
| `soil-html-deck/SKILL.md` | 拆成共用部分（→ `SKILL.md`）+ html 專屬（→ `modes/html-deck.md`）|
| `soil-image-deck/pack_pptx.py` | `scripts/pack_pptx.py`（image / plate 模式共用）|

原本三個資料夾仍保留在 repo（向後相容），但建議新使用情境一律用 `soil-deck`。

---

## 設計決策

### 為什麼合併？

1. 三個 skill 的引擎 1–5 幾乎一模一樣（概念 → 脈絡 → 頁面 → 認知 → 風格），重複維護成本高
2. 使用者經常在三種模式間猶豫，需要一個入口先問「你要哪一種」
3. 「同一份內容輸出三種格式」變得自然——共用前 5 顆引擎的產物，只重跑引擎 6

### 為什麼不再細分？

模式選擇就是 4 選 1（image / teaching / html / 診斷修改），不需要更細的子層。
plate（teaching-style 但純 python-pptx）作為 image 模式的進階子流程處理。

### 為什麼保留原 3 個資料夾？

避免破壞既有自動化（GitHub Actions、其他 agent 引用路徑）。等使用者全面切換後再清理。
