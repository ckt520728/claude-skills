// Life OS Wheel of Life radar (port of Compass Meta/views/wheel.js), labelled from the SSOT.
// Usage:
//   await dv.view("Life OS/Meta/views/wheel")                                   this quarter's retreat, else latest
//   await dv.view("Life OS/Meta/views/wheel", { page: dv.current().file.path })  inside a retreat note
const cfg = dv.page("Life OS/Meta/Compass Config") || {};
const FOLDER = cfg.retreat_folder || "Life OS/02 Retreats";
const PREFIX = cfg.wheel_prefix || "wheel_";
const SUFFIX = " 個人退修";
const names = {};
for (const w of (cfg.wheel_areas || [])) if (w && typeof w === "object") names[w.id || w.key] = w.name || w.id;

let page = input && input.page ? dv.page(input.page) : null, how = "";
if (!page) {
  const q = `${moment().year()}-Q${moment().quarter()}`;
  page = dv.page(`${FOLDER}/${q}${SUFFIX}`);
  how = page ? `本季（${q}）` : "";
}
if (!page) {
  page = dv.pages(`"${FOLDER}"`).where(p => /^\d{4}-Q[1-4] /.test(p.file.name)).sort(p => p.file.name, "desc").array()[0];
  how = page ? "最近一次退修" : "";
}
const root = dv.container.createEl("div", { cls: "lifeos-widget" });
if (!page) {
  root.createEl("p", { text: `還沒有退修筆記。在指南針儀表板按「本季退修」，會建立「${moment().year()}-Q${moment().quarter()}${SUFFIX}」，填好 ${PREFIX}* 分數後這裡就會畫出人生輪。` });
} else {
  const fm = page.file.frontmatter || {};
  const axes = Object.keys(fm)
    .filter(k => k.startsWith(PREFIX) && fm[k] !== null && fm[k] !== "" && !isNaN(Number(fm[k])))
    .map(k => ({ name: names[k] || k.slice(PREFIX.length), v: Math.max(0, Math.min(10, Number(fm[k]))) }));
  if (how) root.createEl("p", { text: `來源：${page.file.name}（${how}）` }).style.opacity = "0.7";
  if (axes.length < 3) {
    root.createEl("p", { text: `${page.file.name} 填了不到 3 個 ${PREFIX}* 分數，還畫不出來。` });
  } else {
    const n = axes.length, cx = 190, cy = 165, R = 105, W = 380, H = 330;
    const ang = i => -Math.PI / 2 + i * 2 * Math.PI / n;
    const pt = (i, r) => [cx + r * Math.cos(ang(i)), cy + r * Math.sin(ang(i))];
    let svg = `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" style="max-width:${W}px">`;
    for (const ring of [2, 4, 6, 8, 10]) {
      svg += `<polygon points="${axes.map((_, i) => pt(i, R * ring / 10).map(c => c.toFixed(1)).join(",")).join(" ")}" fill="none" stroke="currentColor" stroke-opacity="${ring === 10 ? 0.4 : 0.15}"/>`;
    }
    axes.forEach((a, i) => {
      const [x2, y2] = pt(i, R), [lx, ly] = pt(i, R + 20);
      const anchor = Math.abs(lx - cx) < 5 ? "middle" : (lx > cx ? "start" : "end");
      svg += `<line x1="${cx}" y1="${cy}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="currentColor" stroke-opacity="0.2"/>`;
      svg += `<text x="${lx.toFixed(1)}" y="${(ly + 4).toFixed(1)}" font-size="11" text-anchor="${anchor}" fill="currentColor">${a.name}（${a.v}）</text>`;
    });
    svg += `<polygon points="${axes.map((a, i) => pt(i, R * a.v / 10).map(c => c.toFixed(1)).join(",")).join(" ")}" fill="var(--interactive-accent)" fill-opacity="0.35" stroke="var(--interactive-accent)" stroke-width="2"/>`;
    root.createEl("div", { cls: "lifeos-chart" }).innerHTML = svg + "</svg>";
    const avg = axes.reduce((s, a) => s + a.v, 0) / n;
    const low = [...axes].sort((a, b) => a.v - b.v)[0];
    root.createEl("p", { text: `平均 ${avg.toFixed(1)} / 10。最低：${low.name}（${low.v}）—— 這是未來 90 天的候選焦點。` });
  }
}
