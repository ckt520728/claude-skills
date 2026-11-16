import {pipeline, env} from '@huggingface/transformers';
import {Converter} from 'opencc-js/cn2t';
import {MODELS, modelOptions} from './models.mjs';
import {hasSpeech} from './audio.mjs';

env.allowLocalModels = false;
env.useBrowserCache = true;
env.backends.onnx.wasm.numThreads = 1;
env.backends.onnx.wasm.proxy = false;
env.backends.onnx.wasm.wasmPaths = new URL('/vendor/', self.location.href).href;
const traditional = Converter({from: 'cn', to: 'twp'});
let recognizer = null;
let currentModel = '';
let working = false;
self.onmessage = async ({data}) => {
  if (working) return self.postMessage({type: 'error', message: '辨識引擎忙碌中。'});
  working = true;
  try {
    if (data.type === 'load') {
      const config = MODELS[data.model];
      if (!config) throw new Error('不支援的模型。');
      recognizer = await pipeline('automatic-speech-recognition', config.id, {
        ...modelOptions(data.model),
        progress_callback: progress => self.postMessage({type: 'progress', progress}),
      });
      currentModel = data.model;
      self.postMessage({type: 'ready', model: currentModel});
    } else if (data.type === 'transcribe') {
      if (!recognizer) throw new Error('請先下載並載入模型。');
      if (!['zh', 'en', 'translate'].includes(data.mode)) throw new Error('不支援的模式。');
      if (!hasSpeech(data.audio)) return self.postMessage({type: 'result', text: '', seconds: 0, model: currentModel});
      const started = performance.now();
      const output = await recognizer(data.audio, {
        language: data.mode === 'en' ? 'english' : 'chinese',
        task: data.mode === 'translate' ? 'translate' : 'transcribe',
        chunk_length_s: 30, stride_length_s: 5, return_timestamps: false,
        condition_on_prev_tokens: false,
      });
      let text = output.text.trim();
      if (data.mode === 'zh') text = traditional(text);
      self.postMessage({type: 'result', text, seconds: (performance.now() - started) / 1000, model: currentModel});
    }
  } catch (error) {
    self.postMessage({type: 'error', message: String(error.message || error)});
  } finally { working = false; }
};
