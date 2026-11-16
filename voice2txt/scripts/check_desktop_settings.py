"""設定 round-trip 檢查：Anthropic key/model/effort 存檔（DPAPI）後由新的 App 讀回。

使用暫存 LOCALAPPDATA 與隱藏的 Tk root，不會碰使用者真實設定。
結果合併寫入 verification/desktop-anthropic-ui-2026-11-13.json（或第一個參數指定的檔案）。
"""
import json
import os
import sys
import tempfile
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
output = Path(sys.argv[1]) if len(sys.argv) > 1 else repo / 'verification' / 'desktop-anthropic-ui-2026-11-13.json'
temp = tempfile.TemporaryDirectory()
os.environ['LOCALAPPDATA'] = temp.name
os.environ.pop('ANTHROPIC_API_KEY', None)
sys.path.insert(0, str(repo))

import tkinter as tk
from voice2txt.desktop import App, DATA

SECRET = 'FAKE-KEY-roundtrip-0123'
root = tk.Tk()
root.withdraw()
report = {}
try:
    app = App(root)
    root.update()
    report['providers_in_ui'] = list(app.cloud)
    values = app.cloud['Anthropic']
    values['enabled'].set(False)
    values['model'].set('claude-opus-5-5')
    values['effort'].set('high')
    values['key'].set(SECRET)
    app.save_settings()
    raw = (DATA / 'settings.json').read_text(encoding='utf-8')
    saved = json.loads(raw)['cloud']['Anthropic']
    report['key_is_dpapi_protected'] = bool(saved['key']) and saved['key'] != SECRET and SECRET not in raw
    app.close()
    root = tk.Tk()
    root.withdraw()
    app2 = App(root)
    root.update()
    got = app2.cloud['Anthropic']
    report['settings_roundtrip_ok'] = (got['enabled'].get() is False and got['model'].get() == 'claude-opus-5-5'
                                       and got['effort'].get() == 'high' and got['key'].get() == SECRET)
    # 環境變數備援：欄位留空時讀 ANTHROPIC_API_KEY。
    got['key'].set('')
    got['enabled'].set(True)
    os.environ['ANTHROPIC_API_KEY'] = 'env-key'
    clouds = app2._cloud_settings()
    os.environ.pop('ANTHROPIC_API_KEY')
    report['env_fallback_ok'] = [c[0] for c in clouds] == ['Anthropic'] and clouds[0][2] == 'env-key'
    app2.close()
finally:
    try:
        root.destroy()
    except tk.TclError:
        pass
    temp.cleanup()
report['ok_roundtrip'] = bool(report.get('settings_roundtrip_ok') and report.get('key_is_dpapi_protected')
                              and report.get('env_fallback_ok'))
data = {}
if output.exists():
    data = json.loads(output.read_text(encoding='utf-8'))
data.update({k: v for k, v in report.items() if k != 'ok_roundtrip'})
data['providers_in_ui'] = report['providers_in_ui']
output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
raise SystemExit(0 if report['ok_roundtrip'] else 1)
