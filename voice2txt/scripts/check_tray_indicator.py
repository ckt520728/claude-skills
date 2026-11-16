"""系統匣／浮動指示器／登入啟動的真實檢查（Windows）。

- 暫存 LOCALAPPDATA；登入啟動的登錄路徑改成暫存子鍵（startup.RUN_KEY_PATH），不動真實 Voice2Txt 值。
- 驗證：Shell_NotifyIcon NIM_ADD、托盤點擊訊息 -> events queue、關閉鈕縮到系統匣、
  指示器顯示／隱藏前後 GetForegroundWindow 不變且樣式含 WS_EX_NOACTIVATE、登錄 round-trip、
  --minimized 子程序不顯示主視窗、NIM_DELETE 與執行緒結束、tasklist 無殘留 python。
結果寫入 verification/tray-indicator-2026-11-13.json（或第一個參數）。
"""
import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import winreg
from ctypes import wintypes
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
output = Path(sys.argv[1]) if len(sys.argv) > 1 else repo / 'verification' / 'tray-indicator-2026-11-13.json'
sys.path.insert(0, str(repo))

temp = tempfile.TemporaryDirectory()
os.environ['LOCALAPPDATA'] = temp.name
os.environ.pop('ANTHROPIC_API_KEY', None)

from voice2txt import startup, tray

REAL_KEY = startup.RUN_KEY_PATH
TEMP_PARENT = r'Software\Voice2TxtCheck-' + uuid.uuid4().hex[:8]
TEMP_KEY = TEMP_PARENT + r'\Run'
user32 = ctypes.windll.user32
user32.GetForegroundWindow.restype = ctypes.c_void_p
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = ctypes.c_ssize_t
user32.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.IsWindowVisible.argtypes = [wintypes.HWND]


def python_pids():
    """命令列含本專案路徑的 python／Voice2Txt 程序（不含無關的 MCP python）。tasklist 確認映像名稱。"""
    names = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True, text=True).stdout
    running = set()
    for line in names.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) > 1 and parts[0].strip('"').lower() in ('python.exe', 'pythonw.exe', 'voice2txt.exe'):
            running.add(int(parts[1]))
    command = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*run_desktop*' -or "
               "$_.Name -eq 'Voice2Txt.exe' } | ForEach-Object { $_.ProcessId }")
    out = subprocess.run(['powershell', '-NoProfile', '-Command', command], capture_output=True, text=True).stdout
    return {int(x) for x in out.split() if x.isdigit()} & running


def pump(root, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        root.update()
        time.sleep(0.02)


def minimized_child_check():
    """另起 run_desktop.py --minimized：應有系統匣視窗、沒有可見主視窗。"""
    result = {}
    child_data = tempfile.TemporaryDirectory()
    env = dict(os.environ, LOCALAPPDATA=child_data.name)
    proc = subprocess.Popen([sys.executable, str(repo / 'run_desktop.py'), '--minimized'], env=env, cwd=str(repo))
    found = {'tray': None, 'visible_titles': []}
    WNDENUM = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]

    def scan():
        # venv 的 python.exe 可能是 launcher：把子程序樹的 pid 都納入。
        pids = {proc.pid}
        command = 'Get-CimInstance Win32_Process | ForEach-Object { "$($_.ProcessId),$($_.ParentProcessId)" }'
        out = subprocess.run(['powershell', '-NoProfile', '-Command', command], capture_output=True, text=True).stdout
        changed = True
        rows = [line.strip().split(',') for line in out.splitlines() if line.count(',') == 1]
        while changed:
            changed = False
            for pid, ppid in rows:
                if ppid.isdigit() and pid.isdigit() and int(ppid) in pids and int(pid) not in pids:
                    pids.add(int(pid))
                    changed = True
        found['tray'], found['visible_titles'] = None, []

        def callback(hwnd, lparam):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value in pids:
                cls = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, cls, 256)
                title = ctypes.create_unicode_buffer(256)
                user32.GetWindowTextW(hwnd, title, 256)
                if cls.value.startswith('Voice2TxtTray'):
                    found['tray'] = hwnd
                elif user32.IsWindowVisible(hwnd) and title.value:
                    found['visible_titles'].append(title.value)
            return True
        user32.EnumWindows(WNDENUM(callback), 0)
    try:
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline and proc.poll() is None:
            scan()
            if found['tray']:
                break
            time.sleep(1)
        time.sleep(2)
        scan()
        result['minimized_tray_window_found'] = bool(found['tray'])
        result['minimized_visible_windows'] = list(found['visible_titles'])
        result['minimized_no_main_window'] = bool(found['tray']) and not any('Voice2Txt' in t for t in found['visible_titles'])
    finally:
        if found['tray']:
            user32.PostMessageW(found['tray'], tray.WM_CLOSE, 0, 0)  # 讓子程序的 tray 執行緒做 NIM_DELETE
            time.sleep(1)
        subprocess.run(['taskkill', '/T', '/F', '/PID', str(proc.pid)], capture_output=True)
        proc.wait(10)
        time.sleep(1)
        shutil.rmtree(child_data.name, ignore_errors=True)
        child_data.cleanup = lambda: None
    return result



