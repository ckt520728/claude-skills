// Build David Sussillo PowerPoint
// Theme: Midnight Executive (navy 1E2761 + ice blue CADCFC + white)
// Layout: LAYOUT_WIDE (13.3" x 7.5")

const path = require('path');
const fs = require('fs');

// Resolve pptxgenjs from global modules
process.env.NODE_PATH = require('child_process').execSync('npm root -g').toString().trim();
require('module')._initPaths();

const pptxgen = require('pptxgenjs');

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';  // 13.3 x 7.5
pres.title = 'Sussillo 大腦皮層動力學：高維神經計算的解析';
pres.author = 'NotebookLM 整合分析';

// ===== Theme colors =====
const NAVY = '1E2761';      // primary dark
const NAVY_DEEP = '14193F'; // even darker
const ICE = 'CADCFC';        // secondary
const ACCENT = 'F4B400';     // gold accent for highlights
const WHITE = 'FFFFFF';
const TEXT_DARK = '1A1A2E';
const TEXT_MUTED = '5A6378';
const BG_LIGHT = 'F7F9FC';
const RULE = 'D7DCE5';

// Fonts
const HFONT = 'Georgia';
const BFONT = 'Calibri';
const MONOFONT = 'Consolas';

// Slide dimensions
const W = 13.3;
const H = 7.5;

// ===== Helpers =====
function addFooter(slide, num, total) {
  // Thin footer bar
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: H - 0.35, w: W, h: 0.35,
    fill: { color: NAVY }, line: { color: NAVY, width: 0 }
  });
  slide.addText('David Sussillo｜大腦皮層動力學', {
    x: 0.4, y: H - 0.35, w: 8, h: 0.35,
    fontSize: 9, fontFace: BFONT, color: ICE, valign: 'middle', margin: 0
  });
  slide.addText(`${num} / ${total}`, {
    x: W - 1.2, y: H - 0.35, w: 0.8, h: 0.35,
    fontSize: 9, fontFace: BFONT, color: ICE, align: 'right', valign: 'middle', margin: 0
  });
}

function addSlideTitle(slide, title, subtitle) {
  // Title bar at top
  slide.addText(title, {
    x: 0.5, y: 0.35, w: W - 1, h: 0.7,
    fontSize: 28, fontFace: HFONT, bold: true, color: NAVY,
    valign: 'middle', margin: 0
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.5, y: 1.05, w: W - 1, h: 0.4,
      fontSize: 13, fontFace: BFONT, color: TEXT_MUTED, italic: true,
      valign: 'middle', margin: 0
    });
  }
  // Thin underline rule
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: subtitle ? 1.5 : 1.15, w: 1.2, h: 0.04,
    fill: { color: ACCENT }, line: { color: ACCENT, width: 0 }
  });
}

// ===== TOTAL slide count for footer =====
const TOTAL = 22;
let n = 0;

// ============================================================
// SLIDE 1: COVER
// ============================================================
{
  let s = pres.addSlide();
  s.background = { color: NAVY_DEEP };

  // Decorative left bar
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.4, h: H,
    fill: { color: ACCENT }, line: { color: ACCENT, width: 0 }
  });

  // Top tag
  s.addText('CALCULATIONS  ·  COGNITIVE NEUROSCIENCE  ·  RNN', {
    x: 1.0, y: 1.3, w: 11, h: 0.4,
    fontSize: 11, fontFace: BFONT, color: ACCENT, charSpacing: 8, bold: true, margin: 0
  });

  // Main title
  s.addText('大腦皮層動力學', {
    x: 1.0, y: 1.9, w: 11, h: 1.1,
    fontSize: 56, fontFace: HFONT, bold: true, color: WHITE, margin: 0
  });
  s.addText('高維神經計算的解析', {
    x: 1.0, y: 3.0, w: 11, h: 0.9,
    fontSize: 38, fontFace: HFONT, color: ICE, margin: 0
  });

  // Subtitle
  s.addText('David Sussillo 的研究體系與神經群體動力學範式', {
    x: 1.0, y: 4.2, w: 11, h: 0.5,
    fontSize: 18, fontFace: BFONT, color: ICE, italic: true, margin: 0
  });

  // Divider
  s.addShape(pres.shapes.LINE, {
    x: 1.0, y: 5.0, w: 4, h: 0,
    line: { color: ACCENT, width: 1.5 }
  });

  // Footer info
  s.addText([
    { text: '來源：', options: { color: ICE, bold: true } },
    { text: 'NotebookLM 整合分析 + David Sussillo 原始文獻 (2009–2026)', options: { color: WHITE } }
  ], { x: 1.0, y: 5.3, w: 11, h: 0.4, fontSize: 14, fontFace: BFONT, margin: 0 });

  s.addText([
    { text: '日期：', options: { color: ICE, bold: true } },
    { text: '2026-05-05', options: { color: WHITE } }
  ], { x: 1.0, y: 5.7, w: 11, h: 0.4, fontSize: 14, fontFace: BFONT, margin: 0 });

  s.addText('本講為 PhD 等級學術文獻深度解析，整合 FORCE / DSA / CTD 三大研究主軸', {
    x: 1.0, y: 6.5, w: 11, h: 0.4,
    fontSize: 11, fontFace: BFONT, color: TEXT_MUTED, italic: true, margin: 0
  });

  s.addNotes('封面：揭示主題核心——Sussillo 將大腦皮層的高維神經計算，從實驗現象提升為可逆向工程的動力系統理論。');
  n++;
}

// ============================================================
// SLIDE 2: 大綱
// ============================================================
{
  let s = pres.addSlide();
  s.background = { color: BG_LIGHT };
  addSlideTitle(s, '本講大綱', 'Six axes for understanding Sussillo\'s framework');

  const items = [
    { num: '01', title: '核心研究問題與一句話總結', desc: '高維動力學如何突現智慧？' },
    { num: '02', title: '思想演進時序 (2009–2026)', desc: '從 FORCE 到具身圖靈測試的八個里程碑' },
    { num: '03', title: 'FORCE 學習算法', desc: '混沌中尋求秩序的訓練方法' },
    { num: '04', title: 'DSA 與吸引子流形', desc: '打開黑盒子的數學工具與五種吸引子類型' },
    { num: '05', title: 'CTD 框架與無效空間', desc: '經由動力學的運算，橋接人工網絡與生物神經數據' },
    { num: '06', title: '評價、臨床應用與未來展望', desc: '優勢、局限、神經疾病建模、NeuroAI' }
  ];

  // Two-column grid 3x2
  const colW = 5.8;
  const rowH = 1.6;
  const startX = 0.6;
  const startY = 1.9;
  const gapX = 0.3;
  const gapY = 0.25;

  items.forEach((item, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = startX + col * (colW + gapX);
    const y = startY + row * (rowH + gapY);

    // Card
    s.addShape(pres.shapes.RECTANGLE, {
      x: x, y: y, w: colW, h: rowH,
      fill: { color: WHITE }, line: { color: RULE, width: 0.5 }
    });
    // Left accent stripe
    s.addShape(pres.shapes.RECTANGLE, {
      x: x, y: y, w: 0.08, h: rowH,
      fill: { color: NAVY }, line: { color: NAVY, width: 0 }
    });
    // Number
    s.addText(item.num, {
      x: x + 0.25, y: y + 0.15, w: 0.8, h: 0.5,
      fontSize: 26, fontFace: HFONT, bold: true, color: ACCENT, margin: 0
    });
    // Title
    s.addText(item.title, {
      x: x + 1.1, y: y + 0.18, w: colW - 1.3, h: 0.5,
      fontSize: 17, fontFace: HFONT, bold: true, color: NAVY, margin: 0
    });
    // Description
    s.addText(item.desc, {
      x: x + 1.1, y: y + 0.75, w: colW - 1.3, h: 0.7,
      fontSize: 12, fontFace: BFONT, color: TEXT_MUTED, margin: 0
    });
  });

  addFooter(s, ++n, TOTAL);
  s.addNotes('大綱：六個主軸涵蓋 Sussillo 從工具開發到理論框架，再到臨床與 AI 願景的完整研究體系。');
}

