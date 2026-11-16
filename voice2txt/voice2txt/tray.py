"""Win32 系統匣圖示（ctypes Shell_NotifyIcon），不依賴 pystray／Pillow／pywin32。

自己的執行緒建立隱藏視窗並跑 GetMessageW 訊息迴圈；選單選擇透過 callback(action) 交出
（App 會把它包成 ('tray', action) 放進 events queue，Tk 只在 Tk 執行緒操作）。
注意：TaskbarCreated 是廣播訊息，message-only 視窗收不到，所以這裡用不顯示的一般頂層視窗。
"""
import ctypes
import sys
import threading
from ctypes import wintypes
from pathlib import Path

WM_APP_TRAY = 0x8000 + 1  # WM_APP + 1
WM_DESTROY, WM_CLOSE, WM_NULL = 0x0002, 0x0010, 0x0000
WM_LBUTTONUP, WM_RBUTTONUP = 0x0202, 0x0205
NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP = 1, 2, 4
MF_STRING, MF_SEPARATOR = 0, 0x800
TPM_RIGHTBUTTON, TPM_RETURNCMD, TPM_BOTTOMALIGN = 0x2, 0x100, 0x20
IMAGE_ICON, LR_LOADFROMFILE = 1, 0x10
WS_EX_TOOLWINDOW = 0x80

ID_SHOW, ID_TOGGLE, ID_QUIT = 1001, 1002, 1003
MENU_ITEMS = ((ID_SHOW, 'show', '開啟視窗'), (ID_TOGGLE, 'toggle', '開始・停止錄音'), (ID_QUIT, 'quit', '結束'))
TIP = 'Voice2Txt'
MSGFLT_ALLOW = 1
SHOW_MESSAGE_NAME = 'Voice2TxtShowWindow'  # 第二個執行個體廣播此訊息，要求第一個顯示視窗


def action_for_menu_id(menu_id):
    """選單命令 id -> 動作名稱；未知 id（含 0＝取消）回傳 None。"""
    for item_id, action, _ in MENU_ITEMS:
        if item_id == menu_id:
            return action
    return None


def asset_path(name):
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
    return root / 'voice2txt' / 'assets' / name


LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [('style', wintypes.UINT), ('lpfnWndProc', WNDPROC), ('cbClsExtra', ctypes.c_int),
                ('cbWndExtra', ctypes.c_int), ('hInstance', wintypes.HINSTANCE), ('hIcon', wintypes.HANDLE),
                ('hCursor', wintypes.HANDLE), ('hbrBackground', wintypes.HANDLE),
                ('lpszMenuName', wintypes.LPCWSTR), ('lpszClassName', wintypes.LPCWSTR)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [('cbSize', wintypes.DWORD), ('hWnd', wintypes.HWND), ('uID', wintypes.UINT),
                ('uFlags', wintypes.UINT), ('uCallbackMessage', wintypes.UINT), ('hIcon', wintypes.HANDLE),
                ('szTip', wintypes.WCHAR * 128), ('dwState', wintypes.DWORD), ('dwStateMask', wintypes.DWORD),
                ('szInfo', wintypes.WCHAR * 256), ('uVersion', wintypes.UINT),
                ('szInfoTitle', wintypes.WCHAR * 64), ('dwInfoFlags', wintypes.DWORD),
                ('guidItem', ctypes.c_byte * 16), ('hBalloonIcon', wintypes.HANDLE)]


def _bind():
    user32, shell32, kernel32 = ctypes.windll.user32, ctypes.windll.shell32, ctypes.windll.kernel32
    user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.DefWindowProcW.restype = LRESULT
    user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
    user32.RegisterClassW.restype = wintypes.ATOM
    user32.UnregisterClassW.argtypes = [wintypes.LPCWSTR, wintypes.HINSTANCE]
    user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                       ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND,
                                       wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
    user32.CreateWindowExW.restype = wintypes.HWND
    user32.DestroyWindow.argtypes = [wintypes.HWND]
    user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
    user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.DispatchMessageW.restype = LRESULT
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostQuitMessage.argtypes = [ctypes.c_int]
    user32.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
    user32.RegisterWindowMessageW.restype = wintypes.UINT
    user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int,
                                  ctypes.c_int, wintypes.UINT]
    user32.LoadImageW.restype = wintypes.HANDLE
    user32.DestroyIcon.argtypes = [wintypes.HANDLE]
    user32.CreatePopupMenu.restype = wintypes.HMENU
    user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR]
    user32.TrackPopupMenu.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                      wintypes.HWND, ctypes.c_void_p]
    user32.DestroyMenu.argtypes = [wintypes.HMENU]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
    shell32.Shell_NotifyIconW.restype = wintypes.BOOL
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE
    return user32, shell32, kernel32


