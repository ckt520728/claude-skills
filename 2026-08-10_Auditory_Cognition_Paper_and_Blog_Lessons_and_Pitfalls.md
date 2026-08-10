# 專案收尾（第二階段）— 從知識庫到論文與部落格：踩過的坑

**專案：** 2026 Auditory cognition Liu RC
**日期：** 2026-08-10（單一工作階段）
**成果：** 第 15 張卡片（正式版 spine）＋英文整合式綜論（約 6,150 字、17 筆已驗證文獻）＋繁中部落格長文（約 6,600 字，含可操作的競爭模型）＋上線發佈
**環境：** Windows 10、PowerShell 5.1、Claude Code
**前一份：** `2026-08-08_Auditory_Cognition_KB_Lessons_and_Pitfalls.md`（建知識庫階段）。**本文不重複那 20 條**，只寫這一階段新踩到的。

本文寫給**未來的自己與其他 agent**。重點不是研究內容，而是**哪裡會出錯、以及怎麼發現它出錯了**。

---

## 一、最大的一個坑：要找的東西一直在自己家裡

### 1. 被判定「取不到」的來源，就躺在專案自己的 NotebookLM 筆記本裡

上一階段的結論是：正式版 *Science Advances* 論文取不到，這是唯一擋住核心主張的東西（Tier 1 acquisition）。

這一階段第一件事是列出使用者提供的 notebook 的來源清單。裡面有：

- `Lu_Liu_2026_sciadv.aeb3005.pdf` — **正式版論文全文**
- `Robert Liu-auditory cognition.m4a` — **演講錄音**

兩個 Tier 1 阻塞點，都在同一個地方，而且從一開始就在。

**教訓：** 在宣告任何來源「取不到」之前，**先窮舉手上每一個容器的內容**。notebook、Drive 資料夾、既有 repo 都算。`notebook_get` 只要一次呼叫就會回傳完整來源清單，成本幾乎是零。上一階段花在繞過 bioRxiv 403、PMC stub、cell.com 擋抓取的工夫，有一部分是不必要的。

**可重用檢查清單（開始找資料前跑一次）：**

```
mcp__notebooklm-mcp__notebook_list          # 有哪些筆記本
mcp__notebooklm-mcp__notebook_get <id>      # 每本裡面有什麼來源
Glob / ls 專案資料夾與相鄰資料夾
```

### 2. `source_get_content` 的輸出會超過工具上限，要自己解 JSON

**症狀：** 13 萬字元的來源回傳「output too large」，內容被寫到一個 tool-results 檔案。
**解法：** 那個檔案是 **JSON**，不是純文字。要先取出 `content` 欄位再用：

```python
import json, pathlib
d = json.loads(pathlib.Path(saved_path).read_text(encoding='utf-8'))
pathlib.Path('fulltext.txt').write_text(d['content'], encoding='utf-8')
```

**再壓一次空行**（PDF 抽出來的文字每行之間有 4–5 個空行，9,235 行壓成 3,079 行），否則 Read 的行數預算會被空行吃掉三分之二。

---

## 二、正式版 vs 預印本：連「否定」的結論也要重驗

### 3. 標記為 abstract-only 的主張全部翻正 —— 這是預期的

上一階段誠實地把兩個只出現在演講摘要、預印本裡沒有的結果標成 `[abstract-only, unverified]`。正式版拿到後兩個都成立。**這部分運作良好**，分級制度發揮了作用。

### 4. 但**否定**的主張也變了 —— 這是沒預期的，而且更危險

上一階段的核心結論之一是：訊噪比機制「被提出五次、測量零次」。

正式版 Fig. 3H **有**一個族群層次的量化結果：壓抑強度與該節次「解碼聲音來自哪一臂」的正確率相關。

「零次」變成「一次，而且是相關性的」。

