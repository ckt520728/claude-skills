"""測量現有本機模型在較小 context 下的連續翻譯速度與輸出。"""
import json
from pathlib import Path
import time
import urllib.request

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def post(path, body):
    request = urllib.request.Request('http://127.0.0.1:11434/api/' + path,
                                     data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    with opener.open(request, timeout=55) as response:
        return json.load(response)


model = 'gemma4:latest'
corpus = json.loads(Path('tests/fixtures/quality-corpus.json').read_text(encoding='utf-8'))
report = {'model': model, 'num_ctx': 2048, 'cases': [], 'scope': '固定文字，不是音訊端到端測試；不代表一般翻譯品質'}
try:
    started = time.monotonic()
    post('generate', {'model': model, 'stream': False, 'keep_alive': '5m', 'options': {'num_ctx': 2048}})
    report['preload_seconds'] = time.monotonic() - started
    for case in corpus:
        if case['language'] != 'zh':
            continue
        started = time.monotonic()
        result = post('chat', {
            'model': model, 'stream': False, 'think': False, 'keep_alive': '5m',
            'messages': [
                {'role': 'system', 'content': 'Translate the complete Chinese transcript into English. Preserve all events, negations, dates, times, locations and quantities. Return only the English translation.'},
                {'role': 'user', 'content': case['text']},
            ], 'options': {'num_ctx': 2048, 'temperature': 0, 'num_predict': 160},
        })
        text = result['message']['content']
        report['cases'].append({'id': case['id'], 'input': case['text'], 'text': text,
                                'seconds': time.monotonic() - started,
                                'keyword_checks_passed': all(any(word in text.lower() for word in group) for group in case['expected_english'])})
        print(report['cases'][-1], flush=True)
finally:
    Path('verification/local-translation-benchmark.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    post('generate', {'model': model, 'keep_alive': 0, 'stream': False})
