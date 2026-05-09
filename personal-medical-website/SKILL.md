---
name: personal-medical-website
description: |
  單一 HTML 檔案的個人互動式醫學/學術網站技能。
  適合臨床醫師、研究者、雙專長學者建立中文個人作品集 + 知識教育網站。
  輸出：單一 index.html（自含 CSS + JS，無 build 步驟，瀏覽器直接開啟）。
  當使用者說「幫我做個人網站」、「醫師個人頁面」、「學術作品集」、
  「互動式自我介紹網站」、「portfolio 網站」、「個人介紹 HTML」、
  「做一個關於我研究領域的網站」時，請使用此技能。
  本技能內嵌 CKD-EPI 2021 計算器、Chart.js 圖表、SVG 腦區互動地圖、
  MCQ 測驗等醫學教育互動模組，同時提供詳細踩坑紀錄供 AI 避開重複錯誤。
---

# Personal Medical Website Skill

單一 `index.html` 互動式個人醫學網站，整合個人作品集與醫學知識教育。

---

## 適用對象

| 身分 | 典型需求 |
|------|---------|
| 臨床醫師 | 個人作品集 + 病患衛教互動工具 |
| 醫學研究者 | 跨域研究整合展示 + 著作時間軸 |
| 雙專長學者（如腎臟科 + 認知神經科學） | 兩領域知識視覺化 + 跨域連結章節 |
| 教授/講師 | 演講記錄 + 課程列表 + MCQ 測驗 |

---

## 輸入

使用者需提供（分批 OK，可先用佔位符）：
- **個人基本資料**：姓名、職稱、服務單位、Email
- **學術連結**：Google Scholar URL、ORCID（可留空）
- **學經歷 PDF 或文字**：學歷、證照、職涯時間軸
- **研究著作**：論文引用清單（APA / DOI）
- **形象照**：`photo.png` 或 `photo.jpg`（放專案根目錄）
- **Logo**（選填）：`logo.png`（放專案根目錄）
- **專長領域**：供互動圖表設計使用

---

## 輸出結構

```
index.html         ← 唯一輸出，單一檔案，瀏覽器直接開啟
photo.png          ← 形象照（需使用者手動放入）
logo.png           ← 網站 Logo（需使用者手動放入）
```

---

## 網站七大章節

| # | ID | 中文標題 | 主要互動功能 |
|---|----|---------|------------|
| 1 | `#hero` | 英雄首頁 | 打字機動效（4 短語輪播）、Logo 展示、CTA 按鈕 |
| 2 | `#about` | 關於我 | 形象照、Bio、學歷/證照/職涯時間軸、專長卡片 |
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

### 色彩系統（CSS Custom Properties）

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

字型：`Noto Sans TC`（中文）、`Inter`（英數）、`JetBrains Mono`（eGFR 數值輸出）

---

## 關鍵互動模組實作

### A. eGFR 計算器（CKD-EPI 2021，無種族因子）

```javascript
function calcGFR(scr, age, sex) {
  const kappa     = sex === 'female' ? 0.7  : 0.9;
  const alpha     = sex === 'female' ? -0.241 : -0.302;
  const sexFactor = sex === 'female' ? 1.012 : 1.0;
  const ratio     = scr / kappa;
  return 142 * Math.min(ratio, 1) ** alpha
             * Math.max(ratio, 1) ** (-1.200)
             * (0.9938 ** age)
             * sexFactor;
}
```

輸入：性別切換 + 肌酐滑桿（0.4–10.0 mg/dL）+ 年齡滑桿（18–90）  
輸出：eGFR 數值 + CKD 分期徽章 + 圖表即時更新 + 腎元動畫速率

### B. CKD 分期圖（Chart.js 自定義 afterDraw marker plugin）

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
```

### C. 腎元 SVG 動畫（速率與 eGFR 連動）

```javascript
function updateKidneySpeed(gfr) {
  const dots = document.querySelectorAll('.filtrate-dot');
  const duration = gfr > 90 ? 2 : gfr > 60 ? 3 : gfr > 30 ? 5 : gfr > 15 ? 8 : 12;
  dots.forEach(d => d.style.animationDuration = duration + 's');
}
```

### D. 大腦 SVG 互動地圖

6 個 `<path data-region="...">` 腦區，點擊後右側資訊面板滑入：
- Frontal Lobe、Parietal Lobe、Temporal Lobe、Occipital Lobe、Cerebellum、Brainstem

```javascript
const brainData = {
  frontal: { title: '額葉', color: '#4dd9cf', functions: [...], clinical: '...' },
  // ...
};
document.querySelectorAll('[data-region]').forEach(path => {
  path.addEventListener('click', () => showBrainInfo(path.dataset.region));
});
```

### E. 認知雷達圖（典型老化 vs MCI 切換）

6 軸：執行功能、記憶力、語言、注意力、視空間、處理速度  
兩資料集以按鈕切換，`Chart.js` `type: 'radar'`

### F. MCQ 測驗（3 題，即時回饋）

題目整合跨域知識（情節記憶腦區、CKD 認知障礙類型、rs-fMRI 用途）  
完成後顯示分數 + 重新作答按鈕

---

## 踩坑紀錄（建站過程實際遭遇，2026-05）

### 坑 1：Edit 工具的 old_string 必須逐字符吻合

**症狀：** `Edit` 工具報 "String not found in file"，即使目標文字看起來一致。

**根因：** `old_string` 中多了一個 backtick、或空白縮排不一致（tab vs space），導致完全不匹配。

**修正 SOP：**
1. 先用 `Grep` 工具搜尋要改的關鍵字，取得精確行號
2. 用 `Read` 工具讀取那幾行，複製確切的原始文字
3. 再用 `Edit` 工具執行替換

**教訓：** 不要憑記憶寫 old_string，一定要從 Read 工具的輸出複製貼上。

---

### 坑 2：上傳的圖片不會自動存到專案資料夾

**症狀：** 使用者上傳了 `photo.png`，網站卻看不到圖。  
PowerShell 在 Downloads/Desktop/TEMP 搜尋均找不到檔案。

**根因：** Claude Code 的圖片上傳是在對話脈絡中「附加」圖片供 AI 閱讀，  
不等於將檔案寫入到本機檔案系統的特定路徑。

**修正方案：**
```powershell
# 先確認使用者已手動儲存檔案，或搜尋可能的路徑
Get-ChildItem "C:\Users\$env:USERNAME\Documents" -Recurse -Filter "*.png" |
  Sort-Object LastWriteTime -Descending | Select-Object -First 10
