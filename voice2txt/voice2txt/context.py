"""前景視窗脈絡：視窗標題、程序名稱、App 類別，以及用 Ctrl+C 取得的選取文字（僅 ctypes）。"""
import os
import threading
import time

CF_UNICODETEXT = 13
VK_CONTROL, VK_C = 0x11, 0x43
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

CATEGORIES = (
    ('browser', ('chrome', 'msedge', 'firefox', 'brave', 'opera', 'vivaldi')),
    ('email', ('outlook', 'olk', 'thunderbird', 'hxoutlook')),
    ('code', ('code', 'devenv', 'pycharm', 'pycharm64', 'idea', 'idea64', 'windowsterminal', 'powershell',
              'pwsh', 'cmd', 'wt')),
    ('chat', ('teams', 'ms-teams', 'slack', 'discord', 'line', 'telegram', 'whatsapp')),
    ('document', ('winword', 'excel', 'powerpnt', 'notion', 'obsidian', 'notepad')),
)
MAIL_TITLE_WORDS = ('mail', '郵件', '信箱')

had_other_formats = False  # 最近一次 capture_selection 時剪貼簿是否含 CF_UNICODETEXT 以外的格式（無法還原）


def categorize(process_name, title=''):
    """依程序名稱與視窗標題判斷類別：browser/email/code/chat/document/other。"""
    name = os.path.basename(process_name or '').lower()
    if name.endswith('.exe'):
        name = name[:-4]
    lowered = (title or '').lower()
    for category, names in CATEGORIES:
        if name in names:
            if category == 'browser' and any(k in lowered for k in MAIL_TITLE_WORDS):
                return 'email'
            return category
    if not name and any(k in lowered for k in MAIL_TITLE_WORDS):
        return 'email'
    return 'other'


def _api():
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetDesktopWindow.restype = wintypes.HWND
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = ctypes.c_void_p
    user32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.EnumClipboardFormats.argtypes = [wintypes.UINT]
    user32.GetClipboardSequenceNumber.restype = wintypes.DWORD
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                    ctypes.POINTER(wintypes.DWORD)]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    return ctypes, wintypes, user32, kernel32


def foreground_window():
    _, _, user32, _ = _api()
    return user32.GetForegroundWindow() or 0


def window_info(hwnd):
    """回傳 {hwnd, title, process_name, exe_path}；取不到的欄位為空字串。"""
    ctypes, wintypes, user32, kernel32 = _api()
    info = {'hwnd': hwnd or 0, 'title': '', 'process_name': '', 'exe_path': ''}
    if not hwnd:
        return info
    buffer = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buffer, 512)
    info['title'] = buffer.value
    pid = wintypes.DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value:
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if handle:
            try:
                path = ctypes.create_unicode_buffer(1024)
                size = wintypes.DWORD(1024)
                if kernel32.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size)):
                    info['exe_path'] = path.value
                    info['process_name'] = os.path.splitext(os.path.basename(path.value))[0]
            finally:
                kernel32.CloseHandle(handle)
    return info


def _open_clipboard(user32, tries=20, owner=None):
    for _ in range(tries):
        if user32.OpenClipboard(owner):
            return True
        time.sleep(0.01)
    return False


def _read_clipboard():
    """回傳 (ok, text 或 None, 是否另有非文字格式)。ok=False 表示剪貼簿打不開（被占用），與「空的」不同。"""
    ctypes, _, user32, kernel32 = _api()
    if not _open_clipboard(user32):
        return False, None, False
    try:
        formats, fmt = [], 0
        while True:
            fmt = user32.EnumClipboardFormats(fmt)
            if not fmt:
                break
            formats.append(fmt)
        # 1 TEXT、7 OEMTEXT、16 LOCALE 由 Windows 自動隨 UNICODETEXT 合成，不算「其他格式」。
        other = any(f not in (CF_UNICODETEXT, 1, 7, 16) for f in formats)
        if CF_UNICODETEXT not in formats:
            return True, None, other
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        pointer = kernel32.GlobalLock(handle) if handle else None
        if not pointer:
            return True, None, other
        try:
            return True, ctypes.wstring_at(pointer), other
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def _read_text():
    """回傳 (text 或 None, 是否另有非文字格式)；打不開剪貼簿時回傳 (None, False)（舊介面）。"""
    _, text, other = _read_clipboard()
    return text, other


