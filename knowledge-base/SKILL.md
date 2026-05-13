---
name: knowledge-base
description: 個人知識庫的雙向工具——(A) 把外部素材(PDF、論文、文章、網頁、講義、影片字幕)整理成原子化、可連結、有引用的筆記寫入 Obsidian vault 或本地檔案系統;(B) 從現有知識庫查詢、跨筆記綜整、給出帶引用的答案。觸發詞:「加入我的知識庫」「存進 vault」「我之前讀過 X 嗎」「我的筆記裡有沒有提過 Y」「把這份 PDF 加進知識庫」「整理進 Obsidian」「query my knowledge base」「search my notes for」「綜整我看過所有講 X 的筆記」「我之前對 Z 是怎麼想的」「ingest this paper」。優先走 Obsidian(via mcp-obsidian),沒有 vault 才用檔案系統 fallback。也可整合 NotebookLM(via notebooklm-mcp)做語意檢索。不適用:單次性研究筆記整理(那是 research-organizer 的工作,本 skill 是「整理 + 存入長期庫 + 跨筆記連結」)、單純檔案搜尋(直接用 Grep / Glob)、Obsidian plugin 安裝(那是 mcp-obsidian-setup)。
---

# Knowledge Base

## 目的

把使用者的閱讀、研究、思考累積成**有結構的個人知識庫**,而不是一堆散落的 markdown 檔案。

兩個方向:

1. **Ingest**(寫入):外部素材 → 結構化筆記 → vault
2. **Query**(查詢):自然語言提問 → 跨筆記檢索 → 帶引用的答案

跟「向量資料庫 RAG」的差別:這個 skill 假設知識庫的價值來自**人為的結構**(連結、標籤、層級、原子化),而不是 embedding 相似度。Embedding 適合在你**不認識自己的資料**時找東西;個人知識庫的目的剛好相反——你要熟悉自己的資料,並建立連結。

## 環境偵測:用哪個 backend

啟動時先依此順序判斷:

1. **Obsidian MCP** 可用且使用者有設定 vault → 主推
2. 使用者明說「不要存進 Obsidian」或 Obsidian MCP 不可用 → **檔案系統 fallback**(預設 `<working-dir>/knowledge-base/`)
3. 進階:使用者有 **NotebookLM** notebook 想配合 → 寫入時同時 source_add 到對應 notebook;查詢時並用 notebook_query

不確定時詢問:「你想存進 Obsidian vault,還是放本地資料夾?」**只問一次**,記下使用者偏好,後續用同樣 backend。

## 模式判定

使用者一說話,先判斷是 ingest 還是 query:

| 訊號 | 模式 |
|------|------|
| 給了一份外部素材(PDF / URL / 貼上的長文) | **Ingest** |
| 「加入知識庫」「存進 vault」「ingest」 | **Ingest** |
| 「我之前 / 我有沒有 / 我的筆記裡」 | **Query** |
| 「綜整 / 整理我所有講 X 的筆記」 | **Query** |
| 純問題沒附素材(「什麼是 X?」) | **Query**(從 vault 找,找不到再坦白說沒有) |
| 模糊不清 | 直接問:「是要把這份東西**存進**知識庫,還是要從知識庫**查詢**?」 |

---

## Ingest 流程(寫入知識庫)

### I-Step 1:讀進素材

- PDF → 用 anthropic-skills:pdf 抽文字 + 保留頁碼
- DOCX → anthropic-skills:docx
- URL → WebFetch
- 對話貼上的長文 → 直接處理
- 多檔(資料夾)→ Glob 列出,**逐檔**處理,不要合併成一個巨型筆記

### I-Step 2:決定切分粒度(原子化 or 整篇)

**原子化筆記**(Zettelkasten 風格)——一個概念一個筆記。適合:
- 論文(每個 key idea 一筆,加一個 overview 筆記串起來)
- 教科書章節
- 內容密度高、概念多的素材

**整篇筆記**——一份來源一個檔案。適合:
- 部落格文章 / Medium / 新聞
- 講義 / 演講逐字稿
- 內容輕、概念集中的素材

判定標準:**讀完素材後,自問「這份東西裡有幾個我未來想單獨引用的概念?」**
- 1-2 個 → 整篇
- 3+ 個 → 原子化

如果使用者明說了偏好(「拆成多個」/「整篇就好」),照辦。

### I-Step 3:Vault 內現有筆記搜尋(連結準備)

寫新筆記前,**先**在 vault 裡搜尋相關概念,找出可以連結的既有筆記:

- Obsidian backend:用 `obsidian_simple_search` 搜素材的關鍵詞
- 檔案系統 backend:用 Grep 搜 `<vault>/*.md`

把命中的筆記**標題**收集起來,等下寫入新筆記時用 `[[wikilinks]]` 連到它們。