**教訓：新的一手來源到手時，要重新稽核的不只是你標為「未證實」的正面主張，還有你標為「從來沒人做過」的否定主張。** 否定主張感覺上比較安全、比較保守，所以比較不會被複查——這正是它危險的地方。一個過期的「從來沒人測過」會直接變成論文裡的錯誤陳述。

實際處理：把它改成 `[已證實·相關性]`，並且明確寫出它**不能**支撐什麼（跨節次的兩個測量值相關 ≠ 壓抑造成辨別度提升；兩者都可能反映第三變數）。原作者自己用的動詞是「我們推測」，跟著用就對了。

### 5. 衍生文件會**安靜地**過期

寫完第 15 張卡片後，`cards/00-synthesis-ACx-mPFC.md`（綜合論述）有四、五處直接變成錯的——它是在正式版到手前寫的。

沒有任何機制會提醒你這件事。綜合文件不會報錯，它只是繼續存在、繼續被讀。

**做法：** 在新卡片裡放一張**「這改變了知識庫的哪些地方」對照表**（欄位：項目／原本／現在），並在 handoff 裡明確寫「card 00 現在是資料夾裡唯一內部過期的文件」。與其偷偷修掉，不如把差異列出來——因為修改綜合論述本身是一件需要判斷的事，值得單獨做。

---

## 三、演講錄音是一種特別的來源

### 6. 它的證據位階比論文低，但它包含論文裡沒有的東西

錄音裡有三樣東西是論文沒有的：

1. **作者對自己用詞的讓步。** 有聽眾當場質疑「blocking（阻擋）」這個字太強——你的資料顯示的是前額葉代表另一個策略、而權重變小，這跟主動阻擋不一樣。作者同意模型呈現的是「一個蹺蹺板……一個被機率加權的擲硬幣」，並改用「constraining（限制）」辯護。
2. **他自己列的人類對應文獻**（兩篇病灶研究）。
3. **明確標示為推測的臨床延伸**（安靜前額葉、冥想類比）。

第 1 點直接改變了正確的寫法。若只讀論文，很容易照抄標題的 "constrains" 再自行升級成「阻擋」「抑制」。**作者本人不願意說的話，二手改寫更不該說。**

**規則：** 錄音一律標為 **author commentary，位階低於論文，永遠不用來支撐任何結果**，但**可以**用來約束用詞與標示推測。

### 7. 只出現在演講裡的引用，一定要獨立查證

作者口頭提到兩篇人類 vmPFC 病灶研究。口頭引用沒有卷期頁碼，而且講者也可能記錯年份或期刊。

兩篇都查到了，也都成立：

- Manohar S, et al. *Cortex*. 2021;138:24–37. doi:10.1016/j.cortex.2021.01.015
- Holton E, et al. *Nat Hum Behav*. 2024;8(7):1351–1365. doi:10.1038/s41562-024-01844-5

**但查證時發現一個講者沒提、卻必須一起帶走的落差：兩篇人類研究都是 vmPFC，齧齒類的效應在 PL／IL。** 齧齒類與人類前額葉的同源性本身有爭議，把 PL／IL 對應到 vmPFC 是**假設**不是發現。這句但書進了論文也進了部落格。

**通則：跨物種的腦區對應，是科普文章最容易無聲出錯的地方。** 因為兩邊都叫「前額葉」。

---

## 四、發表載體的坑（新的，而且會實際壞掉）

### 8. Canvas 的 devicePixelRatio 回授迴圈 —— 本階段最實際的一個 bug

**症狀：** 頁面在瀏覽器裡截圖逾時、看起來像整個 renderer 當掉；捲到內容區只看到一大片空白。

**原因：** 常見的高解析度 canvas 寫法是

```js
cv.width  = cv.clientWidth  * dpr;
cv.height = cv.clientHeight * dpr;   // ← 這行
```

