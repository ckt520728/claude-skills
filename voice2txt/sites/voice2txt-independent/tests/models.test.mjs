import test from 'node:test';
import assert from 'node:assert/strict';
import {MODELS, modelOptions} from '../src/models.mjs';

test('準確度優先模式必須載入真正的多語 small；所有模型版本固定且在本機執行', () => {
  assert.equal(MODELS.small.id, 'onnx-community/whisper-small');
  assert.equal(modelOptions('small').dtype, 'q8');
  for (const profile of Object.keys(MODELS)) {
    const options = modelOptions(profile);
    assert.equal(options.device, 'wasm');
    assert.match(options.revision, /^[a-f0-9]{40}$/);
  }
});
test('平衡模式保留 q8；無效模型不得默默降級', () => {
  assert.equal(modelOptions('tiny').dtype, 'q8');
  assert.equal(modelOptions('base').dtype, 'q8');
  assert.throws(() => modelOptions('unknown'));
  assert.throws(() => modelOptions('__proto__'));
});
