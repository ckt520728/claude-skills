"""真機檢查：安裝 WH_KEYBOARD_LL，用 SendInput 注入快捷鍵，驗證事件序列、自動貼上延後、hook watchdog。

注意：本機若同時執行 Typeless.exe，它會吞掉真實（以及注入的）Right Alt，所以這支腳本的設定鍵改用
Left Alt（Left Alt、Left Alt+Left Shift）；狀態機與 hook 對左右 Alt 的處理相同，只是避開 Typeless。
JSON 的 configured_keys 會記錄這一點。檢查執行期間請不要操作其他視窗（會注入鍵盤事件）。

步驟：
1. 事件序列（hold、兩次 tap、雙鍵組合），並確認下游 hook 看得到同樣的事件（沒有吞鍵）。
2. 自動貼上：App 的 events queue 送入 'result'，LeftAlt 按住時不得貼；放開後才貼，目標 Tk 視窗收到的
   V 鍵 state 只有 Control（0x4），不能有 Alt（0x20000）。另外直接在 Alt 按住時呼叫 _paste，驗證貼上前的修飾鍵釋放。
3. watchdog：把逾時調短，按住鍵、不產生任何事件，hook 應重新安裝，且之後的 key-up 仍被收到。
4. 吞鍵：下游 hook 吞掉 F24（GetAsyncKeyState 不會更新），按住 1.5 s 並以 33 ms 間隔注入 auto-repeat，
   事件必須剛好是 [start dictate, stop]，且實體校正沒有誤判放開（physical_sync_false_drops == 0）。
5. 兩鍵組合其中一鍵被吞（稽核 C3 major 1）：下游 hook 吞掉 F24，按住 F24+F23 3 s、F23 以 33 ms auto-repeat，
   事件必須剛好是 [start translate, stop]，stop 在放開時（>= 2.9 s），不能在 ~1.2 s 被實體校正誤放開。
6. 閒置計時器（稽核 C3 major 2）：間隔調為 0.5 s、3 s 內不注入任何輸入，GetLastInputInfo 量到的閒置時間必須單調遞增，
   且沒有送出任何探測（探測是注入的鍵盤事件，會重設系統閒置計時器）。
7. 使用者活躍的存活探測：以滑鼠微移模擬使用者活躍（不產生鍵盤 callback），hook 要送出探測 no-op 並自己觀察到，不重裝。
用法：.\\.build-venv\\Scripts\\python.exe scripts\\check_hotkey_hook.py
"""
import ctypes
import json
import os
import queue
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['LOCALAPPDATA'] = TEMP.name  # App 的設定／歷史只寫暫存資料夾
from voice2txt.hotkeys import LowLevelKeyboardHook, PushToTalk, parse_combo, physical_key_down, send_key  # noqa: E402

LALT, LSHIFT = 0xA4, 0xA0
EXPECTED = [['start', 'dictate'], ['stop', None], ['start', 'dictate'], ['stop', None],
            ['start', 'translate'], ['stop', None]]
VK_CONTROL, VK_V = 0x11, 0x56
TK_ALT, TK_CONTROL, TK_SHIFT = 0x20000, 0x4, 0x1


def drain(q):
    out = []
    while not q.empty():
        kind, value = q.get_nowait()
        out.append([kind, value])
    return out