**不要**:沒搜尋就直接寫新筆記,結果新筆記跟既有的相關筆記之間沒有連結——這是個人知識庫最常見的失敗模式。

### I-Step 4:寫筆記(每份檔案的標準格式)

```markdown
---
title: <一句話標題,可以是原文或自取>
source:
  type: paper | book | article | video | lecture | personal
  authors: [<作者 1>, <作者 2>]
  url: <原始連結,若有>
  file: <原始檔名,若有>
  published: <YYYY-MM-DD,若知道>
date_ingested: <YYYY-MM-DD,今天>
status: inbox  # 之後使用者自己改成 reviewed / archived
tags: [<3-7 個英文 tag,用 kebab-case>]
related: ["[[既有筆記 1]]", "[[既有筆記 2]]"]
---

# <標題>

## 為什麼讀這個

<2-3 句,只在使用者明確說了「為什麼讀」時才寫;沒說就刪整個區塊>

## 核心主張

<原作者想證明 / 主張的東西。1 段話。>

## 我的摘錄

> "<原文直接引用 1>"
> —— <page X / section Y / minute Z>

<這段對我有用,因為...(可選的個人註解,沒想到就刪)>

> "<原文直接引用 2>"
> —— <出處>

## 我的延伸思考

<跟自己的工作 / 研究 / 其他筆記的連結。可以提到 [[既有筆記]],可以列疑問,可以列待驗證的假設。>

## 與其他筆記的關係

- 補充了 [[既有筆記 A]] 的 ...
- 跟 [[既有筆記 B]] 的觀點衝突,因為 ...
- 啟發了 [[新問題 / 新筆記題目]](尚未寫)

(沒找到相關既有筆記就刪這整區塊)
```

**強制規則**:
- `tags` 只能用 kebab-case 英文(`large-language-models`,不是 `Large Language Models` 或 `大型語言模型`)——這樣才能跟其他筆記的 tag 對得起來
- `tags` 控制在 3-7 個。多了就失去篩選價值
- 每個原子筆記**至少**有一個 `[[wikilink]]`,連到 vault 內既有筆記。如果 vault 是空的或真的找不到,在筆記末尾加 `TODO: 找不到相關筆記,待 vault 累積後回頭連結`
- **保留語言**:原文是中文就用中文寫筆記,英文就英文。摘錄區一律保留原語言

### I-Step 5:決定存放位置

- Obsidian backend:預設 `<vault>/Inbox/<YYYY-MM-DD> <slug>.md`
  - Inbox 代表「未審查」狀態,使用者之後會移動到正式分類資料夾
- 檔案系統 fallback:`<vault-root>/Inbox/<YYYY-MM-DD> <slug>.md`

如果使用者已經有自己的資料夾結構(e.g. `/Papers/`、`/Books/`),根據 `source.type` 自動歸位:
- `paper` → `/Papers/`
- `book` → `/Books/`
- `article` → `/Articles/`
- 其他 → `/Inbox/`

### I-Step 6:可選——同步到 NotebookLM

如果使用者明說「也加進 NotebookLM」或之前已建立對應 notebook:
- `mcp__notebooklm-mcp__source_add` 把原始檔加到 notebook
- 這樣未來可以 NotebookLM 語意檢索 + Obsidian 結構導航雙路並行

不主動做,問了再做。

### I-Step 7:回報

只說:
- 寫到 `<path>`
- 連到了 N 個既有筆記:[[筆記 A]], [[筆記 B]]
- (如果 N=0)沒找到相關既有筆記,已標 TODO

**不要**把整篇筆記再貼一次。

---

## Query 流程(從知識庫查詢)

### Q-Step 1:理解查詢類型

| 查詢類型 | 例子 | 應對方式 |
|---------|------|---------|
| 概念定義 | 「什麼是 attention mechanism?」 | 找直接講該概念的筆記,優先用使用者自己寫過的詮釋 |
| 我有沒有 | 「我之前讀過 X 嗎?」 | 全 vault 搜尋,有就列出筆記;沒有就明確說「沒找到」 |
| 跨筆記綜整 | 「整理我所有講 X 的筆記」 | 多筆檢索 + 讀全內容 + 寫一篇 synthesis |
| 矛盾 / 對照 | 「我之前對 X 的看法跟最近有沒有改變?」 | 按 `date_ingested` 排序,顯示時間線上的觀點變化 |
| 找來源 | 「X 觀點我是從哪本書讀到的?」 | 在筆記裡搜尋該觀點,回傳 source frontmatter |

### Q-Step 2:檢索

Obsidian backend:
- 簡單關鍵字 → `obsidian_simple_search`
- 多條件(tag + 內容)→ `obsidian_complex_search`
- 列檔案 → `obsidian_list_files_in_dir`

檔案系統 backend:
- Grep + Glob

NotebookLM(如使用者明說配合)→ `mcp__notebooklm-mcp__notebook_query` 做語意檢索

