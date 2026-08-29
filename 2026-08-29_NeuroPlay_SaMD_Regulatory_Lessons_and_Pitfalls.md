# 專案收尾 — NeuroPlay 認知遊戲申請台灣 SaMD：踩過的坑與可重用做法

**專案：** NeuroPlay 腦力訓練 → NeuroPlay Clinical，依《醫療器材管理法》規劃台灣上市，CIPH（中央大學）學術背書
**日期：** 2026-08-29（單一工作階段）
**成果：** `regulatory/` 法規工作區（法規地形圖、18 個月計畫、未知登錄簿、預期用途聲明）+ CIPH 會議用視覺化簡報 Artifact
**環境：** Windows 11、Git Bash / PowerShell 5.1、Claude Code、全國法規資料庫 + TFDA 官方文件

> **語言說明：** 本檔採繁中撰寫，檔名沿用 repo 既有的
> `YYYY-MM-DD_*_Lessons_and_Pitfalls.md` 命名慣例。

> **範圍聲明：** 本檔記錄的是**方法與工具的踩坑**，不是法規意見。
> 具體法條內容以專案內 `regulatory/docs/00-regulatory-landscape.md` 為準；
> 該檔每條主張都標了 `[已查證]` / `[推論]` / `[待查證]` / `[估]`。

---

## 零、一句話總結

**這個案子的核心不是「怎麼申請」，而是「要不要跨線，以及跨線的那一刻是哪一句話」。**
TFDA 的指引明文把「心靈（心理）管理 mental acuity」列為健康促進軟體、**不屬於醫療器材** ——
NeuroPlay 現在就在這一格，而且是合法地在。加上常模比對之後才落入「解釋病患資料協助
診斷」→ 第二等級。**判定的是宣稱，不是技術。**

| # | 發現 | 證據等級 |
|---|---|---|
| 1 | 產品現況合法地不是醫材；加常模是主動跨線，不是被迫合規 | `[已查證]` 指引第五節（三） |
| 2 | 決定性的那句話只在 PDF 原文裡，任何搜尋摘要都沒提到 | `observed`，兩輪 web search 皆未命中 |
| 3 | 刪掉 14 個月的收案期，全案只省 6 個月 | `derived`，關鍵路徑不在那條軌上 |
| 4 | 「資料已收好」≠「證據已備妥」，中間隔著五項稽核 | `derived` |
| 5 | 寫預期用途聲明時才發現常模有 26–64 歲缺口 | `observed`，計畫階段完全沒看到 |
| 6 | MCP 掛掉不等於伺服器掛掉；403/401/502 三段可以定位到層 | `observed` |

---

## 一、產出了什麼

- `regulatory/CLAUDE.md` — 法規工作區規範。雙軌策略、證據分級規則、
  `/grill-with-docs` 與 Finding Unknowns 的具體用法。
- `regulatory/docs/00-regulatory-landscape.md` — 台灣 SaMD 行政流程全貌（參照錨點）。
  法源總表、五道關卡、規費、上市後義務，每條標證據等級並附出處連結。
- `regulatory/docs/01-plan-timeline.md` — 18 個月排程（v3）、5 個 Gate、預算、三大風險。
- `regulatory/docs/02-unknowns.md` — 未知登錄簿。9 個開啟中、1 個已關閉。
- `regulatory/docs/03-intended-use-statement.md` — 預期用途聲明 v0.1（英中對照）+ 設計說明。
- CIPH 會議用 Artifact — 視覺化簡報，含閾值圖、甘特、八項前提但書、名詞對照。
- 順手修好 firebase MCP（見 §5.2）。

---

## 二、最重要的一件事

**先問「這件事會不會讓產品變成醫療器材」，再問「怎麼做這件事」。**

一開始的直覺是「加常模 = 產品升級」，於是自然地去規劃收案、信效度、統計。
但真正該先回答的是：**加了常模之後，這個 App 在法律上還是同一個東西嗎？**

答案是不是。而且轉折點不在技術，在說明書上的一句話：

| 寫法 | 法規地位 |
|---|---|
| 「記錄你今天的表現，跟你上週比」 | 健康促進軟體，非醫材 |
| 「你的表現落在同齡第 12 百分位」 | 解釋病患資料協助診斷 → **第二等級** |

同一段程式碼、同一批資料。**差別只在輸出畫面上那一行字。**

