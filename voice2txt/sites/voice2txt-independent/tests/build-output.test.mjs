import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

test('新版入口使用具雜湊的程式路徑，避免舊 PWA 快取重新執行舊 q8 引擎', async () => {
  const html = await readFile('dist/quality.html', 'utf8');
  assert.match(html, /src="\/app-[A-Z0-9]+\.js"/);
  assert.doesNotMatch(html, /src="\/app\.js"/);
  assert.match(html, /value="small" selected/);
  const manifest = JSON.parse(await readFile('dist/manifest-quality.webmanifest', 'utf8'));
  assert.equal(manifest.start_url, '/recording.html');
  const scriptPath = html.match(/src="(\/app-[A-Z0-9]+\.js)"/)[1];
  const app = await readFile('dist' + scriptPath, 'utf8');
  assert.match(app, /\/worker-[A-Z0-9]+\.js/);
  const worker = await readFile('dist/sw.js', 'utf8');
  assert.match(worker, /request.mode==='navigate'/);
  assert.match(worker, /cache:'reload'/);
});
