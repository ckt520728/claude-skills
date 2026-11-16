// 供 Playwright CLI run-code 使用；只上傳已知合成測試音訊到本機瀏覽器，沒有辨識伺服器。
async page => {
  const target = 'current';
  if (target !== 'current') {
    await page.getByLabel('語音模型').selectOption(target);
    await page.getByRole('button', {name: '下載／載入模型', exact: true}).click();
  }
  await page.waitForFunction(() => !document.getElementById('record').disabled, null, {timeout: 180000});
  const cases = [
    {id: 'meeting', mode: 'zh', reference: '今天下午四點開會，請記得帶研究報告。'},
    {id: 'negation', mode: 'zh', reference: '請不要在星期五開會。報告有三份，不是四份。'},
    {id: 'hospital', mode: 'zh', reference: '我明天上午九點到醫院，下午兩點回家。'},
    {id: 'english', mode: 'en', reference: 'The meeting starts at four in the afternoon. Please bring the research report.'},
    {id: 'negation-en', file: 'accuracy-negation-en.wav', mode: 'en', reference: 'Do not start the medicine today. The appointment is next Thursday, November nineteenth, at nine thirty.'},
    {id: 'renal-en', file: 'accuracy-renal-en.wav', mode: 'en', reference: 'The creatinine concentration increased from one point two to one point eight milligrams per deciliter.'},
    {id: 'diagnoses-en', file: 'accuracy-diagnoses-en.wav', mode: 'en', reference: 'The patient has chronic kidney disease and type two diabetes, but no history of heart failure.'},
  ];
  const results = [];
  for (const sample of cases) {
    await page.getByLabel('辨識模式').selectOption(sample.mode);
    await page.getByRole('textbox', {name: '可編輯的轉錄文字'}).fill('');
    const started = Date.now();
    await page.locator('input[type=file]').setInputFiles('D:/2026 Voice2Txt/tests/fixtures/' + (sample.file || 'quality-' + sample.id + '.wav'));
    await page.waitForFunction(() => {
      const text = document.getElementById('status').textContent;
      return text.includes('本機轉錄完成') || text.includes('辨識失敗') || text.includes('音訊太短');
    }, null, {timeout: 180000});
    results.push({...sample, output: await page.getByRole('textbox', {name: '可編輯的轉錄文字'}).inputValue(),
      wall_seconds: (Date.now() - started) / 1000, status: await page.locator('#status').textContent()});
  }
  return {model: await page.getByLabel('語音模型').inputValue(), model_label: await page.getByLabel('語音模型').locator('option:checked').textContent(), cases: results};
}
