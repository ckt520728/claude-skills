// Life OS daily questions: lines + averages of every dq_* property (port of Compass
// Meta/views/dailyquestions.js), labelled from the SSOT and with the denominator always shown.
// Usage:
//   await dv.view("Life OS/Meta/views/dailyquestions", { days: 30 })
//   await dv.view("Life OS/Meta/views/dailyquestions", { from: "2026-10-01", to: "2026-12-31" })
const cfg = dv.page("Life OS/Meta/Compass Config") || {};
const FOLDER = cfg.daily_folder || cfg.daily_note_folder || "每日筆記";
const PREFIX = cfg.dq_prefix || "dq_";
const DEFAULT_RANGE = (input && input.days) || 30;
const FIXED_FROM = input && input.from ? moment(input.from) : null;
const FIXED_TO = input && input.to ? moment(input.to) : null;
const GOOD = (cfg.display_bands && cfg.display_bands.good) || 8;
const WATCH = (cfg.display_bands && cfg.display_bands.watch) || 6;
const COLORS = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#42d4f4", "#f032e6", "#9a6324"];

// Labels come from Compass Config, so renaming a question never needs a code edit (invariant 7).
const labels = {};
for (const q of (cfg.dq_questions || cfg.questions || [])) {
  if (!q || typeof q !== "object") continue;
  const id = q.id || q.key, text = String(q.short || q.prompt || q.text || id);
  labels[id] = text.replace(/^我今天是否盡力/, "").replace(/[？?]\s*$/, "");
}
const label = k => labels[k] || k.slice(PREFIX.length).replace(/[_-]+/g, " ");

const pages = dv.pages(`"${FOLDER}"`).where(p => /^\d{4}-\d{2}-\d{2}$/.test(p.file.name)).array();
const series = {};
for (const p of pages) {
  const fm = p.file.frontmatter || {};
  for (const k of Object.keys(fm)) {
    if (!k.startsWith(PREFIX)) continue;
    const v = Number(fm[k]);
    if (fm[k] === null || fm[k] === "" || isNaN(v)) continue;
    (series[k] = series[k] || []).push({ date: p.file.name, t: moment(p.file.name).valueOf(), v });
  }
}
const keys = Object.keys(series).sort((a, b) => (Object.keys(labels).indexOf(a) - Object.keys(labels).indexOf(b)));
const root = dv.container.createEl("div", { cls: "lifeos-widget" });