class TrayIcon:
    """start() 會等到 NIM_ADD 結果出來；close() 做 NIM_DELETE 並停止執行緒。"""

    def __init__(self, callback, icon_path=None, tip=TIP):
        self.callback = callback
        self.icon_path = str(icon_path or asset_path('voice2txt.ico'))
        self.tip = tip
        self.hwnd = None
        self.added = False      # 最近一次 NIM_ADD 是否成功
        self.deleted = False    # NIM_DELETE 是否已回傳 TRUE
        self.error = None
        self.filter_error = None
        self.thread = None
        self._ready = threading.Event()
        self._icon = None
        self._taskbar_created = 0
        self._show_message = 0
        self._class_name = f'Voice2TxtTray{id(self):x}'
        self._proc = None
        self._nid = None
        self._user32 = self._shell32 = None

    def start(self, timeout=5.0):
        if sys.platform != 'win32':
            self.error = '僅支援 Windows'
            return False
        self.thread = threading.Thread(target=self._run, name='tray', daemon=True)
        self.thread.start()
        self._ready.wait(timeout)
        return self.added

    def close(self, timeout=5.0):
        if self.hwnd and self.running:
            self._user32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)
        if self.thread is not None:
            self.thread.join(timeout)

    @property
    def running(self):
        return self.thread is not None and self.thread.is_alive()

    def _notify(self, message):
        return bool(self._shell32.Shell_NotifyIconW(message, ctypes.byref(self._nid)))

    def _add(self):
        """NIM_ADD；若失敗（圖示其實還在，例如非 explorer 重啟的 TaskbarCreated）改試 NIM_MODIFY。任一成功即 added。"""
        self.added = self._notify(NIM_ADD) or self._notify(NIM_MODIFY)
        if self.added:
            self.error = None
        else:
            self.error = 'Shell_NotifyIcon NIM_ADD / NIM_MODIFY 失敗'
        return self.added

    def _run(self):
        try:
            self._user32, self._shell32, kernel32 = _bind()
            user32 = self._user32
            self._taskbar_created = user32.RegisterWindowMessageW('TaskbarCreated')
            self._show_message = user32.RegisterWindowMessageW(SHOW_MESSAGE_NAME)
            instance = kernel32.GetModuleHandleW(None)
            self._proc = WNDPROC(self._wndproc)
            cls = WNDCLASSW()
            cls.lpfnWndProc = self._proc
            cls.hInstance = instance
            cls.lpszClassName = self._class_name
            if not user32.RegisterClassW(ctypes.byref(cls)):
                raise OSError('RegisterClassW 失敗')
            self.hwnd = user32.CreateWindowExW(WS_EX_TOOLWINDOW, self._class_name, self.tip, 0, 0, 0, 0, 0,
                                               None, None, instance, None)
            if not self.hwnd:
                raise OSError('CreateWindowExW 失敗')
            # 較低完整性層級的第二個執行個體（例如以一般權限啟動）預設無法 PostMessage 給本視窗：明確允許 SHOW 訊息。
            user32.ChangeWindowMessageFilterEx.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.DWORD, ctypes.c_void_p]
            user32.ChangeWindowMessageFilterEx.restype = wintypes.BOOL
            if not user32.ChangeWindowMessageFilterEx(self.hwnd, self._show_message, MSGFLT_ALLOW, None):
                self.filter_error = ctypes.get_last_error()
            size = user32.GetSystemMetrics(49)  # SM_CXSMICON
            self._icon = user32.LoadImageW(None, self.icon_path, IMAGE_ICON, size, size, LR_LOADFROMFILE)
            nid = NOTIFYICONDATAW()
            nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
            nid.hWnd = self.hwnd
            nid.uID = 1
            nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
            nid.uCallbackMessage = WM_APP_TRAY
            nid.hIcon = self._icon
            nid.szTip = self.tip
            self._nid = nid
            self._add()
        except Exception as error:
            self.error = str(error)
        finally:
            self._ready.set()
        if self.hwnd:
            msg = wintypes.MSG()
            while self._user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                self._user32.TranslateMessage(ctypes.byref(msg))
                self._user32.DispatchMessageW(ctypes.byref(msg))
            self._user32.UnregisterClassW(self._class_name, None)
        if self._icon:
            self._user32.DestroyIcon(self._icon)

    def _wndproc(self, hwnd, msg, wparam, lparam):
        user32 = self._user32
        if msg == WM_APP_TRAY:
            event = lparam & 0xFFFF
            if event == WM_LBUTTONUP:
                self.callback('show')
            elif event == WM_RBUTTONUP:
                self._popup(hwnd)
            return 0
        if msg == WM_CLOSE:
            user32.DestroyWindow(hwnd)
            return 0
        if msg == WM_DESTROY:
            self.deleted = self._notify(NIM_DELETE)
            self.added = False
            user32.PostQuitMessage(0)
            return 0
        if self._taskbar_created and msg == self._taskbar_created:
            self._add()  # explorer 重新啟動後把圖示加回來
            return 0
        if self._show_message and msg == self._show_message:
            self.callback('show')  # 另一個執行個體要求顯示視窗
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _popup(self, hwnd):
        user32 = self._user32
        menu = user32.CreatePopupMenu()
        for index, (item_id, _, label) in enumerate(MENU_ITEMS):
            if index == len(MENU_ITEMS) - 1:
                user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
            user32.AppendMenuW(menu, MF_STRING, item_id, label)
        point = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(point))
        user32.SetForegroundWindow(hwnd)  # 否則點選單外面不會關閉選單
        chosen = user32.TrackPopupMenu(menu, TPM_RETURNCMD | TPM_RIGHTBUTTON | TPM_BOTTOMALIGN,
                                       point.x, point.y, 0, hwnd, None)
        user32.PostMessageW(hwnd, WM_NULL, 0, 0)
        user32.DestroyMenu(menu)
        action = action_for_menu_id(chosen)
        if action:
            self.callback(action)
