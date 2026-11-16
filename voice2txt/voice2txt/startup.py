"""登入 Windows 時自動啟動：HKCU\Software\Microsoft\Windows\CurrentVersion\Run。

RUN_KEY_PATH 可在模組層級被覆寫（檢查腳本用暫存子鍵），函式也可明確傳入 key_path。
"""
import sys
from pathlib import Path

RUN_KEY_PATH = r'Software\Microsoft\Windows\CurrentVersion\Run'
VALUE_NAME = 'Voice2Txt'


def build_run_command(exe, frozen, script=None):
    """frozen：'"<exe>" --minimized'；原始碼：'"<python>" "<run_desktop.py>" --minimized'。"""
    if frozen:
        return f'"{exe}" --minimized'
    if script is None:
        script = Path(__file__).resolve().parent.parent / 'run_desktop.py'
    return f'"{exe}" "{script}" --minimized'


def current_command():
    """目前這份程式的啟動指令；原始碼模式優先用 pythonw.exe 避免跳出主控台。"""
    exe = sys.executable
    frozen = bool(getattr(sys, 'frozen', False))
    if not frozen:
        windowless = Path(exe).with_name('pythonw.exe')
        if windowless.exists():
            exe = str(windowless)
    return build_run_command(exe, frozen)


def _winreg():
    import winreg
    return winreg


def enable(command=None, key_path=None, name=VALUE_NAME):
    winreg = _winreg()
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path or RUN_KEY_PATH) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, command or current_command())


def disable(key_path=None, name=VALUE_NAME):
    winreg = _winreg()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path or RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, name)
    except FileNotFoundError:
        pass


def get_value(key_path=None, name=VALUE_NAME):
    winreg = _winreg()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path or RUN_KEY_PATH) as key:
            return winreg.QueryValueEx(key, name)[0]
    except FileNotFoundError:
        return None


def is_enabled(key_path=None, name=VALUE_NAME):
    return get_value(key_path, name) is not None
