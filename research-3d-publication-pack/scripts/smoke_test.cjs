// Real-browser smoke test: loads each page, records page errors, console errors/warnings,
// failed requests and HTTP >= 400, waits for WebGL/data, saves a screenshot per page.
// Exit code 1 if any page has a problem -- a worker's own "QA PASS" is not evidence.
//
// Setup once (any folder):  npm i playwright-core
// Usage: node smoke_test.cjs <baseUrl> <page1,page2,...> [outDir] [--ignore=favicon.ico]
//   node smoke_test.cjs http://127.0.0.1:8000 site/index.html,site/explorer.html?dataset=cgm shots
// Chrome path: CHROME env var, else the default Windows install.

const path = require('path');
const fs = require('fs');
const { chromium } = require('playwright-core');

const [base, list, outDir = 'smoke_shots', ...flags] = process.argv.slice(2);
if (!base || !list) {
  console.error('usage: node smoke_test.cjs <baseUrl> <comma-separated pages> [outDir] [--ignore=substr,...]');
  process.exit(2);
}
const ignore = (flags.find(f => f.startsWith('--ignore=')) || '--ignore=favicon.ico').slice(9).split(',');
const chrome = process.env.CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe';

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({
    executablePath: chrome,
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'], // WebGL without a GPU
  });
  let bad = 0;
  for (const p of list.split(',')) {
    const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
    const msgs = [];
    const keep = s => !ignore.some(i => i && s.includes(i));
    page.on('pageerror', e => msgs.push('PAGEERROR ' + e.message));
    page.on('console', m => {
      if (['error', 'warning'].includes(m.type())) {
        const loc = (m.location() || {}).url || '';
        const line = `${m.type().toUpperCase()} ${m.text()} ${loc}`;
        if (keep(line)) msgs.push(line);
      }
    });
    // HEAD probes are reported as ERR_ABORTED by Chrome even when they succeed
    page.on('requestfailed', r => { if (r.method() !== 'HEAD' && keep(r.url())) msgs.push('REQFAIL ' + r.url()); });
    page.on('response', r => { if (r.status() >= 400 && keep(r.url())) msgs.push(`HTTP${r.status()} ${r.url()}`); });
    try {
      await page.goto(base.replace(/\/$/, '') + '/' + p, { waitUntil: 'networkidle', timeout: 45000 });
    } catch (e) { msgs.push('GOTO ' + e.message); }
    await page.waitForTimeout(2500);
    const shot = path.join(outDir, p.replace(/[^a-zA-Z0-9]/g, '_') + '.png');
    await page.screenshot({ path: shot });
    if (msgs.length) bad++;
    console.log(`=== ${p} -> ${shot}\n${msgs.length ? msgs.join('\n') : '(no errors)'}`);
    await page.close();
  }
  await browser.close();
  console.log(bad ? `FAIL: ${bad} page(s) with problems` : 'PASS: all pages clean');
  process.exit(bad ? 1 : 0);
})();