def _write_text(text):
    """寫回剪貼簿文字；text 為 None 時清空剪貼簿。"""
    ctypes, _, user32, kernel32 = _api()
    # owner 用 GetDesktopWindow：OpenClipboard(NULL) 後 EmptyClipboard 會讓 SetClipboardData 偶爾失敗（1418）。
    if not _open_clipboard(user32, owner=user32.GetDesktopWindow()):
        return False
    try:
        user32.EmptyClipboard()
        if text is None:
            return True
        data = ctypes.create_unicode_buffer(text)
        size = ctypes.sizeof(data)
        handle = kernel32.GlobalAlloc(0x2, size)  # GMEM_MOVEABLE
        if not handle:
            return False
        pointer = kernel32.GlobalLock(handle)
        ctypes.memmove(pointer, ctypes.addressof(data), size)
        kernel32.GlobalUnlock(handle)
        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            kernel32.GlobalFree(handle)
            return False
        return True
    finally:
        user32.CloseClipboard()


SKIP_MESSAGES = {
    'busy': '剪貼簿正被其他程式使用，這次未擷取選取文字。',
    'non_text': '剪貼簿含有無法還原的內容（圖片、檔案或帶格式文字），為避免遺失，這次未擷取選取文字。',
    'late': '未取得選取文字（目標未回應或無選取）；若目標稍後才回應，剪貼簿會自動還原',
}
last_skip_reason = ''  # 最近一次 capture_selection 略過擷取的原因：'' / 'busy' / 'non_text' / 'late'
last_late_restore = False  # 逾時後由背景 watcher 還原剪貼簿是否已發生（每次新擷取開始時清為 False）
LATE_GRACE = 2.0  # 逾時後 watcher 繼續監看的秒數
_watcher_cancel = None  # 目前 watcher 的取消旗標（threading.Event）


def capture_skip_reason(ok, other):
    """剪貼簿讀取結果 -> 略過擷取的原因（純函式）。打不開（busy）或含非文字格式（non_text）時不能擷取，
    因為只能還原 CF_UNICODETEXT；略過時完全不碰剪貼簿。"""
    if not ok:
        return 'busy'
    if other:
        return 'non_text'
    return ''


def window_pid(hwnd):
    """視窗所屬程序 pid；取不到回傳 0。"""
    if not hwnd:
        return 0
    try:
        ctypes, wintypes, user32, _ = _api()
        pid = wintypes.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value
    except Exception:
        return 0


def clipboard_owner_pid():
    """目前剪貼簿擁有者視窗（GetClipboardOwner）所屬的 pid；沒有擁有者或取不到回傳 0。"""
    try:
        _, _, user32, _ = _api()
        return window_pid(user32.GetClipboardOwner())
    except Exception:
        return 0


def _late_watch(cancel, get_sequence, write, saved, baseline, target_pid=0, owner_pid=None,
                grace=LATE_GRACE, settle=0.4, merge=0.15, poll=0.005):
    """逾時後的背景監看：序號相對 baseline 前進一次「寫入」（目標程式晚寫入）就還原 saved（None＝清空）。
    一次寫入在 Windows 上會讓序號連跳數次（Empty＋各格式），所以相隔不到 merge 秒的變動合併成同一次寫入；
    寫入穩定 settle 秒後，若只有一次寫入、且剪貼簿擁有者（owner_pid()）的 pid 等於擷取時的 target_pid 才還原；
    出現兩次以上、擁有者不是目標程序（例如使用者在別的程式自己複製）、擁有者取不到、target_pid 為 0 或被取消，都不動剪貼簿。
    永不拋例外、不碰 Tk。"""
    global last_late_restore
    try:
        deadline = time.monotonic() + grace
        last = baseline
        groups, last_change = 0, 0.0
        while not cancel.is_set():
            now = time.monotonic()
            current = get_sequence()
            if current != last:
                if groups == 0 or now - last_change > merge:
                    groups += 1
                last, last_change = current, now
            if groups and now - last_change >= settle:
                owner = (owner_pid or clipboard_owner_pid)()
                if groups == 1 and target_pid and owner and owner == target_pid and write(saved):
                    last_late_restore = True
                return
            if not groups and now >= deadline:
                return
            time.sleep(poll)
    except Exception:
        pass


