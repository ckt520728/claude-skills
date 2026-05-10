---
name: personal-medical-website
description: |
  端到端建立並部署個人互動式醫學/學術網站的完整技能。
  從零產出單一 index.html（含嵌入 CSS + JS），搭配形象照與 Logo，
  最後部署到 GitHub Pages 並取得可分享的公開 URL。
  適合臨床醫師、研究者、雙專長學者建立中文個人作品集 + 醫學知識教育網站。
  觸發短語：「幫我做個人網站」、「醫師個人頁面」、「學術作品集」、
  「互動式自我介紹網站」、「portfolio 網站」、「個人介紹 HTML」、
  「做一個關於我研究領域的網站」、「把網站發布上線」、「部署到 GitHub Pages」。
---

# Personal Medical Website — 完整建站與部署技能

單一 `index.html`，零 build 步驟，瀏覽器直接開啟，最終部署至 GitHub Pages。

---

## 適用對象

| 身分 | 典型需求 |
|------|---------|
| 臨床醫師 | 個人作品集 + 病患衛教互動工具 |
| 醫學研究者 | 跨域研究整合展示 + 著作時間軸 |
| 雙專長學者（如腎臟科 + 認知神經科學） | 兩領域知識視覺化 + 跨域連結章節 |
| 教授/講師 | 演講記錄 + 課程列表 + MCQ 測驗 |

---

## 需要從使用者收集的資訊

在開始建站前，逐步確認以下資料（可分批提供，先用佔位符）：

```
□ 姓名、職稱、服務單位
□ Email
□ 學術連結（Google Scholar URL、ORCID）
□ 學歷清單（學校、學位、年份）
□ 證照清單（含證書字號）
□ 職涯時間軸（每個職位：機構、職稱、年份區間）
□ 研究著作（APA 格式引用，含 DOI）
□ 形象照：photo.png（放專案根目錄）
□ Logo：logo.png（放專案根目錄）
□ 專長領域（供互動圖表設計）
```

---

## 輸出結構

```
專案根目錄/
├── index.html     ← 唯一網站主檔（單一檔案，全部內嵌）
├── photo.png      ← 形象照（使用者手動放入）
├── logo.png       ← 網站 Logo（使用者手動放入）
└── .gitignore     ← 部署用（排除草稿/工具資料夾）
```

---

## 網站七大章節

| # | ID | 中文標題 | 主要互動功能 |
|---|----|---------|------------|
| 1 | `#hero` | 英雄首頁 | 打字機動效（4 短語輪播）、Logo 展示、CTA 按鈕 |
| 2 | `#about` | 關於我 | 形象照、Bio、學歷/證照/職涯時間軸（橫向節點）、專長卡片 |
| 3 | `#nephrology` | 腎臟科學 | eGFR 計算器、CKD 分期圖、腎元 SVG 動畫 |
| 4 | `#kidney-brain` | 腎腦軸連結 | 流程圖、盛行率長條圖、認知下降折線圖 |
| 5 | `#neuroscience` | 認知神經科學 | 大腦 SVG 互動地圖、認知雷達圖、MCQ 測驗 |
| 6 | `#research` | 研究與著作 | 垂直時間軸、Google Scholar 按鈕 |
| 7 | `#contact` | 聯絡 | Email、單位、合作邀約 |

---

## 技術規格

### CDN（無 build，直接引用）

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<link  href="https://unpkg.com/aos@2.3.4/dist/aos.css" rel="stylesheet">
<script src="https://unpkg.com/aos@2.3.4/dist/aos.js"></script>
<link  href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
<link  href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700&family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

### 色彩系統

```css
:root {
  --color-bg-primary:    #0a0f1e;  /* 深海軍藍主背景 */
  --color-bg-card:       #111d3c;  /* 卡片背景 */
  --color-accent-teal:   #4dd9cf;  /* 主互動色（腎臟科） */
  --color-accent-purple: #8b5cf6;  /* 神經科學章節 */
  --color-accent-gold:   #f4a261;  /* 跨域整合/CTA 對比 */
  --color-text-primary:  #e8f4f8;
  --color-text-secondary:#8ba8c4;
}
```

字型：`Noto Sans TC`（中文）、`Inter`（英數）、`JetBrains Mono`（eGFR 數值）

---

## 關鍵互動模組

### A. eGFR 計算器（CKD-EPI 2021，無種族因子）

```javascript
function calcGFR(scr, age, sex) {
  const kappa     = sex === 'female' ? 0.7   : 0.9;
  const alpha     = sex === 'female' ? -0.241 : -0.302;
  const sexFactor = sex === 'female' ? 1.012 : 1.0;
  const ratio     = scr / kappa;
  return 142 * Math.min(ratio, 1) ** alpha
             * Math.max(ratio, 1) ** (-1.200)
             * (0.9938 ** age) * sexFactor;
}
```

滑桿：性別切換 + 肌酐（0.4–10.0 mg/dL）+ 年齡（18–90）  
輸出：eGFR 數值 + CKD 分期徽章 + 圖表即時更新 + 腎元動畫速率

