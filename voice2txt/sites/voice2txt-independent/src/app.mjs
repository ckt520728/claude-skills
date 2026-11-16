import {mono, downsample, hasSpeech, appendText, MAX_SECONDS} from './audio.mjs';
import {MODELS} from './models.mjs';
const $ = id => document.getElementById(id);
let worker = null, ready = false, loading = false, busy = false, starting = false;
let recorder = null, stream = null, chunks = [], timer = null, deadline = null;
let pending = null, modelTimer = null, initTimer = null;
let modelPhase = '尚未載入', lastModelError = '';
const completedModels = new Set();
let history = [];
const STORAGE = 'voice2txt-independent-v1';
function status(text) { $('status').textContent = text; }
function withTimeout(promise, ms, message) {
  let id; const limit = new Promise((_, reject) => { id = setTimeout(() => reject(new Error(message)), ms); });
  return Promise.race([promise, limit]).finally(() => clearTimeout(id));
}
// 離線解碼：不需要使用者手勢，也不會被 iOS 的音訊工作階段暫停卡住。
function decodeAudio(data) {
  const Offline = window.OfflineAudioContext || window.webkitOfflineAudioContext;
  // 直接解碼為 Whisper 的 16 kHz（瀏覽器內建重採樣品質較好）；不支援時退回 44.1 kHz 再自行降頻。
  let context;
  try { context = new Offline(1, 1, 16000); } catch { context = new Offline(1, 1, 44100); }
  return new Promise((resolve, reject) => {
    const result = context.decodeAudioData(data, resolve, error => reject(error || new Error('無法解碼這段音訊。')));
    if (result?.then) result.then(resolve, reject);
  });
}
function save() {
  try { localStorage.setItem(STORAGE, JSON.stringify({draft: $('text').value, history, model: $('model').value, accuracyVersion: 3})); }
  catch { $('storageStatus').textContent = '裝置儲存空間不足，請匯出文字；本次修改尚未保存。'; }
}
try {
  const saved = JSON.parse(localStorage.getItem(STORAGE) || '{}');
  $('text').value = typeof saved.draft === 'string' ? saved.draft : '';
  history = Array.isArray(saved.history) ? saved.history.slice(0, 20).filter(row => typeof row.text === 'string') : [];
  if (saved.accuracyVersion === 3 && Object.hasOwn(MODELS, saved.model)) $('model').value = saved.model;
} catch {}
function controls() {
  $('load').disabled = loading || busy || starting || !!recorder;
  $('model').disabled = loading || busy || starting || !!recorder;
  $('record').disabled = busy || starting;
  $('upload').disabled = busy || starting || !!recorder;
  $('mode').disabled = busy || starting || !!recorder;
  $('retry').disabled = !ready || busy || loading;
  $('cancel').hidden = !busy && !loading;
  $('load').textContent = ready ? '重新載入模型' : '下載／載入模型';
  $('engine').textContent = ready ? '此裝置 Whisper ' + MODELS[$('model').value].label + ' · WASM' : '尚未載入模型';
  $('saveAudio').hidden = !pending;
  $('diagnostic').textContent = JSON.stringify({version: 5, model: $('model').value, modelPhase,
    ready, loading, busy, recording: !!recorder, starting, lastModelError, secureContext: window.isSecureContext,
    microphoneAPI: !!navigator.mediaDevices?.getUserMedia, recorderAPI: !!window.MediaRecorder,
    wasmAPI: typeof WebAssembly !== 'undefined', browser: navigator.userAgent}, null, 2);
}
function showHistory() {
  $('history').replaceChildren();
  for (const item of history) {
    const row = document.createElement('button'); row.className = 'historyItem';
    row.textContent = new Date(item.at).toLocaleString('zh-TW') + ' · ' + item.text.slice(0, 60);
    row.onclick = () => { $('text').value = appendText($('text').value, item.text); save(); status('已將這筆紀錄加入編輯區。'); };
    $('history').append(row);
  }
  $('historyEmpty').hidden = history.length > 0;
}
function resetWorker() {
  if (worker) worker.terminate(); worker = null; ready = false; loading = false; busy = false;
  clearTimeout(modelTimer); clearTimeout(initTimer); initTimer = null; completedModels.clear();
  modelPhase = '尚未載入'; $('progress').hidden = true; controls();
}
function workerFailed(message) {
  const wasLoading = loading; resetWorker();
  modelPhase = '失敗'; lastModelError = String(message);
  status((wasLoading ? '模型載入失敗。' : '此裝置辨識失敗。') + '你仍可錄音；已錄音訊可匯出。請複製下方載入診斷。' + String(message).slice(0, 180));
  $('retryBox').hidden = !pending;
  controls();
}
function createWorker() {
  worker = new Worker(__WORKER_URL__, {type: 'module'});
  worker.onerror = event => workerFailed(event.message || '背景辨識引擎無法啟動。');
  worker.onmessage = ({data}) => {
    if (data.type === 'progress') {
      const p = data.progress;
      if (p.status === 'progress') {
        $('progress').hidden = false; $('progress').value = Number.isFinite(p.progress) ? p.progress : 0;
        status('正在準備模型：' + p.file + (Number.isFinite(p.progress) ? ' · ' + Math.round(p.progress) + '%' : ''));
      } else if (p.status === 'done') {
        status('模型檔案已備妥；仍在下載其餘檔案或建立本機辨識引擎。你可以先錄音。');
        if (p.file?.endsWith('.onnx')) completedModels.add(p.file);
        if (completedModels.size >= 2 && !initTimer) {
          modelPhase = '下載已完成，初始化中';
          initTimer = setTimeout(() => workerFailed('模型檔案已完成，但初始化超過 2 分鐘；尚未能在此裝置建立辨識引擎。'), 120000);
        }
        controls();
      }
    } else if (data.type === 'ready') {
      clearTimeout(modelTimer); clearTimeout(initTimer); loading = false; ready = true;
      modelPhase = '已就緒'; lastModelError = ''; $('progress').hidden = true; controls();
      status('模型已載入這台裝置。現在可以錄音，Windows 桌機可以關機。');
      save();
      navigator.storage?.persist?.().catch(() => {});
      if (pending && !recorder && !starting) transcribe();
    } else if (data.type === 'result') {
      busy = false;
      $('text').value = appendText($('text').value, data.text);
      if (data.text) { history.unshift({at: Date.now(), text: data.text, mode: pending?.mode || 'zh'}); history = history.slice(0, 20); }
      pending = null; $('retryBox').hidden = true;
      status(data.text ? '本機轉錄完成 · ' + data.seconds.toFixed(1) + ' 秒。' + (history[0]?.mode === 'translate' ? '試驗譯文，請逐句核對。' : '可編輯、複製或分享。') : '沒有辨識到語音，請靠近麥克風再試一次。');
      controls(); save(); showHistory();
    } else if (data.type === 'error') workerFailed(data.message);
  };
}
$('load').onclick = () => {
  resetWorker(); loading = true; modelPhase = '下載或讀取快取中'; lastModelError = ''; controls();
  status('首次需要下載模型；之後會優先使用這台裝置的快取。請保持畫面開啟。');
  try {
    createWorker(); worker.postMessage({type: 'load', model: $('model').value});
    modelTimer = setTimeout(() => workerFailed('下載等待超過 10 分鐘，可稍後重試。'), 600000);
  } catch (error) { workerFailed(error.message); }
};
$('model').onchange = () => { resetWorker(); status('已選擇 ' + $('model').value + '，請按「下載／載入模型」。'); save(); };
$('cancel').onclick = () => { resetWorker(); $('retryBox').hidden = !pending; status('已停止處理。請重新載入模型；待轉錄的錄音仍暫存在此頁。'); };
function releaseMic() {
  clearInterval(timer); clearTimeout(deadline);
  stream?.getTracks().forEach(track => track.stop()); stream = null;
  $('record').classList.remove('live'); $('recordLabel').textContent = '開始錄音'; $('timer').textContent = '每段最多 90 秒';
}
function stop() { if (recorder?.state === 'recording') recorder.stop(); }
$('record').onclick = async () => {
  if (recorder) return stop();
  if (starting || busy) return;
  if (pending && !confirm('上一段尚未完成轉錄。開始新錄音會取代它，確定繼續？')) return;
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) return status('此瀏覽器無法錄音。請使用 Safari／Chrome／Edge，或選擇音訊檔。');
  starting = true; controls(); status('正在啟用麥克風，請留意 Safari 的麥克風許可提示。');
  try {
    // v5：錄音不再等待 AudioContext.resume()。沒有使用者手勢時 resume() 會永遠不回應，
    // 頁面會卡在「正在啟用麥克風」。解碼改用 OfflineAudioContext，不需要可播放的音訊環境。
    stream = await withTimeout(navigator.mediaDevices.getUserMedia({audio: true}), 60000,
      '麥克風在 60 秒內沒有回應。請確認已允許麥克風，或關閉其他使用麥克風的 App 後再試。');
    if (document.hidden) throw new Error('請保持此頁開啟後再開始錄音。');
    const mimeType = ['audio/mp4', 'audio/webm;codecs=opus', 'audio/webm'].find(type => MediaRecorder.isTypeSupported(type));
    recorder = new MediaRecorder(stream, {audioBitsPerSecond: 128000, ...(mimeType ? {mimeType} : {})});
    chunks = []; const mode = $('mode').value;
    recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
    recorder.onerror = () => { status('錄音中斷，將嘗試處理已收到的音訊。'); stop(); releaseMic(); };
    recorder.onstop = () => {
      const mime = recorder.mimeType; recorder = null; releaseMic();
      pending = {blob: new Blob(chunks, {type: mime}), mode}; chunks = [];
      transcribe();
    };
    recorder.start(); const began = Date.now();
    $('record').classList.add('live'); $('recordLabel').textContent = '停止並轉錄'; status('錄音中。這段錄音只會在目前裝置處理。模型尚未就緒時，停止後會先暫存錄音。');
    timer = setInterval(() => { $('timer').textContent = Math.floor((Date.now() - began) / 1000) + ' / 90 秒'; }, 250);
    deadline = setTimeout(stop, MAX_SECONDS * 1000);
  } catch (error) { recorder = null; releaseMic(); status(error.name === 'NotAllowedError' ? '請允許此網站使用麥克風，再試一次。' : error.message); }
  finally { starting = false; controls(); }
};
async function transcribe() {
  if (!pending || busy) return;
  if (!ready) {
    $('retryBox').hidden = false; controls();
    status('錄音已暫存在此頁，模型尚未就緒。可繼續等待或載入模型；也可先匯出錄音。請勿關閉此頁。');
    return;
  }
  busy = true; controls(); $('retryBox').hidden = true;
  status('正在這台裝置上解碼與辨識，音訊不會上傳。手機可能需要較長時間。');
  try {
    const decoded = await withTimeout(decodeAudio(await pending.blob.arrayBuffer()), 30000, '音訊解碼超過 30 秒，請改用較短的錄音或匯出後改用檔案。');
    if (decoded.duration > MAX_SECONDS + 1) throw new Error('請使用 90 秒以內的音訊，避免手機記憶體不足。');
    const channels = Array.from({length: decoded.numberOfChannels}, (_, i) => decoded.getChannelData(i));
    const audio = downsample(mono(channels), decoded.sampleRate);
    if (!hasSpeech(audio)) { busy = false; pending = null; controls(); return status('音訊太短或沒有偵測到語音。'); }
    // 保留 Blob，轉移 PCM 後若失敗仍可重試。
    if (!ready || !worker) throw new Error('辨識已取消。請重新載入模型。');
    worker.postMessage({type: 'transcribe', audio, mode: pending.mode}, [audio.buffer]);
  } catch (error) { busy = false; controls(); $('retryBox').hidden = !pending; status(error.message || '此裝置無法讀取音訊，請改用 Safari 錄製。'); }
}
$('retry').onclick = transcribe;
$('saveAudio').onclick = () => {
  if (!pending) return;
  const blob = pending.blob;
  const extension = blob.type.includes('mp4') ? 'm4a' : blob.type.includes('webm') ? 'webm' : blob.type.includes('wav') ? 'wav' : 'bin';
  const url = URL.createObjectURL(blob), link = document.createElement('a');
  link.href = url; link.download = 'Voice2Txt-recording.' + extension;
  document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 60000);
};
$('copyDiagnostic').onclick = async () => {
  try { await navigator.clipboard.writeText($('diagnostic').textContent); status('載入診斷已複製，不含錄音或轉錄文字。'); }
  catch { status('請展開「載入診斷」，手動選取並複製內容。'); }
};
$('upload').onchange = () => {
  const file = $('upload').files[0]; if (!file) return;
  $('upload').value = '';
  if (file.size > 15 * 1024 * 1024) return status('音訊檔請小於 15 MB，且在 90 秒以內。');
  if (pending && !confirm('這會取代尚未完成轉錄的錄音，確定繼續？')) return;
  pending = {blob: file, mode: $('mode').value}; transcribe();
};
$('text').oninput = save;
$('copy').onclick = async () => { try { await navigator.clipboard.writeText($('text').value); status('文字已複製。'); } catch { $('text').focus(); $('text').select(); status('請長按已選取的文字，再點「複製」。'); } };
$('share').onclick = async () => { if (!navigator.share) return $('copy').click(); try { await navigator.share({text: $('text').value}); } catch (error) { if (error.name !== 'AbortError') status('無法分享，請改用複製或匯出。'); } };
$('download').onclick = () => {
  const url = URL.createObjectURL(new Blob([$('text').value], {type: 'text/plain;charset=utf-8'}));
  const link = document.createElement('a'); link.href = url; link.download = 'Voice2Txt.txt'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 10000);
};
document.addEventListener('visibilitychange', () => { if (document.hidden && recorder) stop(); });
window.addEventListener('beforeunload', event => { if (pending || recorder || busy) { event.preventDefault(); event.returnValue = ''; } });
function networkStatus() { $('network').textContent = navigator.onLine ? '可連網下載模型' : '目前離線'; }
addEventListener('online', networkStatus); addEventListener('offline', networkStatus); networkStatus();
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js', {updateViaCache: 'none'}).then(async registration => {
    registration.update().catch(() => {});
    await navigator.serviceWorker.ready;
  }).then(() => {
    $('offlineStatus').textContent = '頁面已快取。模型載入完成後，可嘗試開啟飛航模式驗證離線轉錄。';
  }).catch(() => { $('offlineStatus').textContent = '頁面離線快取失敗；本機轉錄仍可用，但離線重開尚未準備好。'; });
}
showHistory(); controls();
