---
name: article-writer
description: 從一個題目或一份素材(研究筆記、草稿、論文、程式碼、會議內容)生出一篇可發布的長文,先產 outline 讓使用者改,再展開成完整文章。觸發詞:「幫我寫一篇文章」「寫一篇技術文章」「把這個整理成 Medium 文章」「draft a blog post」「write a technical article on...」「把這份筆記寫成文章」「幫我寫一篇 LinkedIn 貼文」「擴寫成部落格文章」。也適用於把 research-organizer 產出的研究筆記、會議逐字稿、或任何 .md 草稿擴寫成對外發布內容。支援多平台格式:Medium、dev.to、LinkedIn、個人 blog (Hugo/Jekyll frontmatter)、Substack。不適用:單純文字校對(交給寫作 LLM 直接做)、學術論文寫作(不同流派)、SOIL 教學簡報(改用 soil-teaching-deck)。
---

# Article Writer

## 目的

把一個題目 + 可選的素材,寫成一篇**可直接發布**的長文。預設兩段式:先 outline、使用者點頭後再擴寫,避免一次寫完發現方向不對要整篇重來。

## 觸發後的工作流程

### Step 1:聚焦 4 件事(只問必要的)

確認以下資訊。**如果使用者一開始就把這些都講清楚了,直接跳到 Step 2,不要再問**:

1. **題目**:一句話可以講完的核心主張(不是泛泛主題)
   - ❌ "AI in healthcare"
   - ✅ "為什麼門診醫師用 LLM 整理病歷反而會降低效率——三個我們團隊踩過的坑"

2. **素材**(可選):有沒有現成的草稿、筆記、研究記錄、程式碼可以參考?
   - 若有路徑 → 用 Read / Glob 讀進來
   - 若沒有 → 從題目本身展開(此時要明確告訴使用者「這篇會 100% 從題目生成,沒有引用實際資料」)

3. **平台**:預設 Medium 風格。其他常見選項:
   - `medium` / `dev.to`:會話式、code block 多、無 frontmatter
   - `linkedin`:短(800-1200 字)、hook 前置、少 code、多空行
   - `hugo` / `jekyll`:加 frontmatter (title, date, tags, draft)
   - `substack`:長敘事、少 code、可以更個人化
   - `personal-blog`:純 markdown,使用者後續自己加 frontmatter

4. **長度**:預設 1500-2500 字。其他:
   - short:600-1000 字(類似 LinkedIn)
   - long:3000-5000 字(深度技術文)
   - deep-dive:5000+ 字(教學/長篇)

如果使用者只給了題目,以上 2-4 用預設值繼續,不要連環問問題。

### Step 2:產 Outline 並暫停

產出 6-9 段大綱(原 code 寫死 8 段,但實務上 1500 字適合 5-6 段、5000 字適合 9-10 段,按長度調整)。

格式:

```markdown
# Outline: <文章標題>

**目標讀者**:<一句話描述。例:有 2-5 年經驗的後端工程師,正在評估要不要導入 LLM>
**核心主張**:<一句話,讀者讀完應該記住的那句>
**預估字數**:<根據長度設定>
**平台**:<medium / linkedin / hugo / ...>

---

## 1. <段落標題>
**這段要回答**:<一個具體問題>
**主要內容**:<3-5 個 bullet,各 1 句>
**會用到的素材**:<引用素材的哪幾段 / 哪個概念,如果有>

## 2. ...
```

然後**停下來**,跟使用者說:

> Outline 在上面,你想:
> (a) 直接展開成完整文章
> (b) 改 outline——告訴我哪段要改/砍/加
> (c) 換個切角重來

**例外**:如果使用者一開始就明確說「不要 review,直接寫完」「skip outline」「one-shot」之類,跳過暫停直接進 Step 3。

### Step 3:擴寫成完整文章

依 outline 展開時,每段套用以下原則:

**Hook 段**(第 1 段):
- 不要用「In recent years, AI has become...」這種 LLM 招牌開場
- 用具體場景、具體數字、或具體錯誤經驗起頭
- 第一段就要讓讀者知道「這篇跟我有什麼關係」

