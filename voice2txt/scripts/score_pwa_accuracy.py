"""彙整 PWA 固定合成語料；CER/WER 只代表這組語料，不代表真人一般準確度。"""
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORDS = {'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
         'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10',
         'nineteenth': '19', 'thirty': '30'}


def units(text, mode):
    text = unicodedata.normalize('NFKC', text).lower()
    if mode == 'zh':
        text = text.translate(str.maketrans('零一二三四五六七八九兩', '01234567892'))
        return re.findall(r'[\w]', text)
    for word, digit in WORDS.items():
        text = re.sub(r'\b' + word + r'\b', digit, text)
    text = text.replace('mg/dl', 'milligrams per deciliter')
    text = re.sub(r'(\d)\s+point\s+(\d)', r'\1.\2', text)
    text = re.sub(r'(\d+)(?:st|nd|rd|th)\b', r'\1', text)
    return re.findall(r'[a-z]+|\d+', text)


def distance(reference, hypothesis):
    row = list(range(len(hypothesis) + 1))
    for i, a in enumerate(reference, 1):
        next_row = [i]
        for j, b in enumerate(hypothesis, 1):
            next_row.append(min(row[j] + 1, next_row[-1] + 1, row[j - 1] + (a != b)))
        row = next_row
    return row[-1]


def main():
    report = {'scope': '同一組合成音訊、Windows Chrome、WASM；不是 iPhone/iPad 真人準確度。標點、數字格式及 mg/dL 單位拼法正規化後計算中文 CER、英文 WER。', 'profiles': []}
    for name in ['baseline-tiny', 'baseline-base', 'base-mixed', 'small-mixed', 'small-q8']:
        path = ROOT / 'verification' / ('accuracy-' + name + '-2026-11-15.txt')
        if not path.exists():
            continue
        text = path.read_text(encoding='utf-8-sig')
        if '### Result' not in text:
            continue
        data, _ = json.JSONDecoder().raw_decode(text.split('### Result', 1)[1].lstrip())
        totals = {'zh': [0, 0], 'en': [0, 0]}
        for case in data['cases']:
            reference, hypothesis = units(case['reference'], case['mode']), units(case['output'], case['mode'])
            case['edit_distance'] = distance(reference, hypothesis)
            case['reference_units'] = len(reference)
            totals[case['mode']][0] += case['edit_distance']
            totals[case['mode']][1] += len(reference)
        data['profile'] = name
        data['aggregate'] = {mode: {'edits': edits, 'reference_units': count, 'error_rate': round(edits / count, 4) if count else None} for mode, (edits, count) in totals.items()}
        report['profiles'].append(data)
    (ROOT / 'verification/accuracy-comparison-2026-11-15.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps([{'profile': p['profile'], 'aggregate': p['aggregate']} for p in report['profiles']], ensure_ascii=False))


if __name__ == '__main__':
    main()
