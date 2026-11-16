export const SAMPLE_RATE = 16000;
export const MAX_SECONDS = 90;

export function mono(channels) {
  if (!channels.length) throw new Error('音訊沒有聲道。');
  const output = new Float32Array(channels[0].length);
  for (const channel of channels) {
    for (let i = 0; i < output.length; i++) output[i] += channel[i] / channels.length;
  }
  return output;
}

export function downsample(audio, rate) {
  if (!Number.isFinite(rate) || rate <= 0) throw new Error('取樣率無效。');
  const ratio = rate / SAMPLE_RATE;
  if (ratio === 1) return audio.slice();
  const output = new Float32Array(Math.ceil(audio.length / ratio));
  for (let i = 0; i < output.length; i++) {
    const start = Math.floor(i * ratio), end = Math.min(audio.length, Math.max(start + 1, Math.floor((i + 1) * ratio)));
    let sum = 0;
    for (let j = start; j < end; j++) sum += audio[j];
    output[i] = sum / (end - start);
  }
  return output;
}

export function hasSpeech(audio) {
  if (audio.length < SAMPLE_RATE / 5) return false;
  let energy = 0;
  for (const sample of audio) energy += sample * sample;
  return Math.sqrt(energy / audio.length) >= 0.002;
}

export function appendText(current, addition) {
  const next = addition.trim();
  return next ? current + (current.trim() ? '\n' : '') + next : current;
}
