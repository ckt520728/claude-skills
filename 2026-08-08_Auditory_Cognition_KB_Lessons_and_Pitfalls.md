# 專案收尾 — 踩過的坑與可重用做法

**專案：** 2026 Auditory cognition Liu RC — 以 Robert C. Liu 的著作建立 ACx↔mPFC 聽覺認知知識庫
**日期：** 2026-08-08（單一工作階段）
**成果：** 14 張論文卡片 + 綜合論述 + 中英雙語詞彙表 + 一次文獻檢索記錄 + 2 份 ADR
**環境：** Windows 10、PowerShell 5.1、Claude Code

本文寫給**未來的自己與其他 agent**。重點不是這個專案的內容，而是**哪些地方會踩坑、以及怎麼繞過**。

---

## 一、環境與工具的坑（附可用解法）

### 1. Read 工具讀不了 PDF，必須先抽文字

**症狀：** 直接 Read 一個 PDF 什麼也拿不到。
**解法：** PyMuPDF（`fitz`）。本機已安裝。

```python
import pathlib, fitz
doc = fitz.open(str(pdf_path))
text = "\n".join(doc[i].get_text() for i in range(len(doc)))
doc.close()
dest.write_text(text, encoding="utf-8")
```

**要點：** 抽出的文字寫到 **scratchpad**，不要污染專案資料夾。抽完再用 Grep/Read 去查。

### 2. 主控台是 cp950 — 印出中文會壞掉

**症狀：** Python 印 CJK 會當掉或變亂碼。
**解法：** **寫檔用 UTF-8，然後用 Read 讀回來驗證**，不要用 print / Write-Output 驗證。本專案寫完中文版後，是靠 `Read` 讀回第 20–27 行確認編碼正常的。

### 3. 出版社與資料庫的擋抓取行為（本專案實測）

| 目標 | 結果 | 可用解法 |
|---|---|---|
| bioRxiv 網頁（WebFetch） | **403** | 改用 `api.biorxiv.org/details/biorxiv/<doi>` 取 metadata |
| bioRxiv PDF | 可以 | `Invoke-WebRequest` + 瀏覽器 User-Agent，網址格式 `content/biorxiv/early/<yyyy>/<mm>/<dd>/<id>.full.pdf` |
| cell.com PDF | **403** | 無解，改走 PMC |
| PMC PDF 端點 | **回傳 1.8 KB 的 HTML stub**（假成功！） | 改抓 PMC **HTML** 頁面再轉文字 |
| Europe PMC `fullTextXML` | 非 OA 論文 **404** | 同上，改抓 HTML |
| Europe PMC REST search | ✅ 穩定好用 | 見下方「可重用配方」 |

**最陰險的一個：** PMC 的 PDF 端點不會報錯，而是回傳一個 1.8 KB 的 HTML 檔案，副檔名還是 `.pdf`。
**教訓：下載後一定要檢查檔案大小**，不要只看有沒有丟例外：

```powershell
if ($len -gt 100000) { "OK" } else { "TOO SMALL ($len bytes) — 可能是擋抓取的 stub" }
```

### 4. 資料夾不是 git repo — 沒有 undo

