"""啟動真正 Tk UI，驗證錄音分段到畫面與歷史資料的整合。"""
import os
import json
from pathlib import Path
import tempfile
import time
import tkinter as tk
from unittest.mock import patch

import numpy as np

temp = tempfile.TemporaryDirectory(dir='verification')
os.environ['LOCALAPPDATA'] = temp.name
from voice2txt.desktop import App


class FakeStream:
    def __init__(self, **kwargs):
        self.callback = kwargs['callback']

    def start(self):
        self.callback(np.ones((16000 * 10, 1), dtype=np.float32), 16000 * 10, None, None)

    def stop(self):
        pass

    def close(self):
        pass


class FakeEngine:
    def transcribe(self, audio, mode, vocabulary):
        return f'Whisper direct {len(audio)}' if mode == 'translate' else f'繁體中文測試 {len(audio)}'


root = tk.Tk()
root.withdraw()
try:
    app = App(root)
    app.engine = FakeEngine()
    with patch('sounddevice.InputStream', FakeStream):
        app.toggle()
        app.stop()
        deadline = time.monotonic() + 10
        while app.draining and time.monotonic() < deadline:
            root.update()
            time.sleep(0.02)
        root.update()
    assert not app.draining
    result = app.text.get('1.0', 'end')
    assert '128000' in result and '32000' in result, result
    assert len(app.store.history()) == 2
    assert str(app.start_button.cget('state')) == 'normal'
    app.dictionary.insert('1.0', 'HHSA, 腎臟病')
    app.save_settings()
    assert 'HHSA' in (Path(temp.name) / 'Voice2Txt/settings.json').read_text(encoding='utf-8')
    class FailingEngine:
        def transcribe(self, *args):
            raise RuntimeError('測試音訊辨識失敗')

    app.engine = FailingEngine()
    with patch('sounddevice.InputStream', FakeStream), patch('tkinter.messagebox.showerror'):
        app.toggle()
        app.stop()
        deadline = time.monotonic() + 10
        while app.draining and time.monotonic() < deadline:
            root.update()
            time.sleep(0.02)
        root.update()
    assert '失敗' in app.status.get(), app.status.get()
    class FakeTranslator:
        name = 'Fake LLM'

        def refine(self, source, mode, vocabulary=''):
            return 'Test English translation.' if mode == 'translate' else '整理後的繁體中文。'

    # 第二階段 LLM 整理也套用在繁體中文模式，原始轉錄保留供核對。
    app.engine = FakeEngine()
    app.translator = FakeTranslator()
    app.mode.set('繁體中文')
    with patch('sounddevice.InputStream', FakeStream):
        app.toggle()
        app.stop()
        deadline = time.monotonic() + 10
        while app.draining and time.monotonic() < deadline:
            root.update()
            time.sleep(0.02)
        root.update()
    assert '整理後的繁體中文。' in app.text.get('1.0', 'end')
    assert '繁體中文測試' in app.source_text.get('1.0', 'end')

    app.engine = FakeEngine()
    app.translator = FakeTranslator()
    app.mode.set('中文 → English')
    with patch('sounddevice.InputStream', FakeStream):
        app.toggle()
        app.stop()
        deadline = time.monotonic() + 10
        while app.draining and time.monotonic() < deadline:
            root.update()
            time.sleep(0.02)
        root.update()
    assert 'Test English translation.' in app.text.get('1.0', 'end')
    assert '繁體中文測試' in app.source_text.get('1.0', 'end')
    assert app.store.source(app.store.history()[0][0])

    class FailedTranslator:
        name = 'Failing LLM'
        calls = 0

        def refine(self, source, mode, vocabulary=''):
            self.calls += 1
            raise TimeoutError('測試翻譯逾時')

    failed_translator = FailedTranslator()
    app.translator = failed_translator
    with patch('sounddevice.InputStream', FakeStream), patch('tkinter.messagebox.showerror') as show_error:
        app.toggle()
        app.stop()
        deadline = time.monotonic() + 10
        while app.draining and time.monotonic() < deadline:
            root.update()
            time.sleep(0.02)
        root.update()
        assert show_error.call_count == 0, show_error.call_count
    # 所有 LLM 失敗：不中斷錄音，每段改用 Whisper 直接翻譯並標示備援。
    assert failed_translator.calls == 2
    assert 'Whisper direct 128000' in app.text.get('1.0', 'end')
    assert '備援啟用' in app.status.get() or '已完成' in app.status.get(), app.status.get()
    assert app.store.history()[0][3] == 'translate'
    Path('verification/desktop-integration.json').write_text(json.dumps({
        'passed': True, 'real_tk_ui': True, 'microphone': 'mock',
        'decoder': 'mock', 'checks': ['8 秒上限與 2 秒尾段', '畫面輸出', 'SQLite', '字典儲存',
        '辨識失敗不顯示成功', 'LLM 整理繁體中文並保留原始轉錄', 'LLM 中英文對照',
        'LLM 失敗時改用 Whisper 直接翻譯、不中斷錄音、不彈窗'],
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    app.close()
    print('PASS: 真實 Tk 啟動、模擬麥克風 8 秒段與 2 秒尾段、畫面、SQLite、字典儲存。')
finally:
    if 'app' in globals() and not app.closed:
        app.store.close()
    try:
        root.destroy()
    except tk.TclError:
        pass
    temp.cleanup()