def sequence_check(report, user32):
    foreground_before = user32.GetForegroundWindow()
    combos = {'dictate': [parse_combo('LeftAlt')], 'translate': [parse_combo('LeftAlt+LeftShift')]}
    machine = PushToTalk(combos)
    events = queue.Queue()
    # 觀察用的第二個 hook 先安裝 => 在鏈中排在我們的 hook 之後；它收得到事件，才代表我們的 hook 沒有吞鍵。
    downstream_events = queue.Queue()
    downstream = LowLevelKeyboardHook(PushToTalk(combos), lambda kind, value: downstream_events.put((kind, value)))
    downstream.start()
    hook = LowLevelKeyboardHook(machine, lambda kind, value: events.put((kind, value)))
    installed = hook.start()
    report['hook_installed'] = installed
    if not installed:
        report['error'] = hook.error
        downstream.stop()
        return False
    try:
        # 1. 按住 0.5 秒再放開（hold-to-talk）
        send_key(LALT, False)
        time.sleep(0.5)
        send_key(LALT, True)
        time.sleep(0.4)
        # 2. 點按兩次（tap-to-toggle）
        for _ in range(2):
            send_key(LALT, False)
            time.sleep(0.05)
            send_key(LALT, True)
            time.sleep(0.4)
        # 3. Left Alt + Left Shift 按住 0.5 秒
        send_key(LALT, False)
        time.sleep(0.05)
        send_key(LSHIFT, False)
        time.sleep(0.5)
        send_key(LSHIFT, True)
        send_key(LALT, True)
        time.sleep(0.4)
    finally:
        hook.stop()
        downstream.stop()
    observed = drain(events)
    passed_through = drain(downstream_events)
    foreground_after = user32.GetForegroundWindow()
    report.update({
        'events': observed,
        'expected': EXPECTED,
        'foreground_unchanged': foreground_before == foreground_after,
        'downstream_hook_events': passed_through,
        'keys_not_swallowed': passed_through == EXPECTED,
        'noop_keys_injected': hook.noop_count,
        'noop_waits_when_not_yet_injected': hook.noop_waits,
        'noop_waits_satisfied_within_25ms': hook.noop_wait_satisfied,
        'physical_sync_installed': machine.is_physically_down is physical_key_down,
        'physical_sync_false_drops': list(machine.recovered),
        'hook_stopped': hook.thread is None,
    })
    return (observed == EXPECTED and report['foreground_unchanged'] and report['keys_not_swallowed']
            and hook.noop_count >= 3 and report['hook_stopped'] and hook.error is None
            and report['physical_sync_installed'] and not machine.recovered)


def watchdog_check(report):
    """hook 長時間沒有 callback 但有鍵被視為按住 -> 重新安裝；之後 key-up 仍收得到。"""
    events = queue.Queue()
    machine = PushToTalk({'dictate': [parse_combo('LeftAlt')]})
    hook = LowLevelKeyboardHook(machine, lambda kind, value: events.put((kind, value)))
    hook.watchdog_seconds = 0.4
    result = {}
    if not hook.start():
        result['error'] = hook.error
        report['watchdog'] = result
        return False
    try:
        send_key(LALT, False)
        time.sleep(1.4)   # 按住、不再有任何 callback
        send_key(LALT, True)
        time.sleep(0.4)
    finally:
        hook.stop()
    result['events'] = drain(events)
    result['reinstalls'] = hook.reinstalls
    result['error'] = hook.error
    report['watchdog'] = result
    return result['events'] == [['start', 'dictate'], ['stop', None]] and hook.reinstalls >= 1 and hook.error is None


F24 = 0x87


class SwallowHook:
    """下游 WH_KEYBOARD_LL：吞掉指定 vk（模擬 Typeless / AutoHotkey 對設定鍵的做法）。先安裝 => 排在我們的 hook 之後。"""

    def __init__(self, vk):
        self.vk = vk
        self.seen = 0
        self.thread_id = None
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()
        return self.ready.wait(3.0) and self.thread_id is not None

    def stop(self):
        if self.thread_id:
            ctypes.windll.user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0)
        self.thread.join(2.0)

    def _run(self):
        from ctypes import wintypes
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        proc_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, ctypes.c_size_t, ctypes.c_ssize_t)
        user32.SetWindowsHookExW.argtypes = [ctypes.c_int, proc_type, ctypes.c_void_p, wintypes.DWORD]
        user32.SetWindowsHookExW.restype = ctypes.c_void_p
        user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t, ctypes.c_ssize_t]
        user32.CallNextHookEx.restype = ctypes.c_ssize_t
        user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), ctypes.c_void_p, wintypes.UINT, wintypes.UINT]
        user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
        kernel32.GetModuleHandleW.restype = ctypes.c_void_p
        vk_target = self.vk

        def proc(code, wparam, lparam):
            if code == 0 and ctypes.cast(lparam, ctypes.POINTER(ctypes.c_uint32))[0] == vk_target:
                self.seen += 1
                return 1  # 吞鍵
            return user32.CallNextHookEx(None, code, wparam, lparam)

        self._ref = proc_type(proc)
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)
        self.thread_id = kernel32.GetCurrentThreadId()
        hook = user32.SetWindowsHookExW(13, self._ref, kernel32.GetModuleHandleW(None), 0)
        self.ready.set()
        if hook:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                pass
            user32.UnhookWindowsHookEx(hook)


