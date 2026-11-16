"""真機檢查：Tk Entry 內選取已知文字，capture_selection 取回並還原剪貼簿。不注入 Right Alt。"""
import json
import sys
import time
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from voice2txt import context  # noqa: E402

KNOWN = 'Voice2Txt 選取測試 12345'
PRIOR = 'prior-clipboard-' + str(int(time.time()))
USER_TEXT = 'user-own-copy-' + str(int(time.time()))
OUT = ROOT / 'verification' / 'context-capture-2026-11-13.json'


def clear_clipboard():
    import ctypes
    user32 = ctypes.windll.user32
    for _ in range(20):
        if user32.OpenClipboard(None):
            user32.EmptyClipboard()
            user32.CloseClipboard()
            return True
        time.sleep(0.05)
    return False


def restore_real_clipboard(saved):
    """還原檢查前的真實剪貼簿文字；原本是空的就清空。"""
    if saved is None:
        return clear_clipboard()
    return context._write_text(saved)


def pump(root, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        root.update()
        time.sleep(0.01)


def run_scenario(delay_ms, user_copy=False):
    """delay_ms=0：Tk Entry 內建 Ctrl+C（快速）；>0：攔截 Ctrl+C，延遲 delay_ms 後才寫剪貼簿（慢速目標）。"""
    import threading
    timeout = 0.4 if (delay_ms or user_copy) else 0.9  # 慢速／無選取情境用 0.4 重現原缺陷（出貨預設 0.9 秒）
    report = {'delay_ms': delay_ms, 'user_copy': user_copy, 'timeout_used': timeout, 'ok': False, 'stage': 'start'}
    root = tk.Tk()
    try:
        root.title('V2T-context-check')
        root.geometry('420x80+200+200')
        entry = tk.Entry(root, width=50)
        entry.pack(padx=10, pady=10)
        entry.insert(0, KNOWN)
        if delay_ms:
            def late_copy(_event):
                def write():
                    root.clipboard_clear()
                    root.clipboard_append(entry.selection_get())
                root.after(delay_ms, write)
                return 'break'
            entry.bind('<Control-c>', late_copy)
            entry.bind('<Control-C>', late_copy)
        root.attributes('-topmost', True)
        root.update()
        root.focus_force()
        entry.focus_force()
        if not user_copy:
            entry.select_range(0, 'end')
        pump(root, 0.5)
        root.clipboard_clear()
        root.clipboard_append(PRIOR)
        root.update()
        pump(root, 0.2)
        for _ in range(20):  # 前景偶爾被其他視窗搶走，重試取回焦點
            hwnd = context.foreground_window()
            info = context.window_info(hwnd)
            if info['title'] == 'V2T-context-check':
                break
            root.attributes('-topmost', True)
            root.focus_force()
            entry.focus_force()
            if not user_copy:
                entry.select_range(0, 'end')
            pump(root, 0.2)
        report['foreground'] = {'title': info['title'], 'process_name': info['process_name']}
        if info['title'] != 'V2T-context-check':
            report['stage'] = 'not_foreground'
            return report
        result = {}

        def work():
            started = time.monotonic()
            result['value'] = context.capture_selection(hwnd, timeout=timeout)
            result['seconds'] = round(time.monotonic() - started, 3)

        thread = threading.Thread(target=work)
        thread.start()
        while thread.is_alive():
            root.update()
            time.sleep(0.005)
        selection, restored_ok = result['value']
        report['capture_seconds'] = result['seconds']
        report['selection'] = selection
        report['returned'] = [selection, restored_ok]
        report['last_skip_reason'] = context.last_skip_reason
        if user_copy:
            # 無選取：目標不寫剪貼簿 -> 逾時；使用者 0.3 秒後在「別的程序」（桌面視窗為擁有者）自己複製，watcher 不得覆蓋。
            pump(root, 0.3)
            report['user_copy_written'] = context._write_text(USER_TEXT)
            pump(root, 2.8)  # 超過 watcher 寬限期（2 秒）與 settle
            after, _ = context._read_text()
            report['clipboard_after'] = after
            report['clipboard_kept_user_copy'] = after == USER_TEXT
            report['last_late_restore'] = context.last_late_restore
            report['ok'] = (selection == '' and restored_ok is False and context.last_skip_reason == 'late'
                            and report['user_copy_written'] and report['clipboard_kept_user_copy']
                            and context.last_late_restore is False)
        elif not delay_ms:
            pump(root, 0.2)
            after, _ = context._read_text()
            report['selection_matches'] = selection == KNOWN
            report['clipboard_after'] = after
            report['clipboard_restored'] = after == PRIOR
            report['had_other_formats'] = context.had_other_formats
            report['ok'] = report['selection_matches'] and report['clipboard_restored'] and restored_ok
        else:
            # 目標約 delay_ms 後才寫入；3 秒內剪貼簿應被 watcher 還原為 PRIOR。
            start = time.monotonic()
            restored_after = None
            while time.monotonic() - start < 3.0:
                root.update()
                text, _ = context._read_text()
                if time.monotonic() - start > delay_ms / 1000 + 0.2 and text == PRIOR and context.last_late_restore:
                    restored_after = round(time.monotonic() - start, 3)
                    break
                time.sleep(0.01)
            after, _ = context._read_text()
            report['clipboard_after'] = after
            report['clipboard_restored'] = after == PRIOR
            report['restored_within_seconds_after_return'] = restored_after
            report['last_late_restore'] = context.last_late_restore
            report['ok'] = (selection == '' and restored_ok is False and context.last_skip_reason == 'late'
                            and report['clipboard_restored'] and restored_after is not None
                            and restored_after < 3.0)
        report['stage'] = 'done'
        return report
    finally:
        root.destroy()


def main():
    real_text, real_other = context._read_text()  # 檢查前的真實剪貼簿文字（結束後還原）
    report = {'ok': False, 'stage': 'start',
              'real_clipboard_saved': {'had_text': real_text is not None, 'had_other_formats': bool(real_other)}}
    try:
        report['fast'] = run_scenario(0)
        time.sleep(0.3)
        report['delayed_700ms'] = run_scenario(700)
        # 舊欄位保留（fast 情境）
        for key in ('selection_matches', 'clipboard_restored', 'selection', 'clipboard_after', 'clipboard_prior',
                    'had_other_formats'):
            if key in report['fast']:
                report[key] = report['fast'][key]
        time.sleep(0.3)
        report['no_selection_user_copy'] = run_scenario(0, user_copy=True)
        report['clipboard_prior'] = PRIOR
        report['stage'] = 'done'
        report['ok'] = report['fast']['ok'] and report['delayed_700ms']['ok'] and report['no_selection_user_copy']['ok']
        return report
    finally:
        time.sleep(2.2)  # 等 watcher 寬限期結束，避免它動到之後還原的真實剪貼簿
        report['real_clipboard_restored'] = restore_real_clipboard(real_text)
        after_text, _ = context._read_text()
        report['real_clipboard_equal_after_run'] = after_text == real_text
        if not report['real_clipboard_equal_after_run']:
            report['ok'] = False


if __name__ == '__main__':
    try:
        data = main()
    except Exception as error:  # noqa: BLE001
        data = {'ok': False, 'error': repr(error)}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(data, ensure_ascii=False))
    sys.exit(0 if data.get('ok') else 1)