### B. CKD 分期圖（Chart.js afterDraw marker plugin）

```javascript
const markerPlugin = {
  id: 'eGFRMarker',
  afterDraw(chart) {
    const { ctx, scales: { x, y } } = chart;
    const xPos = x.getPixelForValue(currentGFR);
    ctx.save();
    ctx.strokeStyle = '#f4a261';
    ctx.setLineDash([6, 4]);
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(xPos, y.top);
    ctx.lineTo(xPos, y.bottom);
    ctx.stroke();
    ctx.restore();
  }
};
// 傳入方式：new Chart(ctx, { plugins: [markerPlugin], ... })
```

### C. 腎元動畫速率與 eGFR 連動

```javascript
function updateKidneySpeed(gfr) {
  const duration = gfr > 90 ? 2 : gfr > 60 ? 3 : gfr > 30 ? 5 : gfr > 15 ? 8 : 12;
  document.querySelectorAll('.filtrate-dot')
    .forEach(d => d.style.animationDuration = duration + 's');
}
```

### D. 大腦 SVG 互動地圖（6 腦區）

```javascript
const brainData = {
  frontal:  { title:'額葉',  color:'#4dd9cf', functions:[...], clinical:'...' },
  parietal: { title:'頂葉',  color:'#8b5cf6', ... },
  temporal: { title:'顳葉',  color:'#f4a261', ... },
  occipital:{ title:'枕葉',  color:'#4dd9cf', ... },
  cerebellum:{ title:'小腦', color:'#8b5cf6', ... },
  brainstem:{ title:'腦幹',  color:'#f4a261', ... }
};
document.querySelectorAll('[data-region]').forEach(path => {
  path.addEventListener('click', () => showBrainInfo(path.dataset.region));
});
```

CSS 必加 `pointer-events: all` 否則 SVG path 不響應點擊。

### E. 認知雷達圖 + MCQ 測驗

雷達圖：6 軸，兩資料集（典型老化 vs MCI），按鈕切換  
MCQ：3 題，即時回饋 + 解釋 + 分數，`restartQuiz()` 重置

---

## Logo 與形象照處理

### Logo 在網站三個位置

```html
<!-- 導覽列（height 34px，圓角白底小卡片） -->
<img src="logo.png" height="34" class="logo-img"
     onerror="this.style.display='none'">

<!-- Hero 區（height 110px，浮動大卡片） -->
<div class="hero-logo-wrap" data-aos="zoom-in">
  <img src="logo.png" height="110"
       onerror="this.parentElement.style.display='none'">
</div>

<!-- Footer（height 28px，小徽章） -->
<div class="footer-logo-wrap">
  <img src="logo.png" height="28"
       onerror="this.parentElement.style.display='none'">
</div>
```

### 形象照（onerror 雙層回退鏈）

```html
<img src="photo.png" alt="形象照"
     onerror="this.src='photo.jpg'; this.onerror=function(){this.style.display='none'}">
```

### Logo CSS（白底卡片，搭配深色背景）

```css
.logo-img {
  background: #fff;
  border-radius: 10px;
  padding: 4px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.25);
}
.hero-logo-wrap {
  background: rgba(255,255,255,0.95);
  border-radius: 20px;
  padding: 14px 20px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.35), 0 0 0 1px rgba(77,217,207,0.2);
}
```

---

## 實作順序

1. `<head>` CDN + CSS 變數 + Reset
2. 導覽列（漢堡選單 + 捲動半透明效果）
3. Hero（打字機 + Logo + CTA）
4. 關於我（形象照 + Bio + 學歷 + 職涯時間軸 + 專長卡片）
5. 腎臟科學（eGFR → CKD 圖 → 腎元 SVG）
6. 腎腦軸整合（流程圖 + 兩張 Chart.js）
7. 認知神經科學（大腦 SVG → 雷達圖 → MCQ）
8. 研究著作時間軸 + 演講/教學 Tab
9. 聯絡 + Footer
10. RWD 調整（375 / 768 / 1024 px）

---

## 部署到 GitHub Pages（完整 SOP）

### 前置條件

```powershell
gh auth status   # 確認已登入，Token scopes 包含 repo
```

### 步驟

```powershell
# 1. 在專案根目錄初始化 git
Set-Location "C:\...\專案資料夾"
git init
git checkout -b main

# 2. 建立 .gitignore（排除工具資料夾）
@"
skill-build/
extracted_photo/
*.jsonl
"@ | Out-File .gitignore -Encoding utf8

# 3. 只 stage 網站必要檔案
git add index.html photo.png logo.png .gitignore
git commit -m "feat: 個人醫學網站初版上線"

# 4. 建立 GitHub repo（public）
gh repo create 你的-repo-名稱 --public --description "網站描述"

# 5. 推送
git remote add origin https://github.com/帳號/repo名稱.git
git push -u origin main

# 6. 啟用 GitHub Pages（必須用 JSON file，不能用 --field）
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
$body = '{"source":{"branch":"main","path":"/"}}'
$tmp = "$env:TEMP\gh_pages.json"
[System.IO.File]::WriteAllText($tmp, $body, $utf8NoBom)
gh api repos/帳號/repo名稱/pages --method POST --input $tmp
```