def swallowed_key_check(report):
    """設定鍵被下游 hook 吞掉：按住 1.5 s、33 ms auto-repeat -> 剛好一個 start、一個 stop，且沒有實體校正誤判。"""
    result = {'configured_key': 'F24', 'hold_seconds': 1.5, 'repeat_interval_seconds': 0.033}
    report['swallowed_key'] = result
    events = queue.Queue()
    machine = PushToTalk({'dictate': [(F24,)]})
    swallower = SwallowHook(F24)
    if not swallower.start():
        result['error'] = 'swallow hook 安裝失敗'
        return False
    hook = LowLevelKeyboardHook(machine, lambda kind, value: events.put((kind, value)))
    if not hook.start():
        result['error'] = hook.error
        swallower.stop()
        return False
    sent = 0
    try:
        t0 = time.monotonic()
        send_key(F24, False)
        sent += 1
        while time.monotonic() - t0 < 1.5:
            time.sleep(0.033)
            send_key(F24, False)  # auto-repeat key-down
            sent += 1
        result['async_state_down_during_hold'] = physical_key_down(F24)  # 被吞掉 => 預期 False
        send_key(F24, True)
        time.sleep(0.4)
    finally:
        hook.stop()
        swallower.stop()
    observed = drain(events)
    result.update({
        'events': observed,
        'expected': [['start', 'dictate'], ['stop', None]],
        'key_downs_injected': sent,
        'swallowed_by_downstream_hook': swallower.seen,
        'physical_sync_false_drops': list(machine.recovered),
        'physical_sync_drop_count': len(machine.recovered),
        'held_after': sorted(machine.held_keys()),
    })
    return (observed == result['expected'] and not machine.recovered and swallower.seen >= sent
            and result['async_state_down_during_hold'] is False and hook.error is None)


def two_key_swallowed_check(report):
    """稽核 C3 major 1：RightAlt+RightShift 類情境 -> F24+F23 組合，F24 被下游 hook 吞掉、F23 持續 auto-repeat。"""
    F23 = 0x86
    result = {'configured_combo': 'F24+F23', 'swallowed_key': 'F24', 'repeating_key': 'F23',
              'hold_seconds': 3.0, 'repeat_interval_seconds': 0.033}
    report['two_key_swallowed'] = result
    stamped = []
    t0_box = [0.0]
    machine = PushToTalk({'translate': [(F24, F23)]})
    swallower = SwallowHook(F24)
    if not swallower.start():
        result['error'] = 'swallow hook 安裝失敗'
        return False
    hook = LowLevelKeyboardHook(machine, lambda kind, value: stamped.append(
        (kind, value, round(time.monotonic() - t0_box[0], 3))))
    if not hook.start():
        result['error'] = hook.error
        swallower.stop()
        return False
    try:
        t0_box[0] = t0 = time.monotonic()
        send_key(F24, False)
        time.sleep(0.01)
        send_key(F23, False)
        while time.monotonic() - t0 < 3.0:
            time.sleep(0.033)
            send_key(F23, False)  # F23 auto-repeat
        result['async_state_f24_down_during_hold'] = physical_key_down(F24)   # 被吞 => False
        result['async_state_f23_down_during_hold'] = physical_key_down(F23)   # 真實按著 => True
        release_at = round(time.monotonic() - t0, 3)
        send_key(F23, True)
        send_key(F24, True)
        time.sleep(0.4)
    finally:
        hook.stop()
        swallower.stop()
    events = [[k, v] for k, v, _ in stamped]
    times = [t for _, _, t in stamped]
    result.update({'events': events, 'event_times_seconds': times, 'released_at_seconds': release_at,
                   'expected': [['start', 'translate'], ['stop', None]],
                   'physical_sync_false_drops': list(machine.recovered)})
    return (events == result['expected'] and len(times) == 2 and times[1] >= 2.9
            and not machine.recovered and result['async_state_f24_down_during_hold'] is False
            and result['async_state_f23_down_during_hold'] is True and hook.error is None)