if (keys.length === 0) {
  root.createEl("p", { text: `「${FOLDER}」裡還沒有任何 ${PREFIX}* 分數。今晚按 Ctrl+Shift+Q 評分，明天這裡就會出現第一個點。` });
} else {
  // ---- today vs your own 7-day mean: the signal is the gap, not the absolute number ----
  const todayName = moment().format("YYYY-MM-DD");
  const last7 = new Set([...Array(7).keys()].map(i => moment().subtract(i, "days").format("YYYY-MM-DD")));
  const t7 = root.createEl("table", { cls: "lifeos-table" });
  const hr = t7.createEl("thead").createEl("tr");
  for (const h of ["", "提問", "今天", "7 日平均", "對比"]) hr.createEl("th", { text: h });
  const tb = t7.createEl("tbody");
  for (const k of keys) {
    const vals = series[k].filter(x => last7.has(x.date)).map(x => x.v);
    const now = (series[k].find(x => x.date === todayName) || {}).v;
    const mean = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
    const basis = now !== undefined ? now : mean;
    const light = basis === null ? "⚪" : basis >= GOOD ? "🟢" : basis >= WATCH ? "🟡" : "🔴";
    const delta = now !== undefined && mean !== null ? now - mean : null;
    const r = tb.createEl("tr");
    r.createEl("td", { text: light });
    r.createEl("td", { text: label(k) });
    r.createEl("td", { text: now === undefined ? "—" : String(now) });
    // The denominator travels with the mean: a "7-day mean" of 2 days is not one.
    r.createEl("td", { text: mean === null ? "—" : `${mean.toFixed(1)}（n=${vals.length}/7）` });
    r.createEl("td", { text: delta === null ? "—" : delta > 0.05 ? `▲ +${delta.toFixed(1)}` : delta < -0.05 ? `▼ ${delta.toFixed(1)}` : "＝" });
  }
  root.createEl("p", { text: "問的是「是否盡力」，不是「有沒有做到」。低分代表今天有阻力，不代表你不好。" }).style.opacity = "0.6";

  // ---- the trend chart (upstream) ----
  const controls = root.createEl("div", { cls: "lifeos-controls" });
  let sel = null;
  if (!FIXED_FROM) {
    sel = controls.createEl("select");
    for (const [v, l] of [[7, "近 7 天"], [30, "近 30 天"], [90, "近 90 天"], [365, "近一年"], [0, "全部"]]) {
      const o = sel.createEl("option", { text: l });
      o.value = String(v);
      if (v === DEFAULT_RANGE) o.selected = true;
    }
    sel.addEventListener("change", render);
  } else {
    controls.createEl("span", { text: `${FIXED_FROM.format("YYYY-MM-DD")} → ${FIXED_TO ? FIXED_TO.format("YYYY-MM-DD") : "今天"}` });
  }
  const toggles = {};
  keys.forEach((k, i) => {
    const lab = controls.createEl("label");
    lab.style.cssText = `margin-left:.8em;color:${COLORS[i % COLORS.length]}`;
    const cb = lab.createEl("input", { attr: { type: "checkbox" } });
    cb.checked = true;
    lab.appendText(" " + label(k));
    toggles[k] = cb;
    cb.addEventListener("change", render);
  });
  const chart = root.createEl("div", { cls: "lifeos-chart" });

  function render() {
    const today = moment().startOf("day");
    let from, to = FIXED_TO ? FIXED_TO.clone().endOf("day") : today.clone().endOf("day");
    if (FIXED_FROM) from = FIXED_FROM.clone().startOf("day");
    else {
      const d = Number(sel.value);
      if (d > 0) from = today.clone().subtract(d - 1, "day");
      else from = moment(Math.min(...keys.flatMap(k => series[k].map(x => x.t)))).startOf("day");
    }
    const t0 = from.valueOf(), t1 = to.valueOf();
    const W = 720, H = 240, ml = 30, mr = 12, mt = 10, mb = 26, iw = W - ml - mr, ih = H - mt - mb;
    const x = t => t1 === t0 ? ml + iw / 2 : ml + (t - t0) / (t1 - t0) * iw;
    const y = v => mt + (10 - v) / 9 * ih;
    let svg = `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" style="width:100%">`;
    for (let g = 1; g <= 10; g++) {
      svg += `<line x1="${ml}" x2="${W - mr}" y1="${y(g)}" y2="${y(g)}" stroke="currentColor" stroke-opacity="${g === 1 || g === 10 ? 0.35 : 0.1}"/>`;
      if (g === 1 || g === 5 || g === 10) svg += `<text x="${ml - 6}" y="${y(g) + 4}" font-size="11" text-anchor="end" fill="currentColor" opacity="0.7">${g}</text>`;
    }
    svg += `<text x="${ml}" y="${H - 6}" font-size="11" fill="currentColor" opacity="0.7">${from.format("YYYY-MM-DD")}</text>`;
    svg += `<text x="${W - mr}" y="${H - 6}" font-size="11" text-anchor="end" fill="currentColor" opacity="0.7">${to.format("YYYY-MM-DD")}</text>`;
    keys.forEach((k, i) => {
      if (!toggles[k].checked) return;
      const pts = series[k].filter(p => p.t >= t0 && p.t <= t1).sort((a, b) => a.t - b.t);
      if (!pts.length) return;
      const c = COLORS[i % COLORS.length];
      svg += `<polyline points="${pts.map(p => `${x(p.t).toFixed(1)},${y(p.v).toFixed(1)}`).join(" ")}" fill="none" stroke="${c}" stroke-width="2" stroke-linejoin="round"/>`;
      for (const p of pts) svg += `<circle cx="${x(p.t).toFixed(1)}" cy="${y(p.v).toFixed(1)}" r="2.5" fill="${c}"><title>${p.date}：${p.v}</title></circle>`;
      const avg = pts.reduce((a, p) => a + p.v, 0) / pts.length;
      svg += `<line x1="${ml}" x2="${W - mr}" y1="${y(avg)}" y2="${y(avg)}" stroke="${c}" stroke-opacity="0.35" stroke-dasharray="4 4"/>`;
    });
    chart.innerHTML = svg + "</svg>";
  }
  render();
}