### 結果

約 1–3 分鐘後，網址生效：
```
https://帳號.github.io/repo名稱/
```

之後可貼到 Facebook、LINE、Email 直接分享。

---

## 踩坑紀錄（完整版，共 11 個坑）

### 坑 1：Edit 工具 old_string 必須逐字元吻合

**症狀：** 連續報 "String not found in file"  
**根因：** old_string 多一個 backtick、或 tab/space 不一致  
**SOP：** Grep 找行號 → Read 讀那幾行 → 複製貼上 → 再 Edit  
**教訓：** 不要憑記憶寫 old_string

---

### 坑 2：上傳圖片（photo / logo）不等於存到本機路徑

**症狀：** 圖片附在對話中上傳，網站仍顯示破圖  
**根因：** Claude Code 圖片上傳僅供 AI 閱讀，不寫入磁碟  
**SOP：**
```powershell
# 先列出專案目錄——圖片可能以原始中文檔名存在同層
Get-ChildItem "C:\...\專案資料夾\" -Force | Format-Table Name, Length, LastWriteTime

# 若找到，重新命名複製
Copy-Item "朱國大_醫師形象照.png" "photo.png" -Force
Copy-Item "kidney_brain_logo.png"  "logo.png"  -Force
```
**教訓：** 每次圖片處理前先 `Get-ChildItem` 確認，通常圖片以原始名稱存在專案目錄

---

### 坑 3：img onerror 回退鏈寫法

```html
<!-- 正確：PNG → JPG → 隱藏 -->
<img src="photo.png"
     onerror="this.src='photo.jpg'; this.onerror=function(){this.style.display='none'}">
<!-- 錯誤：會導致無限 retry -->
<img src="photo.png" onerror="this.src='photo.jpg'">
```

---

### 坑 4：Chart.js plugin 必須在 new Chart() 時傳入

```javascript
// 正確
new Chart(ctx, { plugins: [markerPlugin], data:{...}, options:{...} });
// 錯誤（部分情境不生效）
Chart.register(myPlugin);
```

---

### 坑 5：SVG path 預設 pointer-events: none

```css
.brain-region { pointer-events: all; cursor: pointer; }
```

---

### 坑 6：AOS 對動態插入元素需手動 refresh

```javascript
AOS.init({ once: true });
// 動態新增元素後：
AOS.refresh();
```

---

### 坑 7：同一 canvas 不能有兩個 Chart 實例

```javascript
if (window.myChart) window.myChart.destroy();
window.myChart = new Chart(canvas, config);
```

---

### 坑 8：PowerShell 5.1 Out-File 預設加 BOM，GitHub API 會拒絕

```powershell
# 錯誤（含 BOM → HTTP 400）
$json | Out-File $tmp -Encoding utf8

# 正確（無 BOM）
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($tmp, $json, $utf8NoBom)
```

---

### 坑 9：gh api --field 不能傳 JSON 物件，必須用 --input

```powershell
# 錯誤（HTTP 422，GitHub 無法解析 JSON 物件型欄位）
gh api .../pages --method POST --field source='{"branch":"main","path":"/"}'

# 正確（寫入 JSON 檔 → --input 傳入）
$body = '{"source":{"branch":"main","path":"/"}}'
[System.IO.File]::WriteAllText($tmp, $body, $utf8NoBom)
gh api .../pages --method POST --input $tmp
```

---

### 坑 10：GitHub Pages 啟用後需等 1–3 分鐘才生效

啟用後立即訪問會回 404，這是正常的建置等待時間，重新整理即可。

---

### 坑 11：YAML frontmatter 用 | 不要用 >

```yaml
# 正確（Claude Code skill loader 接受）
description: |
  多行描述...

# 錯誤（loader 誤判為沒有 frontmatter）
description: >
  多行描述...
```

---

## 驗收清單

- [ ] eGFR 滑桿：公式、分期徽章、圖表、腎元動畫四者同步更新
- [ ] 大腦 SVG：6 腦區各自點擊後資訊面板正確顯示
- [ ] 雷達圖：兩資料集切換按鈕正常
- [ ] MCQ：即時回饋 + 解釋 + 分數正確
- [ ] 漢堡選單：375px 下可開關，點選後自動關閉
- [ ] 形象照 + Logo：正常顯示，失敗時優雅降級
- [ ] Console：無 JS 錯誤
- [ ] GitHub Pages URL 可正常開啟

---

## 安裝

```powershell
# Windows
xcopy /E /I personal-medical-website "%APPDATA%\Claude\skills\personal-medical-website"
```

```bash
# macOS/Linux
cp -r personal-medical-website ~/.claude/skills/
```

---

## 關聯技能

- `soil-html-deck`：互動式 HTML 簡報
- `admission-note`：住院病歷自動生成