本專案資料夾在 `Documents\` 底下，**不是 git repo**。任何覆寫都無法復原。

**因此：** 產生中文版時選擇**並存**（`cards-zh/`）而非取代。任何大批修改前，先 `git init`。

### 5. 路徑含空格與中文

`2026 Auditory cognition Liu RC` 有空格；Obsidian 路徑含中文。**每次都要引號包起來**。Bash 工具用 glob 展開中文檔名容易出事，改用 PowerShell 或 Python `pathlib` 較安全。

---

## 二、來源與語料庫的坑

### 6. 最大的坑：**要研究的那篇論文不在資料夾裡**

使用者給了演講摘要與 7 篇參考文獻。做完 blindspot pass 才發現：**摘要所描述的那篇論文根本不在裡面**，而且 7 篇中有 **5 篇「prefrontal」出現次數為零**。

整個專案目標的前額葉那一半，在本地**零來源**。

**教訓：** 拿到一組參考文獻，**先驗證它們是否真的支持目標**，方法是實際 grep 關鍵詞，不要看標題猜。這一步花了十分鐘，改變了整個專案的形狀。

```bash
for f in *.txt; do echo "=== $f"; grep -ic "prefrontal" "$f"; done
```

### 7. 同姓不同人

資料夾根目錄有一篇 `fnagi-14-1068175.pdf`，看起來像是專案的一部分。實際上是 **Liu Y.（桂林醫學院）** 的 tACS + 聲音刺激阿茲海默症臨床試驗計畫書 — 與 **Liu R.C.（Emory）** 完全無關。

**教訓：** 檢查**作者全名與單位**，不要只看姓氏。它被隔離在語料庫之外，並記錄在 ADR。

### 8. 預印本 ≠ 正式版

演講摘要宣傳兩項結果：mPFC 抑制會**加速**學習、競爭模型勝過強化學習模型。**兩項在預印本中都不存在。** 預印本唯一的化學遺傳學操作是 ACx，而且結果是**損害**學習。

佐證：兩版之間作者名單多了一人並重新排序。

**教訓：** 用預印本代替正式版時，**逐項核對摘要宣稱的每個結果是否真的在裡面**。本專案為此建立了 `[僅見於摘要]` 標籤，貫穿所有卡片。

### 9. 重複檔案與假重複

使用者後來補了 PDF，其中 `Liu_Robert_2023_Instinct to insight.pdf` 與我下載的預印本 **MD5 不同**，但抽出的文字只差尾端空白 — 是同一份內容。

**教訓：** hash 不同不代表內容不同。比對抽出的文字：

```bash
diff <(tr -s ' \n' ' \n' < a.txt) <(tr -s ' \n' ' \n' < b.txt)
```

---

## 三、推理的坑（包含我自己犯的錯）

### 10. 我推薦錯了一篇論文，理由是錯的

我把 Murugan et al. 2017（*Cell*）列為第一優先，理由是「最接近目標所需的網路解剖」。抓下來才發現：那篇的下行投射是**前額葉→紋狀體**，不是→聽覺皮質。全文中「auditory」出現**一次**，「auditory cortex」**零次**。

**教訓：** 從參考文獻**標題**推斷內容會出錯。而且 — **錯了要在文件裡改掉**，不要只在對話裡道歉。綜合論述中該條目已加刪除線並附更正說明。

### 11. 因果箭頭的方向

Concina et al. 2018 常被引用為「聽覺與前額葉的耦合」。但它的因果操作是抑制 **Te1 → PL 的軸突終末**，也就是**上行**。把它引用成「mPFC 由上而下控制 ACx」是錯的。

**做法：** 把警告寫進**檔案本身的標頭**，不只寫在卡片裡 — 任何人開檔就會看到。

### 12. 「前額葉」不是一個東西

齧齒類 mPFC = ACC + PL + IL（+ 有爭議的 M2），三者在解剖與功能上各自不同。而**投射到聽覺皮質的細胞在前側 ACC，PL 與 IL 貢獻有限**。

這件事推翻了我先前一個推論的強度：我曾說競爭或許可直接在 ACx↔mPFC 之內實現 — 但如果 spine 論文記錄的是 PL，那條路徑可能根本不在。

**教訓：** 只要句子是「X 腦區對 Y 腦區做了什麼」，就必須指名**亞區**。

### 13. 同一個詞，兩種相反的現象

兩篇論文都說「由上而下輸入抑制 A1」：
- Winkowski 2018：抑制發生在**配對頻率上**
- Galindo-Leon 2009：抑制發生在調頻**偏離**相關聲音的神經元上

**空間分布相反，從未被比較過。** 合併它們會得到一個看似漂亮、實則錯誤的綜合。

### 14. 摘要會誇大自己的結果

Mittelstadt & Kanold 2023 的摘要說終末活動「受訊噪比調變」。但 Results 同一段的結論是「**大致與訊噪比無關**」，實際差異只有 2–3% ΔF/F。

**教訓：** 一篇論文被納入是因為摘要中的某個賣點時，**去讀 Results 的數字**再決定它值不值得那個位置。

### 15. 分母不一致會膨脹效果

Garcia-Lazaro 2015 報告聽神經 7%、耳蝸核 9%、下丘 59% 對叫聲有反應。但**聽神經是單纖維、下丘是多單元記錄位點** — 多單元只要有任一神經元反應就算數。方向大概是對的，但 7% vs 59% 誇大了實際的逐神經元差距。

---

## 四、有效的做法

### 16. 先做 blindspot pass，再開始寫

在動筆前先掃描「這個任務的缺口在哪」，而不是直接執行。本專案最重要的發現（目標論文不存在、前額葉零來源）就來自這一步。

### 17. 每個主張都標等級

`[已確立] / [提出] / [未檢驗] / [僅見於摘要] / [推論]`

這個做法在專案後期價值極高：當有人問「這是誰說的」，答案就在標籤裡。特別是 **`[推論]`** — 用來把我自己的綜合與論文的主張分開。本專案最有意思的發現（兩個互不引用的文獻收斂到同一個結構）標的就是 `[推論]`，而不是結果。

### 18. 引用要標「已驗證摘要」vs「僅有 metadata」

文獻檢索時，只讀到標題與 PMID 的項目一律標 `[metadata only]`，**不得引用其內容**。這防止了從搜尋結果的標題編故事。

### 19. 錯誤要往回改進既有文件

專案中至少四次需要修正先前寫下的內容（Garcia-Lazaro 的地位、Galindo-Leon 沒有推翻 Liu 2006、Murugan 的推薦理由、直接迴路推論的強度）。**每一次都回去改了文件**，並在 handoff 裡開一節「已修正，勿重蹈」。

### 20. 抓不到的東西，把「抓不到」也記下來

兩篇 Hockley 論文付費牆擋住時，我把狀態表寫進檢索文件（誰持有、誰沒有、免費的是哪三篇）。使用者後來自己補上了 PDF — 因為他知道缺的是哪兩篇。

---

## 五、可重用配方

### Europe PMC 檢索（本專案主力）

```
https://www.ebi.ac.uk/europepmc/webservices/rest/search
  ?query=<query>&format=json&pageSize=30&sort=CITED%20desc