這個認識直接產生了雙軌策略（A 軌 Wellness 維持上架、B 軌 Clinical 走查驗登記），
以及一條寫進 `CLAUDE.md` 的紅線：**A 軌的宣稱不得被 B 軌污染**。因為 A 軌若被認定
為醫材，就是未經核准製造，管理法 §62 是三年以下有期徒刑併科一千萬元以下罰金。

---

## 三、法規研究的坑

### 3.1 搜尋摘要不會告訴你關鍵的那句話

跑了兩輪 web search 找「醫用軟體是否屬醫療器材」，得到的摘要都在講大原則：
「依產品功能、用途、使用方法綜合評估」、「健康管理產品不屬醫療器材」。
**沒有一則提到「mental acuity 心靈（心理）管理」這七個字。**

而那正是本案唯一重要的一句 —— 它把腦力訓練 App 明文放進排除清單。

抓到它的方式是把《醫用軟體分類分級參考指引》PDF 抓下來、用 `pypdf` 抽文字、
直接 grep。WebFetch 對這份 PDF 直接回「這是二進位檔我看不懂」。

```bash
# WebFetch 讀不了的 PDF，它仍然會落地到 tool-results/
python -c "
import pypdf
r = pypdf.PdfReader('webfetch-xxxx.pdf')
open('guide.txt','w',encoding='utf-8').write('\n'.join(p.extract_text() or '' for p in r.pages))
"
grep -n "認知\|健康管理\|排除" guide.txt
```

**做法：法規、標準、合約這類文件，一律抓一手原文。** 搜尋摘要適合找到「有哪份文件」，
不適合回答「那份文件怎麼說」。這條在 `CLAUDE.md` 裡固化成規則：寫不出條號與版本
日期的主張，一律標 `[待查證]`，不准用推測填空。

### 3.2 「資料已收好」≠「證據已備妥」

案主中途說常模資料已經收完，可以把時間人力成本扣掉。扣掉收案是對的，
但**不能連「把研究資料轉成法規證據」一起扣掉**。中間有五項稽核：

| 稽核 | 為什麼 |
|---|---|
| IRB 範圍 | 原始知情同意有沒有涵蓋商業化開發、以及資料移轉給公司法人 |
| 版本同一性 | 施測版本與送審版本是否同一版；改過就不能沿用常模 |
| 再測信度 | 橫斷面資料只能算百分位，**算不出 RCI** |
| 資料可追溯性 | 研究等級的紀錄未必達到送審的稽核要求 |
| 施測情境 | 社區現場的噪音、裝置差異、有無監督需論證 |

第三項當場就中了：問「有沒有同一批人重複施測」，答案是沒有 —— 於是補充再測研究
從「條件性」變成「必做」。

**做法：對方說「這部分已經完成」時，先問「完成到哪個標準」。** 研究完成、
工程完成、法規完成是三個不同的門檻。

### 3.3 寫正式文件會揪出計畫看不到的缺口

計畫寫了三個版本都沒發現的問題，在動手寫〈預期用途聲明〉第 3 節「預期使用族群」
時一秒現形：常模分層是國小、國中、高中、大學、65+ ——**26 到 64 歲是空的**。

預期使用族群不能寫得比常模涵蓋範圍寬，這是送審會被直接打回的問題。

**做法：把最終交付文件的其中一節提早寫掉，當作規劃階段的檢查工具。**
甘特圖不會逼你回答「族群是誰」，仿單會。

---

## 四、時程推理的坑

### 4.1 刪掉 14 個月的工作，只省下 6 個月

直覺會說：拿掉 14 個月的收案期，24 個月變 10 個月。實際是 **18 個月**。

原因是原本的常模研究（M4–M18）與 QMS（M5–M14）本來就並行，常模只多壓 4 個月在
尾端。真正的節省來自「臨床評估報告能提前完成，讓查驗登記不必等到最後才送件」。

而且省下來之後，**關鍵路徑換人了**：從常模研究換成 QMS 與製造許可。這件事的
連帶影響比省 6 個月更重要：

- 該優先補的人從 CRC／心理師 → QA／RA 與軟體測試工程
- `src/games/` 的單元測試從「早晚要做」→「每延一週，上線延一週」

**做法：時程變動後，第一件事是重新找關鍵路徑，而不是回報省了幾個月。**

### 4.2 「條件性」變成「確定」時，真正的代價是緩衝

