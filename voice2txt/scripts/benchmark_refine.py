"""比較「僅 Whisper」與「Whisper + LLM 整理」：含贅詞、重複、口誤更正的合成語音。

每段只跑一次 Whisper，再把同一份原始轉錄交給各 LLM，結果可直接比較。
雲端 LLM 的 API key 讀取 OPENAI_API_KEY／GEMINI_API_KEY；沒有就略過。
"""
import json
import os
import sys
import time
from pathlib import Path

from faster_whisper.audio import decode_audio
from voice2txt.core import WhisperEngine
from voice2txt.translation import CLOUD, CloudTranslator, LocalTranslator

root = Path(__file__).resolve().parent.parent
model = sys.argv[1] if len(sys.argv) > 1 else 'small'
engine = WhisperEngine(model, device='cpu')
backends = {}
local = LocalTranslator('gemma4:latest')
try:
    local.prepare()
    backends[local.name] = local
except Exception as error:
    print('skip Ollama:', error)
for provider, (_, effort) in CLOUD.items():
    key = os.environ.get(provider.upper() + '_API_KEY', '')
    if key:
        cloud = CloudTranslator(provider, '', key, effort)
        backends[cloud.name] = cloud


def check(text, present, absent):
    lower = text.lower()
    missing = [group[0] for group in present if not any(word.lower() in lower for word in group)]
    leftover = [word for word in absent if word.lower() in lower]
    return {'passed': not missing and not leftover, 'missing': missing, 'leftover': leftover}


report = {'whisper_model': model, 'device': 'cpu', 'backends': list(backends),
          'scope': 'Windows TTS 合成的含贅詞／口誤語句，各 3 句；不代表真人或一般準確度', 'cases': []}
for case in json.loads((root / 'tests/fixtures/disfluent-corpus.json').read_text(encoding='utf-8')):
    audio = decode_audio(str(root / f'tests/fixtures/disfluent-{case["id"]}.wav'), sampling_rate=16000)
    modes = ['zh', 'translate'] if case['language'] == 'zh' else ['en']
    raw = engine.transcribe(audio, 'en' if case['language'] == 'en' else 'zh')
    for mode in modes:
        present, absent = (case['zh_present'], case['zh_absent']) if mode == 'zh' else (case['en_present'], case['en_absent'])
        started = time.monotonic()
        whisper_only = engine.transcribe(audio, 'translate') if mode == 'translate' else raw
        rows = {'Whisper only': {'text': whisper_only, 'seconds': round(time.monotonic() - started, 2),
                                 **check(whisper_only, present, absent)}}
        for name, backend in backends.items():
            started = time.monotonic()
            try:
                text = backend.refine(raw, mode)
                if mode == 'zh':
                    text = engine.converter.convert(text)
                rows[name] = {'text': text, 'seconds': round(time.monotonic() - started, 2), **check(text, present, absent)}
            except Exception as error:
                rows[name] = {'text': '', 'seconds': round(time.monotonic() - started, 2), 'passed': False, 'error': str(error)}
        entry = {'id': case['id'], 'mode': mode, 'spoken': case['text'], 'whisper_raw': raw, 'results': rows}
        report['cases'].append(entry)
        print(json.dumps(entry, ensure_ascii=False), flush=True)
out = root / 'verification' / f'refine-{model}-{time.strftime("%Y-%m-%d")}.json'
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('saved', out)