def capture_selection(hwnd=None, timeout=0.9):
    """以 Ctrl+C（帶 hotkeys.MARKER）取得目標視窗的選取文字，之後還原原本的剪貼簿文字。

    回傳 (selection 或 '', restored_ok)。只保存／還原 CF_UNICODETEXT：剪貼簿含其他格式（無法還原）或打不開時
    不注入 Ctrl+C、不碰剪貼簿，回傳 ('', False)，原因記在模組屬性 last_skip_reason。
    沒有選取時剪貼簿序號不變，不做任何改動。逾時（目標程式 timeout 內沒寫剪貼簿）回傳 ('', False)、
    last_skip_reason='late'，並啟動背景 watcher：之後 LATE_GRACE 秒內若序號恰前進一次就還原原本文字。
    """
    global had_other_formats, last_skip_reason, last_late_restore, _watcher_cancel
    from voice2txt import hotkeys
    _, _, user32, _ = _api()
    if _watcher_cancel is not None:
        _watcher_cancel.set()  # 新的擷取開始：取消上一個 watcher
        _watcher_cancel = None
    last_skip_reason = ''
    last_late_restore = False
    if hwnd and user32.GetForegroundWindow() != hwnd:
        return '', True  # 焦點已不在目標視窗，不注入按鍵。
    ok, saved, had_other_formats = _read_clipboard()
    last_skip_reason = capture_skip_reason(ok, had_other_formats)
    if last_skip_reason:
        return '', False
    sequence = user32.GetClipboardSequenceNumber()
    for vk, up in ((VK_CONTROL, False), (VK_C, False), (VK_C, True), (VK_CONTROL, True)):
        hotkeys.send_key(vk, up, hotkeys.MARKER)
    deadline = time.monotonic() + timeout
    while user32.GetClipboardSequenceNumber() == sequence and time.monotonic() < deadline:
        time.sleep(0.01)
    if user32.GetClipboardSequenceNumber() == sequence:
        last_skip_reason = 'late'
        _watcher_cancel = threading.Event()
        threading.Thread(target=_late_watch, daemon=True, name='ctx-late-restore',
                         args=(_watcher_cancel, user32.GetClipboardSequenceNumber, _write_text, saved, sequence,
                               window_pid(hwnd))).start()
        return '', False
    time.sleep(0.02)
    selection, _ = _read_text()
    restored = _write_text(saved)
    return selection or '', restored


def foreground_context(capture=True):
    """前景視窗脈絡 dict：{app, title, selection, category, process_name, hwnd, capture_skipped}。
    capture_skipped 為略過擷取的原因（'' / 'busy' / 'non_text' / 'late'）。失敗時回傳空欄位。"""
    try:
        hwnd = foreground_window()
        info = window_info(hwnd)
        selection, skipped = '', ''
        if capture and hwnd:
            selection, _ = capture_selection(hwnd)
            skipped = last_skip_reason
        process = info['process_name']
        return {'app': process, 'title': info['title'], 'selection': selection,
                'category': categorize(process, info['title']), 'process_name': process, 'hwnd': hwnd,
                'capture_skipped': skipped}
    except Exception:
        return {'app': '', 'title': '', 'selection': '', 'category': 'other', 'process_name': '', 'hwnd': 0,
                'capture_skipped': ''}
