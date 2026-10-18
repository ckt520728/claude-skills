"""逐項解析大型 REA JSON，確認輸出完整並建立小型索引。"""
import json
from pathlib import Path
import ijson

report = {'json_complete': False, 'fields': [], 'graph_fields': [], 'scalars': {}}
with Path('verification/typeless-rea.json').open('r', encoding='utf-8-sig') as source:
    for prefix, event, value in ijson.parse(source):
        if prefix == 'normalized_result' and event == 'map_key':
            report['fields'].append(value)
        elif prefix == 'normalized_result.graph' and event == 'map_key':
            report['graph_fields'].append(value)
        elif event in ('string', 'number', 'boolean', 'null') and prefix.count('.') < 2:
            report['scalars'][prefix] = value
report['json_complete'] = True
Path('verification/typeless-rea-summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
