"""使用公開音訊測量實際本機推論；不以 mock 取代語音引擎。"""
import json
import time
from pathlib import Path

from faster_whisper.audio import decode_audio
from voice2txt.core import WhisperEngine

fixture = Path('tests/fixtures/jfk.wav')
audio = decode_audio(str(fixture), sampling_rate=16000)
started = time.monotonic()
engine = WhisperEngine('base')
loaded = time.monotonic()
text = engine.transcribe(audio, 'en')
finished = time.monotonic()
assert 'country' in text.lower() and 'ask' in text.lower(), text
report = {
    'fixture': 'https://github.com/ggml-org/whisper.cpp/blob/master/samples/jfk.wav',
    'model': 'base', 'device': 'cpu', 'compute_type': 'int8',
    'audio_seconds': len(audio) / 16000,
    'load_seconds': round(loaded - started, 3),
    'inference_seconds': round(finished - loaded, 3), 'text': text,
    'scope': '公開英文音訊的實際推論；不證明中文準確度或即時麥克風品質',
}
Path('verification').mkdir(exist_ok=True)
Path('verification/english-inference.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