def idle_timer_check(report):
    """稽核 C3 major 2：使用者閒置時 hook 不得注入探測（會重設系統閒置計時器）。以 GetLastInputInfo 量測。"""
    from voice2txt.hotkeys import user_idle_seconds
    machine = PushToTalk({'dictate': [parse_combo('LeftAlt')]})
    hook = LowLevelKeyboardHook(machine, lambda kind, value: None)
    hook.liveness_seconds = 0.5
    result = {'liveness_seconds': 0.5, 'duration_seconds': 3.0}
    report['idle_timer'] = result
    if not hook.start():
        result['error'] = hook.error
        return False
    samples = []
    try:
        t0 = time.monotonic()
        while time.monotonic() - t0 < 3.0:
            samples.append((round(time.monotonic() - t0, 2), user_idle_seconds()))
            time.sleep(0.1)
    finally:
        hook.stop()
    idle_values = [v for _, v in samples]
    monotonic = all(b is not None and a is not None and b >= a for a, b in zip(idle_values, idle_values[1:]))
    result.update({'idle_samples_seconds': [v for v in idle_values], 'first_idle': idle_values[0],
                   'last_idle': idle_values[-1], 'idle_monotonic_increasing': monotonic,
                   'probes_sent': hook.probes_sent, 'reinstalls': hook.reinstalls,
                   'liveness_reinstalls': hook.liveness_reinstalls, 'error': hook.error})
    return (monotonic and idle_values[-1] - idle_values[0] >= 2.5 and hook.probes_sent == 0
            and hook.reinstalls == 0 and hook.error is None)


def liveness_check(report):
    """使用者活躍（滑鼠微移，不產生鍵盤 callback）時 hook 仍會自己送探測 no-op 並觀察到，不重裝。"""
    machine = PushToTalk({'dictate': [parse_combo('LeftAlt')]})
    hook = LowLevelKeyboardHook(machine, lambda kind, value: None)
    hook.liveness_seconds = 0.5
    result = {'liveness_seconds': 0.5, 'user_activity': '滑鼠微移 1 px 來回（每 100 ms）'}
    report['liveness_probe'] = result
    user32 = ctypes.windll.user32
    if not hook.start():
        result['error'] = hook.error
        return False
    try:
        end = time.monotonic() + 2.0
        while time.monotonic() < end:
            user32.mouse_event(0x0001, 1, 0, 0, 0)    # MOUSEEVENTF_MOVE
            user32.mouse_event(0x0001, -1 & 0xFFFFFFFF, 0, 0, 0)
            time.sleep(0.1)
    finally:
        hook.stop()
    result.update({'probes_sent': hook.probes_sent, 'probes_observed': hook.probes_observed,
                   'liveness_reinstalls': hook.liveness_reinstalls, 'reinstalls': hook.reinstalls,
                   'error': hook.error})
    return hook.probes_sent >= 1 and hook.probes_observed >= 1 and hook.liveness_reinstalls == 0 and hook.error is None


def foreground_window(user32, window):
    hwnd = user32.GetAncestor(window.winfo_id(), 2) or window.winfo_id()
    user32.ShowWindow(hwnd, 5)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    window.focus_force()
    return hwnd