補充再測確認要做之後，上線日期**沒有變**（M18 不變），因為那條軌不在關鍵路徑上。
容易就這樣回報「不影響時程」然後結案。

但實際變化是：臨床評估報告從 M7 延到 M10，距離送件（M12）的餘裕從 **5 個月縮到
2 個月**。日期沒動，但抗風險能力少了六成。

**做法：並行工作的變動要報「緩衝剩多少」，不是只報「里程碑有沒有動」。**

---

## 五、工具與環境的坑

### 5.1 MCP 掛掉 ≠ 伺服器掛掉：用 403/401/502 定位到層

`twinkle-hub` MCP 回 Cloudflare 502，附帶一句「retryable, wait 60s」。等了四小時仍然一樣。

不要停在「服務掛了」。三個 curl 就能定位：

```bash
curl -o /dev/null -w "%{http_code}\n" https://api.twinkleai.tw/health          # 200 → 服務活著
curl -X POST .../mcp/ -d '{...}'                                              # 403 → 認證層在
curl -X POST .../mcp/ -H 'Authorization: Bearer BAD-TOKEN' -d '{...}'         # 401 → 認證邏輯正確
curl -X POST .../mcp/ -H 'Authorization: Bearer <真 token>' -d '{...}'        # 502 → 已認證路徑壞掉
```

結論精確得多：**不是整台掛掉，是通過認證之後的下游崩了。** 而且連
`initialize` 這種不做任何查詢的握手都 502，代表與查詢負載無關。

這個結論對回報有用（附 CF ray ID 給維運方可以直接查 log），對自己也有用 ——
確認本機設定沒問題，不用浪費時間改 config。

**做法：外部服務失敗時，先做一次「權限階梯掃描」再下結論。**

### 5.2 npx 是 MCP stdio server 的效能地雷

`firebase` MCP 註冊成 `npx -y firebase-tools mcp --dir ...`，健康檢查時好時壞。
記憶裡甚至存了一條「這是已知的 false failure，調高 `MCP_TIMEOUT` 就好」——
那是在治症狀。

實際情況：`firebase-tools` **早就全域安裝了**，但 npx 預設不用全域套件，
`-y` 還會每次去 registry 重新解析。冷啟動 21–30 秒，正好卡在 30 秒健康檢查邊界。

| 呼叫方式 | 啟動時間 |
|---|---|
| `npx -y firebase-tools` | 21–30s（逾時邊界，時好時壞） |
| `firebase.cmd` shim | 1.4s |
| `node <path>/lib/bin/firebase.js` | **0.6s**（MCP 握手全程 8s） |

```bash
claude mcp remove firebase -s user
claude mcp add firebase -s user -- node \
  "C:\Users\User\AppData\Roaming\npm\node_modules\firebase-tools\lib\bin\firebase.js" \
  mcp --dir "D:/2026 Open code"
```

**通則：全域安裝的 npm MCP server，用 `node` 直接叫 `lib/bin/*.js`，
不要用 `npx`，也不要用 `.cmd` shim。** MCP server 只在 session 啟動時載入，
改完要重開才生效。

### 5.3 Git Bash + Python heredoc 的編碼坑（同一天踩兩次）

```bash
python - <<'PY'
s = "醫療器材"        # ← 炸
PY
```

Python 從 **stdin** 讀取時，Windows 上用的是系統 locale 編碼（cp950），不是 UTF-8。
中文字元直接變亂碼，接著出現看不懂的 `AssertionError: anchor missing: '> v1 ������ git ���v�C'`。

`python -c "..."` 也有另一個坑：字串裡有 Windows 路徑時，
`\U`、`\N` 會被當成 unicode escape → `SyntaxError: (unicode error) truncated \UXXXXXXXX escape`。

**做法：任何含中文或反斜線的 Python，一律寫成 `.py` 檔再執行。**
Python 讀**檔案**時預設 UTF-8，讀 stdin 時不是。

同理，`cat > file <<'EOF'` 寫檔完全沒問題 —— 坑只在「把 heredoc 當程式源碼餵給直譯器」。

### 5.4 錨點替換一定要先 assert，而且不要假設換行位置

批次改文件時用了 `s.replace(old, new)`。有一個錨點寫成 `"> v1 版本見 git 歷史。"`，
以為它獨立成行，實際上它接在上一句後面，同一行。

因為腳本裡有 `assert old in s` 才沒有默默寫出半套修改。