```

如找到，再複製到專案根目錄：
```powershell
Copy-Item "原始路徑\photo.png" "C:\Users\User\Documents\New project 4\photo.png" -Force
```

**最終發現：** 圖片有時以中文原檔名存在專案目錄同層，直接 `Copy-Item` 即可。

**教訓：** 上傳圖片後，第一步是 `Get-ChildItem` 列出專案目錄，  
可能圖片已在那裡，只是檔名是中文原始名稱，重新命名為 `photo.png` 即可。

---

### 坑 3：img 的 onerror 回退鏈寫法

單一 `onerror` 只觸發一次，需串聯回退：

```html
<!-- 正確：PNG → JPG → 隱藏 -->
<img src="photo.png" alt="..."
     onerror="this.src='photo.jpg'; this.onerror=function(){this.style.display='none'}">
```

錯誤寫法（`onerror` 無限迴圈）：
```html
<!-- 錯誤：若 fallback 也不存在會無限 retry -->
<img src="photo.png" onerror="this.src='photo.jpg'">
```

---

### 坑 4：Chart.js 自定義 plugin 必須在 `new Chart()` 前或 plugins 陣列中傳入

```javascript
// 錯誤：全局 register 後 plugin 可能不影響已建立的 chart instance
Chart.register(myPlugin);

// 正確：在 config 的 plugins 陣列中直接傳入 plugin 物件
new Chart(ctx, {
  plugins: [markerPlugin],  // ← 直接放這裡
  data: { ... },
  options: { ... }
});
```

---

### 坑 5：SVG 腦區地圖的 path 必須設 pointer-events

純 SVG `<path>` 預設 `pointer-events: none`（在某些瀏覽器），  
點擊事件不觸發。

```css
.brain-region {
  pointer-events: all;
  cursor: pointer;
  transition: fill 0.2s;
}
.brain-region:hover { fill: rgba(77, 217, 207, 0.4); }
```

---

### 坑 6：AOS 動效只初始化一次，動態插入的元素需 refresh

```javascript
AOS.init({ once: true, duration: 800 });

// 動態新增元素後：
AOS.refresh();
```

---

### 坑 7：單頁多個 Chart.js 實例共享同一 canvas 會報錯

每個 canvas 只能有一個 Chart 實例。  
重新建立前必須先 `destroy()`：

```javascript
if (window.myCkdChart) window.myCkdChart.destroy();
window.myCkdChart = new Chart(document.getElementById('ckdChart'), config);
```

---

### 坑 8：GitHub 推送前確認 gh 工具已登入

```powershell
gh auth status  # 確認 Token scopes 包含 repo
```

---

### 坑 9：YAML frontmatter 用 | 不要用 >

(繼承自 SOIL skill 踩坑：Claude Code skill loader 不接受 folded block `>`)

```yaml
# 正確
description: |
  多行描述...

# 錯誤（loader 可能誤判為沒有 frontmatter）
description: >
  多行描述...
```

---

## 實作順序建議

1. `<head>` CDN + CSS 變數 + Reset
2. 導覽列（漢堡選單 + 捲動半透明效果）
3. Hero（打字機 + Logo + CTA）
4. 關於我（形象照 + Bio + 學歷 + 職涯時間軸 + 專長卡片）
5. 腎臟科學（eGFR 計算器 → CKD 圖 → 腎元 SVG）
6. 腎腦軸整合（流程圖 + 兩張 Chart.js）
7. 認知神經科學（大腦 SVG → 雷達圖 → MCQ）
8. 研究著作時間軸
9. 聯絡 + Footer
10. RWD 調整（375px / 768px / 1024px）

---

## 驗收清單

- [ ] eGFR 滑桿：公式、分期徽章、圖表、腎元動畫四者同步更新
- [ ] 大腦 SVG：6 個腦區各自點擊後資訊面板正確顯示
- [ ] 雷達圖：兩個資料集切換按鈕正常
- [ ] MCQ：回答後即時顯示正確/錯誤 + 解釋，分數正確累加
- [ ] 漢堡選單：375px 下可開關，點選項目後自動關閉
- [ ] 形象照：若 `photo.png` 不存在，自動嘗試 `photo.jpg`，仍失敗則隱藏
- [ ] Console：無 JS 錯誤

---

## 安裝

```bash
cp -r personal-medical-website ~/.claude/skills/
# 或 Windows：
xcopy /E /I personal-medical-website "%APPDATA%\Claude\skills\personal-medical-website"
```

重啟 Claude Code 即可使用。

---

## 關聯技能

- `soil-html-deck`：互動式 HTML 簡報（更輕量的單頁展示）
- `admission-note`：住院病歷自動生成