def paste_check(report, user32):
    """App 的 'result' 事件在 LeftAlt 按住時不得貼上；放開後才貼，且目標視窗收到的是 Control-only。"""
    import tkinter as tk
    from voice2txt.desktop import App
    result = {'configured_keys': 'LeftAlt（本機 Typeless.exe 會吞 Right Alt，故以 LeftAlt 代替）'}
    report['paste_check'] = result
    root = tk.Tk()
    clipboard_before = None
    try:
        clipboard_before = root.clipboard_get()
    except tk.TclError:
        pass
    app = None
    finished = threading.Event()
    try:
        app = App(root)
        app.hotkeys['dictate'] = ['LeftAlt']
        app.hotkeys['translate'] = ['LeftAlt+LeftShift']
        app._apply_hotkeys()
        root.withdraw()
        target = tk.Toplevel(root)
        target.geometry('360x120+300+300')
        entry = tk.Text(target, width=40, height=3)
        entry.pack()
        seen = []
        entry.bind('<KeyPress>', lambda e: seen.append((e.keysym, e.state)))

        heartbeat = [time.monotonic()]
        result['modal_menu_hang_escapes'] = 0

        def unstick():
            # Alt 被當成「單獨按放」時，視窗會進入系統選單的 modal 迴圈，root.update() 不再返回：補送 Esc 讓腳本能收尾。
            while not finished.wait(0.5):
                if time.monotonic() - heartbeat[0] > 4:
                    send_key(0x1B, False)
                    send_key(0x1B, True)
                    result['modal_menu_hang_escapes'] += 1
                    heartbeat[0] = time.monotonic()
        threading.Thread(target=unstick, daemon=True).start()

        def pump(seconds):
            end = time.monotonic() + seconds
            while time.monotonic() < end:
                root.update()
                heartbeat[0] = time.monotonic()
                time.sleep(0.02)

        target.update()
        hwnd = foreground_window(user32, target)
        entry.focus_force()
        pump(0.4)
        foreground = user32.GetForegroundWindow()
        result['target_is_foreground'] = (foreground == hwnd)
        if foreground != hwnd:
            result['error'] = '無法把測試視窗帶到前景，貼上檢查不成立'
            return False
        app.session_paste = True
        app.target_window = hwnd
        app.session_mode = 'zh'
        app.session_vocab = ''
        app.recording = False

        def v_events():
            return [(k, hex(s)) for k, s in seen if k.lower() == 'v']

        # A. 模擬一段錄音：LeftAlt 按住期間送入 result（走 App 真正的 events queue 路徑）。
        send_key(LALT, False)
        pump(0.6)
        result['held_keys_while_pressed'] = sorted(app.ptt.held_keys())
        app.events.put(('result', ('測試貼上文字', 'zh', 1.0, 0.1, '', '', None)))
        pump(0.6)
        result['deferred_while_held'] = len(app.deferred_pastes)
        result['v_events_while_held'] = v_events()
        result['text_while_held'] = entry.get('1.0', 'end').strip()
        send_key(LALT, True)
        pump(0.8)
        after = v_events()
        result['deferred_after_release'] = len(app.deferred_pastes)
        result['v_events_after_release'] = after
        result['text_after_release'] = entry.get('1.0', 'end').strip()
        states = [int(s, 16) for _, s in after]
        result['observed_tk_state_hex'] = [hex(s) for s in states]
        result['control_only'] = bool(states) and all(s & TK_CONTROL and not s & (TK_ALT | TK_SHIFT) for s in states)
        result['state_exactly_0x4'] = bool(states) and all(s == TK_CONTROL for s in states)
        result['modifiers_released_by_paste'] = list(app.last_paste_released)
        deferral_ok = (result['deferred_while_held'] == 1 and not result['v_events_while_held']
                       and result['text_while_held'] == '')
        paste_ok = (result['deferred_after_release'] == 0 and len(after) == 1 and result['control_only']
                    and '測試貼上文字' in result['text_after_release'])

        # B. 對照組：Alt 按住時用舊方式（單純 keybd_event Ctrl+V）貼 -> 預期 Alt 位元存在（重現稽核缺陷）。
        seen.clear()
        send_key(LALT, False)
        pump(0.3)
        for vk, flag in ((VK_CONTROL, 0), (VK_V, 0), (VK_V, 2), (VK_CONTROL, 2)):
            user32.keybd_event(vk, 0, flag, 0)
        pump(0.4)
        send_key(LALT, True)
        pump(0.5)
        baseline = v_events()
        result['baseline_raw_ctrl_v_with_alt_held_state_hex'] = [s for _, s in baseline]
        result['baseline_has_alt_bit'] = bool(baseline) and any(int(s, 16) & TK_ALT for _, s in baseline)

        # C. 直接在 Alt 按住時呼叫 _paste：貼上前會先放開 Alt（SendInput key-up + MARKER）。
        seen.clear()
        send_key(LALT, False)
        pump(0.3)
        result['alt_physically_down_before_paste'] = physical_key_down(LALT)
        app._paste('直接貼上', hwnd)
        pump(0.5)
        direct = v_events()
        result['direct_paste_with_alt_held_released_vks'] = list(app.last_paste_released)
        result['direct_paste_tk_state_hex'] = [s for _, s in direct]
        result['direct_paste_control_only'] = (bool(direct) and all(
            int(s, 16) & TK_CONTROL and not int(s, 16) & (TK_ALT | TK_SHIFT) for _, s in direct))
        send_key(LALT, True)
        pump(0.5)
        result['alt_up_after_cleanup'] = not physical_key_down(LALT)
        direct_ok = result['direct_paste_control_only'] and LALT in app.last_paste_released
        result['ok'] = bool(deferral_ok and paste_ok and direct_ok and result['baseline_has_alt_bit'])
        return result['ok']
    except Exception as error:
        import traceback
        result['error'] = repr(error)
        result['traceback'] = traceback.format_exc()
        return False
    finally:
        finished.set()
        if clipboard_before is not None:
            try:
                root.clipboard_clear()
                root.clipboard_append(clipboard_before)
                root.update()
            except tk.TclError:
                pass
        for vk in (LALT, LSHIFT):
            if physical_key_down(vk):
                send_key(vk, True)
        if app is not None:
            app.close()
        else:
            try:
                root.destroy()
            except tk.TclError:
                pass