// ============================================================
// SLIDE 3: 核心研究問題
// ============================================================
{
  let s = pres.addSlide();
  s.background = { color: BG_LIGHT };
  addSlideTitle(s, '核心研究問題', 'The two questions that drive Sussillo\'s entire research program');

  // Two big question cards
  const cardY = 2.0;
  const cardH = 4.5;
  const cardW = 6.0;

  // Card 1
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.6, y: cardY, w: cardW, h: cardH,
    fill: { color: WHITE }, line: { color: RULE, width: 0.5 }
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.6, y: cardY, w: cardW, h: 0.08,
    fill: { color: NAVY }, line: { color: NAVY, width: 0 }
  });
  s.addText('Q1', {
    x: 0.85, y: cardY + 0.3, w: 1.0, h: 0.7,
    fontSize: 36, fontFace: HFONT, bold: true, color: ACCENT, margin: 0
  });
  s.addText('生物學的問題', {
    x: 1.85, y: cardY + 0.4, w: 4, h: 0.5,
    fontSize: 16, fontFace: HFONT, bold: true, color: NAVY, margin: 0
  });
  s.addText('大腦的智慧如何從高維神經群體動力學中突現？', {
    x: 0.85, y: cardY + 1.3, w: cardW - 0.5, h: 1.2,
    fontSize: 18, fontFace: HFONT, bold: true, color: TEXT_DARK, margin: 0
  });
  s.addText('複雜的計算不是來自單一神經元，而是來自神經群體在高維狀態空間中的集體軌跡。本問題追問：這種「突現 (emergence)」的數學與物理機制是什麼？', {
    x: 0.85, y: cardY + 2.6, w: cardW - 0.5, h: 1.7,
    fontSize: 13, fontFace: BFONT, color: TEXT_MUTED, margin: 0
  });

  // Card 2
  s.addShape(pres.shapes.RECTANGLE, {
    x: W - 0.6 - cardW, y: cardY, w: cardW, h: cardH,
    fill: { color: WHITE }, line: { color: RULE, width: 0.5 }
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: W - 0.6 - cardW, y: cardY, w: cardW, h: 0.08,
    fill: { color: NAVY }, line: { color: NAVY, width: 0 }
  });
  s.addText('Q2', {
    x: W - 0.6 - cardW + 0.25, y: cardY + 0.3, w: 1.0, h: 0.7,
    fontSize: 36, fontFace: HFONT, bold: true, color: ACCENT, margin: 0
  });
  s.addText('方法論的問題', {
    x: W - 0.6 - cardW + 1.25, y: cardY + 0.4, w: 4, h: 0.5,
    fontSize: 16, fontFace: HFONT, bold: true, color: NAVY, margin: 0
  });
  s.addText('訓練後的 RNN 如何從「黑盒子」轉化為解釋大腦的「假設產生器」？', {
    x: W - 0.6 - cardW + 0.25, y: cardY + 1.3, w: cardW - 0.5, h: 1.2,
    fontSize: 18, fontFace: HFONT, bold: true, color: TEXT_DARK, margin: 0
  });
  s.addText('循環神經網路 (RNN) 訓練成功後，要能告訴神經科學家「大腦也許就是這樣運作」，而不是只展示「我能擬合資料」。逆向工程 (reverse engineering) 是達成此目標的方法。', {
    x: W - 0.6 - cardW + 0.25, y: cardY + 2.6, w: cardW - 0.5, h: 1.7,
    fontSize: 13, fontFace: BFONT, color: TEXT_MUTED, margin: 0
  });

  addFooter(s, ++n, TOTAL);
  s.addNotes('Sussillo 研究體系由兩個問題驅動：一個關於大腦本體論（運算如何從動力學突現），一個關於方法論（如何讓訓練後的 RNN 變成可解釋的科學工具）。');
}

// ============================================================
// SLIDE 4: 一句話總結
// ============================================================
{
  let s = pres.addSlide();
  s.background = { color: NAVY_DEEP };

  s.addText('THE ONE-LINE THESIS', {
    x: 1.0, y: 1.5, w: 11, h: 0.4,
    fontSize: 11, fontFace: BFONT, color: ACCENT, charSpacing: 8, bold: true, margin: 0
  });

  // Big quote mark
  s.addText('"', {
    x: 0.8, y: 1.7, w: 1.5, h: 2,
    fontSize: 120, fontFace: HFONT, color: ACCENT, margin: 0
  });

  // Main statement
  s.addText([
    { text: '大腦的智慧與運算', options: { color: WHITE } },
    { text: '並非編碼於單一神經元的靜態放電中，', options: { color: WHITE, breakLine: true } },
    { text: '而是源於神經群體活動在高維狀態空間中', options: { color: ICE, breakLine: true } },
    { text: '沿著特定動力結構（吸引子）演化的軌跡。', options: { color: ICE, bold: true } }
  ], {
    x: 1.5, y: 2.4, w: 11, h: 3.0,
    fontSize: 28, fontFace: HFONT, paraSpaceAfter: 8, margin: 0
  });

  // Divider
  s.addShape(pres.shapes.LINE, {
    x: 1.5, y: 5.6, w: 3, h: 0,
    line: { color: ACCENT, width: 1.5 }
  });

  s.addText('—— 本講貫穿始終的核心命題', {
    x: 1.5, y: 5.8, w: 11, h: 0.4,
    fontSize: 14, fontFace: BFONT, color: ICE, italic: true, margin: 0
  });

  addFooter(s, ++n, TOTAL);
  s.addNotes('一句話總結：將整個研究框架壓縮成一個命題——智慧 = 高維狀態空間中沿吸引子演化的軌跡。');
}

// ============================================================
// SLIDE 5: 三大核心學術貢獻
// ============================================================
{
  let s = pres.addSlide();
  s.background = { color: BG_LIGHT };
  addSlideTitle(s, '三大核心學術貢獻', 'Three pillars of the Sussillo framework');

  const pillars = [
    {
      year: '2009',
      key: '工具',
      title: 'FORCE 學習算法',
      en: 'First-Order Reduced and Controlled Error',
      desc: '解決混沌神經網路的訓練困境。利用遞迴最小二乘法 (RLS) 即時馴服混沌動力學，讓 RNN 能精準產生時序輸出。'
    },
    {
      year: '2013',
      key: '理論',
      title: '動力系統分析 (DSA)',
      en: 'Dynamical Systems Analysis',
      desc: '逆向工程訓練後的 RNN：尋找定點、慢點、各種吸引子流形，把高維黑盒子簡化為低維可解釋動力系統。'
    },
    {
      year: '2014+',
      key: '框架',
      title: 'CTD 範式',
      en: 'Computation Through Dynamics',
      desc: '經由動力學的運算。把 RNN 分析法套用到生物神經數據——運動皮層、PFC、決策、獎勵——成為現代神經族群動力學學派的奠基綱領。'
    }
  ];

  const colW = 4.0;
  const startX = 0.6;
  const startY = 2.0;
  const gapX = 0.25;
  const cardH = 4.6;

  pillars.forEach((p, i) => {
    const x = startX + i * (colW + gapX);
    // Card
    s.addShape(pres.shapes.RECTANGLE, {
      x: x, y: startY, w: colW, h: cardH,
      fill: { color: WHITE }, line: { color: RULE, width: 0.5 }
    });
    // Top accent
    s.addShape(pres.shapes.RECTANGLE, {
      x: x, y: startY, w: colW, h: 0.5,
      fill: { color: NAVY }, line: { color: NAVY, width: 0 }
    });
    // Year + key in accent
    s.addText(p.year, {
      x: x + 0.25, y: startY + 0.05, w: 1.5, h: 0.4,
      fontSize: 14, fontFace: BFONT, bold: true, color: ACCENT, valign: 'middle', margin: 0
    });
    s.addText(p.key, {
      x: x + colW - 1.2, y: startY + 0.05, w: 1.0, h: 0.4,
      fontSize: 11, fontFace: BFONT, color: ICE, align: 'right', valign: 'middle', margin: 0, charSpacing: 4
    });
    // Title
    s.addText(p.title, {
      x: x + 0.25, y: startY + 0.75, w: colW - 0.5, h: 0.6,
      fontSize: 22, fontFace: HFONT, bold: true, color: NAVY, margin: 0
    });
    // English subtitle
    s.addText(p.en, {
      x: x + 0.25, y: startY + 1.4, w: colW - 0.5, h: 0.5,
      fontSize: 11, fontFace: BFONT, color: TEXT_MUTED, italic: true, margin: 0
    });
    // Divider line
    s.addShape(pres.shapes.LINE, {
      x: x + 0.25, y: startY + 2.0, w: 1.0, h: 0,
      line: { color: ACCENT, width: 1.2 }
    });
    // Description
    s.addText(p.desc, {
      x: x + 0.25, y: startY + 2.2, w: colW - 0.5, h: 2.2,
      fontSize: 12, fontFace: BFONT, color: TEXT_DARK, paraSpaceAfter: 4, margin: 0
    });
  });

  addFooter(s, ++n, TOTAL);
  s.addNotes('三大貢獻彼此承接：FORCE 是工具（製造能運算的網路）、DSA 是理論（理解這些網路）、CTD 是框架（套用到真實大腦數據）。');
}

// ============================================================
// SLIDE 6: 思想演進時序
// ============================================================
{
  let s = pres.addSlide();
  s.background = { color: BG_LIGHT };
  addSlideTitle(s, '思想演進時序 (2009–2026)', 'Eight milestones from "emergence" to "embodied Turing test"');

  const milestones = [
    { y: '前緣', t: '突現哲學基礎', d: '受《生命遊戲》啟發，主張複雜功能可從簡單組件互動自發產生' },
    { y: '2009', t: 'FORCE 學習', d: '與 Larry Abbott 合作；解決混沌系統訓練困境；Neuron 發表' },
    { y: '2013', t: '逆向工程 + 吸引子', d: '與 Omri Barak 合作；提出尋找定點、慢點與線/環/平面吸引子的數學框架' },
    { y: '2013–14', t: 'CNPD / CTD 框架', d: '正式提出「經由動力學的運算」；統合人工 RNN 分析與生物神經數據' },
    { y: '2014–17', t: '無效空間 + CIS', d: '針對運動皮質：Null/Potent space 與條件不變信號 (CIS) 解釋準備與啟動' },
    { y: '2018', t: 'LFADS', d: '隱性因子分析；用動力系統約束推斷單次試驗的潛在因子' },
    { y: '2019+', t: '非正常線性系統', d: '進一步解釋吸引子與選擇向量的角度差，理解 PFC 上下文切換' },
    { y: '2022–26', t: '具身圖靈測試', d: '推向 NeuroAI：開發能像生物與物理世界互動的人工智能系統' }
  ];

  // Timeline horizontal layout: 2 rows x 4 cols
  const cols = 4;
  const cellW = (W - 1.0) / cols;
  const cellH = 2.4;
  const startX = 0.5;
  const startY = 1.95;

  milestones.forEach((m, i) => {
    const col = i % cols;
    const row = Math.floor(i / cols);
    const x = startX + col * cellW;
    const y = startY + row * (cellH + 0.2);

    // Year badge
    s.addShape(pres.shapes.RECTANGLE, {
      x: x + 0.1, y: y, w: cellW - 0.3, h: 0.5,
      fill: { color: NAVY }, line: { color: NAVY, width: 0 }
    });
    s.addText(m.y, {
      x: x + 0.1, y: y, w: cellW - 0.3, h: 0.5,
      fontSize: 13, fontFace: BFONT, bold: true, color: ACCENT, align: 'center', valign: 'middle', margin: 0
    });
    // Title
    s.addText(m.t, {
      x: x + 0.1, y: y + 0.6, w: cellW - 0.3, h: 0.5,
      fontSize: 14, fontFace: HFONT, bold: true, color: NAVY, align: 'center', valign: 'middle', margin: 0
    });
    // Description
    s.addText(m.d, {
      x: x + 0.1, y: y + 1.15, w: cellW - 0.3, h: 1.15,
      fontSize: 10, fontFace: BFONT, color: TEXT_MUTED, align: 'center', valign: 'top', margin: 0
    });
    // Connector arrow (between cells horizontally, except last in each row)
    if (col < cols - 1) {
      s.addShape(pres.shapes.LINE, {
        x: x + cellW - 0.18, y: y + 0.25, w: 0.15, h: 0,
        line: { color: ACCENT, width: 1.5, endArrowType: 'triangle' }
      });
    }
    // Down arrow at end of row 1 col 4 to row 2 col 1 (skip — visually too crowded; just imply chronology)
  });

  addFooter(s, ++n, TOTAL);
  s.addNotes('八個里程碑展示 Sussillo 從「能訓練混沌系統」到「能解釋大腦」再到「能設計具身 AI」的研究弧線，每一步都是前一步的因果延伸。');
}

