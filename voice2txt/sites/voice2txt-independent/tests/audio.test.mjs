import test from 'node:test';
import assert from 'node:assert/strict';
import {downsample, mono, hasSpeech, appendText} from '../src/audio.mjs';

test('48 kHz 音訊轉成 16 kHz 並保留正確長度與常數訊號', () => {
  const result = downsample(new Float32Array(48000).fill(0.25), 48000);
  assert.equal(result.length, 16000);
  assert.ok(result.every(sample => sample === 0.25));
});
test('44.1 kHz 非整數比例不會遺失尾端', () => {
  const audio = new Float32Array(44101).fill(0.1);
  const result = downsample(audio, 44100);
  assert.equal(result.length, 16001);
  assert.ok(result.every(Number.isFinite));
});
test('雙聲道平均，單聲道不改動樣本', () => {
  assert.deepEqual(Array.from(mono([new Float32Array([1, 0]), new Float32Array([-1, 1])])), [0, 0.5]);
  assert.deepEqual(Array.from(mono([new Float32Array([0.2])])), Array.from(new Float32Array([0.2])));
});
test('拒絕無效取樣率，純靜音與過短樣本不送入模型', () => {
  assert.throws(() => downsample(new Float32Array(100), 0));
  assert.equal(hasSpeech(new Float32Array(16000)), false);
  assert.equal(hasSpeech(new Float32Array(100).fill(0.5)), false);
  assert.equal(hasSpeech(new Float32Array(16000).fill(0.1)), true);
});
test('新段落不覆蓋已有或手動修改的內容，空結果不新增行', () => {
  assert.equal(appendText('已修改的文字', ' 新段落 '), '已修改的文字\n新段落');
  assert.equal(appendText('已修改的文字', '  '), '已修改的文字');
});
