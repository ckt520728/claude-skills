"""固定合成語料的品質與速度比較；關鍵詞檢查不等同完整語意評分。"""
import argparse
import json
import os
from pathlib import Path
import time

parser = argparse.ArgumentParser()
parser.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
parser.add_argument('--model', default='small')
args = parser.parse_args()

import numpy as np
from faster_whisper.audio import decode_audio
from voice2txt.core import WhisperEngine

engine = WhisperEngine(args.model, device=args.device)
report = {'model': args.model, 'device': args.device, 'cases': [],
          'scope': 'Windows 合成語音；關鍵詞檢查不證明完整語意、真人音訊或一般準確度'}
for case in json.loads(Path('tests/fixtures/quality-corpus.json').read_text(encoding='utf-8')):
    audio = decode_audio('tests/fixtures/quality-' + case['id'] + '.wav', sampling_rate=16000)
    mode = 'en' if case['language'] == 'en' else 'translate'
    started = time.monotonic()
    text = engine.transcribe(audio, mode)
    seconds = time.monotonic() - started
    source_text = engine.transcribe(audio, 'zh') if case['language'] == 'zh' else ''
    checks = [any(word in text.lower() for word in alternatives) for alternatives in case['expected_english']]
    report['cases'].append({'id': case['id'], 'input': case['text'], 'text': text, 'source_transcript': source_text,
                            'audio_seconds': len(audio) / 16000, 'inference_seconds': seconds,
                            'keyword_checks': checks, 'keyword_checks_passed': all(checks)})
    print(case['id'], round(seconds, 2), text, flush=True)
Path(f'verification/quality-{args.model}-{args.device}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