// ============================================================
// SLIDE 7: FORCE — 為什麼需要它
// ============================================================
{
  let s = pres.addSlide();
  s.background = { color: BG_LIGHT };
  addSlideTitle(s, 'FORCE 學習算法：為什麼需要它', 'The chaos-training problem before 2009');

  // Left side: problem
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.6, y: 1.95, w: 5.8, h: 4.8,
    fill: { color: WHITE }, line: { color: RULE, width: 0.5 }
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.6, y: 1.95, w: 0.08, h: 4.8,
    fill: { color: 'CC4444' }, line: { color: 'CC4444', width: 0 }
  });
  s.addText('傳統 RNN 訓練困境', {
    x: 0.85, y: 2.1, w: 5.5, h: 0.5,
    fontSize: 18, fontFace: HFONT, bold: true, color: 'CC4444', margin: 0
  });
  s.addText('Pre-2009: the chaos training problem', {
    x: 0.85, y: 2.6, w: 5.5, h: 0.35,
    fontSize: 11, fontFace: BFONT, color: TEXT_MUTED, italic: true, margin: 0
  });

  s.addText([
    { text: '混沌神經網路本質不可預測', options: { bullet: true, bold: true, color: TEXT_DARK, breakLine: true } },
    { text: '梯度下降 (BPTT) 在強連接系統中梯度爆炸', options: { bullet: true, color: TEXT_DARK, breakLine: true, paraSpaceAfter: 6 } },
    { text: '回聲狀態網路 (ESN) 的妥協：', options: { bullet: true, bold: true, color: TEXT_DARK, breakLine: true } },
    { text: '訓練時必須「鉗制 (clamping)」斷開反饋迴路', options: { bullet: true, indentLevel: 1, color: TEXT_MUTED, breakLine: true } },
    { text: '一旦脫離鉗制，網路容易崩潰', options: { bullet: true, indentLevel: 1, color: TEXT_MUTED, breakLine: true, paraSpaceAfter: 6 } },
    { text: '生物大腦本來就是強連接、混沌的', options: { bullet: true, italic: true, color: NAVY } }
  ], {
    x: 0.85, y: 3.05, w: 5.5, h: 3.5,
    fontSize: 13, fontFace: BFONT, paraSpaceAfter: 4, margin: 0
  });

  // Right side: insight
  s.addShape(pres.shapes.RECTANGLE, {
    x: 6.9, y: 1.95, w: 5.8, h: 4.8,
    fill: { color: NAVY }, line: { color: NAVY, width: 0 }
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 6.9, y: 1.95, w: 0.08, h: 4.8,
    fill: { color: ACCENT }, line: { color: ACCENT, width: 0 }
  });
  s.addText('Sussillo & Abbott 2009 的洞見', {
    x: 7.15, y: 2.1, w: 5.5, h: 0.5,
    fontSize: 18, fontFace: HFONT, bold: true, color: ACCENT, margin: 0
  });
  s.addText('A radical inversion of the strategy', {
    x: 7.15, y: 2.6, w: 5.5, h: 0.35,
    fontSize: 11, fontFace: BFONT, color: ICE, italic: true, margin: 0
  });

  s.addText('與其抑制混沌，不如即時馴服它。', {
    x: 7.15, y: 3.2, w: 5.5, h: 0.7,
    fontSize: 22, fontFace: HFONT, bold: true, color: WHITE, margin: 0
  });

  s.addText([
    { text: '保留網路內部豐富的混沌動力學', options: { bullet: true, color: ICE, breakLine: true } },
    { text: '從第一個時間步就把輸出誤差壓到極小', options: { bullet: true, color: ICE, breakLine: true } },
    { text: '反饋回路保持完整、不鉗制', options: { bullet: true, color: ICE, breakLine: true } },
    { text: '混沌變成「儲備計算」(reservoir) 的資源', options: { bullet: true, color: ACCENT, bold: true } }
  ], {
    x: 7.15, y: 4.4, w: 5.5, h: 2.2,
    fontSize: 13, fontFace: BFONT, paraSpaceAfter: 5, margin: 0
  });

  addFooter(s, ++n, TOTAL);
  s.addNotes('FORCE 的核心洞見：與其壓制混沌（傳統作法），不如把混沌當資源、用快速校正壓住誤差。這是方法論上的徹底反轉。');
}

// ============================================================
// SLIDE 8: FORCE 數學原理
// ============================================================
{
  let s = pres.addSlide();
  s.background = { color: BG_LIGHT };
  addSlideTitle(s, 'FORCE 數學原理', 'Three equations that define the algorithm');

  const eqs = [
    {
      no: '①',
      title: '網路輸出',
      formula: 'z_out(t) = Σᵢ wᵢ · xᵢ(t)',
      desc: '輸出 = 所有神經元活動 xᵢ(t) 的加權線性組合，wᵢ 為讀出權重'
    },
    {
      no: '②',
      title: '即時誤差',
      formula: 'e(t) = z_target(t) − z_out(t)',
      desc: '誤差 = 期望輸出與實際輸出之差；此值需在每個時步監控'
    },
    {
      no: '③',
      title: 'RLS 權重更新',
      formula: 'Δw ≈ Gain × Error',
      desc: '遞迴最小平方法 (RLS)：每 ~0.01 秒重新計算權重，增益矩陣根據過去預測誤差動態調整'
    }
  ];

  // Three equation cards stacked horizontally
  const cardW = 4.0;
  const cardH = 3.0;
  const startX = 0.6;
  const startY = 2.0;
  const gapX = 0.25;

  eqs.forEach((e, i) => {
    const x = startX + i * (cardW + gapX);
    s.addShape(pres.shapes.RECTANGLE, {
      x: x, y: startY, w: cardW, h: cardH,
      fill: { color: WHITE }, line: { color: RULE, width: 0.5 }
    });
    // Number circle
    s.addShape(pres.shapes.OVAL, {
      x: x + cardW / 2 - 0.4, y: startY - 0.4, w: 0.8, h: 0.8,
      fill: { color: NAVY }, line: { color: NAVY, width: 0 }
    });
    s.addText(e.no, {
      x: x + cardW / 2 - 0.4, y: startY - 0.4, w: 0.8, h: 0.8,
      fontSize: 22, fontFace: HFONT, bold: true, color: ACCENT,
      align: 'center', valign: 'middle', margin: 0
    });
    // Title
    s.addText(e.title, {
      x: x + 0.2, y: startY + 0.55, w: cardW - 0.4, h: 0.4,
      fontSize: 15, fontFace: HFONT, bold: true, color: NAVY,
      align: 'center', margin: 0
    });
    // Formula in mono font
    s.addText(e.formula, {
      x: x + 0.2, y: startY + 1.05, w: cardW - 0.4, h: 0.7,
      fontSize: 18, fontFace: MONOFONT, color: TEXT_DARK,
      align: 'center', valign: 'middle', bold: true, margin: 0
    });
    // Description
    s.addText(e.desc, {
      x: x + 0.2, y: startY + 1.85, w: cardW - 0.4, h: 1.0,
      fontSize: 11, fontFace: BFONT, color: TEXT_MUTED,
      align: 'center', margin: 0
    });
  });

  // Bottom takeaway box
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.6, y: 5.5, w: W - 1.2, h: 1.3,
    fill: { color: NAVY }, line: { color: NAVY, width: 0 }
  });
  s.addText('關鍵機制', {
    x: 0.85, y: 5.6, w: 2, h: 0.4,
    fontSize: 13, fontFace: BFONT, bold: true, color: ACCENT, charSpacing: 6, margin: 0
  });
  s.addText('修正速度極快 → 輸出立刻緊貼目標 → 反饋穩定後，混沌神經元被「牽引」沿正確軌跡運動 → 內部協作 (synchronization) 自發突現', {
    x: 0.85, y: 5.95, w: W - 1.7, h: 0.85,
    fontSize: 14, fontFace: BFONT, color: WHITE, margin: 0
  });

  addFooter(s, ++n, TOTAL);
  s.addNotes('FORCE 的數學核心：三個方程式 + RLS 更新規則。關鍵不是某個複雜方程，而是「修正極快，所以系統來不及失控」。');
}