MENU_CHILD = r'''
import json, sys, ctypes, tkinter as tk
root = tk.Tk()
root.title('V2T-menu-child')
root.geometry('360x120+300+300')
bar = tk.Menu(root)
file_menu = tk.Menu(bar, tearoff=0)
file_menu.add_command(label='Item')
bar.add_cascade(label='File', menu=file_menu)
root.config(menu=bar)
text = tk.Text(root, width=30, height=3)
text.pack()
log = open(sys.argv[1], 'a', encoding='utf-8')
def on_key(event):
    log.write(json.dumps({'keysym': event.keysym, 'state': event.state}) + chr(10))
    log.flush()
root.bind_all('<KeyPress>', on_key)
root.update()
user32 = ctypes.windll.user32
user32.GetAncestor.restype = ctypes.c_void_p
hwnd = user32.GetAncestor(root.winfo_id(), 2)
text.focus_force()
print('READY', hwnd, flush=True)
root.mainloop()
'''


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [('cbSize', ctypes.c_uint32), ('flags', ctypes.c_uint32), ('hwndActive', ctypes.c_void_p),
                ('hwndFocus', ctypes.c_void_p), ('hwndCapture', ctypes.c_void_p),
                ('hwndMenuOwner', ctypes.c_void_p), ('hwndMoveSize', ctypes.c_void_p),
                ('hwndCaret', ctypes.c_void_p), ('rcCaret', ctypes.c_long * 4)]


GUI_INMENUMODE, GUI_SYSTEMMENUMODE = 0x4, 0x8
SPACE_VK, ESC_VK = 0x20, 0x1B


def menu_flags(user32, hwnd):
    """另一行程視窗的執行緒是否處於選單模式：回傳 flags（GUI_INMENUMODE 0x4 / GUI_SYSTEMMENUMODE 0x8）。"""
    thread = user32.GetWindowThreadProcessId(ctypes.c_void_p(hwnd), None)
    info = GUITHREADINFO()
    info.cbSize = ctypes.sizeof(GUITHREADINFO)
    if not user32.GetGUIThreadInfo(thread, ctypes.byref(info)):
        return None
    return info.flags & (GUI_INMENUMODE | GUI_SYSTEMMENUMODE)


def force_foreground(user32, hwnd):
    """把另一行程的視窗帶到前景（AttachThreadInput 取得前景權限）；回傳是否成功。"""
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
    return user32.GetForegroundWindow() == hwnd


def read_log(path):
    try:
        return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]
    except OSError:
        return []