```python
for old, new in reps:
    assert old in s, 'anchor missing: %r' % old[:60]   # 全部檢查完再寫檔
    s = s.replace(old, new, 1)
io.open(p, 'w', encoding='utf-8').write(s)
```

**做法：（1）先 assert 全部錨點再寫檔，不要邊檢查邊寫。
（2）錨點取「行內一定存在的片段」，不要含推測的行首標記。
（3）不確定就先 `repr()` 印出實際行內容。**

---

## 六、Artifact 製作的坑

### 6.1 硬編碼的 grid 欄數

甘特圖 24 個月改成 18 個月時，`repeat(24, 1fr)` 出現在三個地方（bar 軌、月份列、
Gate 列），還有一處藏在 `repeating-linear-gradient` 的 `calc(100% / 24)` 裡。

```css
.gantt { --cols: 18; }
.g-track, .g-months, .g-gates { grid-template-columns: repeat(var(--cols), 1fr); }
.g-track::before { background: repeating-linear-gradient(90deg, …, calc(100% / var(--cols))); }
```

CSS custom property 可以穿過 `display: contents` 繼承，所以子元素直接用得到。
**做法：任何會變的維度一開始就設成變數，即使當下只用一次。**

### 6.2 絕對定位的標籤會在最後一欄溢出

Gate 標籤用 `position: absolute` + `transform: translateX(-50%)` 置中，最後一個
Gate 在第 24 欄時會被切掉。加一個 `.end` 變體即可：

```css
.gm em      { left: 50%; transform: translateX(-50%); }
.gm.end em  { left: auto; right: 0; transform: none; }
```

### 6.3 驗證結構要用程式數，不要用眼睛看

18 欄的 Gate 列要放 18 個 `<span>`，其中 5 個有內容、13 個是佔位。手數會錯。

```python
print('gate cells:', len(re.findall(r'<span', gates_block)))   # 必須 == 18
print('bars:', re.findall(r'grid-column:(\d+) / (\d+)', s))    # 全部要在 1..cols+1
```

順帶一提：Windows 主控台印中文會亂碼，但**那只是主控台編碼，檔案是好的** ——
不要因為 stdout 亂碼就以為寫壞了。

---

## 七、可重用做法

1. **證據分級標記。** 每條主張標 `[已查證]` / `[推論]` / `[待查證]` / `[估]`，
   並在簡報裡用顏色 chip 呈現。開會被問「這條你確定嗎」，指著 chip 就能回答。
   降級比誤導安全。
2. **未知登錄簿（`02-unknowns.md`）比甘特圖誠實。** 每個 Phase 開始前跑
   `decision-first-plan` 寫下「要決定什麼」，結束後跑 `blindspot-pass` 補新的未知。
   已關閉的未知保留在檔案底部 —— 刪掉就失去「我們曾經以為什麼」的紀錄。
3. **參照錨點文件。** 指定一份文件為單一事實來源（本案是
   `00-regulatory-landscape.md`），其他文件的敘述以它為準，它更新時下游一起校對。
4. **Phase 的存在目的是關掉一個不確定性，不是做完一批事。**
   排序依據是「哪個未知一旦答錯會讓後面全部重做」。
5. **把最終交付文件的一節提早寫掉**，用它當規劃階段的檢查工具（§3.3）。

---

## 八、未解與下一步

| # | 未解 | 何時能知道 |
|---|---|---|
| U-01 | 分類分級究竟是第幾等級（推論第二級，但辦法 §4 對未列品項是第三級） | TFDA 個案判定，M3 |
| U-10 | 原始 IRB 與知情同意是否涵蓋商業化與資料移轉 —— **目前最大單點風險** | 本月可查 |
| U-08 | 查驗登記能否在製造許可核准前先送件（可的話再省 1–2 個月） | TFDA 諮詢，M3 |
| — | 26–64 歲常模缺口：限縮族群 / 補收 / 分段上市 | CIPH 會議拍板 |
| — | 補測後 ICC 是否足以支撐 RCI | M9 |
| — | `twinkle-hub` MCP 已認證路徑 502，四小時未恢復 | 待維運方修復 |

**下一步：** 寫定 Intended Use Statement → 打 TFDA 諮詢專線 02-8170-6008 →
送件個案分類分級判定 → 送 IRB（資料使用變更案 + 補充再測計畫書）→
`src/games/` 補單元測試（現在在關鍵路徑上）。
