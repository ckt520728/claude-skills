"""單一執行個體真機檢查：啟動兩個 `run_desktop.py --minimized`。

驗證：
- 第二個執行個體在 5 秒內以 exit code 0 結束；
- 結束後只剩一個系統匣圖示（也就是只有一個擁有 WH_KEYBOARD_LL hook 的程序）；
- 第二個執行個體廣播的 Voice2TxtShowWindow 讓第一個顯示主視窗；
- 最後終止第一個，確認沒有任何程序、系統匣視窗與 mutex 殘留。
每個子程序用各自的暫存 LOCALAPPDATA，不碰真實設定；不動真實 HKCU Run。
結果寫入 verification/single-instance-2026-11-13.json（或第一個參數）。
"""
import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
output = Path(sys.argv[1]) if len(sys.argv) > 1 else repo / 'verification' / 'single-instance-2026-11-13.json'
sys.path.insert(0, str(repo))
from voice2txt.desktop import SINGLE_INSTANCE_MUTEX  # noqa: E402

user32 = ctypes.windll.user32
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
kernel32.OpenMutexW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.OpenMutexW.restype = ctypes.c_void_p
kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
WNDENUM = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
SYNCHRONIZE = 0x00100000


def mutex_exists():
    handle = kernel32.OpenMutexW(SYNCHRONIZE, False, SINGLE_INSTANCE_MUTEX)
    if handle:
        kernel32.CloseHandle(handle)
        return True
    return False


def process_rows():
    command = ('Get-CimInstance Win32_Process | ForEach-Object { "$($_.ProcessId),$($_.ParentProcessId),'
               '$($_.Name),$($_.CommandLine)" }')
    out = subprocess.run(['powershell', '-NoProfile', '-Command', command], capture_output=True, text=True,
                         encoding='utf-8', errors='replace').stdout
    rows = []
    for line in out.splitlines():
        parts = line.strip().split(',', 3)
        if len(parts) >= 3 and parts[0].isdigit() and parts[1].isdigit():
            rows.append((int(parts[0]), int(parts[1]), parts[2], parts[3] if len(parts) > 3 else ''))
    return rows


def tree(root_pid, rows):
    pids = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, ppid, _, _ in rows:
            if ppid in pids and pid not in pids:
                pids.add(pid)
                changed = True
    return pids


def windows():
    """回傳 [(hwnd, pid, class, title, visible)]。"""
    found = []

    def callback(hwnd, lparam):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        title = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, title, 256)
        found.append((hwnd, pid.value, cls.value, title.value, bool(user32.IsWindowVisible(hwnd))))
        return True
    user32.EnumWindows(WNDENUM(callback), 0)
    return found


def tray_windows():
    return [w for w in windows() if w[2].startswith('Voice2TxtTray')]


def project_processes(rows):
    """命令列含 run_desktop 的 python，或 Voice2Txt.exe。"""
    return [(pid, name) for pid, _, name, cmd in rows
            if ('run_desktop' in cmd and name.lower().startswith('python')) or name.lower() == 'voice2txt.exe']


def launch(data_dir):
    env = dict(os.environ, LOCALAPPDATA=data_dir)
    return subprocess.Popen([sys.executable, str(repo / 'run_desktop.py'), '--minimized'], env=env, cwd=str(repo))


