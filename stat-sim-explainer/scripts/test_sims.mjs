// Headless test harness for stat-sim-explainer pages.
// Usage: node test_sims.mjs <page.html> [tests.js]
// Evaluates the FIRST plain <script> block (pure sim functions, no DOM), then the tests file.
// Without a tests file it only checks that script 1 parses and runs.
import { readFileSync } from "node:fs";
const [page, tests] = process.argv.slice(2);
if (!page) { console.error("usage: node test_sims.mjs <page.html> [tests.js]"); process.exit(2); }
const html = readFileSync(page, "utf8");
const blocks = html.split("<script>").slice(1).map(b => b.split("</script>")[0]);
if (!blocks.length) { console.error("no plain <script> block found"); process.exit(1); }
if (/document\.|window\./.test(blocks[0])) console.warn("warning: script 1 touches the DOM; keep it pure");
const code = blocks[0] + "\n" + (tests ? readFileSync(tests, "utf8") : 'console.log("script 1 OK");');
const t0 = Date.now();
(0, eval)(code);
console.log(`done in ${Date.now() - t0} ms`);