def swallow_rule_check(report, user32):
    """稽核 E D2：LeftAlt+Space 當 ask，前景是另一行程帶 menubar 的 Tk 視窗。

    對照組（沒有 hook）：Alt+Space 會開啟系統選單。有 hook：按住 0.5 s 後系統選單不得開啟；
    Alt 本身不被吞（視窗仍看到 Alt_L）；單獨按 Space（沒有 Alt）仍送達視窗。
    另外斷言 hook 程式碼只有兩個出口（return 1 吞鍵／CallNextHookEx），且吞鍵規則只涵蓋非修飾鍵。
    """
    import inspect
    import subprocess
    from voice2txt.hotkeys import NEVER_SWALLOW_VKS
    result = {'configured_keys': 'LeftAlt+Space (ask)'}
    report['swallow_rule'] = result
    source = inspect.getsource(LowLevelKeyboardHook._run)
    result['return_paths'] = {'swallow_return_1': source.count('return 1 '),
                              'call_next_hook': source.count('return user32.CallNextHookEx')}
    result['modifiers_never_swallowed'] = all(vk in NEVER_SWALLOW_VKS for vk in (0x10, 0x11, 0x12, 0xA0, 0xA1, 0xA2,
                                                                                 0xA3, 0xA4, 0xA5, 0x5B, 0x5C))
    paths_ok = (result['return_paths'] == {'swallow_return_1': 1, 'call_next_hook': 1}
                and result['modifiers_never_swallowed'])
    log_path = Path(TEMP.name) / 'menu-child-keys.jsonl'
    child = subprocess.Popen([sys.executable, '-c', MENU_CHILD, str(log_path)], stdout=subprocess.PIPE, text=True)
    try:
        line = child.stdout.readline()
        if not line.startswith('READY'):
            result['error'] = 'child 沒有啟動：' + line
            return False
        hwnd = int(line.split()[1])
        result['child_foreground'] = force_foreground(user32, hwnd)
        if not result['child_foreground']:
            result['error'] = '無法把另一行程的測試視窗帶到前景'
            return False

        def close_menu():
            for _ in range(2):
                send_key(ESC_VK, False)
                send_key(ESC_VK, True)
                time.sleep(0.15)

        # 對照組：沒有 hook，Alt+Space 開啟系統選單（證明這個檢查有效）。
        send_key(LALT, False)
        time.sleep(0.05)
        send_key(SPACE_VK, False)
        time.sleep(0.5)
        result['baseline_menu_flags_during_hold'] = menu_flags(user32, hwnd)
        send_key(SPACE_VK, True)
        send_key(LALT, True)
        time.sleep(0.3)
        result['baseline_menu_flags_after'] = menu_flags(user32, hwnd)
        close_menu()
        result['baseline_menu_closed'] = menu_flags(user32, hwnd) == 0
        force_foreground(user32, hwnd)
        Path(log_path).write_text('', encoding='utf-8')

        events = queue.Queue()
        # 觀察用的下游 hook（先安裝 => 排在我們之後）：它看得到 LeftAlt（修飾鍵沒被吞），看不到 Space（被吞）。
        downstream_events = queue.Queue()
        downstream = LowLevelKeyboardHook(PushToTalk({'dictate': [parse_combo('LeftAlt')],
                                                       'ask': [parse_combo('LeftAlt+Space')]}),
                                          lambda kind, value: downstream_events.put((kind, value)))
        if not downstream.start():
            result['error'] = downstream.error
            return False
        machine = PushToTalk({'ask': [parse_combo('LeftAlt+Space')]})
        hook = LowLevelKeyboardHook(machine, lambda kind, value: events.put((kind, value)))
        if not hook.start():
            result['error'] = hook.error
            downstream.stop()
            return False
        try:
            send_key(LALT, False)
            time.sleep(0.05)
            send_key(SPACE_VK, False)
            t0 = time.monotonic()
            sampled = False
            while time.monotonic() - t0 < 0.6:
                time.sleep(0.033)
                send_key(SPACE_VK, False)  # auto-repeat：同樣被吞
                if not sampled and time.monotonic() - t0 >= 0.5:
                    result['menu_flags_during_hold'] = menu_flags(user32, hwnd)
                    sampled = True
            send_key(SPACE_VK, True)
            send_key(LALT, True)
            time.sleep(0.4)
            result['menu_flags_after_release'] = menu_flags(user32, hwnd)
            swallowed_after_combo = hook.swallowed_count
            keys_after_combo = [k['keysym'] for k in read_log(log_path)]
            # 單獨按 Space（沒有 Alt）：不是組合的完成鍵，必須送達視窗，也不得被吞。
            send_key(SPACE_VK, False)
            time.sleep(0.05)
            send_key(SPACE_VK, True)
            time.sleep(0.4)
            bare = [k for k in read_log(log_path)[len(keys_after_combo):] if k['keysym'] == 'space']
            result['bare_space_events'] = bare
            result['bare_space_reaches_window'] = len(bare) >= 1 and all(not (k['state'] & 0x20000) for k in bare)
            result['swallowed_count_combo'] = swallowed_after_combo
            result['swallowed_count_after_bare_space'] = hook.swallowed_count
        finally:
            hook.stop()
            downstream.stop()
        close_menu()
        got = drain(events)
        result['events'] = got
        result['window_keys_during_combo'] = keys_after_combo
        result['space_hidden_from_window'] = 'space' not in keys_after_combo
        downstream_got = drain(downstream_events)
        result['downstream_events'] = downstream_got
        result['alt_not_swallowed'] = ['start', 'dictate'] in downstream_got and ['start', 'ask'] not in downstream_got
        result['ask_started'] = ['start', 'ask'] in got
        menu_closed = (result['menu_flags_during_hold'] == 0 and result['menu_flags_after_release'] == 0)
        baseline_ok = bool(result['baseline_menu_flags_during_hold'])  # 對照組確實開了選單
        result['ok'] = bool(paths_ok and menu_closed and baseline_ok and result['space_hidden_from_window']
                            and result['alt_not_swallowed'] and result['ask_started']
                            and result['bare_space_reaches_window'] and swallowed_after_combo >= 1
                            and hook.swallowed_count == swallowed_after_combo)
        return result['ok']
    except Exception as error:
        import traceback
        result['error'] = repr(error)
        result['traceback'] = traceback.format_exc()
        return False
    finally:
        for vk in (LALT, SPACE_VK):
            if physical_key_down(vk):
                send_key(vk, True)
        child.terminate()


