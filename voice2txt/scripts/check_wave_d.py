"""Wave D 桌面整合檢查：真正的 Tk App + 暫存 LOCALAPPDATA + 替身 Whisper 引擎／翻譯後端。

涵蓋：舊 settings.json 的預設值、口述工作階段更新洞察、隨便問（脈絡、歷史篩選、不擷取自己視窗）、
自動字典候選、聲音／靜音其他音訊（含 overflow／close 還原）、外觀切換、歷史保留 prune、貼上後還原剪貼簿。
結果寫入 verification/wave-d-2026-11-13.json。不碰真實設定，不注入 Right Alt，不真的發聲或靜音。
"""
import ast
import json
import os
import sqlite3
import sys
import tempfile
import time
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

import numpy as np

repo = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo))
OUT = repo / 'verification' / 'wave-d-2026-11-13.json'
temp = tempfile.TemporaryDirectory()
os.environ['LOCALAPPDATA'] = temp.name
for name in ('ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'GEMINI_API_KEY'):
    os.environ.pop(name, None)

from voice2txt import context as window_context, insights, theme  # noqa: E402
from voice2txt import desktop  # noqa: E402
from voice2txt.core import MODES  # noqa: E402

DATA = desktop.DATA
SELECTION = '請把這段改成英文'
results, details = {}, {}


class FakeStream:
    def __init__(self, **kwargs):
        self.callback = kwargs['callback']

    def start(self):
        self.callback(np.ones((16000 * 10, 1), dtype=np.float32), 16000 * 10, None, None)

    def stop(self):
        pass

    def close(self):
        pass


class StubEngine:
    size, device = 'stub', 'cpu'

    def __init__(self):
        self.calls = []

    def transcribe(self, audio, mode, vocabulary=''):
        self.calls.append((mode, vocabulary))
        return '我們討論 Hasa 的計畫' if mode == 'zh' else 'We discussed Hasa today'


class StubTranslator:
    name = 'Stub LLM'
    last_backend = 'Stub LLM'
    errors = []

    def __init__(self):
        self.calls = []

    def refine(self, text, mode, vocabulary='', context=None):
        self.calls.append({'text': text, 'mode': mode, 'vocabulary': vocabulary, 'context': context})
        return 'Answer: press Ctrl+K.' if mode == 'ask' else 'The Hasa plan is ready'


EDIT_CHILD = r'''
import ctypes, json, sys
from ctypes import wintypes
user32 = ctypes.WinDLL('user32', use_last_error=True)
user32.CreateWindowExW.restype = ctypes.c_void_p
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p,
                                   ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
user32.SendMessageW.argtypes = [ctypes.c_void_p, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]
user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
user32.SetFocus.argtypes = [ctypes.c_void_p]
user32.SetWindowTextW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), ctypes.c_void_p, wintypes.UINT, wintypes.UINT]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
# 頂層的原生 EDIT 控制項（WS_OVERLAPPEDWINDOW | WS_VISIBLE | ES_MULTILINE | ES_AUTOVSCROLL | ES_WANTRETURN）
hwnd = user32.CreateWindowExW(0, 'EDIT', 'V2T-edit-child', 0xCF0000 | 0x10000000 | 0x4 | 0x40 | 0x1000,
                              300, 300, 420, 160, None, None, None, None)
user32.SetWindowTextW(hwnd, sys.argv[2])
user32.SetForegroundWindow(hwnd)
user32.SetFocus(hwnd)
user32.SendMessageW(hwnd, 0xB1, 0, -1)  # EM_SETSEL 全選
log = open(sys.argv[1], 'a', encoding='utf-8')
print('READY', hwnd, flush=True)
msg = wintypes.MSG()
while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
    if msg.message in (0x100, 0x104) and msg.wParam in (0x43, 0x56, 0x12, 0xA4):
        alt = bool(user32.GetKeyState(0x12) & 0x8000)
        log.write(json.dumps({'vk': msg.wParam, 'msg': hex(msg.message), 'alt_down': alt,
                              'alt_bit_in_lparam': bool(msg.lParam & (1 << 29))}) + chr(10))
        log.flush()
    user32.TranslateMessage(ctypes.byref(msg))
    user32.DispatchMessageW(ctypes.byref(msg))
'''


def clear_clipboard():
    window_context._write_text(None)


def restore_real_clipboard(saved):
    """還原檢查前的真實剪貼簿文字；原本是空的就清空（m7）。"""
    return window_context._write_text(saved)


def force_foreground(hwnd):
    import ctypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    fg = user32.GetForegroundWindow()
    fg_thread = user32.GetWindowThreadProcessId(ctypes.c_void_p(fg), None) if fg else 0
    me = kernel32.GetCurrentThreadId()
    attached = bool(fg_thread and fg_thread != me and user32.AttachThreadInput(me, fg_thread, True))
    try:
        user32.ShowWindow(ctypes.c_void_p(hwnd), 5)
        user32.BringWindowToTop(ctypes.c_void_p(hwnd))
        user32.SetForegroundWindow(ctypes.c_void_p(hwnd))
    finally:
        if attached:
            user32.AttachThreadInput(me, fg_thread, False)
    time.sleep(0.4)
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    return user32.GetForegroundWindow() == hwnd


def add_extra_clipboard_format():
    """在目前剪貼簿文字旁邊再加一個自訂（非文字）格式，模擬瀏覽器／Word 複製的帶格式內容。"""
    import ctypes
    from ctypes import wintypes
    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    user32.RegisterClipboardFormatW.restype = wintypes.UINT
    user32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    fmt = user32.RegisterClipboardFormatW('V2T-wave-d-extra')
    for _ in range(50):
        if user32.OpenClipboard(None):
            break
        time.sleep(0.02)
    else:
        return False
    try:
        handle = kernel32.GlobalAlloc(0x0002, 16)
        pointer = kernel32.GlobalLock(handle)
        ctypes.memmove(pointer, b'v2t-extra-data' + bytes(2), 16)
        kernel32.GlobalUnlock(handle)
        return bool(user32.SetClipboardData(fmt, handle))
    finally:
        user32.CloseClipboard()


def edit_text(hwnd):
    import ctypes
    buffer = ctypes.create_unicode_buffer(4096)
    ctypes.windll.user32.SendMessageW(ctypes.c_void_p(hwnd), 0xD, 4096, ctypes.byref(buffer))  # WM_GETTEXT
    return buffer.value.replace(chr(13) + chr(10), chr(10))


def read_child_log(path):
    try:
        return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]
    except OSError:
        return []


