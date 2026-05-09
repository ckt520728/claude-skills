---
title: 安裝 SOIL 三件套簡報 Skill 的踩坑與啟示
date: 2026-05-09
tags:
  - claude-code
  - skills
  - soil-teaching-deck
  - presentation-tools
  - yaml
  - 踩坑紀錄
  - 知識成長
type: 創作-技術筆記
related:
  - "[[Codex 懶人包/02.5-連接GitHub與Obsidian-安裝踩坑]]"
---

# 安裝 SOIL 三件套簡報 Skill 的踩坑與啟示

> 日期：2026-05-09
> 主題：在 Claude Code 上安裝 `soil-image-deck` / `soil-teaching-deck` / `soil-html-deck` 三個簡報生成 Skill 的失敗、修正與意外收穫。

---

## 一、想做什麼

收到一個 zip：`skills_claude-20260509T003246Z-3-001.zip`，裡頭是李俊儀教授 SOIL 教學設計的三件套簡報技能，要安裝到 Claude Code，讓我以後在 Claude 介面就能一句話產出三種型態的簡報：

| Skill | 產出格式 | 用途 |
|---|---|---|
| `soil-image-deck` | 純圖片 `.pptx`（每頁一張 AI 圖） | 直播暖場、社群貼文、視覺衝擊 |
| `soil-teaching-deck` | 圖 + 可編輯文字 `.pptx` | 教學現場、後續可手動微調 |
| `soil-html-deck` | 單一 `.html`（base64 內嵌圖、可互動） | 線上研習、可分享連結 |

三個 Skill 都依林長揚 30 條簡報原則 + SOIL 六引擎設計，是經過實戰調校的工作流。

---

## 二、踩到的坑

### 坑 1：YAML frontmatter 解析失敗

安裝時跳警示：

```
Skill.md must start with YAML front matter
```

但檔案開頭明明就是 `---`，hex dump 看也沒有 BOM 或編碼髒污。

**根因找到了。** 三個 SKILL.md 的 frontmatter 都長這樣：

```yaml
---
name: soil-image-deck
description: >
  SOIL 純圖片教學簡報技能。…
  …
---
```

關鍵在 `description: >`——這是 YAML 的 **folded block scalar**（折疊型多行字串），會把換行折成空格。雖然語法上合法，但 Claude Code 的 skill loader 對這個欄位解析較嚴格，遇到折疊型多行就誤判為「沒有 frontmatter」。

對照已能正常運作的 `lecture-notes/SKILL.md`，它用的是：

```yaml
description: |
  Generate beautifully formatted lecture notes…
```

`|` 是 **literal block scalar**，保留原始換行。把三個 SKILL.md 的 `>` 都改成 `|`，loader 立刻接受。

### 坑 2：dead reference

`soil-teaching-deck/SKILL.md` 第 21 行寫：

```markdown
> 完整理論參考：讀取 [references/soil-theory.md](references/soil-theory.md)
```

但 zip 內並沒有 `references/` 子目錄。這是個 dead link，執行時 Claude 會試圖 Read 失敗。已改成中性註記。

---

## 三、修正後的做法

```yaml
# 修正前
description: >
  SOIL 純圖片教學簡報技能。…

# 修正後
description: |
  SOIL 純圖片教學簡報技能。…
```

接著 `cp -r` 到 `C:\Users\User\.claude\skills\`，loader 立刻偵測到三個 Skill 並列入可用清單：

```
- soil-html-deck
- soil-image-deck
- soil-teaching-deck
```

---

## 四、意外的查證收穫：gpt-image-2 + Codex 訂閱

三個 Skill 都依賴 `draw` skill 呼叫 OpenAI 的 `gpt-image-2` 模型生圖。我訂閱了 ChatGPT Plus + Codex，所以查證了一下取用權：

| 取得管道 | 是否可用 gpt-image-2 |
|---|---|
| **Codex 內** | ✅ 用既有 ChatGPT 訂閱即可，不必另外申請 API key |
| **ChatGPT 網頁/桌面 App** | ✅ Instant 模式所有訂閱者（含免費）都能用；Thinking 模式需 Plus/Pro |
| **OpenAI API** | ✅ 需 API key + 帳戶驗證；定價 $30/M output tokens |

**關鍵時序：**
- 2026-04-21：OpenAI 發布 gpt-image-2，當天在 Codex 與 API 開放
- 2026-04-22：ChatGPT 網頁版開放
- 2026-05-12：DALL-E 2/3 退役

對應到我的需求——在 Claude 介面用 SOIL skills 做 PPT，方案有兩條：
1. **打通 Codex 走 API**：在 `draw` skill 裡呼叫 OpenAI image API（需 API key，但我可以透過 Codex 訂閱對應的開發者額度 / 或另設 API key）
2. **生成內容由 Claude 處理、圖像跨工具協作**：Claude 規劃章節骨架與 layout，圖像生成這一步切到 Codex CLI 或 ChatGPT 網頁版

要在 Claude Code 內**完整跑完一次工作流**，最簡乾淨的路是方案 1，前提是 `draw` skill 已經在我的 `~/.claude/skills/` 內並設好 OpenAI API key 環境變數。下一步要：
- [ ] 確認本機 `draw` skill 的位置與 API key 設定
- [ ] 試跑一次 `soil-image-deck` 的最小範例（10 頁、low quality，預估 NT$3–4）

---

## 五、學到什麼（Pattern that travels）

1. **YAML 多行字串：寫 Skill 時統一用 `|`（literal），不要用 `>`（folded）。** 跨 loader 相容性更高、行為更可預期。
2. **dead reference 是隱形地雷。** zip 派發 Skill 前要先 `grep -n "\[.*\](.*\.md)"` 把所有外部連結列出來核對。
3. **錯誤訊息不一定講真話。** "must start with YAML front matter" 在這個案例其實是 description 欄位解析失敗的代償錯誤——下次遇到看似不合理的錯誤訊息，先把鄰近欄位逐個拆出來測試。
4. **取用權查證不能憑印象。** Codex 訂閱者可用 gpt-image-2 是 2026-04-21 才開放的，模型可用性月月在變，動手前一定 WebSearch 一次。

---

## 六、後續行動清單

- [x] 三個 SKILL.md 的 frontmatter 修正
- [x] 安裝到 `C:\Users\User\.claude\skills\`
- [x] 在每個 SKILL.md 末尾加上「安裝踩坑紀錄」段落
- [x] 推送修正版到 `ckt520728/claude-skills` GitHub repo
- [x] Obsidian 知識成長紀錄（本檔）
- [ ] 確認 `draw` skill 與 OpenAI API key 設定
- [ ] 試跑 `soil-image-deck` 最小範例驗證端到端工作流

---

## 七、外部資料來源

- [GPT Image 2 Model | OpenAI API](https://developers.openai.com/api/docs/models/gpt-image-2)
- [Introducing gpt-image-2 — available today in the API and Codex](https://community.openai.com/t/introducing-gpt-image-2-available-today-in-the-api-and-codex/1379479)
- [Introducing ChatGPT Images 2.0 | OpenAI](https://openai.com/index/introducing-chatgpt-images-2-0/)

---

> 這份紀錄同步存於 GitHub `ckt520728/claude-skills` 的 commit message 與該 repo 的 `docs/2026-05-09-install-pitfalls.md`，供未來重灌或他人安裝時參考。