// ============================================================
// SLIDE 9: FORCE vs ESN 比較
// ============================================================
{
  let s = pres.addSlide();
  s.background = { color: BG_LIGHT };
  addSlideTitle(s, 'FORCE vs. ESN — 方法論比較', 'Why FORCE generalizes when ESN does not');

  const headerOpts = { fill: { color: NAVY }, color: WHITE, bold: true, fontFace: HFONT, fontSize: 14, align: 'center', valign: 'middle' };
  const cellOpts = { fontSize: 12, fontFace: BFONT, color: TEXT_DARK, valign: 'middle', align: 'left' };
  const goodOpts = { fontSize: 12, fontFace: BFONT, color: '0F7B0F', bold: true, valign: 'middle', align: 'center' };
  const badOpts = { fontSize: 12, fontFace: BFONT, color: 'CC4444', bold: true, valign: 'middle', align: 'center' };

  const tableData = [
    [
      { text: '比較面向', options: headerOpts },
      { text: '回聲狀態網路 (ESN)', options: headerOpts },
      { text: 'FORCE 學習', options: headerOpts }
    ],
    [
      { text: '訓練時的反饋迴路', options: cellOpts },
      { text: '斷開（鉗制 clamping）', options: badOpts },
      { text: '完整保留', options: goodOpts }
    ],
    [
      { text: '訓練後的網路穩定性', options: cellOpts },
      { text: '脫離導師易崩潰', options: badOpts },
      { text: '自力更生即穩定', options: goodOpts }
    ],
    [
      { text: '混沌動力學保留', options: cellOpts },
      { text: '部分壓制', options: badOpts },
      { text: '完整保留為資源', options: goodOpts }
    ],
    [
      { text: '輸出複雜時序的能力', options: cellOpts },
      { text: '受限', options: badOpts },
      { text: '可生成肌肉電位、語音、3-bit memory', options: goodOpts }
    ],
    [
      { text: '對生物學的啟發性', options: cellOpts },
      { text: '較低', options: badOpts },
      { text: '較高（生物大腦本就混沌）', options: goodOpts }
    ]
  ];

  s.addTable(tableData, {
    x: 0.6, y: 2.0, w: W - 1.2,
    colW: [3.5, 4.3, 4.3],
    rowH: [0.55, 0.65, 0.65, 0.65, 0.7, 0.7],
    border: { pt: 1, color: RULE }
  });

  addFooter(s, ++n, TOTAL);
  s.addNotes('FORCE 與 ESN 最關鍵差別：訓練時是否斷開反饋。這個看似技術細節的選擇，徹底改變了訓練後的網路能否獨立運作。');
}

// ============================================================
// SLIDE 10: 教學類比
// ============================================================
{
  let s = pres.addSlide();
  s.background = { color: BG_LIGHT };
  addSlideTitle(s, '教學類比：自動恆溫空調系統', 'A precalculus-friendly intuition for FORCE');

  // Big metaphor box
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.6, y: 2.0, w: W - 1.2, h: 1.2,
    fill: { color: NAVY }, line: { color: NAVY, width: 0 }
  });
  s.addText('想像一個裝在溫室裡的自動恆溫系統，但溫室內部風扇雜亂無章。', {
    x: 0.85, y: 2.0, w: W - 1.7, h: 0.6,
    fontSize: 18, fontFace: HFONT, color: WHITE, valign: 'middle', italic: true, margin: 0
  });
  s.addText('FORCE 不是把氣流「靜下來」，而是用毫秒等級的溫度修正去配合亂流。', {
    x: 0.85, y: 2.55, w: W - 1.7, h: 0.6,
    fontSize: 14, fontFace: BFONT, color: ICE, valign: 'middle', margin: 0
  });

  // Mapping table
  const headerOpts = { fill: { color: NAVY }, color: WHITE, bold: true, fontFace: HFONT, fontSize: 13, align: 'center', valign: 'middle' };
  const physOpts = { fontSize: 12, fontFace: BFONT, color: TEXT_DARK, bold: true, valign: 'middle', align: 'left' };
  const arrowOpts = { fontSize: 18, color: ACCENT, bold: true, align: 'center', valign: 'middle' };
  const neuroOpts = { fontSize: 12, fontFace: BFONT, color: NAVY, bold: true, valign: 'middle', align: 'left' };

  const map = [
    [
      { text: '空調系統 (物理直觀)', options: headerOpts },
      { text: '→', options: headerOpts },
      { text: '神經網路 (FORCE 對應)', options: headerOpts }
    ],
    [
      { text: '溫室內的混亂氣流', options: physOpts },
      { text: '→', options: arrowOpts },
      { text: '混沌的神經元活動', options: neuroOpts }
    ],
    [
      { text: '每毫秒讀取的溫度誤差', options: physOpts },
      { text: '→', options: arrowOpts },
      { text: '即時輸出誤差 e(t)', options: neuroOpts }
    ],
    [
      { text: 'RLS 計算電熱絲熱量', options: physOpts },
      { text: '→', options: arrowOpts },
      { text: '讀出權重 wᵢ 的更新', options: neuroOpts }
    ],
    [
      { text: '長期同步成穩定循環', options: physOpts },
      { text: '→', options: arrowOpts },
      { text: '混沌被馴服為精確時序', options: neuroOpts }
    ]
  ];

  s.addTable(map, {
    x: 0.6, y: 3.5, w: W - 1.2,
    colW: [5.0, 1.0, 6.1],
    rowH: [0.5, 0.55, 0.55, 0.55, 0.55],
    border: { pt: 1, color: RULE }
  });

  s.addText('因為修正極快，溫度計幾乎不動 → 系統「誤以為」已學會正確軌跡 → 真的學會了。', {
    x: 0.6, y: 6.4, w: W - 1.2, h: 0.4,
    fontSize: 13, fontFace: BFONT, color: TEXT_MUTED, italic: true, align: 'center', margin: 0
  });

  addFooter(s, ++n, TOTAL);
  s.addNotes('用空調類比讓非數學背景的觀眾抓到 FORCE 直覺：不是強迫系統安靜，而是用快速反應跟上系統的混亂。');
}

// ============================================================
// SLIDE 11: DSA — 打開黑盒子
// ============================================================
{
  let s = pres.addSlide();
  s.background = { color: BG_LIGHT };
  addSlideTitle(s, '動力系統分析 (DSA)：打開黑盒子', 'Sussillo & Barak 2013 — Reverse engineering trained RNNs');

  // Top row: Problem statement
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.6, y: 2.0, w: W - 1.2, h: 0.9,
    fill: { color: NAVY }, line: { color: NAVY, width: 0 }
  });
  s.addText('核心問題：訓練後的 RNN 若不可解釋，則只是另一個黑盒子，無法用來理解大腦。', {
    x: 0.85, y: 2.0, w: W - 1.7, h: 0.9,
    fontSize: 16, fontFace: HFONT, color: WHITE, valign: 'middle', margin: 0
  });

  // Three step process
  const steps = [
    {
      no: '1',
      t: '尋找定點 (Fixed Points)',
      d: '在高維狀態空間中搜尋網路活動的「平衡位置」——這些是動力系統的骨架'
    },
    {
      no: '2',
      t: '局部線性化分析',
      d: '在每個定點周圍計算 Jacobian 矩陣，求其特徵值——揭示系統的局部穩定性與旋轉模式'
    },
    {
      no: '3',
      t: '識別吸引子拓樸',
      d: '把高維動力學壓縮為低維吸引子流形——線吸引子、環吸引子、平面吸引子等'
    }
  ];

  const cardW = 4.0;
  const cardH = 3.0;
  const startX = 0.6;
  const startY = 3.2;
  const gapX = 0.25;

  steps.forEach((step, i) => {
    const x = startX + i * (cardW + gapX);
    s.addShape(pres.shapes.RECTANGLE, {
      x: x, y: startY, w: cardW, h: cardH,
      fill: { color: WHITE }, line: { color: RULE, width: 0.5 }
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: x, y: startY, w: cardW, h: 0.08,
      fill: { color: NAVY }, line: { color: NAVY, width: 0 }
    });
    // Big number
    s.addText(step.no, {
      x: x + 0.25, y: startY + 0.3, w: 1.0, h: 1.0,
      fontSize: 56, fontFace: HFONT, bold: true, color: ACCENT, margin: 0
    });
    // Title
    s.addText(step.t, {
      x: x + 1.4, y: startY + 0.45, w: cardW - 1.6, h: 0.8,
      fontSize: 14, fontFace: HFONT, bold: true, color: NAVY, valign: 'middle', margin: 0
    });
    // Description
    s.addText(step.d, {
      x: x + 0.3, y: startY + 1.6, w: cardW - 0.5, h: 1.3,
      fontSize: 12, fontFace: BFONT, color: TEXT_DARK, margin: 0
    });
  });

  // Bottom takeaway
  s.addText('結果：把高維 RNN 轉化為「假設產生器」——告訴神經科學家「大腦也許就是這樣運作」', {
    x: 0.6, y: 6.4, w: W - 1.2, h: 0.4,
    fontSize: 13, fontFace: BFONT, color: NAVY, italic: true, bold: true, align: 'center', margin: 0
  });

  addFooter(s, ++n, TOTAL);
  s.addNotes('DSA 是 Sussillo 第二項里程碑式貢獻：把訓練後的 RNN 從「能擬合」提升到「能解釋」，是現代 task-trained RNN 學派的方法學基石。');
}