**論證段**(中間段):
- 每段一個論點,論點要可反駁(不要寫所有人都同意的廢話)
- 技術文章:**至少一個段落有實際 code block**(不是 pseudo code,是能跑的)
- code block 之後要有「為什麼這段這樣寫」的 1-2 句說明,不要只貼 code

**例子段**:
- 例子要具體到「你的同事讀完馬上知道是誰/哪個 PR/哪個專案」的程度
- 不要寫「Imagine you have a database with millions of rows...」這種空泛假設
- 如果使用者素材裡有真實例子,**直接用**,不要稀釋成「假設情境」

**收尾段**:
- 不要做 listicle 式總結(「In conclusion, we covered: 1)... 2)... 3)...」)
- 收尾要回扣 Hook 的具體場景,告訴讀者「現在你看完了,下一步可以做什麼」

### Step 4:平台微調

按 Step 1 第 3 點的平台補上對應元素:

| 平台 | 補上 |
|------|------|
| medium / dev.to | 不加 frontmatter。標題用 `#`(H1),次標題從 `##` 開始 |
| linkedin | 移除 H1,改成粗體標題。段落間多空一行(LinkedIn 沒 markdown 渲染)。砍掉長 code block,留短片段 |
| hugo | 加 frontmatter:`title`, `date`, `draft: true`, `tags`, `summary` |
| jekyll | 加 frontmatter:`layout: post`, `title`, `date`, `categories`, `tags` |
| substack | 不加 frontmatter。確保第一段是強 hook(Substack 預覽只截前 200 字) |
| personal-blog | 不加 frontmatter,純內容 |

### Step 5:寫檔 + 簡短回報

預設輸出檔名:`<slug>.md`,slug 從標題轉成英文/拼音的 kebab-case。

寫到使用者指定路徑;沒指定就寫到當前工作目錄。

回報只說:
- 路徑
- 字數
- 一句話:這篇最強的賣點是什麼(讓使用者決定要不要發)

**不要**在 chat 裡把整篇文章再貼一次。

## 重要的編輯原則

**第一人稱 + 具體**:這類文章的價值是「作者的真實經驗」,不是「教科書知識」。寫的時候用 "I"/"我",而不是 "we"/"one"。寧可講一個你踩過的坑,也不要列三個 best practices。

**反 LLM 文風清單**(以下這些寫法看到就改掉):
- ❌ "In today's fast-paced world of AI..."
- ❌ "It's important to note that..."
- ❌ "Let's dive deep into..."
- ❌ "delve into" / "leverage" / "robust" / "seamless"
- ❌ "In conclusion, ..." 結尾
- ❌ 每個段落都用 "Firstly, Secondly, Thirdly" 開頭
- ❌ 過度使用 emoji 分節(技術文一個都不要)

**code 要能跑**:任何 code block 都要是可以複製貼上就執行的(import 寫齊、變數定義齊全)。寫完後在腦中走一遍語法,有疑慮的部分用 Bash 跑一下驗證。

**素材引用要標來源**:如果使用者餵了 research notes 進來,引用具體段落時用 blockquote + 標明來源檔名。不要把素材裡的句子直接當自己的話用——既不誠實也容易被讀者抓包。

## 輸出檔案的編碼

寫檔一律用 UTF-8(無 BOM)。Windows PowerShell 環境用 Write 工具或:

```powershell
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($path, $content, $utf8NoBom)
```

## 不要做的事

- ❌ 不要呼叫外部 LLM API——Claude 本身就在寫,呼叫 OpenAI/Gemini 只是多一層失真且要錢
- ❌ 不要在 outline 階段就先寫好整篇——這樣使用者無法干預方向
- ❌ 不要把 LinkedIn 文章寫成 3000 字長文,也不要把深度技術文寫成 800 字
- ❌ 不要在文章中加「本文由 AI 協助撰寫」這類聲明——使用者要不要標自己決定
- ❌ 不要產出「7 個 tips」「10 種方法」式的列表文——除非使用者明確要 listicle
- ❌ 不要每段都加 emoji 標題(技術文 / Medium 主流文風完全不這樣寫)
