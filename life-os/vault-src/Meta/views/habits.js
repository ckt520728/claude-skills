// Life OS Habit Canvas (port of Compass Meta/views/habits.js), labelled from the SSOT.
// Usage: await dv.view("Life OS/Meta/views/habits", { days: 14 })
// Last N days grid, current streak, best streak, longest break, completion %, total.
const cfg = dv.page("Life OS/Meta/Compass Config") || {};
const FOLDER = cfg.daily_folder || cfg.daily_note_folder || "每日筆記";
const PREFIX = cfg.habit_prefix || "habit_";
const DAYS = (input && input.days) || 14;
const names = {};
for (const h of (cfg.habits || [])) {
  if (h && typeof h === "object") names[h.id || h.key] = h.name || h.id;
}
const label = k => names[k] || k.slice(PREFIX.length).replace(/[_-]+/g, " ");

const pages = dv.pages(`"${FOLDER}"`).where(p => /^\d{4}-\d{2}-\d{2}$/.test(p.file.name)).array();
const byDate = new Map();
const habits = new Set(Object.keys(names));
for (const p of pages) {
  const fm = p.file.frontmatter || {};
  const vals = {};
  for (const k of Object.keys(fm)) {
    if (!k.startsWith(PREFIX)) continue;
    habits.add(k);
    vals[k] = fm[k] === true;
  }
  byDate.set(p.file.name, vals);
}

const root = dv.container.createEl("div", { cls: "lifeos-widget" });
if (habits.size === 0 || byDate.size === 0) {
  root.createEl("p", { text: `還沒有任何 ${PREFIX}* 紀錄。夜間評分（Ctrl+Shift+Q）會一起問習慣，答了這裡就會出現。` });
} else {
  const today = moment().startOf("day");
  const fmt = d => d.format("YYYY-MM-DD");
  const first = moment([...byDate.keys()].sort()[0]);
  const table = root.createEl("table", { cls: "lifeos-table" });
  const th = table.createEl("thead").createEl("tr");
  for (const h of ["習慣", `近 ${DAYS} 天`, "目前連續", "最長連續", "最長中斷", "完成率", "總次數"]) th.createEl("th", { text: h });
  const tb = table.createEl("tbody");
  for (const h of [...habits]) {
    const rec = d => byDate.get(fmt(d));
    const tracked = d => { const v = rec(d); return !!v && (h in v); };
    const done = d => { const v = rec(d); return !!v && v[h] === true; };
    let cur = 0, d = today.clone();
    if (!done(d)) d.subtract(1, "day");
    while (done(d)) { cur++; d.subtract(1, "day"); }
    let best = 0, run = 0, brk = 0, gap = 0, total = 0, trackedDays = 0;
    for (let x = first.clone(); !x.isAfter(today); x.add(1, "day")) {
      if (tracked(x)) trackedDays++;
      if (done(x)) { total++; run++; best = Math.max(best, run); brk = Math.max(brk, gap); gap = 0; }
      else if (tracked(x)) { run = 0; gap++; }
      else run = 0;   // no note that day: breaks the streak, is not a "missed" day
    }
    brk = Math.max(brk, gap);
    const grid = [];
    for (let i = DAYS - 1; i >= 0; i--) {
      const x = today.clone().subtract(i, "day");
      grid.push(done(x) ? "●" : tracked(x) ? "○" : "·");
    }
    const r = tb.createEl("tr");
    for (const c of [label(h), grid.join(""), `${cur} 天`, `${best} 天`, `${brk} 天`,
                     `${trackedDays ? Math.round(100 * total / trackedDays) : 0}%`, String(total)]) r.createEl("td", { text: c });
    r.children[1].style.fontFamily = "monospace";
  }
  root.createEl("p", { text: "● 做到　○ 有記錄但沒做到　· 那天沒有日記。誠實追蹤比完美追蹤重要。" }).style.opacity = "0.6";
}