// ============================================================
// SLIDE 12: 五種吸引子流形
// ============================================================
{
  let s = pres.addSlide();
  s.background = { color: BG_LIGHT };
  addSlideTitle(s, '五種吸引子流形', 'Five geometric primitives of neural computation');

  const attractors = [
    {
      name: '定點',
      en: 'Fixed Points',
      func: '穩態 / 記憶',
      desc: '單一穩定狀態；對應持續活動 (persistent activity)'
    },
    {
      name: '慢點',
      en: 'Slow Points',
      func: '瞬態決策',
      desc: '近似定點但有緩慢漂移；解釋決策累積證據'
    },
    {
      name: '線吸引子',
      en: 'Line Attractor',
      func: '連續記憶',
      desc: '一維連續穩定流形；如頭部方向、眼動位置'
    },
    {
      name: '環吸引子',
      en: 'Ring Attractor',
      func: '空間導航',
      desc: '環狀連續流形；對應方位角編碼（如海馬迴 head direction）'
    },
    {
      name: '平面吸引子',
      en: 'Plane Attractor',
      func: '二維工作記憶',
      desc: '二維連續流形；同時編碼兩個正交變量'
    }
  ];

  const cardW = 2.4;
  const cardH = 4.5;
  const startX = 0.6;
  const startY = 2.0;
  const gapX = 0.12;

  attractors.forEach((a, i) => {
    const x = startX + i * (cardW + gapX);
    s.addShape(pres.shapes.RECTANGLE, {
      x: x, y: startY, w: cardW, h: cardH,
      fill: { color: WHITE }, line: { color: RULE, width: 0.5 }
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: x, y: startY, w: cardW, h: 0.5,
      fill: { color: NAVY }, line: { color: NAVY, width: 0 }
    });
    // Header
    s.addText(a.name, {
      x: x, y: startY, w: cardW, h: 0.5,
      fontSize: 16, fontFace: HFONT, bold: true, color: WHITE,
      align: 'center', valign: 'middle', margin: 0
    });
    // English
    s.addText(a.en, {
      x: x, y: startY + 0.6, w: cardW, h: 0.4,
      fontSize: 11, fontFace: BFONT, color: TEXT_MUTED, italic: true,
      align: 'center', margin: 0
    });
    // Function badge
    s.addShape(pres.shapes.RECTANGLE, {
      x: x + 0.2, y: startY + 1.15, w: cardW - 0.4, h: 0.5,
      fill: { color: BG_LIGHT }, line: { color: ACCENT, width: 1 }
    });
    s.addText(a.func, {
      x: x + 0.2, y: startY + 1.15, w: cardW - 0.4, h: 0.5,
      fontSize: 12, fontFace: BFONT, bold: true, color: NAVY,
      align: 'center', valign: 'middle', margin: 0
    });
    // Description
    s.addText(a.desc, {
      x: x + 0.2, y: startY + 1.85, w: cardW - 0.4, h: 2.4,
      fontSize: 11, fontFace: BFONT, color: TEXT_DARK, margin: 0
    });
  });

  addFooter(s, ++n, TOTAL);
  s.addNotes('五種吸引子是 Sussillo 學派的「幾何基本元」——任何複雜認知任務都可以拆解為這些動力結構的組合。');
}

// ============================================================
// SLIDE 13: CTD 框架
// ============================================================
{
  let s = pres.addSlide();
  s.background = { color: BG_LIGHT };
  addSlideTitle(s, 'CTD 框架：經由動力學的運算', 'Computation Through Dynamics — bridging artificial RNNs and biological neural data');

  // Central concept
  s.addShape(pres.shapes.RECTANGLE, {
    x: 4.5, y: 2.0, w: 4.3, h: 1.5,
    fill: { color: NAVY }, line: { color: NAVY, width: 0 }
  });
  s.addText('CTD', {
    x: 4.5, y: 2.0, w: 4.3, h: 0.7,
    fontSize: 36, fontFace: HFONT, bold: true, color: ACCENT,
    align: 'center', valign: 'middle', margin: 0
  });
  s.addText('Computation Through Dynamics', {
    x: 4.5, y: 2.7, w: 4.3, h: 0.5,
    fontSize: 13, fontFace: BFONT, color: WHITE, italic: true,
    align: 'center', valign: 'middle', margin: 0
  });
  s.addText('運算體現於狀態空間軌跡', {
    x: 4.5, y: 3.1, w: 4.3, h: 0.4,
    fontSize: 12, fontFace: BFONT, color: ICE,
    align: 'center', valign: 'middle', margin: 0
  });

  // Left: ARTIFICIAL
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.6, y: 2.5, w: 3.5, h: 1.2,
    fill: { color: WHITE }, line: { color: RULE, width: 0.5 }
  });
  s.addText('人工 RNN 分析', {
    x: 0.6, y: 2.5, w: 3.5, h: 0.5,
    fontSize: 14, fontFace: HFONT, bold: true, color: NAVY,
    align: 'center', valign: 'middle', margin: 0
  });
  s.addText('FORCE + DSA + 吸引子拓樸', {
    x: 0.6, y: 2.95, w: 3.5, h: 0.7,
    fontSize: 11, fontFace: BFONT, color: TEXT_MUTED,
    align: 'center', valign: 'middle', margin: 0
  });

  // Right: BIOLOGICAL
  s.addShape(pres.shapes.RECTANGLE, {
    x: 9.2, y: 2.5, w: 3.5, h: 1.2,
    fill: { color: WHITE }, line: { color: RULE, width: 0.5 }
  });
  s.addText('生物神經數據', {
    x: 9.2, y: 2.5, w: 3.5, h: 0.5,
    fontSize: 14, fontFace: HFONT, bold: true, color: NAVY,
    align: 'center', valign: 'middle', margin: 0
  });
  s.addText('多單元電生理 + 大規模影像', {
    x: 9.2, y: 2.95, w: 3.5, h: 0.7,
    fontSize: 11, fontFace: BFONT, color: TEXT_MUTED,
    align: 'center', valign: 'middle', margin: 0
  });

  // Arrows
  s.addShape(pres.shapes.LINE, {
    x: 4.1, y: 3.1, w: 0.4, h: 0,
    line: { color: ACCENT, width: 2.5, endArrowType: 'triangle' }
  });
  s.addShape(pres.shapes.LINE, {
    x: 8.8, y: 3.1, w: 0.4, h: 0,
    line: { color: ACCENT, width: 2.5, endArrowType: 'triangle', beginArrowType: 'triangle' }
  });

  // Bottom: applications
  const apps = [
    { t: '運動皮層', d: 'M1 旋轉動力學、肌肉電位生成' },
    { t: '前額葉', d: '上下文切換、決策累積' },
    { t: '獎勵迴路', d: '價值編碼、學習信號' },
    { t: '視知覺', d: '物件辨識、注意力選擇' }
  ];

  const aw = 2.95;
  const ah = 1.6;
  const ay = 4.2;

  apps.forEach((a, i) => {
    const ax = 0.6 + i * (aw + 0.15);
    s.addShape(pres.shapes.RECTANGLE, {
      x: ax, y: ay, w: aw, h: ah,
      fill: { color: WHITE }, line: { color: RULE, width: 0.5 }
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: ax, y: ay, w: 0.08, h: ah,
      fill: { color: ACCENT }, line: { color: ACCENT, width: 0 }
    });
    s.addText(a.t, {
      x: ax + 0.2, y: ay + 0.2, w: aw - 0.3, h: 0.5,
      fontSize: 14, fontFace: HFONT, bold: true, color: NAVY, margin: 0
    });
    s.addText(a.d, {
      x: ax + 0.2, y: ay + 0.75, w: aw - 0.3, h: 0.8,
      fontSize: 11, fontFace: BFONT, color: TEXT_MUTED, margin: 0
    });
  });

  // Caption
  s.addText('CTD 的橋接力是 Sussillo 學派的核心價值：同一套動力學語言貫穿四大應用領域', {
    x: 0.6, y: 6.05, w: W - 1.2, h: 0.4,
    fontSize: 12, fontFace: BFONT, color: TEXT_MUTED, italic: true, align: 'center', margin: 0
  });

  addFooter(s, ++n, TOTAL);
  s.addNotes('CTD 把 FORCE/DSA 從「人工網路的玩具」提升為「神經科學的通用語言」，是 Sussillo 框架的最高綜合層。');
}

// ============================================================
// SLIDE 14: PNG 視覺化
// ============================================================
{
  let s = pres.addSlide();
  s.background = { color: NAVY_DEEP };

  // Title at top
  s.addText('Neural Population Dynamics and Computation', {
    x: 0.5, y: 0.3, w: W - 1, h: 0.6,
    fontSize: 24, fontFace: HFONT, bold: true, color: WHITE, margin: 0
  });
  s.addText('神經群體動力學的視覺化呈現 — CTD 框架的核心圖示', {
    x: 0.5, y: 0.9, w: W - 1, h: 0.4,
    fontSize: 13, fontFace: BFONT, color: ICE, italic: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.35, w: 1.2, h: 0.04,
    fill: { color: ACCENT }, line: { color: ACCENT, width: 0 }
  });

  // Insert image — preserve aspect ratio (2752x1536 ≈ 1.79:1)
  const imgPath = 'C:\\Users\\User\\AppData\\Local\\Temp\\sussillo_notes\\Neural Population Dynamics and Computation.png';
  const origW = 2752, origH = 1536;
  const maxH = 5.0;
  const calcW = maxH * (origW / origH);
  const centerX = (W - calcW) / 2;

  s.addImage({
    path: imgPath,
    x: centerX, y: 1.6, w: calcW, h: maxH
  });

  // Caption
  s.addText('神經群體軌跡 (state-space trajectories) 在高維狀態空間中沿吸引子流形演化；不同任務條件呈現不同的拓樸結構。', {
    x: 0.5, y: 6.7, w: W - 1, h: 0.4,
    fontSize: 11, fontFace: BFONT, color: ICE, italic: true, align: 'center', margin: 0
  });

  addFooter(s, ++n, TOTAL);
  s.addNotes('視覺化重點：用 NotebookLM 產生的概念圖展示 CTD 框架的核心——軌跡在狀態空間中的幾何結構就是「運算」本身。');
}

