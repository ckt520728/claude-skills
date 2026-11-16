'use strict';
const $ = id => document.getElementById(id);
let token = '', recorder = null, stream = null, chunks = [], pending = null;
let busy = false, connected = false, starting = false, started = 0, clock = null, deadline = null;
function message(text) { $('status').textContent = text; }
function controls() {
  $('record').disabled = busy || starting || !connected;
  $('upload').disabled = busy || starting || !!recorder || !connected;
  $('mode').disabled = busy || starting || !!recorder;
  $('refine').disabled = busy || starting || !!recorder;
  $('retry').disabled = busy;
}
function saveToken(value) { token = value; try { localStorage.setItem('voice2txt-pairing', value); } catch {} }
try { token = localStorage.getItem('voice2txt-pairing') || ''; } catch {}
const fromLink = new URLSearchParams(location.hash.slice(1)).get('key');
if (fromLink) saveToken(fromLink);
// 配對碼只在 fragment 與此裝置儲存，從網址列移除以免分享時意外洩漏。
if (location.hash) history.replaceState(null, '', location.pathname);
window.addEventListener('hashchange', () => {
  const value = new URLSearchParams(location.hash.slice(1)).get('key');
  if (value) { saveToken(value); history.replaceState(null, '', location.pathname); check(); }
});
async function check() {
  try {
    const res = await fetch('/api/status', {headers: {Authorization: 'Bearer ' + token}, signal: AbortSignal.timeout(12000)});
    if (!res.ok) throw new Error(res.status === 401 ? '請貼上配對碼或電腦提供的完整連結。' : '桌機暫時無法連線。');
    connected = true; $('pairing').hidden = true; message('桌機已連線，可以開始錄音。');
  } catch (error) { connected = false; $('pairing').hidden = false; message(error.message || '連線失敗。'); }
  controls();
}
$('pair').onclick = () => {
  let value = $('key').value.trim();
  try { if (value.startsWith('https://') || value.startsWith('http://')) value = new URLSearchParams(new URL(value).hash.slice(1)).get('key') || ''; } catch {}
  saveToken(value); $('key').value = ''; check();
};
function releaseMic() {
  clearInterval(clock); clearTimeout(deadline); clock = deadline = null;
  if (stream) stream.getTracks().forEach(track => track.stop());
  stream = null; $('record').classList.remove('live');
  $('recordLabel').textContent = '開始錄音'; $('timer').textContent = '每段最多 90 秒';
}
function stop() { if (recorder?.state === 'recording') recorder.stop(); }
async function start() {
  if (starting || busy) return;
  if (recorder) return stop();
  if (pending && !confirm('尚有未成功轉錄的錄音。開始新錄音會捨棄上一段，確定繼續？')) return;
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) return message('此瀏覽器無法錄音。請用 Safari 開啟 HTTPS 連結，或選擇音訊檔。');
  starting = true; controls();
  try {
    stream = await navigator.mediaDevices.getUserMedia({audio: true});
    if (document.hidden) throw new Error('請回到此頁後再開始錄音。');
    const mimeType = ['audio/mp4', 'audio/webm;codecs=opus', 'audio/webm'].find(type => MediaRecorder.isTypeSupported(type));
    recorder = new MediaRecorder(stream, mimeType ? {mimeType} : {});
    chunks = []; pending = null; $('retryBox').hidden = true;
    const mode = $('mode').value, refine = $('refine').checked;
    recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
    recorder.onerror = () => { message('錄音發生錯誤，請重新錄製。'); stop(); releaseMic(); };
    recorder.onstop = () => {
      const mime = recorder.mimeType; recorder = null;
      releaseMic(); pending = {blob: new Blob(chunks, {type: mime}), mode, refine}; chunks = [];
      send();
    };
    recorder.start(); started = Date.now();
    $('record').classList.add('live'); $('recordLabel').textContent = '停止並轉錄';
    message('錄音中，請保持畫面開啟。');
    clock = setInterval(() => { $('timer').textContent = Math.floor((Date.now() - started) / 1000) + ' / 90 秒'; }, 250);
    deadline = setTimeout(stop, 90000);
  } catch (error) {
    recorder = null; releaseMic();
    message(error.name === 'NotAllowedError' ? '尚未允許麥克風。請在 Safari 允許本網站使用麥克風，再試一次。' : error.message);
  } finally { starting = false; controls(); }
}
async function send() {
  if (!pending || busy) return;
  busy = true; controls(); $('retryBox').hidden = true;
  message('正在上傳並轉錄，請保持畫面開啟…');
  const request = pending;
  try {
    const res = await fetch('/api/transcribe?mode=' + request.mode + '&refine=' + Number(request.refine), {
      method: 'POST', headers: {Authorization: 'Bearer ' + token, 'Content-Type': request.blob.type || 'application/octet-stream'},
      body: request.blob, signal: AbortSignal.timeout(180000)
    });
    let data; try { data = await res.json(); } catch { throw new Error('桌機連線中斷，請稍後重試。'); }
    if (!res.ok) throw new Error(data.error || '轉錄失敗。');
    const separator = $('text').value.trim() ? '\n' : '';
    $('text').value += separator + data.text;
    $('source').textContent = data.source || ''; $('sourceBox').hidden = !data.source;
    $('backend').textContent = '處理引擎：' + data.backend;
    pending = null;
    message(data.warning || (data.text ? '轉錄完成，可修改、複製或分享。' : '沒有辨識到語音，請靠近麥克風再試一次。'));
  } catch (error) { message(error.name === 'TimeoutError' ? '轉錄等待逾時，請稍後重試。' : (error.message || '無法連線桌機。')); $('retryBox').hidden = false; }
  finally { busy = false; controls(); }
}
$('record').onclick = start;
$('retry').onclick = send;
$('upload').onchange = () => {
  const file = $('upload').files[0]; if (!file) return;
  if (file.size > 15 * 1024 * 1024) { message('檔案超過 15 MB，請選較短的音訊。'); $('upload').value = ''; return; }
  if (pending && !confirm('這會取代尚未成功轉錄的錄音，確定繼續？')) { $('upload').value = ''; return; }
  pending = {blob: file, mode: $('mode').value, refine: $('refine').checked}; $('upload').value = ''; send();
};
$('copy').onclick = async () => { try { await navigator.clipboard.writeText($('text').value); message('文字已複製。'); } catch { $('text').focus(); $('text').select(); message('請長按選取的文字，再點「複製」。'); } };
$('share').onclick = async () => { if (!navigator.share) return $('copy').click(); try { await navigator.share({text: $('text').value}); } catch (error) { if (error.name !== 'AbortError') message('無法分享，請改用複製文字。'); } };
$('download').onclick = () => { const url = URL.createObjectURL(new Blob([$('text').value], {type: 'text/plain;charset=utf-8'})); const link = document.createElement('a'); link.href = url; link.download = 'Voice2Txt.txt'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 10000); };
document.addEventListener('visibilitychange', () => { if (document.hidden && recorder) stop(); });
window.addEventListener('beforeunload', event => { if (recorder || pending || busy || $('text').value) { event.preventDefault(); event.returnValue = ''; } });
check();
