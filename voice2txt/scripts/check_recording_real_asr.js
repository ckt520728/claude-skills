async page => {
  await page.goto('http://127.0.0.1:8787/recording.html');
  await page.getByLabel('語音模型').selectOption('tiny');
  if (!(await page.locator('#record').isEnabled())) throw new Error('模型尚未載入時按鈕再次被鎖住。');
  await page.locator('input[type=file]').setInputFiles('D:/2026 Voice2Txt/tests/fixtures/quality-meeting.wav');
  await page.waitForFunction(() => document.getElementById('status').textContent.includes('錄音已暫存'));
  await page.getByRole('button', {name: '下載／載入模型', exact: true}).click();
  await page.waitForFunction(() => document.getElementById('status').textContent.includes('本機轉錄完成'), null, {timeout: 180000});
  const text = await page.getByRole('textbox', {name: '可編輯的轉錄文字'}).inputValue();
  if (!text.trim()) throw new Error('真實 Whisper 未產生轉錄。');
  return {pass: true, model: 'tiny q8 WASM', audio: 'synthetic Chinese fixture selected before model load', text, pipeline: 'actual browser Whisper; microphone not exercised'};
}