def cross_process_check():
    """稽核 E D1／D3 真機：LeftAlt+F23（VK 0x86）設為 ask，另一行程的原生 EDIT 已選取文字。

    按住組合 -> App 的 hook 觸發 _begin_ask -> 放開 Alt 再 Ctrl+C（帶 MARKER）-> 取得選取；目標看到的 C 鍵沒有 Alt 位元。
    之後三段貼回合併成一次貼上。不注入 Right Alt（Typeless 會吞）。
    """
    import ctypes
    import subprocess
    from voice2txt.hotkeys import physical_key_down, send_key
    user32 = ctypes.windll.user32
    LALT, F23 = 0xA4, 0x86
    HOLD_SECONDS = 3.0
    prior = 'prior-wave-d-clipboard-' + str(int(time.time()))
    log_path = Path(temp.name) / 'edit-child.jsonl'
    expected_selection = 'CROSS-PROCESS-SELECTION 選取'
    d = {}
    details['cross_process'] = d
    child = subprocess.Popen([sys.executable, '-c', EDIT_CHILD, str(log_path), expected_selection],
                             stdout=subprocess.PIPE, text=True)
    root, app = None, None
    try:
        line = child.stdout.readline()
        if not line.startswith('READY'):
            d['error'] = 'EDIT child 沒有啟動：' + line
            return False
        hwnd = int(line.split()[1])
        root, app = new_app()
        app.hotkeys['dictate'] = []
        app.hotkeys['translate'] = []
        app.hotkeys['ask'] = ['LeftAlt+VK0x86']
        app._apply_hotkeys()
        app.engine, app.translator = StubEngine(), StubTranslator()
        app.hotkey_paste.set(False)  # 擷取階段不貼回答，才能單獨驗證剪貼簿還原
        d['hook_installed'] = app.hook is not None and app.hook.thread is not None
        d['configured_ask'] = list(app.hotkeys['ask'])
        d['child_is_foreground'] = force_foreground(hwnd)
        if not d['child_is_foreground'] or not d['hook_installed']:
            return False
        window_context._write_text(prior)
        translator = app.translator
        pump(root, 0.3)
        d['foreground_before_keys'] = window_context.window_info(window_context.foreground_window())['title']
        if d['foreground_before_keys'] != 'V2T-edit-child':
            force_foreground(hwnd)
            d['foreground_after_refocus'] = window_context.window_info(window_context.foreground_window())['title']
        with patch('sounddevice.InputStream', FakeStream):
            send_key(LALT, False)
            time.sleep(0.05)
            t_press = time.monotonic()
            send_key(F23, False)
            started = wait_for(root, lambda: app.recording, 8)
            d['recording_started'] = started
            session_context = dict(app.session_context or {})
            # 稽核 E2 N1：按住 3 s（F23 像真鍵盤一樣 auto-repeat，LeftAlt 不 repeat）；錄音不得在放開前自行停止。
            stopped_at = None
            while time.monotonic() - t_press < HOLD_SECONDS:
                send_key(F23, False)
                pump(root, 0.033)
                if stopped_at is None and not app.recording:
                    stopped_at = time.monotonic() - t_press
            held_still_recording = app.recording
            send_key(F23, True)
            send_key(LALT, True)
            t_release = time.monotonic() - t_press
            done = wait_for(root, lambda: started and not app.recording and not app.draining, 20)
            if stopped_at is None:
                stopped_at = t_release  # 放開之後才停止
            d['hold_seconds_requested'] = HOLD_SECONDS
            d['recording_still_on_before_release'] = bool(held_still_recording)
            d['ask_stop_seconds_after_press'] = round(stopped_at, 3)
            d['ask_not_stopped_before_release'] = bool(held_still_recording) and stopped_at >= HOLD_SECONDS - 0.1
            d['ptt_recovered_during_hold'] = list(app.ptt.recovered)
            d['ptt_not_recovered'] = app.ptt.recovered == []
        d['session_finished'] = done
        d['session_selection'] = session_context.get('selection')
        d['selection_obtained'] = session_context.get('selection') == expected_selection
        ask_calls = [c for c in translator.calls if c['mode'] == 'ask']
        d['llm_received_selection'] = bool(ask_calls) and ask_calls[0]['context']['selection'] == expected_selection
        events = read_child_log(log_path)
        c_events = [e for e in events if e['vk'] == 0x43]
        d['target_c_key_events'] = c_events
        d['c_key_without_alt'] = bool(c_events) and all(e['msg'] == '0x100' and not e['alt_down']
                                                        and not e['alt_bit_in_lparam'] for e in c_events)
        # 擷取完成後剪貼簿文字必須還原
        after, _ = window_context._read_text()
        d['clipboard_restored_after_capture'] = after == prior
        d['ask_hold_ended_cleanly'] = not physical_key_down(LALT) and not physical_key_down(F23)

        # ---- 三段貼回合併成一次貼上 ----
        user32.SendMessageW(ctypes.c_void_p(hwnd), 0xC, 0, '')  # WM_SETTEXT 清空
        force_foreground(hwnd)
        before_v = len([e for e in read_child_log(log_path) if e['vk'] == 0x56])
        app.deferred_pastes = [('SEG-ONE', hwnd), ('SEG-TWO', hwnd), ('SEG-THREE', hwnd)]
        app.target_window = hwnd
        app.clip_saved = None
        app.last_clipboard_restore = ''
        window_context._write_text(prior)
        pump(root, 0.2)
        app._flush_pastes()
        pump(root, 1.6)
        text = edit_text(hwnd)
        v_events = [e for e in read_child_log(log_path) if e['vk'] == 0x56][before_v:]
        d['merged_paste_text'] = text
        d['merged_paste_exact'] = text == 'SEG-ONE' + chr(10) + 'SEG-TWO' + chr(10) + 'SEG-THREE'
        d['ctrl_v_count'] = len(v_events)
        d['single_ctrl_v'] = len(v_events) == 1
        d['deferred_cleared'] = app.deferred_pastes == []
        after, _ = window_context._read_text()
        d['clipboard_restored_after_paste'] = after == prior and app.last_clipboard_restore == 'restored'

        # ---- 稽核 E2 nit：擷取會被略過（剪貼簿含非文字格式）-> 完全不注入按鍵 ----
        from voice2txt import hotkeys as hotkeys_module

        def ask_begin_injections(extra_format):
            window_context._write_text(prior)
            if extra_format:
                add_extra_clipboard_format()
            force_foreground(hwnd)
            send_key(LALT, False)          # 真的按住 LeftAlt（之後才攔截 send_key，所以是真實注入）
            time.sleep(0.1)
            sent = []
            with patch.object(hotkeys_module, 'send_key', lambda vk, up, extra=0: sent.append((vk, up, extra))):
                app._begin_ask(hotkey=True)
                app.ask_cancel = True      # 事件回來時當作取消，不真的開始錄音
                wait_for(root, lambda: not app.ask_pending, 5)
                pump(root, 0.3)
            send_key(LALT, True)
            pump(root, 0.2)
            return sent

        skipped = ask_begin_injections(True)
        d['skip_path_injected_keys'] = skipped
        d['skip_path_injects_nothing'] = skipped == []
        control = ask_begin_injections(False)
        d['control_text_only_injected_count'] = len(control)
        d['control_text_only_injects_keys'] = len(control) >= 4
        window_context._write_text(prior)
        return all(v for v in d.values() if isinstance(v, bool))
    finally:
        child.terminate()
        for vk in (LALT, F23):
            if physical_key_down(vk):
                send_key(vk, True)
        if app is not None:
            try:
                app.close()
            except Exception:
                pass


