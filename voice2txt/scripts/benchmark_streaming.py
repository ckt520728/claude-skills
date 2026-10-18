"""以 100 ms 音訊區塊重播固定語料，驗證分段後的真實推論。"""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from faster_whisper.audio import decode_audio
from voice2txt.core import Chunker, WhisperEngine

parser = argparse.ArgumentParser()
parser.add_argument('--model', default='medium')
parser.add_argument('--device', default='cuda', choices=['cpu', 'cuda'])
args = parser.parse_args()
audio = np.concatenate([np.concatenate((decode_audio(f'tests/fixtures/quality-{case}.wav', sampling_rate=16000),
                                        np.zeros(16000, dtype=np.float32)))
                        for case in ('meeting', 'negation', 'hospital')])
chunker = Chunker(seconds=8, silence_seconds=0.5)
engine = WhisperEngine(args.model, device=args.device)
report = {'model': args.model, 'device': args.device, 'input_seconds': len(audio) / 16000,
          'scope': '固定合成語料以 100 ms 區塊加速重播，非真人麥克風或實際長時間錄音', 'chunks': []}
processed = []


def decode(chunk, available_at):
    processed.append(chunk)
    start = time.monotonic()
    text = engine.transcribe(chunk, 'translate')
    elapsed = time.monotonic() - start
    report['chunks'].append({'samples': len(chunk), 'available_at_audio_seconds': available_at,
                            'inference_seconds': elapsed, 'text': text})


for offset in range(0, len(audio), 1600):
    block = audio[offset:offset + 1600]
    for chunk in chunker.feed(block):
        decode(chunk, (offset + len(block)) / 16000)
for chunk in chunker.flush():
    decode(chunk, len(audio) / 16000)
np.testing.assert_array_equal(np.concatenate(processed), audio)
report['samples_preserved'] = True
Path(f'verification/streaming-{args.model}-{args.device}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