```

查詢語法：`ABSTRACT:"auditory cortex" AND ABSTRACT:"prefrontal" AND (ABSTRACT:"projection" OR ABSTRACT:"top-down")`

用 `sort=CITED desc` 讓關鍵論文浮到最上面。取單篇詳情用 `EXT_ID:<pmid>` 加 `resultType=core`（會回完整摘要）。

### PMC 全文（PDF 被擋時）

```powershell
Invoke-WebRequest -Uri "https://pmc.ncbi.nlm.nih.gov/articles/PMC<id>/" `
  -OutFile "$scratch\paper.html" -UseBasicParsing `
  -Headers @{"User-Agent"="Mozilla/5.0 ..."; "Accept"="text/html"}
```

再用簡單的 HTML→text 腳本（去掉 script/style，區塊標籤換行，`html.unescape`）。取回後**檢查有沒有 Results / Methods 段落**，確認拿到的是全文而非摘要頁。

### 檢索要留下可重現的記錄

`docs/lit-search-*.md` 裡逐字記下每一條查詢字串、日期、以及每筆結果的驗證狀態。半天後我自己就回頭用了兩次。

---

## 六、仍未解決的

- 兩篇付費牆論文最後由使用者提供 — **agent 無法取得機構權限**，這是硬邊界。
- 專案資料夾**仍不是 git repo**。
- `references/` 內含多份標記 **keep local / do not redistribute** 的取得全文（`isOpenAccess = N` 的作者手稿）與 CC-BY-NC-ND 預印本。**任何推送到公開位置的動作都必須排除這個資料夾。**