// ============================================================
// SLIDE 15: 無效空間 vs 效應空間
// ============================================================
{
  let s = pres.addSlide();
  s.background = { color: BG_LIGHT };
  addSlideTitle(s, '無效空間 vs. 效應空間', 'Null space vs. Potent space — the elegant solution to motor preparation');

  // Left: Null Space
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.6, y: 2.0, w: 5.8, h: 4.7,
    fill: { color: WHITE }, line: { color: RULE, width: 0.5 }
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.6, y: 2.0, w: 5.8, h: 0.7,
    fill: { color: NAVY }, line: { color: NAVY, width: 0 }
  });
  s.addText('無效空間 (Null Space)', {
    x: 0.85, y: 2.0, w: 5.5, h: 0.7,
    fontSize: 18, fontFace: HFONT, bold: true, color: WHITE, valign: 'middle', margin: 0
  });

  s.addText('容納準備活動，但不引發運動', {
    x: 0.85, y: 2.9, w: 5.5, h: 0.5,
    fontSize: 14, fontFace: HFONT, italic: true, color: NAVY, margin: 0
  });
  s.addText([
    { text: '神經群體在「沉默」維度上活動', options: { bullet: true, color: TEXT_DARK, breakLine: true } },
    { text: '對下游肌肉的投影 = 0', options: { bullet: true, color: TEXT_DARK, breakLine: true } },
    { text: '解釋：為何運動皮層在 reach 之前活動劇烈，但手不動', options: { bullet: true, color: TEXT_DARK, breakLine: true, paraSpaceAfter: 6 } },
    { text: '生物意義：運算分層 (computational hierarchy)', options: { bullet: true, italic: true, color: NAVY, bold: true } }
  ], {
    x: 0.85, y: 3.5, w: 5.5, h: 3.0,
    fontSize: 12, fontFace: BFONT, paraSpaceAfter: 4, margin: 0
  });

  // Right: Potent Space
  s.addShape(pres.shapes.RECTANGLE, {
    x: 6.9, y: 2.0, w: 5.8, h: 4.7,
    fill: { color: WHITE }, line: { color: RULE, width: 0.5 }
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 6.9, y: 2.0, w: 5.8, h: 0.7,
    fill: { color: ACCENT }, line: { color: ACCENT, width: 0 }
  });
  s.addText('效應空間 (Potent Space)', {
    x: 7.15, y: 2.0, w: 5.5, h: 0.7,
    fontSize: 18, fontFace: HFONT, bold: true, color: NAVY, valign: 'middle', margin: 0
  });

  s.addText('直接驅動下游肌肉', {
    x: 7.15, y: 2.9, w: 5.5, h: 0.5,
    fontSize: 14, fontFace: HFONT, italic: true, color: NAVY, margin: 0
  });
  s.addText([
    { text: '神經群體在「有效」維度上活動', options: { bullet: true, color: TEXT_DARK, breakLine: true } },
    { text: '對下游有非零投影', options: { bullet: true, color: TEXT_DARK, breakLine: true } },
    { text: '由條件不變信號 (CIS) 觸發狀態切換', options: { bullet: true, color: TEXT_DARK, breakLine: true } },
    { text: 'CIS 像「啟動信號 + 計時器」', options: { bullet: true, color: TEXT_DARK, breakLine: true, paraSpaceAfter: 6 } },
    { text: '生物意義：相同網路、不同維度，多任務複用', options: { bullet: true, italic: true, color: NAVY, bold: true } }
  ], {
    x: 7.15, y: 3.5, w: 5.5, h: 3.0,
    fontSize: 12, fontFace: BFONT, paraSpaceAfter: 4, margin: 0
  });

  addFooter(s, ++n, TOTAL);
  s.addNotes('Null/Potent 空間是 Sussillo 學派最美的單一發現之一：解釋了長期困惑的 motor preparation 之謎，並啟發了多任務神經計算的後續研究。');
}

// ============================================================
// SLIDE 16: 學術師承
// ============================================================
{
  let s = pres.addSlide();
  s.background = { color: BG_LIGHT };
  addSlideTitle(s, '學術師承與合作網絡', 'The intellectual lineage behind Sussillo\'s framework');

  const mentors = [
    {
      name: 'Larry Abbott',
      role: 'PhD 導師',
      affil: '哥倫比亞大學',
      contrib: 'FORCE 共同作者；理論神經科學奠基者；指引 Sussillo 從工程進入計算神經'
    },
    {
      name: 'Omri Barak',
      role: '理論合作者',
      affil: '哥倫比亞時期',
      contrib: 'DSA 共同作者；逆向工程 RNN 框架的數學基礎'
    },
    {
      name: 'Krishna Shenoy',
      role: 'Postdoc 導師',
      affil: '史丹佛大學',
      contrib: '運動皮層 BMI 領域權威；引導 Sussillo 把理論套用到真實神經數據'
    },
    {
      name: 'Bill Newsome',
      role: '合作者',
      affil: '史丹佛',
      contrib: '決策神經科學奠基者；提供前額葉決策實驗範式'
    }
  ];

  const cardW = 2.95;
  const cardH = 4.7;
  const startX = 0.6;
  const startY = 2.0;
  const gapX = 0.15;

  mentors.forEach((m, i) => {
    const x = startX + i * (cardW + gapX);
    s.addShape(pres.shapes.RECTANGLE, {
      x: x, y: startY, w: cardW, h: cardH,
      fill: { color: WHITE }, line: { color: RULE, width: 0.5 }
    });
    // Avatar circle
    s.addShape(pres.shapes.OVAL, {
      x: x + cardW / 2 - 0.6, y: startY + 0.3, w: 1.2, h: 1.2,
      fill: { color: NAVY }, line: { color: NAVY, width: 0 }
    });
    // Initials
    const initials = m.name.split(' ').map(w => w[0]).join('');
    s.addText(initials, {
      x: x + cardW / 2 - 0.6, y: startY + 0.3, w: 1.2, h: 1.2,
      fontSize: 32, fontFace: HFONT, bold: true, color: ACCENT,
      align: 'center', valign: 'middle', margin: 0
    });
    // Name
    s.addText(m.name, {
      x: x + 0.2, y: startY + 1.7, w: cardW - 0.4, h: 0.5,
      fontSize: 16, fontFace: HFONT, bold: true, color: NAVY,
      align: 'center', margin: 0
    });
    // Role badge
    s.addText(m.role, {
      x: x + 0.2, y: startY + 2.2, w: cardW - 0.4, h: 0.4,
      fontSize: 12, fontFace: BFONT, bold: true, color: ACCENT,
      align: 'center', margin: 0
    });
    // Affiliation
    s.addText(m.affil, {
      x: x + 0.2, y: startY + 2.6, w: cardW - 0.4, h: 0.4,
      fontSize: 11, fontFace: BFONT, color: TEXT_MUTED, italic: true,
      align: 'center', margin: 0
    });
    // Divider
    s.addShape(pres.shapes.LINE, {
      x: x + cardW / 2 - 0.5, y: startY + 3.1, w: 1.0, h: 0,
      line: { color: ACCENT, width: 1.2 }
    });
    // Contribution
    s.addText(m.contrib, {
      x: x + 0.25, y: startY + 3.3, w: cardW - 0.5, h: 1.3,
      fontSize: 11, fontFace: BFONT, color: TEXT_DARK,
      align: 'center', margin: 0
    });
  });

  addFooter(s, ++n, TOTAL);
  s.addNotes('Sussillo 的研究體系是兩個學派的合流：Abbott 的理論神經科學 (Columbia) + Shenoy 的系統神經科學 (Stanford)。');
}