如果 CSS **沒有**指定 canvas 的高度，元素的版面高度就來自 `height` 屬性。於是設定 `cv.height` 會**改變版面高度**，下一次重繪讀到更大的 `clientHeight`，再放大一次——每次重繪都長大。在 dpr = 1 的螢幕上剛好穩定（× 1），所以**在一般螢幕上測不出來**，只在 HiDPI 螢幕上炸。

**解法：用 CSS 把高度釘死。**

```css
#cvA { height:230px; }   /* 沒有這行，canvas 每次重繪都會變高 */
#cvB { height:190px; }
```

```js
function fit(cv, ctx){
  var dpr = Math.max(1, window.devicePixelRatio || 1);
  var r = cv.getBoundingClientRect();
  if(!r.width || !r.height) return false;          // 版面還沒好，安全跳過
  var bw = Math.round(r.width*dpr), bh = Math.round(r.height*dpr);
  if(cv.width !== bw || cv.height !== bh){ cv.width = bw; cv.height = bh; }
  ctx.setTransform(dpr,0,0,dpr,0,0);
  return true;
}
```

**⚠️ 同站的 `blog/hhsa-amplitude-modulation-closed-loop-tacs.html` 有同樣的潛在寫法**，下次動到那篇時要一起修。

順帶：resize 要 debounce（150 ms），並且不要在載入時重複呼叫三次 draw()。

### 9. flex 的 `<label>` 會把 `<sub>` 拆成獨立的 flex item

**症狀：** `SW<sub>0</sub>` 的下標「0」跑到標籤和數值中間，變成一個孤立的小字。

**原因：** `.control-row label { display:flex; justify-content:space-between; }`。文字節點被包成匿名 flex item，但 `<sub>` 是元素，**自成一個 flex item**，於是被 space-between 推開。

**解法：** 把標籤文字整個包進一個 `<span>`。

```html
<label><span>初始 win-stay 權重 SW<sub>0</sub></span><output id="o-sw">2.00</output></label>
```

### 10. 瀏覽器自動化開不了 `file://`

**症狀：** `Can't interact with browser-internal or unparseable URLs`。

**解法：** 起一個本機伺服器，用 `127.0.0.1`：

```bash
cd <repo>
python -m http.server 8731 --bind 127.0.0.1   # 背景執行
```

驗完記得關掉（PowerShell）：

```powershell
Get-NetTCPConnection -LocalPort 8731 -State Listen -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty OwningProcess -Unique |
  ForEach-Object { Stop-Process -Id $_ -Force }
```

### 11. 截圖逾時 ≠ 頁面壞掉（差點誤診）

`Page.captureScreenshot` 會間歇性逾時並回報「renderer may be frozen」。這一階段至少發生三次，而其中只有第一次是真的有 bug。

**判斷順序：先看分頁標題有沒有正確解析、再看 console 有沒有錯誤，最後才懷疑頁面。** 標題正確＋沒有 console error＝頁面是活的，重試截圖即可。

---

## 五、重寫別人的模型時

### 12. 雙欄 PDF 抽出來的**表格**會錯行錯欄

論文 Table 1（權重更新規則）抽出來之後，列與欄混在一起，讀起來自相矛盾（出現了在該設計下不可能發生的「同臂且答錯」組合）。

**教訓：不要用一張抽壞的表去重建一個形式模型。** 兩個選項：(a) 回到正文敘述交叉驗證；(b) 明確標示自己的實作是**簡化重寫版**。本專案選 (b)，並在面板抬頭與頁尾各寫一次「為說明機制用的示意模擬，非原始資料重現」。

### 13. 重寫的模型要拿論文的數字校準，不能只看曲線「像不像」

第一組參數看起來很合理，實際跑起來 win-stay 權重在 1.5 天內就崩到地板——因為每回合的漂移量算錯了一個數量級。

**做法：先寫下三個可查核的定錨點，再調參數。** 本例：

