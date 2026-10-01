// Life OS Memento mori (port of Compass Meta/views/memento.js).
// Reads birthdate + life_expectancy from Compass Config. Never guesses a birthdate.
const cfg = dv.page("Life OS/Meta/Compass Config") || {};
const root = dv.container.createEl("div", { cls: "lifeos-widget" });
if (!cfg.birthdate) {
  root.createEl("p", { text: "在 Life OS/Meta/Compass Config 填上 birthdate（YYYY-MM-DD），這裡就會顯示你的人生週數。" }).style.opacity = "0.7";
} else {
  const birth = moment(String(cfg.birthdate).slice(0, 10));
  const years = Number(cfg.life_expectancy) || 80;
  const today = moment().startOf("day");
  const lived = today.diff(birth, "weeks"), total = Math.round(years * 52.1775);
  const pct = Math.min(100, Math.round(1000 * lived / total) / 10), age = today.diff(birth, "years");
  root.createEl("p", { text: `你 ${age} 歲，活了約 ${lived.toLocaleString()} 週。若活到 ${years} 歲，大約還剩 ${Math.max(0, total - lived).toLocaleString()} 週（已用 ${pct}%）。` });
  const grid = root.createEl("div");
  grid.style.cssText = "display:grid;grid-template-columns:repeat(20,12px);gap:3px;margin:.5em 0";
  for (let y = 0; y < years; y++) {
    const s = grid.createEl("span");
    s.title = `${y} 歲`;
    s.style.cssText = `width:12px;height:12px;border-radius:2px;border:1px solid var(--background-modifier-border);` +
      (y < age ? "background:var(--text-muted)" : y === age ? "background:var(--interactive-accent)" : "");
  }
  root.createEl("p", { text: "一格一年。下一格，刻意地用。" }).style.opacity = "0.6";
}
