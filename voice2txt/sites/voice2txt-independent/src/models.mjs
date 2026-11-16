export const MODELS = {
  tiny: {id: 'onnx-community/whisper-tiny', revision: 'ff4177021cc41f7db950912b73ea4fdf7d01d8e7', label: 'tiny 省記憶體版', dtype: 'q8'},
  base: {id: 'onnx-community/whisper-base', revision: '27a07b4b52b3a4c5886134bb4320e93e1a4bbc7c', label: 'base 標準版', dtype: 'q8'},
  small: {id: 'onnx-community/whisper-small', revision: '36050c46d777d46dc4b5f43f6d90574fc38f8732', label: 'small 準確度優先版', dtype: 'q8'},
};

export function modelOptions(key) {
  if (!Object.hasOwn(MODELS, key)) throw new Error('不支援的模型。');
  const config = MODELS[key];
  return {revision: config.revision, device: 'wasm', dtype: config.dtype};
}