def main():
    report = {'ok': False}
    dirs = [tempfile.mkdtemp(prefix='v2t-si-1-'), tempfile.mkdtemp(prefix='v2t-si-2-')]
    first = second = None
    try:
        rows = process_rows()
        report['preflight'] = {'mutex_exists': mutex_exists(), 'tray_windows': len(tray_windows()),
                               'project_processes': project_processes(rows)}
        if report['preflight']['mutex_exists'] or report['preflight']['tray_windows'] or report['preflight']['project_processes']:
            report['error'] = '已有 Voice2Txt 在執行，無法做乾淨的單一執行個體檢查'
            return finish(report)
        before_pids = {pid for pid, _, _, _ in rows}

        first = launch(dirs[0])
        first_tree = {first.pid}
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline and first.poll() is None:
            first_tree = tree(first.pid, process_rows())
            if any(w[1] in first_tree for w in tray_windows()) and mutex_exists():
                break
            time.sleep(0.5)
        first_trays = [w for w in tray_windows() if w[1] in first_tree]
        report['first'] = {'pid': first.pid, 'tree_pids': sorted(first_tree), 'tray_windows': len(first_trays),
                           'mutex_exists': mutex_exists(),
                           'main_window_visible_before': any(w[4] and 'Voice2Txt' in w[3] and w[1] in first_tree
                                                             for w in windows())}
        if not first_trays:
            report['error'] = '第一個執行個體沒有建立系統匣視窗'
            return finish(report)

        started = time.monotonic()
        second = launch(dirs[1])
        try:
            second.wait(5)
        except subprocess.TimeoutExpired:
            pass
        elapsed = time.monotonic() - started
        report['second_instance_exit_code'] = second.poll()
        report['second_instance_exit_seconds'] = round(elapsed, 2)
        time.sleep(1.5)  # 讓第一個處理廣播訊息、顯示視窗

        rows = process_rows()
        now_trays = tray_windows()
        owners = sorted({w[1] for w in now_trays})
        second_tree_alive = [pid for pid in tree(second.pid, rows) if pid != second.pid or second.poll() is None]
        report['after_second'] = {
            'first_alive': first.poll() is None,
            'tray_windows_total': len(now_trays),
            'tray_window_owner_pids': owners,
            'second_tree_alive_pids': [pid for pid in second_tree_alive if pid in {r[0] for r in rows}],
            'project_processes': project_processes(rows),
            'mutex_exists': mutex_exists(),
        }
        visible_main = [w[3] for w in windows() if w[4] and 'Voice2Txt' in w[3] and w[1] in first_tree]
        report['first_window_shown_by_broadcast'] = bool(visible_main)
        report['first_visible_window_titles'] = visible_main
        # 擁有系統匣視窗（= 擁有鍵盤 hook）的程序只有一個，且屬於第一個執行個體。
        report['one_instance_remaining'] = (len(now_trays) == 1 and len(owners) == 1 and owners[0] in first_tree
                                           and not report['after_second']['second_tree_alive_pids']
                                           and report['after_second']['first_alive'])
        report['ok'] = (report['second_instance_exit_code'] == 0 and elapsed <= 5
                        and report['one_instance_remaining'] and report['first_window_shown_by_broadcast'])
        return finish(report, first, first_tree, before_pids)
    finally:
        for proc in (second, first):
            if proc is not None and proc.poll() is None:
                subprocess.run(['taskkill', '/T', '/F', '/PID', str(proc.pid)], capture_output=True)
        for path in dirs:
            shutil.rmtree(path, ignore_errors=True)


def finish(report, first=None, first_tree=None, before_pids=None):
    if first is not None:
        # 終止第一個，確認沒有殘留。
        subprocess.run(['taskkill', '/T', '/F', '/PID', str(first.pid)], capture_output=True)
        try:
            first.wait(10)
        except subprocess.TimeoutExpired:
            pass
        time.sleep(1.5)
        rows = process_rows()
        leftover = [pid for pid in (first_tree or ()) if pid in {r[0] for r in rows}]
        report['after_terminate'] = {'leftover_tree_pids': leftover, 'tray_windows': len(tray_windows()),
                                     'mutex_exists': mutex_exists(), 'project_processes': project_processes(rows)}
        report['no_process_left'] = (not leftover and not report['after_terminate']['tray_windows']
                                     and not report['after_terminate']['project_processes']
                                     and not report['after_terminate']['mutex_exists'])
        report['ok'] = bool(report['ok'] and report['no_process_left'])
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    print('PASS' if report['ok'] else 'FAIL')
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