**不要**:只看標題就回答。檢索到的筆記要**用 Read 完整讀過**(`obsidian_get_file_contents` 或檔案系統 Read),才有資格回答。

### Q-Step 3:綜整答案

每個說法都要附引用:

```
LLM 的 attention 機制本質是 weighted sum (from [[2024-11-03 Attention Is All You Need]]),
但實務上不同 head 學到的東西高度冗餘 (from [[2025-02-18 BERT Pruning Notes]]),
所以你之前在 [[2025-03-10 Project ABC Plan]] 提過想試 head pruning——可以重新考慮。
```

格式重點:
- 每個事實附 `(from [[筆記名]])`
- 如果是使用者自己的延伸思考,標 `(your note in [[筆記名]])`
- 引用原文時用 blockquote
- **不要捏造**——vault 找不到的東西不能回答;只能說「vault 中沒找到 X,但若你想我可以從通用知識回答(會清楚分開)」

### Q-Step 4:處理矛盾

跨筆記如果有衝突觀點,**明確標出來**:

```
你的筆記在這點上有分歧:
- [[2024-09-01 Note A]] 主張 X
- [[2025-04-20 Note B]] 主張相反
時間上看,你的觀點是從 X 變成 -X。要不要我幫你寫一篇 synthesis 釐清?
```

### Q-Step 5:可選——把這次 Q&A 存回 vault

如果這次的綜整本身有價值,問使用者:
- 「這次的回答要不要存成一篇 synthesis 筆記到 `<vault>/Synthesis/`?」
- 如使用者說好,寫一份新筆記,frontmatter 標 `source.type: synthesis`,正文是這次 Q&A 的整理,並連回所有引用的原筆記。

**不主動寫**——問了再做。

---

## 重要的編輯原則

**Atomic > Monolithic**:寧可一份素材拆成 5 個原子筆記 + 1 個 overview,也不要寫一個 5000 字的巨型筆記。理由:三個月後想引用「第 3 點」時,5000 字筆記只能用「貼整篇」這種粗糙方式;5 個原子筆記可以精準連到某一筆。

**Link forward, not back**(預設):新筆記**單向**連到既有筆記,**不要**主動修改既有筆記讓它反向連回新筆記。理由:Obsidian 的 backlinks 自動處理反向關係,你手動加只會製造維護成本。例外:使用者明說「也更新舊筆記加連結」。

**`status: inbox` 是預設**:不要直接寫 `status: reviewed`——審不審查是使用者的事,skill 沒資格代為決定。使用者之後在 Obsidian 裡自己改 status。

**摘錄保留原文,延伸思考分開**:
- 「我的摘錄」區塊 = 原文 verbatim,用 blockquote
- 「我的延伸思考」區塊 = 我(使用者)自己的話,沒有 blockquote
這兩區分開的理由:三年後你需要知道哪些是原作者說的、哪些是你自己想的——混在一起就無法引用了。

**tags 是 vault 級協定**:第一次寫筆記時要的 tag 命名規則,後續所有筆記都要遵守。所以在 ingest 時,**先用 obsidian_simple_search 看 vault 既有的 tag 命名習慣**,跟著用,而不是憑空造新 tag。

**不捏造引用**:Query 模式回答問題時,只能引用 vault 裡**真實存在**的筆記。如果 vault 沒有相關內容,坦白說「沒找到」。**絕對不能**編一個假筆記名讓回答看起來很豐富。

## 跟其他 skill 的協作

- **research-organizer 的輸出 → 直接 ingest 進知識庫**:research-organizer 產出 `notes_xxx.md` 後,使用者說「加入知識庫」→ 本 skill 接手,加 frontmatter、找連結、寫進 vault
- **meeting-minutes 的決議 → 可選擇 ingest**:重要會議的決議筆記可以變成 `source.type: meeting` 的知識庫筆記,日後查「我們之前對 X 是怎麼決定的」就找得到
- **article-writer 寫文章前 → 先 query 知識庫**:寫文章的素材常常已經在 vault 裡了,先 query 出來再餵給 article-writer

## 不要做的事

- ❌ 不要呼叫外部 embedding API,也不要自己跑 sentence-transformers——本 skill 走「結構化 + 連結」路線,不是 vector RAG
- ❌ 不要在沒搜尋既有筆記的情況下寫新筆記(會孤島化)
- ❌ 不要產出 `tags: []` 的筆記(沒 tag 等於沒進系統)
- ❌ 不要把同一份 PDF ingest 兩次而沒提醒使用者(寫入前用檔名/標題搜一下)
- ❌ Query 模式不要從通用知識回答然後假裝是 vault 來的——這會污染使用者對自己知識庫的信任
- ❌ 不要主動修改既有筆記去「補連結」,除非使用者明說
- ❌ 不要在 chat 裡把整篇筆記再貼出來——使用者自己會在 Obsidian / vault 開
