// Life OS weekly review table (port of Compass Meta/views/week.js): one row per day with
// daily-question scores and habit hits. Usage (inside a weekly note named gggg-[W]ww):
//   await dv.view("Life OS/Meta/views/week", { week: dv.current().file.name })
const cfg = dv.page("Life OS/Meta/Compass Config") || {};
const FOLDER = cfg.daily_folder || cfg.daily_note_folder || "每日筆記";
const DQ = cfg.dq_prefix || "dq_", HB = cfg.habit_prefix || "habit_";
const weekName = (input && input.week) || moment().format("gggg-[W]ww");
const start = moment(weekName, "gggg-[W]ww").startOf("week");
const short = {};
for (const q of (cfg.dq_questions || cfg.questions || [])) {
  if (q && typeof q === "object") short[q.id || q.key] = String(q.short || q.prompt || q.text || q.id).replace(/^我今天是否盡力/, "").replace(/[？?]\s*$/, "").slice(0, 8);
}
const byName = new Map(dv.pages(`"${FOLDER}"`).array().map(p => [p.file.name, p]));
const days = [...Array(7).keys()].map(i => start.clone().add(i, "day"));
const dqKeys = new Set(), hbKeys = new Set();
for (const d of days) {
  const p = byName.get(d.format("YYYY-MM-DD"));
  for (const k of Object.keys((p && p.file.frontmatter) || {})) { if (k.startsWith(DQ)) dqKeys.add(k); if (k.startsWith(HB)) hbKeys.add(k); }
}
const dqs = [...dqKeys].sort(), hbs = [...hbKeys].sort();
const sums = {}, counts = {}, rows = [];
for (const d of days) {
  const p = byName.get(d.format("YYYY-MM-DD"));
  const fm = p ? (p.file.frontmatter || {}) : null;
  const cells = [p ? dv.fileLink(p.file.path, false, d.format("M/D ddd")) : d.format("M/D ddd")];
  for (const k of dqs) {
    const v = fm && fm[k] !== null && fm[k] !== "" && !isNaN(Number(fm[k])) ? Number(fm[k]) : null;
    if (v !== null) { sums[k] = (sums[k] || 0) + v; counts[k] = (counts[k] || 0) + 1; }
    cells.push(v === null ? "" : String(v));
  }
  cells.push(fm ? `${hbs.filter(k => fm[k] === true).length}/${hbs.length}` : "");
  rows.push(cells);
}
rows.push(["**平均**", ...dqs.map(k => counts[k] ? `${(sums[k] / counts[k]).toFixed(1)}（n=${counts[k]}）` : ""), ""]);
if (!dqs.length && !hbs.length) dv.paragraph(`${weekName} 這週還沒有任何評分。`);
else dv.table(["日", ...dqs.map(k => short[k] || k), "習慣"], rows);