def main():
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    user32.GetAncestor.restype = ctypes.c_void_p
    user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
    user32.BringWindowToTop.argtypes = [ctypes.c_void_p]
    user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
    report = {'ok': False,
              'configured_keys': 'LeftAlt / LeftAlt+LeftShift（Typeless.exe 在本機執行並吞掉 Right Alt，故以 LeftAlt 代替）',
              'checks': {}}
    sequence_ok = sequence_check(report, user32)
    watchdog_ok = watchdog_check(report) if sequence_ok else False
    swallowed_ok = swallowed_key_check(report) if sequence_ok else False
    two_key_ok = two_key_swallowed_check(report) if sequence_ok else False
    idle_ok = idle_timer_check(report) if sequence_ok else False
    liveness_ok = liveness_check(report) if sequence_ok else False
    paste_ok = paste_check(report, user32) if sequence_ok else False
    swallow_ok = swallow_rule_check(report, user32) if sequence_ok else False
    report['checks'] = {'event_sequence': sequence_ok, 'watchdog_reinstall': watchdog_ok,
                        'swallowed_key_single_start_stop': swallowed_ok,
                        'two_key_swallowed_single_start_stop': two_key_ok,
                        'idle_timer_not_reset_no_probe': idle_ok, 'active_user_liveness_probe': liveness_ok,
                        'deferred_paste_control_only': paste_ok,
                        'alt_combo_swallow_no_system_menu': swallow_ok}
    report['ok'] = (sequence_ok and watchdog_ok and swallowed_ok and two_key_ok and idle_ok and liveness_ok
                    and paste_ok and swallow_ok)
    return finish(report)


def finish(report):
    out = ROOT / 'verification' / 'hotkey-hook-2026-11-13.json'
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    print('PASS' if report['ok'] else 'FAIL')
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    code = main()
    try:
        TEMP.cleanup()
    except OSError:
        pass
    sys.exit(code)