def pump(root, seconds=0.1):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        root.update()
        time.sleep(0.01)


def wait_for(root, condition, timeout=15):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        root.update()
        if condition():
            return True
        time.sleep(0.02)
    return False


def new_app():
    root = tk.Tk()
    root.withdraw()
    app = desktop.App(root)
    root.update()
    return root, app


def fake_context(capture=True):
    fake_context.calls.append(capture)
    return {'app': 'notepad', 'title': 'notes.txt - Notepad', 'selection': SELECTION if capture else '',
            'category': 'document', 'process_name': 'notepad', 'hwnd': 0x7777}


fake_context.calls = []


def run_hotkey_session(root, app, action):
    """透過 events queue 模擬快捷鍵：start -> 錄音 -> stop -> 等待處理完成。"""
    with patch('sounddevice.InputStream', FakeStream):
        app.events.put(('hotkey', ('start', action)))
        started = wait_for(root, lambda: app.recording, 8)
        app.events.put(('hotkey', ('stop', None)))
        done = wait_for(root, lambda: started and not app.recording and not app.draining, 20)
    root.update()
    return started and done


def main():
    real_text, real_other = window_context._read_text()  # 檢查前的真實剪貼簿文字（m7：結束後還原）
    details['real_clipboard_saved'] = {'had_text': real_text is not None, 'had_other_formats': bool(real_other)}
    main.real_text = real_text
    # ---- 0. 舊的 ask 預設 RightAlt+Space 載入時遷移成 RightAlt+RightCtrl；使用者自訂值保留 ------------------
    migration = {}
    for label, saved_ask in (('old_default', ['RightAlt+Space']), ('custom_kept', ['LeftAlt+F5'])):
        DATA.mkdir(parents=True, exist_ok=True)
        (DATA / 'settings.json').write_text(json.dumps({'hotkeys': {'ask': saved_ask}}), encoding='utf-8')
        root, app = new_app()
        migration[label] = list(app.hotkeys['ask'])
        app.close()
    details['ask_hotkey_migration'] = migration
    results['ask_hotkey_migration'] = (migration['old_default'] == ['RightAlt+RightCtrl']
                                       and migration['custom_kept'] == ['LeftAlt+F5'])
    # ---- 1. 舊 settings.json（沒有任何新鍵）載入後使用文件化的預設值 ----------------------------------
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / 'settings.json').write_text(json.dumps({'model': 'small', 'dictionary': 'ProjectX',
                                                     'translation_backend_v2': '僅 Whisper',
                                                     'hotkeys': {'dictate': ['RightAlt'], 'translate': ['RightAlt+RightShift']}},
                                                    ensure_ascii=False), encoding='utf-8')
    root, app = new_app()
    defaults = {'context_aware': app.context_aware.get() is True, 'hotkey_paste': app.hotkey_paste.get() is True,
                'sounds': app.sounds_on.get() is True, 'mute_others': app.mute_others_on.get() is False,
                'appearance': app.appearance.get() == '系統', 'retention': app.retention.get() == '永久',
                'dictionary_auto': app.dictionary_auto == [], 'dictionary_ignored': app.dictionary_ignored == [],
                'ask_hotkey_default': app.hotkeys['ask'] == ['RightAlt+RightCtrl'],
                'ask_hotkey_label': 'Right Ctrl' in app.hotkey_labels['ask'].get(),
                'tab_order': [app.tabs.tab(i, 'text') for i in range(4)] == ['洞察', '即時語音', '歷史紀錄', '字典與設定'],
                'old_keys_kept': app.vocabulary == 'ProjectX' and app.hotkeys['dictate'] == ['RightAlt']}
    details['old_settings_defaults'] = defaults
    results['old_settings_defaults'] = all(defaults.values())
    results['defaults_include_ask_title'] = desktop.HOTKEY_TITLES.get('ask') == '隨便問' and '隨便問' in MODES.values()

    # ---- 2. 口述工作階段：聲音／靜音／脈絡／貼回／洞察 --------------------------------------------------
    engine, translator = StubEngine(), StubTranslator()
    app.engine, app.translator = engine, translator
    app.vocabulary = 'ProjectX'
    app.hotkey_paste.set(True)
    app.mute_others_on.set(True)
    pastes, sound_calls, mute_calls, restore_calls = [], [], [], []
    app._paste = lambda text, target=None: pastes.append((text, target))
    handle = object()

    def fake_mute(pid=None):
        mute_calls.append(pid)
        return handle

    before_words = app.insight_vars['words'].get()
    with patch('voice2txt.desktop.sounds.play', lambda name, enabled=True: sound_calls.append((name, enabled))), \
         patch('voice2txt.desktop.audiofocus.mute_others', fake_mute), \
         patch('voice2txt.desktop.audiofocus.restore', lambda h: restore_calls.append(h)), \
         patch.object(window_context, 'foreground_context', fake_context):
        ok = run_hotkey_session(root, app, 'dictate')
        rows = [r for r in app.store.rows_for_stats() if r[1] != 'ask']
        expected = sum(insights.count_words(r[3]) for r in rows)
        stats = app.insight_stats
        cells = app.heatmap.find_withtag('cell')
        d = {
            'session_finished': ok, 'rows_added': len(rows) == 2,
            'words_before_zero': before_words in ('0', '—'),
            'words_label_updated': app.insight_vars['words'].get() == f'{expected:,}' and expected > 0,
            'stats_match': stats['total_words'] == expected and stats['active_days'] == 1 and stats['current_streak'] == 1,
            'rate_and_time_labels': app.insight_vars['wpm'].get().endswith('字/分') and bool(app.insight_vars['time'].get())
                                     and app.insight_vars['saved'].get() != '—',
            'heatmap_drawn': len(cells) == len(app.insight_cells) > 0
                             and any(c[4] > 0 for c in app.insight_cells),
            'mode_line': '依模式' in app.insight_modes.get() and '繁體中文' in app.insight_modes.get(),
            'context_passed_to_llm': bool(translator.calls) and translator.calls[0]['context'] is not None
                                     and translator.calls[0]['context']['app'] == 'notepad'
                                     and translator.calls[0]['context']['selection'] == '',
            'glossary_to_whisper': all('ProjectX' in v for _, v in engine.calls),
            'hotkey_auto_paste': len(pastes) == 1 and pastes[0][1] == app.target_window and pastes[0][0].count(chr(10)) == 1,
            'sound_start_stop': ('start', True) in sound_calls and ('stop', True) in sound_calls
                                and sound_calls.index(('start', True)) < sound_calls.index(('stop', True)),
            'mute_and_restore_on_stop': mute_calls == [os.getpid()] and restore_calls == [handle] and app.mute_handle is None,
        }
        details['dictate_session'] = d
        results['dictate_session_insights'] = all(d.values())

        # 脈絡設定關閉：LLM 不再收到前景視窗資訊
        app.context_aware.set(False)
        app.hotkey_paste.set(False)
        app.mute_others_on.set(False)
        pastes.clear()
        n = len(translator.calls)
        ok2 = run_hotkey_session(root, app, 'dictate')
        off = {'finished': ok2, 'context_none': all(c['context'] is None for c in translator.calls[n:]) and len(translator.calls) > n,
               'no_auto_paste': pastes == []}
        details['context_aware_off'] = off
        results['context_aware_toggle_and_hotkey_paste_toggle'] = all(off.values())
        app.context_aware.set(True)

        # 聲音關閉：仍呼叫 play 但 enabled=False
        sound_calls.clear()
        run_hotkey_session(root, app, 'dictate')
        sounds_off_ok = False
        app.sounds_on.set(False)
        sound_calls.clear()
        run_hotkey_session(root, app, 'dictate')
        sounds_off_ok = bool(sound_calls) and all(enabled is False for _, enabled in sound_calls)
        app.sounds_on.set(True)
        results['sounds_setting_respected'] = sounds_off_ok

        # ---- 3. 隨便問 ----------------------------------------------------------------------------
        translator.calls.clear()
        engine.calls.clear()
        pastes.clear()
        fake_context.calls.clear()
        app.hotkey_paste.set(True)
        ok = run_hotkey_session(root, app, 'ask')
        ask_calls = [c for c in translator.calls if c['mode'] == 'ask']
        rows_all = app.store.history()
        ask_rows = [r for r in rows_all if r[3] == 'ask']
        app.history_filter.set('隨便問')
        app._history()
        ask_list = list(app.history.get(0, 'end'))
        app.history_filter.set('口述')
        app._history()
        dict_list = list(app.history.get(0, 'end'))
        app.history_filter.set('翻譯')
        app._history()
        tr_list = list(app.history.get(0, 'end'))
        app.history_filter.set('全部')
        app._history()
        all_list = list(app.history.get(0, 'end'))
        d = {
            'session_finished': ok,
            'capture_requested': True in fake_context.calls,
            'stub_received_context': bool(ask_calls) and ask_calls[0]['context']['selection'] == SELECTION
                                     and ask_calls[0]['context']['app'] == 'notepad',
            'whisper_used_dictation_language': bool(engine.calls) and all(m == 'zh' for m, _ in engine.calls),
            'answer_in_editor': 'Answer: press Ctrl+K.' in app.text.get('1.0', 'end'),
            'history_mode_ask': len(ask_rows) == 2 and all(r[2] == 'Answer: press Ctrl+K.' for r in ask_rows),
            'filter_ask': len(ask_list) == len(ask_rows) and all('隨便問' in line for line in ask_list),
            'filter_dictation': len(dict_list) > 0 and all('隨便問' not in line for line in dict_list)
                                and len(dict_list) + len(ask_list) == len(all_list),
            'filter_translate_empty': tr_list == [],
            'ask_pasted_back': len(pastes) == 1 and pastes[0][0].count(chr(10)) == 1,
            'ask_excluded_from_insights': app.insight_stats['total_words'] == sum(
                insights.count_words(r[2]) for r in rows_all if r[3] != 'ask'),
        }
        details['ask_session'] = d
        results['ask_session_and_history_filter'] = all(d.values())

        # 前景是 Voice2Txt 自己：不擷取（不注入 Ctrl+C），改用編輯區選取文字
        fake_context.calls.clear()
        translator.calls.clear()
        app.text.tag_add('sel', '1.0', '1.4')
        selected = app.text.get('sel.first', 'sel.last')
        with patch.object(window_context, 'foreground_window', lambda: 0x5555), \
             patch.object(app, '_own_hwnd', lambda: 0x5555):
            ok = run_hotkey_session(root, app, 'ask')
        own = {'finished': ok, 'no_capture_call': fake_context.calls == [],
               'uses_editor_selection': bool(translator.calls) and translator.calls[-1]['context']['selection'] == selected
                                        and translator.calls[-1]['context']['app'] == ''}
        details['ask_own_window'] = own
        results['ask_skips_capture_in_own_window'] = all(own.values())

        # m5：關閉前景脈絡時，隨便問只送選取文字（沒有 app／標題）
        app.context_aware.set(False)
        translator.calls.clear()
        fake_context.calls.clear()
        ok = run_hotkey_session(root, app, 'ask')
        sent = [c['context'] for c in translator.calls if c['mode'] == 'ask']
        m5 = {'finished': ok, 'selection_only': bool(sent) and all(c == {'selection': SELECTION} for c in sent)}
        app.context_aware.set(True)
        details['ask_context_off_selection_only'] = m5
        results['ask_context_off_selection_only'] = all(m5.values())

        # m1：隨便問沒有 LLM（Whisper）時，最終狀態保留「沒有可用的 LLM，顯示原始轉錄」
        app.translator = None
        pastes.clear()
        ok = run_hotkey_session(root, app, 'ask')
        root.update()
        m1 = {'finished': ok, 'final_status': app.status.get(), 'not_pasted': pastes == []}
        m1['status_kept'] = m1['final_status'] == '沒有可用的 LLM，顯示原始轉錄'
        app.translator = translator
        details['ask_no_llm_status'] = m1
        results['ask_no_llm_status'] = m1['finished'] and m1['status_kept'] and m1['not_pasted']

        # ---- 4. 自動字典 ---------------------------------------------------------------------------
        text = app.text.get('1.0', 'end-1c')
        app.text.delete('1.0', 'end')
        app.text.insert('1.0', text.replace('Hasa', 'HHSA'))
        app.text.event_generate('<FocusOut>')
        root.update()
        focus_out_bound = bool(app.candidates)
        if not focus_out_bound:
            app._learn_check()
        terms = [c['term'] for c in app.candidates]
        app.candidate_list.selection_clear(0, 'end')
        app.candidate_list.selection_set(terms.index('HHSA') if 'HHSA' in terms else 0)
        app.candidate_add_button.invoke()
        saved = json.loads((DATA / 'settings.json').read_text(encoding='utf-8'))
        engine.calls.clear()
        run_hotkey_session(root, app, 'dictate')
        # 第二個候選：忽略
        text = app.text.get('1.0', 'end-1c')
        app.text.delete('1.0', 'end')
        app.text.insert('1.0', text.replace('ready', 'done'))
        app._learn_check()
        ignore_terms = [c['term'] for c in app.candidates]
        if app.candidates:
            app.candidate_list.selection_set(0)
            app.candidate_ignore_button.invoke()
        saved2 = json.loads((DATA / 'settings.json').read_text(encoding='utf-8'))
        d = {
            'focusout_binding': focus_out_bound,
            'candidate_found': 'HHSA' in terms,
            'accepted_in_auto': app.dictionary_auto == ['HHSA'],
            'glossary_merged': app._glossary() == 'ProjectX, HHSA',
            'persisted_dictionary_auto': saved.get('dictionary_auto') == ['HHSA'],
            'glossary_reaches_whisper': bool(engine.calls) and all('HHSA' in v and 'ProjectX' in v for _, v in engine.calls),
            'ignored_remembered': 'done' in ignore_terms and saved2.get('dictionary_ignored') == ['done'],
            'candidate_list_empty_after': app.candidate_list.size() == 0,
            'auto_label': 'HHSA' in app.auto_label.get(),
        }
        details['auto_dictionary'] = d
        results['auto_dictionary_candidates'] = all(d.values())

        # ---- 5. 靜音其他音訊：overflow／close 都會還原 --------------------------------------------
        app.mute_others_on.set(True)
        mute_calls.clear()
        restore_calls.clear()
        sound_calls.clear()
        with patch('sounddevice.InputStream', FakeStream):
            app.events.put(('hotkey', ('start', 'dictate')))
            wait_for(root, lambda: app.recording, 8)
            muted_during = app.mute_handle is handle
            app.events.put(('overflow', '測試溢位'))
            wait_for(root, lambda: not app.recording and not app.draining, 20)
        overflow_ok = muted_during and restore_calls == [handle] and ('error', True) in sound_calls
        restore_calls.clear()
        app.mute_handle = handle
        app._restore_audio()
        app._restore_audio()
        close_path = restore_calls == [handle] and app.mute_handle is None
        d = {'overflow_restores': overflow_ok, 'restore_idempotent_in_app': close_path}
        details['audiofocus'] = d
        # close() 本身：先設 handle 再關閉
        app.mute_handle = handle
        restore_calls.clear()
        app.close()
        d['close_restores'] = restore_calls == [handle]
        results['mute_others_restore_paths'] = all(d.values())

    # ---- 6. 外觀 --------------------------------------------------------------------------------------
    root, app = new_app()
    themes = {}
    for choice, expected_palette in (('淺色', theme.LIGHT), ('深色', theme.DARK), ('系統', theme.resolve('系統'))):
        app.appearance.set(choice)
        app._appearance_changed()
        root.update()
        themes[choice] = (str(root.cget('bg')).lower() == expected_palette['bg']
                          and str(app.text.cget('bg')).lower() == expected_palette['text_bg']
                          and str(app.dictionary.cget('bg')).lower() == expected_palette['text_bg']
                          and str(app.history.cget('bg')).lower() == expected_palette['list_bg']
                          and str(app.indicator.window.cget('background')).lower() == expected_palette['panel']
                          and str(app.indicator.label.cget('foreground')).lower() == expected_palette['fg'])
    app.appearance.set('深色')
    app.save_settings()
    root.update()
    persisted = json.loads((DATA / 'settings.json').read_text(encoding='utf-8')).get('appearance') == '深色'
    details['theme'] = themes
    results['theme_switch'] = all(themes.values()) and persisted
    results['theme_persisted'] = persisted

    # ---- 7. 歷史保留 prune --------------------------------------------------------------------------
    app.store.db.execute("INSERT INTO history(created,mode,text,seconds) VALUES ('2020-01-01 00:00:00','zh','old row',1)")
    app.store.db.execute("INSERT INTO history(mode,text,seconds) VALUES ('zh','fresh row',1)")
    app.store.db.commit()
    app._history()
    app.retention.set('永久')
    app.save_settings()
    kept_forever = any(r[2] == 'old row' for r in app.store.history())
    app.retention.set('1 週')
    app.save_settings()
    texts = [r[2] for r in app.store.history()]
    pruned = 'old row' not in texts and 'fresh row' in texts
    list_updated = not any('old row' in line for line in app.history.get(0, 'end'))
    saved_retention = json.loads((DATA / 'settings.json').read_text(encoding='utf-8')).get('retention') == '1 週'
    app.close()
    # 啟動時 prune：直接寫入舊資料列，重新開啟
    db = sqlite3.connect(str(DATA / 'history.sqlite3'))
    db.execute("INSERT INTO history(created,mode,text,seconds) VALUES ('2019-05-05 00:00:00','zh','older row',1)")
    db.commit()
    db.close()
    root, app = new_app()
    startup_pruned = 'older row' not in [r[2] for r in app.store.history()] and app.retention.get() == '1 週'
    details['retention'] = {'forever_keeps': kept_forever, 'one_week_prunes': pruned, 'list_updated': list_updated,
                            'persisted': saved_retention, 'startup_prune': startup_pruned}
    results['retention_prune'] = all(details['retention'].values())

    # ---- 8. 貼上後還原剪貼簿 -------------------------------------------------------------------------
    prior = 'prior-clipboard-' + str(int(time.time()))
    top = tk.Toplevel(root)
    top.title('V2T-wave-d-paste')
    top.geometry('420x80+260+260')
    entry = tk.Entry(top, width=50)
    entry.pack(padx=10, pady=10)
    top.attributes('-topmost', True)
    top.update()
    top.focus_force()
    entry.focus_force()
    pump(root, 0.5)
    window_context._write_text(prior)
    hwnd = window_context.foreground_window()
    is_fg = window_context.window_info(hwnd)['title'] == 'V2T-wave-d-paste'
    if not is_fg:
        force_foreground(desktop.ctypes.windll.user32.GetParent(top.winfo_id()) or top.winfo_id())
        pump(root, 0.3)
        hwnd = window_context.foreground_window()
        is_fg = window_context.window_info(hwnd)['title'] == 'V2T-wave-d-paste'
    clip = {'foreground_ok': is_fg}
    if is_fg:
        app.last_clipboard_restore = ''
        app._paste('PASTED-TEXT', target=hwnd)
        pump(root, 1.6)
        after, _ = window_context._read_text()
        clip.update({'entry_received_text': entry.get() == 'PASTED-TEXT', 'clipboard_restored': after == prior,
                     'state_restored': app.last_clipboard_restore == 'restored', 'pending_cleared': app.clip_saved is None})
    top.destroy()
    # 原本是非文字內容：略過還原並寫在狀態列
    window_context._write_text('pasted-answer')
    app.clip_saved = (None, True, 2)
    app.clip_seq = desktop.ctypes.windll.user32.GetClipboardSequenceNumber()
    app._restore_clipboard()
    clip['nontext_skipped'] = app.last_clipboard_restore == 'skipped' and '非文字' in app.status.get() \
        and window_context._read_text()[0] == 'pasted-answer'
    # 貼上後剪貼簿被別人改過：不覆蓋
    app.clip_saved = ('old', False, 1)
    app.clip_seq = -1
    app._restore_clipboard()
    clip['changed_by_others_skipped'] = app.last_clipboard_restore == 'skipped' and window_context._read_text()[0] == 'pasted-answer'
    details['clipboard'] = clip
    results['clipboard_restore'] = all(clip.values())
    app.close()

    # ---- 9. 靜態：背景執行緒不碰 Tk -------------------------------------------------------------------
    tree = ast.parse((repo / 'voice2txt' / 'desktop.py').read_text(encoding='utf-8'))
    allowed = {'events', 'jobs', 'audio', 'engine', 'session_translator', 'session_context', 'session_language'}
    violations = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in ('work', 'load', 'callback', '_decode'):
            used = {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)
                    and isinstance(n.value, ast.Name) and n.value.id == 'self'}
            if used - allowed:
                violations[node.name] = sorted(used - allowed)
    source = (repo / 'voice2txt' / 'desktop.py').read_text(encoding='utf-8')
    restore_sites = source.count('self._restore_audio()')
    details['thread_discipline'] = {'violations': violations, 'restore_audio_call_sites': restore_sites}
    results['tk_thread_discipline'] = not violations and restore_sites >= 2

    # ---- 10. 跨行程：LeftAlt+F23 ask 擷取另一行程 EDIT 的選取、三段合併貼上 -----------------------------
    results['cross_process_edit_capture_and_merged_paste'] = cross_process_check()


def finish():
    restored = restore_real_clipboard(getattr(main, 'real_text', None))
    after, _ = window_context._read_text()
    details['real_clipboard_restore'] = {'restored': restored, 'equal_after_run': after == getattr(main, 'real_text', None)}
    results['real_clipboard_restored'] = restored and after == getattr(main, 'real_text', None)
    report = {'ok': bool(results) and all(results.values()), 'results': results, 'details': details}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'ok': report['ok'], 'results': results}, ensure_ascii=False, indent=2))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    code = 1
    try:
        main()
    except Exception as error:
        import traceback
        results['exception'] = False
        details['exception'] = traceback.format_exc()
        print(details['exception'])
    finally:
        try:
            code = finish()
        finally:
            temp.cleanup()
    raise SystemExit(code)
