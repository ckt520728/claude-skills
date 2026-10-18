"""Whisper 音訊 → 繁體原文 → 本機 LLM 英譯的端到端測試。"""
import json
from pathlib import Path
import time

from faster_whisper.audio import decode_audio
from voice2txt.core import WhisperEngine
from voice2txt.translation import LocalTranslator, decode_segment

engine = WhisperEngine('small', device='cpu')
translator = LocalTranslator('gemma4:latest')
started = time.monotonic()
translator.prepare()
report = {'whisper_model': 'small', 'device': 'cpu', 'llm_model': translator.model,
          'prepare_seconds': time.monotonic() - started,
          'scope': '固定合成音訊的端到端測試；不代表真人或一般準確度', 'cases': []}
for case in json.loads(Path('tests/fixtures/quality-corpus.json').read_text(encoding='utf-8')):
    if case['language'] != 'zh':
        continue
    audio = decode_audio(f'tests/fixtures/quality-{case["id"]}.wav', sampling_rate=16000)
    started = time.monotonic()
    result = decode_segment(engine, audio, 'translate', translator=translator)
    entry = {'id': case['id'], 'input': case['text'], 'source': result.source, 'text': result.text,
             'error': result.error, 'seconds': time.monotonic() - started,
             'keyword_checks_passed': all(any(word in result.text.lower() for word in group) for group in case['expected_english'])}
    report['cases'].append(entry)
    print(entry, flush=True)
Path('verification/pipeline-small-ollama.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
