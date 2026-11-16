// 私有 Sites 路由的唯讀檢查；認證僅由隱藏 stdin 讀入，不寫檔或輸出。
process.stdout.write('Ready for route-check JSON on stdin (input is hidden).\n');
if (process.stdin.isTTY) process.stdin.setRawMode(true);
process.stdin.setEncoding('utf8');
const input = await new Promise((resolve, reject) => {
  let buffer = '';
  const receive = chunk => {
    if (chunk.includes('\u0003')) return reject(new Error('已取消'));
    buffer += chunk;
    if (/[\r\n]/.test(buffer)) {
      process.stdin.removeListener('data', receive);
      if (process.stdin.isTTY) process.stdin.setRawMode(false);
      process.stdin.pause();
      resolve(JSON.parse(buffer.split(/[\r\n]/)[0]));
    }
  };
  process.stdin.on('data', receive);
  process.stdin.resume();
});
const origin = 'https://voice2txt-independent.safecoconut4.chatgpt.site';
const results = [];
let appScript = null;
for (const path of ['/recording', '/recording.html', '/quality', '/quality.html', '/']) {
  const response = await fetch(origin + path, {
    headers: {'OAI-Sites-Authorization': 'Bearer ' + input.token},
    redirect: 'manual', signal: AbortSignal.timeout(25000),
  });
  const html = await response.text();
  results.push({path, status: response.status, type: response.headers.get('content-type'),
    location: response.headers.get('location'),
    title: html.match(/<title[^>]*>([^<]*)<\/title>/i)?.[1] || '',
    is_app: html.includes('id="record"'), login_gate: html.includes('signin-with-chatgpt'),
    recording_v4: html.includes('錄音流程修正 · v4'),
    record_disabled_in_html: /<button[^>]*id="record"[^>]*disabled/.test(html),
    script: html.match(/src="(\/app-[A-Z0-9]+\.js)"/)?.[1] || null});
  appScript ||= html.match(/src="(\/app-[A-Z0-9]+\.js)"/)?.[1];
}
const assets = ['/manifest-quality.webmanifest', '/sw.js'];
if (appScript) assets.push(appScript);
for (let index = 0; index < assets.length; index++) {
  const path = assets[index];
  const response = await fetch(origin + path, {headers: {'OAI-Sites-Authorization': 'Bearer ' + input.token}, redirect: 'manual', signal: AbortSignal.timeout(25000)});
  const text = await response.text();
  results.push({path, status: response.status, type: response.headers.get('content-type'), location: response.headers.get('location'), csp: response.headers.get('content-security-policy')});
  if (path === appScript) {
    const worker = text.match(/["'](\/worker-[A-Z0-9]+\.js)["']/)?.[1];
    if (worker) assets.push(worker);
  }
}
const wasm = await fetch(origin + '/vendor/ort-wasm-simd-threaded.jsep.wasm', {headers: {'OAI-Sites-Authorization': 'Bearer ' + input.token}, redirect: 'manual', signal: AbortSignal.timeout(25000)});
results.push({path: '/vendor/ort-wasm-simd-threaded.jsep.wasm', status: wasm.status, type: wasm.headers.get('content-type')});
await wasm.body?.cancel();
console.log(JSON.stringify(results));