LEFTOVER_KEY = r'Software\Voice2TxtCheck-abef8643'  # 早先某次執行（本腳本）留下的空鍵；只刪這一個確切名稱
EMPTY_REPORT_KEY = 'leftover_key_cleanup'


def key_tree(path):
    """回傳子鍵樹 {name: {...}} 與是否有任何值；不存在回傳 None。"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            subkeys, values, _ = winreg.QueryInfoKey(key)
            return {'values': values,
                    'subkeys': {winreg.EnumKey(key, i): key_tree(path + '\\' + winreg.EnumKey(key, i))
                                for i in range(subkeys)}}
    except FileNotFoundError:
        return None


def tree_is_empty(tree):
    return tree is not None and tree['values'] == 0 and all(tree_is_empty(t) for t in tree['subkeys'].values())


def delete_tree(path, tree):
    for name, sub in tree['subkeys'].items():
        delete_tree(path + '\\' + name, sub)
    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)


def remove_leftover_key():
    """刪除先前留下的空鍵 HKCU\\Software\\Voice2TxtCheck-abef8643（確認整棵樹沒有任何值才刪），並記錄前後。"""
    before = key_tree(LEFTOVER_KEY)
    record = {'key': 'HKCU\\' + LEFTOVER_KEY, 'existed_before': before is not None, 'tree_before': before}
    if before is not None:
        record['was_empty'] = tree_is_empty(before)
        if record['was_empty']:
            delete_tree(LEFTOVER_KEY, before)
        else:
            record['skipped'] = '鍵內有值，未刪除'
    record['exists_after'] = key_tree(LEFTOVER_KEY) is not None
    return record


def cleanup_registry():
    """finally 內呼叫：不論前面哪一步失敗，都刪掉這次建立的暫存登錄子鍵、還原 RUN_KEY_PATH。"""
    startup.RUN_KEY_PATH = REAL_KEY
    errors = []
    for path in (TEMP_KEY, TEMP_PARENT):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
        except FileNotFoundError:
            pass
        except OSError as error:
            errors.append(f'{path}: {error}')
    report['temp_key_removed'] = key_tree(TEMP_PARENT) is None
    if errors:
        report['temp_key_cleanup_errors'] = errors
    previous = None
    if output.exists():
        try:
            previous = json.loads(output.read_text(encoding='utf-8')).get(EMPTY_REPORT_KEY)
        except (OSError, ValueError):
            previous = None
    record = remove_leftover_key()
    if not record['existed_before'] and previous and previous.get('existed_before'):
        record = dict(previous, carried_over_from_previous_run=True)  # 上一次執行已刪掉，保留當時的前後記錄
    report[EMPTY_REPORT_KEY] = record


report = {}
real_before = startup.get_value(REAL_KEY)
report['real_run_value_before'] = real_before
before_pids = python_pids()
try:
    startup.RUN_KEY_PATH = TEMP_KEY  # 之後所有 enable/disable/is_enabled 都只碰暫存子鍵

    import tkinter as tk
    from voice2txt.desktop import App, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW

    root = tk.Tk()
    root.withdraw()
    app = None
    try:
        app = App(root, enable_tray=True)
        root.update()
        t = app.tray
        report['tray_added'] = bool(t.added)
        report['tray_thread_alive'] = t.running
        report['tray_window_class'] = t._class_name
        report['tray_error'] = t.error

        # 模擬左鍵點擊托盤圖示：訊息由 tray 執行緒的 WndProc 處理，轉成 ('tray', 'show') 事件。
        root.withdraw()
        user32.SendMessageW(t.hwnd, tray.WM_APP_TRAY, 1, tray.WM_LBUTTONUP)
        pump(root, 0.3)
        report['tray_click_shows_window'] = root.state() == 'normal'

        # 關閉鈕 + close_to_tray：只隱藏，不結束。
        app.close_to_tray.set(True)
        app.on_window_close()
        pump(root, 0.2)
        report['close_button_hides_to_tray'] = root.state() == 'withdrawn' and not app.closed
        app.events.put(('tray', 'show'))
        pump(root, 0.3)
        report['tray_show_event_restores'] = root.state() == 'normal'
        root.withdraw()

        # 指示器不得搶焦點。
        fg_before = user32.GetForegroundWindow()
        app.indicator.show('● 錄音中 · 口述（繁體中文）')
        pump(root, 0.5)
        fg_shown = user32.GetForegroundWindow()
        viewable = bool(app.indicator.window.winfo_viewable())
        geometry = (app.indicator.window.winfo_x(), app.indicator.window.winfo_y(), app.indicator.window.winfo_width(),
                    app.indicator.window.winfo_height())
        screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
        app.indicator.set_text('整理中…')
        pump(root, 0.3)
        fg_processing = user32.GetForegroundWindow()
        label_text = app.indicator.text.get()
        app.indicator.hide()
        pump(root, 0.3)
        fg_after = user32.GetForegroundWindow()
        styles = [user32.GetWindowLongW(h, -20) for h in {app.indicator.window.winfo_id(),
                                                          user32.GetAncestor(app.indicator.window.winfo_id(), 2) or 0}
                  if h]
        report['indicator'] = {
            'foreground_before': fg_before, 'foreground_shown': fg_shown, 'foreground_processing': fg_processing,
            'foreground_after': fg_after, 'viewable_when_shown': viewable, 'hidden_after': not app.indicator.visible,
            'text_while_processing': label_text, 'geometry_xywh': list(geometry), 'screen': [screen_w, screen_h],
            'horizontally_centered': abs((geometry[0] + geometry[2] / 2) - screen_w / 2) <= 2,
            'near_bottom': screen_h - (geometry[1] + geometry[3]) < screen_h * 0.2,
            'ex_styles_hex': [hex(s) for s in styles],
            'has_noactivate_toolwindow': all(s & WS_EX_NOACTIVATE and s & WS_EX_TOOLWINDOW for s in styles),
        }
        report['indicator_foreground_unchanged'] = len({fg_before, fg_shown, fg_processing, fg_after}) == 1
        report['indicator_foreground_unchanged'] = bool(report['indicator_foreground_unchanged'])

        # 登入啟動 round-trip（暫存登錄子鍵）。
        expected = startup.current_command()
        steps = {'initial': startup.is_enabled()}
        app.start_at_login.set(True)
        app._login_toggled()
        steps['after_enable'] = startup.is_enabled()
        steps['value_matches_command'] = startup.get_value() == expected
        app.start_at_login.set(False)
        app._login_toggled()
        steps['after_disable'] = startup.is_enabled()
        steps['run_command'] = expected
        report['startup_steps'] = steps
        report['startup_roundtrip_ok'] = (steps['initial'] is False and steps['after_enable'] is True
                                          and steps['value_matches_command'] and steps['after_disable'] is False)

        # 設定持久化。
        app.close_to_tray.set(False)
        app.start_at_login.set(False)
        app.save_settings()
        saved = json.loads((Path(temp.name) / 'Voice2Txt' / 'settings.json').read_text(encoding='utf-8'))
        report['settings_persisted'] = saved.get('close_to_tray') is False and saved.get('start_at_login') is False

        # 沒有勾選縮到系統匣時，關閉鈕等同結束（另建一個 App 驗證，避免影響後面的 tray 乾淨結束檢查）。
        # 結束：走托盤 '結束' 事件 -> close()。
        app.events.put(('tray', 'quit'))
        deadline = time.monotonic() + 5
        while not app.closed and time.monotonic() < deadline:
            try:
                root.update()
            except tk.TclError:
                break
            time.sleep(0.02)
        report['quit_event_closes_app'] = app.closed
        report['tray_deleted_nim_delete'] = bool(t.deleted)
        report['tray_thread_stopped'] = not t.running
        report['tray_added_after_close'] = bool(t.added)
    except Exception as error:  # 保留已完成的欄位，讓失敗位置可見
        import traceback
        report['error'] = repr(error)
        report['traceback'] = traceback.format_exc()
        if app is not None and app.tray is not None:
            app.tray.close()
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass

    report.update(minimized_child_check())

finally:
    cleanup_registry()

startup.RUN_KEY_PATH = REAL_KEY
real_after = startup.get_value(REAL_KEY)
report['real_run_value_after'] = real_after
report['real_run_value_unchanged'] = real_before == real_after
time.sleep(1)
new_pids = python_pids() - before_pids
report['new_python_processes_after'] = sorted(new_pids)
report['no_zombie_python'] = not new_pids
temp.cleanup()

required = ['tray_added', 'tray_click_shows_window', 'close_button_hides_to_tray', 'tray_show_event_restores',
            'indicator_foreground_unchanged', 'startup_roundtrip_ok', 'settings_persisted', 'quit_event_closes_app',
            'tray_deleted_nim_delete', 'tray_thread_stopped', 'minimized_no_main_window', 'temp_key_removed',
            'real_run_value_unchanged', 'no_zombie_python']
indicator = report.get('indicator', {})
report['ok'] = (all(report.get(k) is True for k in required) and 'error' not in report
                and report.get(EMPTY_REPORT_KEY, {}).get('exists_after') is False
                and indicator.get('has_noactivate_toolwindow') is True and indicator.get('viewable_when_shown') is True
                and indicator.get('horizontally_centered') is True and indicator.get('hidden_after') is True
                and indicator.get('text_while_processing') == '整理中…')
output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in report.items() if k not in ('traceback', 'startup_steps')}, ensure_ascii=False))
raise SystemExit(0 if report['ok'] else 1)
