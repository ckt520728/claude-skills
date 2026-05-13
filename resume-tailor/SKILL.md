---
name: resume-tailor
description: 把現有履歷根據特定職缺 JD(Job Description)做客製化調整——重新排序、調整用詞、補強關鍵字、刪減不相關段落,**但絕不捏造**事實。觸發詞:「幫我改履歷」「履歷對著這個職缺優化」「tailor my resume」「optimize resume for this job」「把履歷調整成適合 XX 公司」「這份 JD 我的履歷要怎麼改」「投這個職缺前幫我看一下履歷」。也支援:同一份履歷對多個職缺產出多版、附帶寫求職信(cover letter)、ATS 友善純文字版。不適用:從零生成履歷(這 skill 假設使用者已有履歷)、面試準備、薪資談判建議。
---

# Resume Tailor

## 目的

幫使用者把**已有的履歷**針對特定職缺做最適化:強調對得上的經驗、重排順序、自然帶入關鍵字、移除不相關段落。

這個 skill 跟「叫 LLM 重寫履歷」最大的差別是:**只重寫、不捏造**。使用者投出去的履歷上每一個字、每一個數字,都必須在原始履歷裡找得到根據,或經過使用者親口確認。

## 🚨 鐵則:零捏造(Zero-Fabrication Rule)

履歷捏造的後果不是「被退件」——是**入職後被查到、被開除、被產業列黑名單**。所以本 skill 嚴守以下:

| 元素 | 規則 |
|------|------|
| 數字 / 指標 / % | 原文有就保留,**原文沒有就絕對不能加**。寧可留下「improved performance」,也不能改成「improved performance by 30%」 |
| 公司 / 職稱 / 日期 | 100% 照原文,不能換職稱、不能延長任職時間、不能拉抬團隊規模 |
| 技術 / 工具 / 語言 | JD 提到但原履歷沒有的技術,**禁止**自行塞進履歷。即使「JD 要 Kubernetes,而你寫了 Docker」,也不能直接改成 Kubernetes |
| 學歷 / 證照 | 完全照原文,不可升級 |
| 成就動詞 | 可以換更精準的動詞(`worked on` → `built`),但**不可以**升級語意強度(`contributed to` → `led`) |

**唯一例外**:使用者在 Step 2 的 gap 確認階段**親口告訴你**「我其實做過 X 但忘了寫」,此時可以加,但要在輸出時用 `<!-- 使用者於 <date> 補充:... -->` 標明來源。

## 觸發後的工作流程

### Step 1:收集兩份輸入

1. **履歷**:
   - 對話貼進來 / `.md` / `.txt` / `.docx` / `.pdf`
   - DOCX → 用 anthropic-skills:docx 讀取
   - PDF → 用 anthropic-skills:pdf 抽文字
2. **JD**:
   - 貼進來 / 檔案路徑 / URL(URL 用 WebFetch)
3. **附加偏好**(若使用者沒明說就用預設):
   - 輸出格式:預設 Markdown。也可 `ats-plain`(純文字、無 markdown 符號、給 ATS 系統用)、`docx`(走 docx skill 產 .docx)
   - 語言:履歷是中文就中文、英文就英文。**混雜不翻譯**
   - 客製強度:預設「moderate」(重排 + 換詞 + 強調)。可選 `conservative`(只重排不換詞)、`aggressive`(允許整段改寫,但仍不可捏造)

### Step 2:Gap 分析(寫前必跑,寫後不能補)

讀完兩份輸入後,**先暫停**,產出以下分析給使用者看:

```markdown
## JD 拆解

**硬性需求**(must-have):
- <條 1>
- <條 2>

**加分項目**(nice-to-have):
- <條 1>

**JD 中重複出現的關鍵字 / 工具**:
- <Python>(出現 5 次)
- <FastAPI>(出現 3 次)
- ...

**JD 隱含的公司價值/文化訊號**:
- <例如:強調 ownership / 強調快速迭代 / 強調跨部門協作>

---

## 履歷對應分析

### ✅ 履歷已有,且 JD 重視的(將強調)
- <某段經驗 → 對應 JD 第 X 條>

### 🔄 履歷已有,但表述沒對到 JD 用語(將換詞)
- 履歷寫「web service development」→ JD 用語「distributed systems」→ 建議調成 `distributed web services` (如果你的實際經驗確實是分散式架構)

### ⚠️ JD 想要,但履歷沒寫到——需要你確認
為了避免我幫你捏造,請逐項回答以下:

1. **Kubernetes**:你有實際使用經驗嗎?
   - (a) 有,只是履歷沒寫 → 請補:做過什麼專案、多大規模、多久
   - (b) 沒有 → 跳過,不會塞進履歷
   - (c) 略懂,但不敢說有實戰 → 跳過,不塞進履歷主文

2. **Team lead 經驗**:你有帶過人嗎?
   - ...

### ❌ JD 不重視,履歷佔很多版面的(將縮減)
- <例如:你寫了三段關於 frontend 的經驗,但 JD 是純後端職>

---

請回答上面的 ⚠️ 項目,我再開始改履歷。
```

**例外**:如果使用者一開始就明說「skip review, just rewrite」「直接改不用問」,跳過暫停,但在最終輸出的開頭明確標註「以下版本未經 gap 確認,可能漏掉你有但沒寫的經驗」。

### Step 3:依使用者回答,產出客製版履歷

收到使用者對 ⚠️ 項目的回應後,開始改寫。每一段改動要符合:

