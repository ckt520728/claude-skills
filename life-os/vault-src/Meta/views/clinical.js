// Life OS clinical load: numbers only (clinical_access: derived).
// nightly.js counts pending cases inside Obsidian and writes two scalars to frontmatter.
// This view reads those scalars and nothing else. It never opens the ## 🏥 臨床 text.
// Usage: await dv.view("Life OS/Meta/views/clinical", { days: 7 })
const cfg = dv.page("Life OS/Meta/Compass Config") || {};
const FOLDER = cfg.daily_folder || cfg.daily_note_folder || "每日筆記";
const DAYS = (input && input.days) || 7;
const names = new Set([...Array(DAYS).keys()].map(i => moment().subtract(i, "days").format("YYYY-MM-DD")));
const rows = dv.pages(`"${FOLDER}"`).where(p => names.has(p.file.name) && typeof p.clinical_pending === "number")
  .sort(p => p.file.name, "desc").array()
  .map(p => [p.file.link, `${p.clinical_pending} 例`, typeof p.clinical_load === "number" ? "▮".repeat(p.clinical_load) + "▯".repeat(5 - p.clinical_load) : "—"]);
if (rows.length) {
  dv.table(["日期", "待處理", "負荷"], rows);
  dv.paragraph("_負荷重的日子分數低是解釋，不是失敗。這一欄的用途是歸因。_");
} else {
  dv.paragraph("_近幾天沒有臨床負荷數字（夜間評分時若 🏥 臨床 區塊有列個案，會自動算出數字）。_");
}
