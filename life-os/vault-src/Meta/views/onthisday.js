// Life OS "on this day" (Compass daily-note query): what you wrote on this date in earlier
// years. "It's not the act of writing the entry, it's bumping into your past self."
// Shows the reflection section only; the clinical section is never embedded.
// Usage: await dv.view("Life OS/Meta/views/onthisday")
const cfg = dv.page("Life OS/Meta/Compass Config") || {};
const FOLDER = cfg.daily_folder || cfg.daily_note_folder || "每日筆記";
const HEADING = cfg.reflection_heading || "💡 今日反思";
const me = moment().format("YYYY-MM-DD"), mmdd = me.slice(4), yr = Number(me.slice(0, 4));
const hits = dv.pages(`"${FOLDER}"`).where(p => p.file.name !== me && p.file.name.endsWith(mmdd) && /^\d{4}-/.test(p.file.name)).sort(p => p.file.name, "desc");
if (!hits.length) dv.paragraph("_往年的今天還沒有紀錄。留一個未來的你用得上的記號吧。_");
for (const p of hits) {
  const n = yr - Number(p.file.name.slice(0, 4));
  dv.header(4, `${n} 年前：${p.file.name}`);
  dv.paragraph(`![[${p.file.name}#${HEADING}]]`);
}