// ============================================================
// SLIDE 17: 三大方法論議題
// ============================================================
{
  let s = pres.addSlide();
  s.background = { color: BG_LIGHT };
  addSlideTitle(s, '三大方法論議題與 Sussillo 的解答', 'Three unmet needs and how Sussillo addressed them');

  const issues = [
    {
      letter: 'A',
      problem: '混沌系統訓練困境',
      desc: 'BPTT 在強連接 RNN 中梯度爆炸；ESN 必須鉗制反饋',
      solution: 'FORCE 算法',
      sdesc: '即時 RLS 修正壓制誤差；保留完整反饋與混沌動力學',
      year: '2009'
    },
    {
      letter: 'B',
      problem: '黑盒子可解釋性缺口',
      desc: '訓練後 RNN 能擬合但不能解釋；無法成為大腦假設',
      solution: 'DSA 動力系統分析',
      sdesc: '尋找定點/慢點 + 局部線性化；高維 → 低維可解釋拓樸',
      year: '2013'
    },
    {
      letter: 'C',
      problem: '跨個體與非平穩性',
      desc: '單次試驗噪聲大；不同猴子/不同日記錄資料無法直接比對',
      solution: 'LFADS 隱性因子分析',
      sdesc: '生成模型 + 動力系統約束；推斷穩定的潛在因子',
      year: '2018'
    }
  ];

  const startY = 2.0;
  const rowH = 1.5;
  const gapY = 0.15;

  issues.forEach((iss, i) => {
    const y = startY + i * (rowH + gapY);

    // Letter badge
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.6, y: y, w: 0.9, h: rowH,
      fill: { color: NAVY }, line: { color: NAVY, width: 0 }
    });
    s.addText(iss.letter, {
      x: 0.6, y: y, w: 0.9, h: rowH,
      fontSize: 40, fontFace: HFONT, bold: true, color: ACCENT,
      align: 'center', valign: 'middle', margin: 0
    });

    // Problem
    s.addShape(pres.shapes.RECTANGLE, {
      x: 1.55, y: y, w: 5.2, h: rowH,
      fill: { color: 'F8E8E8' }, line: { color: 'CC4444', width: 0.5 }
    });
    s.addText('問題', {
      x: 1.7, y: y + 0.1, w: 1, h: 0.3,
      fontSize: 9, fontFace: BFONT, bold: true, color: 'CC4444', charSpacing: 3, margin: 0
    });
    s.addText(iss.problem, {
      x: 1.7, y: y + 0.4, w: 4.9, h: 0.4,
      fontSize: 14, fontFace: HFONT, bold: true, color: TEXT_DARK, margin: 0
    });
    s.addText(iss.desc, {
      x: 1.7, y: y + 0.85, w: 4.9, h: 0.6,
      fontSize: 11, fontFace: BFONT, color: TEXT_MUTED, margin: 0
    });

    // Arrow
    s.addShape(pres.shapes.LINE, {
      x: 6.85, y: y + rowH / 2, w: 0.3, h: 0,
      line: { color: ACCENT, width: 2.5, endArrowType: 'triangle' }
    });

    // Solution
    s.addShape(pres.shapes.RECTANGLE, {
      x: 7.25, y: y, w: 5.45, h: rowH,
      fill: { color: 'E8F4E8' }, line: { color: '0F7B0F', width: 0.5 }
    });
    s.addText(`Sussillo 解答 (${iss.year})`, {
      x: 7.4, y: y + 0.1, w: 3, h: 0.3,
      fontSize: 9, fontFace: BFONT, bold: true, color: '0F7B0F', charSpacing: 3, margin: 0
    });
    s.addText(iss.solution, {
      x: 7.4, y: y + 0.4, w: 5.15, h: 0.4,
      fontSize: 14, fontFace: HFONT, bold: true, color: NAVY, margin: 0
    });
    s.addText(iss.sdesc, {
      x: 7.4, y: y + 0.85, w: 5.15, h: 0.6,
      fontSize: 11, fontFace: BFONT, color: TEXT_MUTED, margin: 0
    });
  });

  addFooter(s, ++n, TOTAL);
  s.addNotes('Sussillo 的三項貢獻不是孤立的工具，而是針對神經計算研究的三個系統性瓶頸的精確回應。');
}

// ============================================================
// SLIDE 18: 框架優點
// ============================================================
{
  let s = pres.addSlide();
  s.background = { color: BG_LIGHT };
  addSlideTitle(s, '框架優點 (Strengths)', 'Why CTD has become the dominant paradigm');

  const strengths = [
    {
      t: '物理機制洞察力',
      d: '從現象到機制：不只描述「神經元做什麼」，而是揭示「為什麼必然這樣做」'
    },
    {
      t: '系統魯棒性',
      d: '吸引子拓樸對擾動具天然耐受性；解釋了大腦為何能在突觸雜訊下穩定運作'
    },
    {
      t: '矽實驗預測力',
      d: 'In silico → in vivo：訓練好的 RNN 可預測未做過的實驗結果，再回到動物驗證'
    },
    {
      t: '跨任務泛化',
      d: '同一套動力學語言適用於運動、決策、工作記憶、語言、視覺等多個領域'
    }
  ];

  const cardW = 5.9;
  const cardH = 2.1;
  const startX = 0.6;
  const startY = 2.0;
  const gapX = 0.3;
  const gapY = 0.25;

  strengths.forEach((str, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = startX + col * (cardW + gapX);
    const y = startY + row * (cardH + gapY);

    s.addShape(pres.shapes.RECTANGLE, {
      x: x, y: y, w: cardW, h: cardH,
      fill: { color: WHITE }, line: { color: RULE, width: 0.5 }
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: x, y: y, w: 0.08, h: cardH,
      fill: { color: '0F7B0F' }, line: { color: '0F7B0F', width: 0 }
    });
    // Check icon (use ✓ in big font as substitute)
    s.addShape(pres.shapes.OVAL, {
      x: x + 0.3, y: y + 0.4, w: 0.7, h: 0.7,
      fill: { color: '0F7B0F' }, line: { color: '0F7B0F', width: 0 }
    });
    s.addText('✓', {
      x: x + 0.3, y: y + 0.4, w: 0.7, h: 0.7,
      fontSize: 22, color: WHITE, bold: true,
      align: 'center', valign: 'middle', margin: 0
    });
    // Title
    s.addText(str.t, {
      x: x + 1.15, y: y + 0.3, w: cardW - 1.3, h: 0.55,
      fontSize: 16, fontFace: HFONT, bold: true, color: NAVY, margin: 0
    });
    // Description
    s.addText(str.d, {
      x: x + 1.15, y: y + 0.9, w: cardW - 1.3, h: 1.0,
      fontSize: 12, fontFace: BFONT, color: TEXT_DARK, margin: 0
    });
  });

  addFooter(s, ++n, TOTAL);
  s.addNotes('CTD 的四項優勢使它從一個小眾理論成長為主導範式：解釋力、預測力、跨領域泛化能力都同時具備。');
}

// ============================================================
// SLIDE 19: 框架局限性
// ============================================================
{
  let s = pres.addSlide();
  s.background = { color: BG_LIGHT };
  addSlideTitle(s, '框架局限性 (Limitations)', 'Three honest critiques to keep in mind');

  const limits = [
    {
      no: '1',
      t: '學習算法與生物物理斷層',
      d: 'FORCE 用 RLS 算法進行權重更新，但真實突觸層級無證據顯示能進行如此精確的全局誤差計算。網路結果像大腦，但學習過程未必。'
    },
    {
      no: '2',
      t: '解剖結構缺失',
      d: '當前 CNPD 框架多視大腦為「均質池子」，忽略細胞類型多樣性、樹突局部運算、區域間連接權重差異。對藥物干預與細胞特定損傷的預測力受限。'
    },
    {
      no: '3',
      t: '功能等效不等於機制同一',
      d: '逆向工程發現的吸引子結構是「一種解決方案」，不是「唯一的生物方案」。多個不同動力系統可產生相同輸出，導致機制解釋上的多義性 (multiplicity)。'
    }
  ];

  const cardH = 1.5;
  const startY = 2.0;
  const gapY = 0.2;

  limits.forEach((lim, i) => {
    const y = startY + i * (cardH + gapY);

    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.6, y: y, w: W - 1.2, h: cardH,
      fill: { color: WHITE }, line: { color: RULE, width: 0.5 }
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.6, y: y, w: 1.0, h: cardH,
      fill: { color: 'CC4444' }, line: { color: 'CC4444', width: 0 }
    });
    s.addText(lim.no, {
      x: 0.6, y: y, w: 1.0, h: cardH,
      fontSize: 48, fontFace: HFONT, bold: true, color: WHITE,
      align: 'center', valign: 'middle', margin: 0
    });
    s.addText(lim.t, {
      x: 1.8, y: y + 0.2, w: W - 2.4, h: 0.5,
      fontSize: 16, fontFace: HFONT, bold: true, color: NAVY, margin: 0
    });
    s.addText(lim.d, {
      x: 1.8, y: y + 0.7, w: W - 2.4, h: 0.75,
      fontSize: 12, fontFace: BFONT, color: TEXT_DARK, margin: 0
    });
  });

  // Bottom takeaway
  s.addText('這些局限不否定 CTD 的價值——而是定義了下一個世代研究的方向', {
    x: 0.6, y: 6.4, w: W - 1.2, h: 0.4,
    fontSize: 12, fontFace: BFONT, color: TEXT_MUTED, italic: true, align: 'center', margin: 0
  });

  addFooter(s, ++n, TOTAL);
  s.addNotes('誠實面對局限：CTD 強大但不完美，三個缺口正是未來研究方向（生物學習規則、細胞型多樣性、機制唯一性檢驗）。');
}