| 定錨點 | 論文值 | 重寫版 |
|---|---|---|
| 第 1 天 win-stay 使用率 | ~90% | 93.5% |
| 第 1 天聲音策略表現 | 顯著**低於**隨機 | 44.5% |
| 對照組達標日 | 過半在第 4 天前 | 第 3 天 |
| 抑制組達標日 | 2–3 天 | 第 2 天 |
| 恢復後 | 顯著下滑 | 60.0% → 55.2% |

用 Node 跑 200 次模擬取平均來驗，比在瀏覽器裡目測快得多也可靠得多。

---

## 六、出版與發佈

### 14. 三個註冊點，缺一個就等於沒發表

1. `blog/<slug>.html` — 文章本身
2. `index.html` — `#panel-lecture .teach-grid` **最上方**新增一張 `teach-card`
3. `sitemap.xml` — 新增 `<url>`，並且**更新首頁的 `<lastmod>`**

### 15. 每個 repo 的預設分支不一樣

- `kidney-cognition-lab` → **`main`**
- `claude-skills` → **`master`**

推之前一定 `git branch --show-current`。

### 16. 推送要用 PowerShell，不要用 Git Bash

Git Bash 讀不到 Windows 認證管理員（`credential.helper=manager`），會失敗在 "could not read Username"。PowerShell 可以。

PowerShell 會把 git 的 stderr 進度輸出包成紅色的 `NativeCommandError`，**即使成功也一樣**。判斷成功與否要看 `dd..aa  <branch> -> <branch>` 那一行，不是看有沒有紅字。

### 17. 授權邊界（延續前一階段，仍然有效）

`references/` 內含 `isOpenAccess = N` 的作者手稿與 CC-BY-NC-ND 預印本。**任何推送到公開位置的動作都必須排除這個資料夾。** 本階段推上公開 repo 的只有：部落格 HTML、首頁卡片、sitemap、以及這份收尾文件——**沒有任何一份原始 PDF 或全文**。

---

## 七、有效的做法（本階段新增）

### 18. 先問清楚會改變產出的三件事，再動筆

論文型態（整合式綜論／觀點短文／轉譯橋接）、語言（英文論文＋繁中部落格）、發佈方式（先看再推／直接推）。這三個答案會決定接下來所有的工作，事後再改等於重寫。**其餘的判斷自己做完，不要一路問。**

### 19. 把「這篇論文的設計能支持什麼」單獨寫成一節

本專案論文的第 4 節與部落格的第六節，內容是：兩個方向相反的因果操弄**不等於**一條迴路（不同動物、沒有交互作用測量、沒有連結性資料、裁決者未定位）。

這一節不是在挑毛病——它同時列出這個設計**比一般雙病灶研究強**的三個理由（雙向雙分離、可逆的恢復實驗、零自由參數的預測）。**先劃清界線，再給足credit**，兩件事都做才是公允的。

### 20. 部落格的主張強度不得超過論文

同一套證據分級標籤（已證實／提出／未測試／我的推論）直接做成 CSS badge 放進 HTML，讓讀者在句子層級看到強度。這樣就不可能在科普版裡偷偷升級一個主張——因為標籤就在旁邊。

---

## 八、仍未解決的

- **正式版 PDF 仍不在 `references/`**，專案目前依賴 NotebookLM 的副本作為自己的 spine。
- **`cards/00-synthesis-ACx-mPFC.md` 尚未併入第 15 張卡片**的變更（清單在 card 15 §4）。
- **論文的 affiliation 仍是刻意留白的 placeholder**，投稿或流通前必須補上。**不要替作者編造單位。**
- 專案資料夾**仍不是 git repo**。
- 原始簡報中的 **「eeg」仍未解釋**，但路線浮現了：演講結尾的推測（安靜前額葉以擺脫既有偏誤）＋作者計畫與台灣 Chin's lab 的人體研究，是通往既有 tACS／EEG 工作的自然橋接。**但兩份產出裡它都被明確標為推測，必須維持原樣。**
