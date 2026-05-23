---
name: interactive-website-designer
description: |
  端到端建立互動式單頁網站（含個人醫學/學術作品集 + 即時課堂投票系統），
  支援 Firebase Firestore 即時資料同步、QR Code 入場、主持人控答案揭示，
  最後部署至 GitHub Pages。
  觸發短語：「幫我做互動式網站」、「個人網站 + 投票系統」、「課堂即時投票」、
  「做一個有投票功能的網站」、「幫我設計課堂互動投票頁」、「interactive voting website」、
  「personal website with live poll」、「portfolio + 投票」。
  適用平台：Windows / macOS / Linux，共用同一套 HTML + Firebase 架構。
---

# 互動式網站設計（跨平台通用）

單一 `index.html` 或 `vote.html`，零 build 步驟，瀏覽器直接開啟，可部署至 GitHub Pages。

---

## 目錄

- [模式 A：個人醫學/學術網站](#模式-a個人醫學學術網站)
- [模式 B：即時課堂投票網站](#模式-b即時課堂投票網站)
- [部署到 GitHub Pages（跨平台）](#部署到-github-pages跨平台)
- [Firebase 設定 SOP](#firebase-設定-sop)
- [踩坑紀錄（15 個實戰坑）](#踩坑紀錄15-個實戰坑)
- [驗收清單](#驗收清單)
- [安裝](#安裝)

---

## 模式 A：個人醫學/學術網站

（本模式繼承 `personal-medical-website` 技能，此處僅摘要）

### 輸出結構

```
專案根目錄/
├── index.html      ← 唯一網站主檔（全部內嵌）
├── photo.png       ← 形象照
├── logo.png        ← Logo
└── .gitignore
```

### 七大章節

| # | 區域 | 中文標題 | 功能 |
|---|------|---------|------|
| 1 | `#hero` | 英雄首頁 | 打字機動效、Logo、CTA |
| 2 | `#about` | 關於我 | 形象照、Bio、學歷/職涯時間軸、專長卡片 |
| 3 | `#nephrology` | 腎臟科學 | eGFR 計算器（CKD-EPI 2021）、CKD 分期圖、腎元 SVG |
| 4 | `#kidney-brain` | 腎腦軸 | 流程圖、盛行率長條圖、認知下降折線圖 |
| 5 | `#neuroscience` | 認知神經科學 | 大腦 SVG 互動地圖、認知雷達圖、MCQ |
| 6 | `#research` | 研究著作 | 垂直時間軸、Google Scholar |
| 7 | `#contact` | 聯絡 | Email、單位 |

### CDN（單頁內嵌，零 build）

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<link  href="https://unpkg.com/aos@2.3.4/dist/aos.css" rel="stylesheet">
<script src="https://unpkg.com/aos@2.3.4/dist/aos.js"></script>
<link  href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
<link  href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700&family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

### 關鍵互動模組

**eGFR 計算器（CKD-EPI 2021 無種族因子）：**

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

**大腦 SVG 互動地圖（6 腦區，注意 `pointer-events: all`）：**

```css
.brain-region { pointer-events: all; cursor: pointer; }
```

### 完整實作參考

完整 SKILL.md 內容另見 `personal-medical-website` skill，此處不再重複 400+ 行。

---

## 模式 B：即時課堂投票網站

使用 Firebase Firestore 作為即時資料庫，搭配 Firebase Anonymous Auth 識別參與者。

### 架構圖

```
┌──────────────┐     Firestore（teachers-study）     ┌──────────────┐
│  主持人瀏覽器  │ ─── reads/writes ──►   votes/{id}  ◄── ──│  參與者瀏覽器  │
│  (isHost=true) │     controls/host doc     │  (匿名登入)   │
└──────────────┘                          └──────────────┘
                        ▲
                        │
                    GitHub Pages（靜態託管）
```

### 核心功能

| 功能 | 實作方式 |
|------|---------|
| 即時長條圖 | Firestore `onSnapshot` 監聽 `responses` map |
| 參與者計數 | 跨題目 UID 聯集 |
| 重新開始 | Firestore batch write，清除所有 `responses` + `answersRevealed` |
| 主持人公佈答案 | Firestore doc 欄位 `answersRevealed`，由主持人按鈕寫入 |
| QR Code 入場 | `api.qrserver.com` 伺服端生成（純 `<img>`，無 client library） |
| 更改答案 | 選項保持可點擊，submit 時 `update` 覆寫 `responses.{uid}` |

### Firebase 資料結構

```
votes/CP1
  ├── question: "訓練混沌 RNN 為什麼難?"
  ├── options: ["A. ...", "B. ...", "C. ...", "D. ..."]
  ├── responses: { uid1: "A", uid2: "C", ... }
  ├── answersRevealed: false
  └── active: true

controls/host
  └── uid: "first-visitor-anonymous-uid"
```

### 安全規則（`firestore.rules`）

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /votes/{document} {
      allow read, write: if true;
    }
    match /controls/{document} {
      allow read, write: if true;
    }
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

### 投票頁面完整實作

以下是完整的 `vote.html` 範本。將其中的 Firebase Config 替換為你自己的專案資料，
`DATA` 陣列替換為你的題目，即可使用。

```html
<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title><!-- TODO: 替換為你的標題 --></title>
<script src="https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.14.1/firebase-auth-compat.js"></script>

<style>
:root {
  color-scheme: dark;
  --bg: #0d1117;
  --panel: #141b24;
  --panel-strong: #182231;
  --line: rgba(148, 163, 184, .28);
  --text: #f1f5f9;
  --muted: #94a3b8;
  --green: #10b981;
  --violet: #a78bfa;
  --amber: #f59e0b;
  --rose: #f43f5e;
  --cyan: #22d3ee;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  min-height: 100vh;
  font-family: Inter, "Noto Sans TC", "Microsoft JhengHei", system-ui, sans-serif;
  background: radial-gradient(circle at 20% 0%, rgba(34, 211, 238, .14), transparent 28rem), linear-gradient(135deg, #0d1117 0%, #111827 55%, #0f172a 100%);
  color: var(--text);
}
a { color: inherit; }
.app-shell { width: min(1120px, calc(100% - 32px)); margin: 0 auto; padding: 24px 0 32px; }
.topbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 10px 0 22px; flex-wrap: wrap; }
.topbar-left { display: flex; align-items: center; gap: 12px; }
.mark {
  display: grid; place-items: center; width: 34px; height: 34px;
  border: 1px solid var(--line); border-radius: 8px;
  background: rgba(15, 23, 42, .8); color: var(--green); font-weight: 800;
}
.brand-label { color: var(--muted); font-size: 14px; }
.navlinks { display: flex; flex-wrap: wrap; gap: 8px; }
.navlinks a {
  min-height: 36px; padding: 8px 11px; border: 1px solid var(--line); border-radius: 8px;
  background: rgba(15, 23, 42, .62); color: #cbd5e1; text-decoration: none; font-size: 13px; line-height: 18px; cursor: pointer;
  transition: border-color .16s, background .16s, color .16s;
}
.navlinks a.active { border-color: rgba(16, 185, 129, .7); color: white; background: rgba(16, 185, 129, .14); }
.navlinks a:hover { border-color: rgba(34, 211, 238, .5); }
.qr-area { display: flex; align-items: center; gap: 8px; }
.qr-area #qrImg { border-radius: 8px; width: 100px; height: 100px; }
.qr-area .qr-label { font-size: 11px; color: var(--muted); line-height: 1.3; text-align: right; }
.participant-bar {
  display: flex; justify-content: space-between; align-items: center;
  border: 1px solid var(--line); border-radius: 8px; background: rgba(20, 27, 36, .88);
  padding: 10px 16px; margin-bottom: 22px; font-size: 14px; box-shadow: 0 18px 60px rgba(0,0,0,.28);
}
.participant-bar .count { font-weight: 700; color: var(--green); font-size: 16px; }
.participant-bar .reset-btn {
  background: none; border: 1px solid rgba(244,63,94,.4); color: var(--rose); font: inherit; font-size: 12px;
  padding: 5px 12px; border-radius: 6px; cursor: pointer; transition: border-color .16s, background .16s;
}
.participant-bar .reset-btn:hover { border-color: var(--rose); background: rgba(244,63,94,.12); }
.overlay {
  display: none; position: fixed; inset: 0; background: rgba(0,0,0,.7); z-index: 1000;
  justify-content: center; align-items: center;
}
.overlay.show { display: flex; }
.overlay .box {
  background: #141b24; border: 1px solid var(--line); border-radius: 12px; padding: 28px; max-width: 400px; width: 90%;
  text-align: center; box-shadow: 0 24px 80px rgba(0,0,0,.5);
}
.overlay .box h2 { font-size: 18px; margin-bottom: 8px; }
.overlay .box p { color: #cbd5e1; font-size: 14px; line-height: 1.6; margin-bottom: 20px; }
.overlay .box .actions { display: flex; gap: 10px; justify-content: center; }
.overlay .box .actions button {
  min-height: 40px; padding: 8px 20px; border-radius: 8px; border: 1px solid var(--line);
  font: inherit; font-weight: 700; cursor: pointer; font-size: 14px;
}
.overlay .box .actions .danger { background: var(--rose); color: #fff; border-color: transparent; }
.overlay .box .actions .cancel { background: rgba(15,23,42,.72); color: #cbd5e1; }
.layout { display: grid; grid-template-columns: minmax(0, 1fr) 360px; gap: 22px; align-items: start; }
.quiz-card, .side-panel { border: 1px solid var(--line); border-radius: 8px; background: rgba(20, 27, 36, .88); box-shadow: 0 18px 60px rgba(0,0,0,.28); }
.quiz-card { padding: 28px; }
.kicker { color: var(--green); font-family: "SFMono-Regular", Consolas, monospace; font-size: 13px; font-weight: 800; text-transform: uppercase; }
h1 { margin: 10px 0 8px; font-size: 36px; line-height: 1.18; }
.prompt { margin: 0 0 22px; color: #cbd5e1; font-size: 18px; line-height: 1.65; }
.question-label {
  display: inline-flex; align-items: center; min-height: 28px; margin-bottom: 10px; padding: 4px 9px;
  border-radius: 8px; background: rgba(167, 139, 250, .16); color: #ddd6fe;
  font-family: "SFMono-Regular", Consolas, monospace; font-size: 12px; font-weight: 800;
}
.options { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 10px; }
.option {
  display: grid; grid-template-columns: 42px minmax(0, 1fr); align-items: center; min-height: 62px;
  border: 1px solid var(--line); border-radius: 8px; background: rgba(15, 23, 42, .74);
  color: var(--text); cursor: pointer; text-align: left;
  transition: border-color .16s ease, transform .16s ease, background .16s ease;
  font: inherit; font-size: 15px; padding: 0;
}
.option:hover, .option:focus-visible { outline: none; transform: translateY(-1px); border-color: rgba(34, 211, 238, .7); }
.option.selected { border-color: rgba(167, 139, 250, .92); background: rgba(167, 139, 250, .13); }
.option.voted { border-color: rgba(16, 185, 129, .96); background: rgba(16, 185, 129, .14); }
.option .letter {
  display: grid; place-items: center; width: 30px; height: 30px; margin-left: 12px;
  border-radius: 8px; background: rgba(148, 163, 184, .13); color: white;
  font-family: "SFMono-Regular", Consolas, monospace; font-weight: 900;
}
.option.voted .letter { background: rgba(16, 185, 129, .4); }
.option .option-text { min-width: 0; padding: 12px 14px 12px 2px; line-height: 1.45; overflow-wrap: anywhere; }
.actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }
.primary {
  min-height: 42px; border: 1px solid transparent; border-radius: 8px; padding: 10px 16px;
  background: linear-gradient(135deg, #0ea5e9, var(--green)); color: white;
  font: inherit; font-weight: 800; cursor: pointer;
}
.primary:disabled { cursor: not-allowed; opacity: .48; }
.poll-bars { display: grid; gap: 9px; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--line); }
.poll-row { display: grid; grid-template-columns: 38px minmax(0, 1fr) 48px 32px; gap: 10px; align-items: center; color: #cbd5e1; font-size: 13px; }
.poll-row .lbl { font-weight: 700; color: var(--text); font-family: "SFMono-Regular", Consolas, monospace; }
.bar-track { height: 10px; border-radius: 999px; background: rgba(148, 163, 184, .17); overflow: hidden; }
.bar-fill { height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--violet), var(--cyan)); transition: width .4s ease; }
.poll-row .pct { text-align: right; font-weight: 700; }
.poll-row .votes { text-align: right; font-size: 11px; color: var(--muted); }
.pager { display: flex; justify-content: space-between; gap: 10px; margin-top: 18px; }
.pager a {
  flex: 1; min-height: 42px; padding: 10px 12px; border: 1px solid var(--line); border-radius: 8px;
  background: rgba(15, 23, 42, .62); color: #cbd5e1; text-align: center; text-decoration: none; font-size: 14px; cursor: pointer;
  transition: border-color .16s;
}
.pager a:hover { border-color: rgba(34, 211, 238, .7); }
.side-panel { position: sticky; top: 18px; overflow: hidden; }
.visual { min-height: 260px; padding: 14px; background: #11161d; }
.visual svg { display: block; width: 100%; height: auto; }
.note-box { padding: 18px; border-top: 1px solid var(--line); }
.note-box h2 { margin: 0 0 9px; font-size: 18px; }
.note-box p { margin: 0; color: #cbd5e1; line-height: 1.6; }
.toast {
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
  background: #1e293b; border: 1px solid var(--line); color: #d1fae5; padding: 10px 24px;
  border-radius: 8px; font-size: 14px; opacity: 0; transition: opacity .3s; pointer-events: none; z-index: 999;
}
.toast.show { opacity: 1; }

@media (max-width: 900px) {
  .layout { display: block; }
  .topbar { flex-direction: column; align-items: stretch; }
  .topbar-left { flex-wrap: wrap; }
  .navlinks { justify-content: flex-start; }
  .quiz-card { padding: 22px; }
  h1 { font-size: 30px; }
  .options { grid-template-columns: 1fr; }
  .side-panel { position: static; margin-top: 18px; }
}
@media (max-width: 520px) {
  .app-shell { width: calc(100% - 20px); padding-top: 12px; }
  .quiz-card { padding: 18px; }
  h1 { font-size: 26px; }
  .prompt { font-size: 16px; }
  .option { min-height: 52px; }
}
</style>
</head>
<body>
<main class="app-shell">
  <header class="topbar">
    <div class="topbar-left">
      <div class="mark" id="navMark"><!-- TODO: 簡稱 --></div>
      <span class="brand-label"><!-- TODO: 品牌名稱 --></span>
      <span id="hostBadge" style="display:none;font-size:11px;color:var(--amber);border:1px solid rgba(245,158,11,.4);border-radius:6px;padding:2px 8px">主持人</span>
      <nav class="navlinks" id="navLinks"></nav>
    </div>
    <div class="qr-area">
      <div class="qr-label" id="voteUrlLabel">載入中...</div>
      <img id="qrImg" alt="QR Code">
      <a id="qrFallback" href="#" target="_blank" style="display:none;font-size:11px;color:var(--cyan);word-break:break-all;max-width:100px;text-align:right">打開投票頁面</a>
    </div>
  </header>

  <div class="participant-bar">
    <span>👥 參與人數 <span class="count" id="participantCount">—</span></span>
    <button class="reset-btn" id="resetBtn">重新開始</button>
  </div>

  <div class="overlay" id="resetOverlay">
    <div class="box">
      <h2>確定要重新開始？</h2>
      <p>這將清除所有投票資料（共 <span id="totalVotesSpan">0</span> 筆），且無法復原。</p>
      <div class="actions">
        <button class="cancel" id="cancelReset">取消</button>
        <button class="danger" id="confirmReset">確定歸零</button>
      </div>
    </div>
  </div>

  <section class="layout" id="layout">
    <div id="cardsContainer"></div>
    <aside class="side-panel" id="sidePanel">
      <div class="visual" id="visualContainer"></div>
      <div class="note-box" id="noteBox">
        <h2 id="noteTitle"></h2>
        <p id="noteBody"></p>
      </div>
    </aside>
  </section>
  <div class="toast" id="toast"></div>
</main>

<script>
// ═══════════════════════════════════════════════════
// 步驟 1：替換為你的 Firebase Config
// ═══════════════════════════════════════════════════
const firebaseConfig = {
  apiKey: "AIzaSyXXXXXXXX-xxxxxxxxxxxxxxxxxx",
  authDomain: "your-project.firebaseapp.com",
  projectId: "your-project",
  storageBucket: "your-project.firebasestorage.app",
  messagingSenderId: "000000000000",
  appId: "1:000000000000:web:xxxxxxxxxxxxxxxx"
};
firebase.initializeApp(firebaseConfig);
const db = firebase.firestore();
const auth = firebase.auth();

const COLORS = ['#3b82f6','#10b981','#f59e0b','#ef4444'];

// ═══════════════════════════════════════════════════
// 步驟 2：定義你的題目陣列
// ═══════════════════════════════════════════════════
const DATA = [
  // 每個題目物件格式：
  // { id:'CP1',          ← Firestore doc ID，必須唯一
  //   kicker:'標題前綴',   ← monospace 綠色標籤
  //   title:'題目標題',
  //   prompt:'題目說明文字',
  //   qlabel:'SELECT ONE', ← 紫色標籤
  //   subPrompt:'副提示',   ← 選填
  //   opts:[四行選項],      ← 四字串
  //   svg:`<svg>...</svg>`,← 側欄圖形
  //   noteTitle:'解答標題',
  //   noteBody:'解答內容' }
  { id:'CP1', kicker:'投票 · 1', title:'範例問題',
    prompt:'請選擇你的答案。',
    qlabel:'SELECT ONE',
    opts:['A. 選項一','B. 選項二','C. 選項三','D. 選項四'],
    svg:`<svg viewBox="0 0 420 300"><rect width="420" height="300" fill="#11161d"/><text x="210" y="150" fill="#94a3b8" font-size="20" text-anchor="middle">替換為你的 SVG 圖形</text></svg>`,
    noteTitle:'解答標題', noteBody:'解答說明文字。' }
];
/* 複製上述物件以新增更多題目
   { id:'CP2', ... },
   { id:'CP3', ... },
*/

// ═══════════════════════════════════════════════════
// 以下為引擎程式碼，通常無需修改
// ═══════════════════════════════════════════════════
let uid = null, currentIdx = 0, isHost = false;
let unsubscribes = [], myVotes = {}, voteData = {};
const container = document.getElementById('cardsContainer');
const visualC = document.getElementById('visualContainer');
const noteTitle = document.getElementById('noteTitle');
const noteBody = document.getElementById('noteBody');
const navLinks = document.getElementById('navLinks');

auth.signInAnonymously().then(async cred => {
  uid = cred.user.uid;
  var url = window.location.href;
  document.getElementById('voteUrlLabel').textContent = url;
  var qrImg = document.getElementById('qrImg');
  var qrFallback = document.getElementById('qrFallback');
  qrFallback.href = url;
  qrImg.onload = function() { qrImg.style.display = ''; qrFallback.style.display = 'none'; };
  qrImg.onerror = function() { qrImg.style.display = 'none'; qrFallback.style.display = 'inline'; };
  qrImg.src = 'https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=' + encodeURIComponent(url);
  var hostRef = db.collection('controls').doc('host');
  var hostSnap = await hostRef.get();
  if (!hostSnap.exists) { await hostRef.set({ uid: uid }); isHost = true; }
  else if (hostSnap.data().uid === uid) { isHost = true; }
  if (isHost) document.getElementById('hostBadge').style.display = '';
  await ensureDocs();
  listenVotes();
  switchTo(0);
}).catch(err => {
  container.innerHTML = `<article class="quiz-card" style="text-align:center;padding:60px 28px;">
    <div class="kicker" style="color:var(--rose)">連線失敗</div>
    <p style="color:var(--muted);margin-top:12px">${err.message}</p>
  </article>`;
});

// 建立導覽列
DATA.forEach((d,i) => {
  var a = document.createElement('a');
  a.dataset.cp = i;
  a.textContent = String(i+1).padStart(2,'0');
  a.addEventListener('click', () => switchTo(i));
  navLinks.appendChild(a);
});

async function ensureDocs() {
  const batch = db.batch();
  for (const d of DATA) {
    const ref = db.collection('votes').doc(d.id);
    if (!(await ref.get()).exists)
      batch.set(ref, { question: d.title, options: d.opts, responses: {}, answersRevealed: false, active: true, createdAt: firebase.firestore.FieldValue.serverTimestamp() });
  }
  await batch.commit();
}

function listenVotes() {
  for (const d of DATA) {
    const unsub = db.collection('votes').doc(d.id).onSnapshot(snap => {
      if (!snap.exists) return;
      var sd = snap.data();
      voteData[d.id] = { responses: sd.responses || {}, answersRevealed: !!sd.answersRevealed };
      if (d.id === DATA[currentIdx].id) { renderCard(currentIdx); showSide(currentIdx); }
      updateCount();
    });
    unsubscribes.push(unsub);
  }
}

function updateCount() {
  const all = new Set();
  Object.values(voteData).forEach(m => Object.keys(m.responses || {}).forEach(k => all.add(k)));
  document.getElementById('participantCount').textContent = all.size;
}

function switchTo(idx) {
  currentIdx = idx;
  document.querySelectorAll('.navlinks a').forEach((a,i) => a.classList.toggle('active', i===idx));
  document.getElementById('navMark').textContent = String(idx+1).padStart(2,'0');
  renderCard(idx);
  showSide(idx);
}

function renderCard(idx) {
  const d = DATA[idx];
  const respMap = (voteData[d.id] || {}).responses || {};
  const total = Object.keys(respMap).length;
  const counts = {};
  d.opts.forEach((_,i) => { const l = String.fromCharCode(65+i); counts[l] = Object.values(respMap).filter(v=>v===l).length; });
  const myVote = myVotes[d.id] || (respMap[uid] || null);
  const promptHtml = d.subPrompt ? `<p class="prompt">${d.subPrompt}</p>` : '';
  let selectedNow = selectedIdx !== null ? String.fromCharCode(65+selectedIdx) : null;
  let optsHtml = d.opts.map((opt,i) => {
    const letter = String.fromCharCode(65+i);
    const label = opt.replace(/^[A-D]\.\s*/, '');
    let cls = 'option';
    if (selectedNow === letter) cls += ' selected';
    else if (myVote === letter && selectedNow === null) cls += ' voted';
    return `<button class="${cls}" data-idx="${i}">
      <span class="letter">${letter}</span><span class="option-text">${label}</span></button>`;
  }).join('');
  let pollHtml = '';
  if (myVote) {
    pollHtml = d.opts.map((_,i) => {
      const letter = String.fromCharCode(65+i);
      const count = counts[letter]||0;
      const pct = total ? Math.round(count/total*100) : 0;
      return `<div class="poll-row">
        <span class="lbl">${letter}</span>
        <div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:${COLORS[i]}"></div></div>
        <span class="pct">${pct}%</span>
        <span class="votes">${count}</span>
      </div>`;
    }).join('');
  } else {
    pollHtml = '<div style="margin-top:16px;padding-top:16px;border-top:1px solid var(--line);color:var(--muted);font-size:13px;text-align:center">📊 投票後即可查看即時結果</div>';
  }
  const prevIdx = idx > 0 ? idx-1 : -1;
  const nextIdx = idx < DATA.length-1 ? idx+1 : -1;
  let pagerHtml = '';
  if (prevIdx >=0) pagerHtml += `<a class="pg prev" data-idx="${prevIdx}">← 上一題</a>`;
  else pagerHtml += `<a style="visibility:hidden"></a>`;
  if (nextIdx >=0) pagerHtml += `<a class="pg next" data-idx="${nextIdx}">下一題 →</a>`;
  else pagerHtml += `<a style="visibility:hidden"></a>`;
  container.innerHTML = `<article class="quiz-card">
    <div class="kicker">${d.kicker}</div>
    <h1>${d.title}</h1>
    <p class="prompt">${d.prompt}</p>
    <div class="question-label">${d.qlabel}</div>
    ${promptHtml}
    <div class="options">${optsHtml}</div>
    <div class="actions">
      <button class="primary" data-submit ${selectedIdx===null?'disabled':''}>${myVote ? '更改答案' : '送出答案'}</button>
    </div>
    <div class="poll-bars">${pollHtml}</div>
    <div class="pager">${pagerHtml}</div>
  </article>`;
  container.querySelectorAll('.option').forEach(btn => {
    btn.addEventListener('click', () => selectOption(idx, parseInt(btn.dataset.idx)));
  });
  container.querySelector('.primary')?.addEventListener('click', () => submitVote(idx));
  container.querySelectorAll('.pg').forEach(a => a.addEventListener('click', () => switchTo(parseInt(a.dataset.idx))));
}

function showSide(idx) {
  const d = DATA[idx];
  visualC.innerHTML = d.svg;
  var revealed = (voteData[d.id] || {}).answersRevealed;
  if (revealed) {
    noteTitle.textContent = d.noteTitle;
    noteBody.textContent = d.noteBody;
  } else {
    noteTitle.textContent = '🔒 答案已隱藏';
    noteBody.innerHTML = isHost
      ? '<span style="color:var(--muted);font-size:13px">主持人請點擊下方按鈕公佈答案</span><br><br><button id="revealBtn" style="min-height:38px;padding:8px 18px;border:1px solid var(--green);border-radius:8px;background:rgba(16,185,129,.13);color:var(--green);font:inherit;font-size:13px;font-weight:700;cursor:pointer">📢 全班公佈答案</button>'
      : '<span style="color:var(--muted);font-size:13px">等待主持人公佈答案中⋯</span>';
    setTimeout(function() {
      var btn = document.getElementById('revealBtn');
      if (btn) btn.addEventListener('click', function() {
        db.collection('votes').doc(d.id).update({ answersRevealed: true });
      });
    }, 0);
  }
}

let selectedIdx = null;
function selectOption(idx, optIdx) {
  selectedIdx = optIdx;
  renderCard(idx);
}

async function submitVote(idx) {
  if (selectedIdx === null) return;
  const d = DATA[idx];
  const answer = String.fromCharCode(65 + selectedIdx);
  await db.collection('votes').doc(d.id).update({ [`responses.${uid}`]: answer });
  myVotes[d.id] = answer;
  selectedIdx = null;
  renderCard(idx);
  showToast('✓ 已送出');
}

function showToast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(window._tt);
  window._tt = setTimeout(() => el.classList.remove('show'), 2000);
}

document.getElementById('resetBtn').addEventListener('click', function() {
  var total = 0;
  Object.values(voteData).forEach(m => total += Object.keys(m.responses || {}).length);
  document.getElementById('totalVotesSpan').textContent = total;
  document.getElementById('resetOverlay').classList.add('show');
});
document.getElementById('cancelReset').addEventListener('click', function() {
  document.getElementById('resetOverlay').classList.remove('show');
});
document.getElementById('confirmReset').addEventListener('click', async function() {
  document.getElementById('resetOverlay').classList.remove('show');
  var batch = db.batch();
  for (var d of DATA) {
    batch.update(db.collection('votes').doc(d.id), { responses: {}, answersRevealed: false });
  }
  await batch.commit();
  myVotes = {};
  voteData = {};
  selectedIdx = null;
  for (var i = 0; i < unsubscribes.length; i++) unsubscribes[i]();
  unsubscribes = [];
  listenVotes();
  switchTo(currentIdx);
  showToast('已歸零 — 所有投票資料已清除');
});
</script>
</body>
</html>
```

### 使用說明（投票模式）

1. 建立 Firebase 專案 → 啟用 Anonymous Auth → 部署上述 firestore.rules
2. 將 `firebaseConfig` 替換為你的專案資料（可從 Firebase Console → 專案設定 → 一般 → 您的應用程式取得）
3. 修改 `DATA` 陣列為你的題目，每題包含：id、kicker、title、prompt、qlabel、opts、svg、noteTitle、noteBody
4. 將檔案部署到 GitHub Pages（見部署章節）

### 行為流程

```
參與者開啟頁面 → 匿名登入 → Firestore 監聽啟動
  ├─ 點選選項（高亮）→ 送出答案
  │    └─ 選項變綠色（已投票狀態）→ 長條圖出現
  │    └─ 可再次點選 → 更換選項 → 重新送出 → 覆寫回應
  ├─ 主持人看到「📢 全班公佈答案」按鈕
  │    └─ 點擊後所有裝置側欄顯示答案
  └─ 可隨時點「重新開始」→ 確認對話框 → 全部清除
```

---

## 部署到 GitHub Pages（跨平台）

### Windows（PowerShell 5.1）

```powershell
# 前置條件
gh auth status   # 確認已登入

# 1. 初始化
Set-Location "C:\path\to\project"
git init
git checkout -b main

# 2. 只 stage 網站必要檔案
git add index.html photo.png logo.png .gitignore
git commit -m "feat: 互動式網站初版"

# 3. 建立 GitHub repo（public）
gh repo create your-repo-name --public --description "網站描述"

# 4. 推送
git remote add origin https://github.com/your-account/your-repo.git
git push -u origin main

# 5. 啟用 GitHub Pages
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
$body = '{"source":{"branch":"main","path":"/"}}'
$tmp = "$env:TEMP\gh_pages.json"
[System.IO.File]::WriteAllText($tmp, $body, $utf8NoBom)
gh api repos/your-account/your-repo/pages --method POST --input $tmp
```

### macOS / Linux（Bash）

```bash
# 前置條件
gh auth status

# 1. 初始化
cd /path/to/project
git init
git checkout -b main

# 2. Stage + Commit
git add index.html photo.png logo.png .gitignore
git commit -m "feat: 互動式網站初版"

# 3. 建立 GitHub repo
gh repo create your-repo-name --public --description "網站描述"

# 4. 推送
git remote add origin https://github.com/your-account/your-repo.git
git push -u origin main

# 5. 啟用 GitHub Pages
cat > /tmp/gh_pages.json << 'EOF'
{"source":{"branch":"main","path":"/"}}
EOF
gh api repos/your-account/your-repo/pages --method POST --input /tmp/gh_pages.json
```

部署成功後約 1-3 分鐘生效：
```
https://your-account.github.io/your-repo/
```

---

## Firebase 設定 SOP

### 1. 建立 Firebase 專案

```bash
firebase login
firebase projects:create your-project-id
```

### 2. 啟用 Anonymous Authentication

```bash
firebase init auth
```

在專案根目錄產生的 `firebase.json` 中加入：

```json
{
  "auth": {
    "providers": {
      "anonymous": true
    }
  }
}
```

然後部署：

```bash
firebase deploy --only auth
```

### 3. 設定 Firestore 安全規則

```bash
firebase init firestore
```

編輯 `firestore.rules` 為上方提供的內容，然後部署：

```bash
firebase deploy --only firestore:rules
```

### 4. 取得 Firebase Config

1. 前往 [Firebase Console](https://console.firebase.google.com)
2. 點選你的專案 → 專案設定（齒輪）→ 一般 → 您的應用程式
3. 選擇「網頁應用程式」→ 複製 `firebaseConfig` 物件

---

## 踩坑紀錄（15 個實戰坑）

### 坑 1：Firestore 規則沒開 → `Missing or insufficient permissions`

**症狀：** `auth/configuration-not-found` 或 `Missing or insufficient permissions`  
**根因：** 匿名驗證未啟用，或 Firestore rules 沒開放對應 collection  
**SOP：** 
```
1. firebase deploy --only auth (確認 firebase.json 含 anonymous: true)
2. firebase deploy --only firestore:rules (確認 rules 含 votes + controls)
```

### 坑 2：Google Charts QR API 已棄用 → 404

**症狀：** `chart.googleapis.com/chart?cht=qr` 回 404  
**正確做法：** 改用 `api.qrserver.com/v1/create-qr-code/?size=200x200&data=URL`

### 坑 3：PowerShell Out-File 預設加 BOM → GitHub API 400

**SOP：** 用 `[System.IO.File]::WriteAllText()` 取代 `Out-File`，如下：
```powershell
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($tmp, $json, $utf8NoBom)
```

### 坑 4：`gh api --field` 不能傳 JSON 物件 → HTTP 422

**正確做法：** 寫入 JSON 檔案後用 `--input`：
```powershell
gh api repos/帳號/repo名稱/pages --method POST --input $tmp
```

### 坑 5：Edit 工具 old_string 必須逐字元吻合

**SOP：** 先 Read 複製 → 再 Edit，不要憑記憶打 old_string。

### 坑 6：Claude Code 圖片上傳不等於寫入本機

**SOP：** 上傳圖片後先 `Get-ChildItem` 確認實際檔名，再 `Copy-Item`。

### 坑 7：SVG path 預設 `pointer-events: none`

**SOP：** 在 CSS 中手動設 `pointer-events: all`。

### 坑 8：Chart.js plugin 必須在 `new Chart()` 時傳入

```javascript
// 正確
new Chart(ctx, { plugins: [myPlugin], ... });
// 錯誤（部分情境不生效）
Chart.register(myPlugin);
```

### 坑 9：同一 canvas 不能有兩個 Chart 實例

```javascript
if (window.myChart) window.myChart.destroy();
window.myChart = new Chart(canvas, config);
```

### 坑 10：YAML frontmatter 用 `|` 不要用 `>`

```yaml
# 正確（Claude Code / OpenCode skill loader 接受）
description: |
  多行描述...
```

### 坑 11：GitHub Pages 啟用後需等 1-3 分鐘

**SOP：** 耐心等待，不要一直刷新。

### 坑 12：Firebase `cmd /c` 繞過 PowerShell 執行原則

PowerShell 5.1 的執行原則會阻擋 `firebase` CLI 在部分環境執行。
**SOP：** 用 `cmd /c "firebase deploy ..."` 包裝。

### 坑 13：voteData 結構變更未同步更新所有消費者

當將 `voteData[d.id]` 從單純的 `responses` map 改為 `{ responses, answersRevealed }`
物件時，所有讀取 `voteData[d.id]` 的地方都必須更新（`updateCount`、`showResetOverlay`、`renderCard`）。
**教訓：** 重構資料結構時 grep 所有消費點。

### 坑 14：主持人識別的 race condition

第一個訪客寫入 `controls/host` 的同時，第二個訪客可能也檢查到 `!hostSnap.exists`，
**SOP：** 用 Firestore `set` 而非 `create`，後續訪客只做 `get` 比對 UID。

### 坑 15：答案揭示後切換題目再回來應保持顯示

**根因：** 答案揭示狀態存在 Firestore，snapshot listener 持續更新 `voteData`，
切換分頁時 `showSide` 重新讀取 `voteData[d.id].answersRevealed`。
**確認：** 只要 listener 不中斷，這個行為是自動正確的。

---

## 驗收清單

- [ ] Firebase Anonymous Auth 正常：頁面載入後未出現連線錯誤
- [ ] QR Code 顯示正常，手機掃描可開啟
- [ ] 選項點擊後高亮，送出後變綠色
- [ ] 長條圖在投票後才出現，投票前顯示「投票後即可查看」
- [ ] 側欄答案在主持人公佈前保持隱藏
- [ ] 主持人看到「📢 全班公佈答案」按鈕
- [ ] 非主持人看到「等待主持人公佈答案中⋯」
- [ ] 公佈後所有裝置同時顯示答案
- [ ] 可更改答案：重新選選項 → 送出 → 長條圖即時更新
- [ ] 參與人數統計正確（跨題目 UID 聯集）
- [ ] 「重新開始」→ 確認對話框 → 全部清除
- [ ] 題目切換（分頁按鈕 + prev/next）順暢
- [ ] RWD：手機排版正常（`max-width: 900px` 觸發）
- [ ] Console：無 JS 錯誤
- [ ] GitHub Pages 網域可正常連線

---

## 安裝

### Windows（OpenCode）

```powershell
# 複製到 OpenCode skills 目錄
xcopy /E /I "互動式網站設計" "%APPDATA%\opencode\skills\互動式網站設計"
```

### macOS / Linux（OpenCode）

```bash
# 複製到 OpenCode skills 目錄
cp -r "互動式網站設計" ~/.config/opencode/skills/
```

### 跨工具 Claude ➝ OpenCode

若需從 Claude Code 切換到其他工具（ChatGPT / Codex），先將此 SKILL.md
的「模式 B」段落分享給對方，確保實作一致。