// ============================================================
// SLIDE 20: 臨床與應用價值
// ============================================================
{
  let s = pres.addSlide();
  s.background = { color: BG_LIGHT };
  addSlideTitle(s, '臨床與應用價值', 'For neurologists, psychiatrists, rehab physicians, and BMI researchers');

  const apps = [
    {
      t: '運動疾病建模',
      icon: '⚙',
      diseases: 'Parkinson · ALS · Stroke',
      d: '把運動皮層代償視為動力學重組；預測復健介入後的軌跡修復'
    },
    {
      t: '癲癇新觀點',
      icon: '⚡',
      diseases: 'Focal · Generalized seizure',
      d: '從「過度同步」重新定義為動力學失調的特例；尋找吸引子失穩的早期指標'
    },
    {
      t: '工作記憶疾病',
      icon: '◐',
      diseases: 'Schizophrenia · ADHD · Alzheimer',
      d: '前額葉持續活動的時序解體；可量化動力學特徵作為早期生物標記'
    },
    {
      t: '腦機介面 (BMI)',
      icon: '⌬',
      diseases: 'Spinal cord injury · LIS',
      d: '基於 LFADS 的解碼器設計；跨日穩定的潛在因子提升解碼準確率'
    }
  ];

  const cardW = 5.9;
  const cardH = 2.15;
  const startX = 0.6;
  const startY = 2.0;
  const gapX = 0.3;
  const gapY = 0.2;

  apps.forEach((a, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = startX + col * (cardW + gapX);
    const y = startY + row * (cardH + gapY);

    s.addShape(pres.shapes.RECTANGLE, {
      x: x, y: y, w: cardW, h: cardH,
      fill: { color: WHITE }, line: { color: RULE, width: 0.5 }
    });
    // Icon area
    s.addShape(pres.shapes.RECTANGLE, {
      x: x, y: y, w: 1.0, h: cardH,
      fill: { color: NAVY }, line: { color: NAVY, width: 0 }
    });
    s.addText(a.icon, {
      x: x, y: y, w: 1.0, h: cardH,
      fontSize: 38, color: ACCENT, bold: true,
      align: 'center', valign: 'middle', margin: 0
    });
    // Title
    s.addText(a.t, {
      x: x + 1.15, y: y + 0.2, w: cardW - 1.3, h: 0.5,
      fontSize: 16, fontFace: HFONT, bold: true, color: NAVY, margin: 0
    });
    // Diseases tag
    s.addText(a.diseases, {
      x: x + 1.15, y: y + 0.7, w: cardW - 1.3, h: 0.35,
      fontSize: 10, fontFace: BFONT, bold: true, color: ACCENT, charSpacing: 2, margin: 0
    });
    // Description
    s.addText(a.d, {
      x: x + 1.15, y: y + 1.1, w: cardW - 1.3, h: 1.0,
      fontSize: 11, fontFace: BFONT, color: TEXT_DARK, margin: 0
    });
  });

  addFooter(s, ++n, TOTAL);
  s.addNotes('對臨床醫師：CTD 不只是理論——已可在腦機介面、Parkinson 復健、癲癇監測等場景產生可驗證的應用。');
}

// ============================================================
// SLIDE 21: 未來展望
// ============================================================
{
  let s = pres.addSlide();
  s.background = { color: NAVY_DEEP };

  // Title at top
  s.addText('FUTURE HORIZON', {
    x: 0.5, y: 0.5, w: W - 1, h: 0.4,
    fontSize: 12, fontFace: BFONT, color: ACCENT, charSpacing: 8, bold: true, margin: 0
  });
  s.addText('未來展望：具身圖靈測試', {
    x: 0.5, y: 1.0, w: W - 1, h: 0.7,
    fontSize: 36, fontFace: HFONT, bold: true, color: WHITE, margin: 0
  });
  s.addText('Embodied Turing Test — Sussillo 推向 NeuroAI 的終極願景 (2022–2026)', {
    x: 0.5, y: 1.7, w: W - 1, h: 0.4,
    fontSize: 14, fontFace: BFONT, color: ICE, italic: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 2.15, w: 1.5, h: 0.04,
    fill: { color: ACCENT }, line: { color: ACCENT, width: 0 }
  });

  // Big quote
  s.addText('「不再問機器能否與人對話，而是問：機器能否像生物一樣，在物理世界中行動、學習、適應？」', {
    x: 0.7, y: 2.6, w: 11.9, h: 1.5,
    fontSize: 22, fontFace: HFONT, color: WHITE, italic: true, margin: 0
  });

  // Three pillars
  const pillars = [
    { t: '神經科學基礎', d: 'CTD + 動力學語言' },
    { t: '具身互動', d: '機器人 + 物理世界耦合' },
    { t: '終身學習', d: '從一次任務到持續適應' }
  ];

  const cardW = 4.0;
  const cardH = 2.0;
  const startY = 4.5;

  pillars.forEach((p, i) => {
    const x = 0.5 + i * (cardW + 0.2);
    s.addShape(pres.shapes.RECTANGLE, {
      x: x, y: startY, w: cardW, h: cardH,
      fill: { color: NAVY }, line: { color: ACCENT, width: 1 }
    });
    s.addText(p.t, {
      x: x + 0.2, y: startY + 0.4, w: cardW - 0.4, h: 0.6,
      fontSize: 18, fontFace: HFONT, bold: true, color: ACCENT,
      align: 'center', valign: 'middle', margin: 0
    });
    s.addText(p.d, {
      x: x + 0.2, y: startY + 1.05, w: cardW - 0.4, h: 0.7,
      fontSize: 13, fontFace: BFONT, color: WHITE,
      align: 'center', valign: 'middle', margin: 0
    });
  });

  addFooter(s, ++n, TOTAL);
  s.addNotes('Sussillo 把研究弧線拉到 NeuroAI 的最遠端：神經科學的動力學洞見如何回頭塑造下一代 AI。這也是領域融合的方向。');
}

// ============================================================
// SLIDE 22: 核心參考文獻
// ============================================================
{
  let s = pres.addSlide();
  s.background = { color: BG_LIGHT };
  addSlideTitle(s, '核心參考文獻', 'Essential reading list (recommended order)');

  const refs = [
    { yr: '2009', auth: 'Sussillo D, Abbott LF', title: 'Generating coherent patterns of activity from chaotic neural networks', jrnl: 'Neuron 63(4):544-57', tag: 'FORCE 原始論文' },
    { yr: '2013', auth: 'Sussillo D, Barak O', title: 'Opening the Black Box: Low-Dimensional Dynamics in High-Dimensional Recurrent Neural Networks', jrnl: 'Neural Computation 25(3):626-49', tag: 'DSA 方法論' },
    { yr: '2014', auth: 'Sussillo D', title: 'Neural circuits as computational dynamical systems', jrnl: 'Curr Opin Neurobiol 25:156-63', tag: 'CTD 概念性入門' },
    { yr: '2015', auth: 'Sussillo D, Churchland MM, Kaufman MT, Shenoy KV', title: 'A neural network that finds a naturalistic solution for the production of muscle activity', jrnl: 'Nat Neurosci 18(7):1025-33', tag: '運動皮層應用代表作' },
    { yr: '2018', auth: 'Pandarinath C, ..., Sussillo D', title: 'Inferring single-trial neural population dynamics using sequential auto-encoders (LFADS)', jrnl: 'Nat Methods 15:805-815', tag: '單次試驗解析' },
    { yr: '2020', auth: 'Vyas S, Golub MD, Sussillo D, Shenoy KV', title: 'Computation Through Neural Population Dynamics', jrnl: 'Annu Rev Neurosci 43:249-275', tag: '學派總綜述（必讀）' },
    { yr: '2022', auth: 'Driscoll LN, Shenoy K, Sussillo D', title: 'Flexible multitask computation in recurrent networks utilizes shared dynamical motifs', jrnl: 'Nat Neurosci', tag: '多任務動力學' }
  ];

  const headerOpts = { fill: { color: NAVY }, color: WHITE, bold: true, fontFace: HFONT, fontSize: 12, align: 'center', valign: 'middle' };
  const yearOpts = { fontSize: 11, fontFace: BFONT, bold: true, color: ACCENT, valign: 'middle', align: 'center' };
  const authOpts = { fontSize: 10, fontFace: BFONT, color: TEXT_DARK, valign: 'middle' };
  const titleOpts = { fontSize: 10, fontFace: BFONT, color: TEXT_DARK, italic: true, valign: 'middle' };
  const jrnlOpts = { fontSize: 9, fontFace: BFONT, color: TEXT_MUTED, valign: 'middle' };
  const tagOpts = { fontSize: 10, fontFace: BFONT, bold: true, color: NAVY, valign: 'middle', align: 'center' };

  const tableData = [
    [
      { text: '年份', options: headerOpts },
      { text: '作者', options: headerOpts },
      { text: '標題', options: headerOpts },
      { text: '期刊', options: headerOpts },
      { text: '重要性', options: headerOpts }
    ]
  ];

  refs.forEach(r => {
    tableData.push([
      { text: r.yr, options: yearOpts },
      { text: r.auth, options: authOpts },
      { text: r.title, options: titleOpts },
      { text: r.jrnl, options: jrnlOpts },
      { text: r.tag, options: tagOpts }
    ]);
  });

  s.addTable(tableData, {
    x: 0.5, y: 2.0, w: W - 1.0,
    colW: [0.8, 2.5, 4.8, 2.5, 1.7],
    rowH: [0.45].concat(refs.map(() => 0.55)),
    border: { pt: 0.5, color: RULE }
  });

  s.addText('建議閱讀順序：先讀 2014 (概念) → 2009 (原始) → 2020 (綜述) → 2015 (應用代表) → 2013 (DSA 細節)', {
    x: 0.5, y: 6.55, w: W - 1.0, h: 0.4,
    fontSize: 11, fontFace: BFONT, color: TEXT_MUTED, italic: true, align: 'center', margin: 0
  });

  addFooter(s, ++n, TOTAL);
  s.addNotes('七篇核心文獻涵蓋從原始方法到最新延伸；建議閱讀順序：先讀 2014 入門 → 2009 原始 → 2020 綜述。');
}

// ===== Write file =====
const outPath = 'C:\\Users\\User\\AppData\\Local\\Temp\\sussillo_pptx\\Sussillo_大腦皮層動力學_高維神經計算的解析.pptx';
pres.writeFile({ fileName: outPath })
  .then(fname => {
    console.log('PPTX written:', fname);
    const stats = fs.statSync(fname);
    console.log('Size:', (stats.size / 1024).toFixed(1) + ' KB');
    console.log('Slides:', n + 1);
  })
  .catch(err => {
    console.error('ERROR:', err);
    process.exit(1);
  });