1. **保留原始結構**(學歷/經歷/技能/作品這幾個區塊的順序不變,除非使用者明說可重排)
2. **同段內可以重排 bullet**——把對得上 JD 的 bullet 移到該段最上面
3. **bullet 用詞優化**:
   - 動詞從 `worked on` / `helped with` 這類弱動詞,換成 `built` / `shipped` / `migrated` / `optimized`(只能在你**確實主導**的工作上換)
   - 模糊描述換成精準描述,例如 `worked with various databases` → `worked with PostgreSQL, MongoDB, Redis`(只能用原本就在履歷裡或使用者已確認的技術)
4. **關鍵字自然帶入**:JD 用 `microservices`,而你的原履歷用 `service-oriented architecture`——可以調整成 `microservices` **如果你的實際架構確實是微服務**;但不要為了塞關鍵字而把單體應用包裝成微服務
5. **無關段落縮減**:JD 不關心的經驗從 3 個 bullet 砍到 1 個,或整段移到附錄

### Step 4:輸出兩份檔案

**A. 客製履歷**:`resume_<company>_<role-slug>_<YYYY-MM-DD>.md`

開頭加註解(只有 Markdown 版有,ATS 純文字版不要):

```markdown
<!--
Tailored for: <Company> · <Role>
JD source: <URL 或檔案路徑>
Date: <YYYY-MM-DD>
Base resume: <原始履歷檔名>
User-confirmed additions: <列出 Step 2 中使用者親口補充的項目,沒有就寫 None>
-->
```

**B. 改動清單**:`resume_<company>_<role-slug>_changes.md`

讓使用者**逐項審查**有沒有問題:

```markdown
# 改動清單

## 1. 段落重排
- 把「<某經驗>」從第 3 段移到第 1 段(理由:JD 第 X 條重視)

## 2. 用詞替換
| 原文 | 改後 | 理由 |
|------|------|------|
| worked on web service | built distributed web service | 對應 JD 用語 + 你的經驗確實是分散式 |

## 3. 新增內容(來自你的補充)
- 在「<某段>」加上「<新 bullet>」——根據你在 chat 中提到的:「<原話>」

## 4. 刪減內容
- 移除「<某 bullet>」(理由:JD 完全不相關)

## ⚠️ 我刻意「沒做」的事(避免捏造)
- JD 要 5 年 Python,你履歷顯示 3 年 → 我**沒有**改日期
- JD 要團隊管理經驗,你沒提過帶人 → 我**沒有**加 lead 字眼
- 你某個 bullet「improved API performance」沒有數字 → 我**沒有**自己加 % 數字。若你記得實際數字,可以自己補
```

### Step 5(可選):求職信 + ATS 版

問使用者要不要:
- 順便寫一份 cover letter(基於這份客製履歷 + JD,300-400 字)
- 產 ATS-friendly 純文字版(無 `**bold**`、無 `- `、改用 `*` 或純換行)
- 走 anthropic-skills:docx 轉成 .docx

不要主動全做完。問,再做。

## 反 LLM 履歷句型禁用清單

看到這些**一定要改掉**:

- ❌ `Spearheaded` / `Orchestrated` / `Championed` / `Pioneered` —— 換成 `Led` / `Built` / `Shipped`
- ❌ `Leveraged` —— 換成 `Used`
- ❌ `Synergized` / `Streamlined cross-functional collaboration` —— 直接刪
- ❌ `Results-driven professional` / `Passionate about` / `Self-starter` —— 整段刪(沒有招募者讀 self-summary)
- ❌ `Worked closely with stakeholders to deliver value` —— 重寫成具體交付物
- ❌ 每個 bullet 都用同一個動詞起頭(全部 `Developed`)—— 動詞多樣化
- ❌ `Utilized` —— 換成 `Used`
- ❌ 中文履歷的「具備溝通能力」「抗壓性強」「具團隊合作精神」—— 刪,招募者不信這些
- ❌ Emoji(技術履歷不用 emoji)

## 重要的編輯原則

**JD 關鍵字 ≠ 履歷關鍵字**:有 ATS 過濾的職缺,確實需要關鍵字命中率。但塞關鍵字的方式必須是「找出你履歷裡描述同一件事的不同說法,改用 JD 的說法」,不是「把 JD 的詞硬塞進不相關的句子」。

**指標化只能基於既有事實**:
- 原:「improved system performance」
- ✅ 可以:「reduced API latency」(更精準的動詞,但沒加數字)
- ❌ 不可以:「reduced API latency by 40%」(沒人查過你不能加)
- ✅ 可以:在改動清單裡標註「⚠️ 此 bullet 可以加數字加分,你記得實際幅度嗎?」

**強度匹配**:履歷長度應該配合資歷。如果使用者只有 2 年經驗卻寫了 3 頁,客製時要協助縮減。如果有 15 年資歷只有 1 頁,要協助展開。但**不能**為了長度去稀釋或灌水。

**保留使用者口語特徵**:有些使用者履歷裡有獨特的個人語氣(例如「shipped a side project that 3 people actually use」),這種反 LLM 樣板的句子是優勢,不要被改成 standard corporate speak。

## 輸出檔案的編碼

UTF-8 無 BOM。Windows PowerShell 環境用 Write 工具或:

```powershell
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($path, $content, $utf8NoBom)
```

## 不要做的事

- ❌ 不要呼叫外部 LLM API
- ❌ 不要跳過 Step 2 的 gap 分析,除非使用者明說「skip review」
- ❌ 不要把「我刻意沒做的事」這節從改動清單中省略——這節是使用者信任這個工具的基礎
- ❌ 不要產出超過原履歷 20% 長度的版本(代表你塞了太多無中生有的東西)
- ❌ 不要主動寫 cover letter / ATS 版 / docx 版——問了再做
- ❌ 不要在 chat 裡把整份客製履歷再貼一次——使用者去開檔案
- ❌ 不要對使用者已有的個人風格(語氣、自嘲、獨特用詞)做 standardization——除非他要求
