"""Push-to-talk 快捷鍵：純 Python 狀態機 + Win32 WH_KEYBOARD_LL hook。

狀態機（PushToTalk）不依賴 Win32，時鐘由呼叫端傳入，方便測試。
hook（LowLevelKeyboardHook）絕不吞修飾鍵（Alt/Shift/Ctrl/Win，AltGr 安全）。唯一的例外（稽核 E D2）：
「完成一組含 Alt 的已設定組合」的非修飾鍵（例如 Alt+Space 的 Space），它的 key-down（含 auto-repeat）
與對應的 key-up 會被吞掉，否則前景視窗會把 Alt+Space 當成開啟系統選單。其餘按鍵一律 CallNextHookEx。
"""
import itertools
import queue
import threading
import time

# ---- VK 名稱表 ---------------------------------------------------------------

GENERIC = {0x12: (0xA4, 0xA5, 0x12), 0x10: (0xA0, 0xA1, 0x10), 0x11: (0xA2, 0xA3, 0x11)}

_NAMES = [
    ('RightAlt', 0xA5, 'Right Alt'), ('LeftAlt', 0xA4, 'Left Alt'), ('Alt', 0x12, 'Alt'),
    ('RightShift', 0xA1, 'Right Shift'), ('LeftShift', 0xA0, 'Left Shift'), ('Shift', 0x10, 'Shift'),
    ('RightCtrl', 0xA3, 'Right Ctrl'), ('LeftCtrl', 0xA2, 'Left Ctrl'), ('Ctrl', 0x11, 'Ctrl'),
    ('Space', 0x20, 'Space'), ('CapsLock', 0x14, 'Caps Lock'), ('Tab', 0x09, 'Tab'),
    ('Enter', 0x0D, 'Enter'), ('Esc', 0x1B, 'Esc'), ('Backspace', 0x08, 'Backspace'),
    ('LeftWin', 0x5B, 'Left Win'), ('RightWin', 0x5C, 'Right Win'),
]
_NAMES += [(f'F{i}', 0x6F + i, f'F{i}') for i in range(1, 13)]
_NAMES += [(chr(c), c, chr(c)) for c in range(0x30, 0x3A)] + [(chr(c), c, chr(c)) for c in range(0x41, 0x5B)]

NAME_TO_VK = {}
VK_TO_NAME = {}
VK_TO_DISPLAY = {}
for _name, _vk, _display in _NAMES:
    NAME_TO_VK[_name.lower()] = _vk
    NAME_TO_VK[_display.replace(' ', '').lower()] = _vk
    VK_TO_NAME[_vk] = _name
    VK_TO_DISPLAY[_vk] = _display


def _token_vk(token):
    key = token.replace(' ', '').lower()
    if key in NAME_TO_VK:
        return NAME_TO_VK[key]
    if key.startswith('vk0x'):
        return int(key[4:], 16)
    raise ValueError(f'未知的按鍵：{token!r}')


def parse_combo(text):
    """'RightAlt+RightShift' 或 'Right Alt + Right Shift' -> (0xA5, 0xA1)。"""
    tokens = [t for t in str(text).split('+') if t.strip()]
    if not tokens:
        raise ValueError('空的組合')
    combo = tuple(_token_vk(t) for t in tokens)
    if len(set(combo)) != len(combo):
        raise ValueError('組合內按鍵重複')
    return combo


def combo_name(combo):
    """儲存用名稱：(0xA5, 0xA1) -> 'RightAlt+RightShift'。"""
    return '+'.join(VK_TO_NAME.get(vk, f'VK0x{vk:02X}') for vk in combo)


def format_combo(combo):
    """顯示用名稱：(0xA5, 0xA1) -> 'Right Alt + Right Shift'。"""
    return ' + '.join(VK_TO_DISPLAY.get(vk, f'VK 0x{vk:02X}') for vk in combo)


# ---- 狀態機 -----------------------------------------------------------------

HOLD_SECONDS = 0.35
GRACE_SECONDS = 0.15
MAX_COMBOS = 2


def _matches(element, vk):
    return vk == element or vk in GENERIC.get(element, ())


# 修飾鍵（左右與泛用 Shift/Ctrl/Alt，以及 Win）：永遠不吞。
NEVER_SWALLOW_VKS = frozenset((0x10, 0x11, 0x12, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0x5B, 0x5C))
ALT_ELEMENTS = (0xA4, 0xA5, 0x12)

# 舊版預設值 -> 載入設定時換成目前預設值（使用者自訂的值不動）。
# 'ask' 舊預設 RightAlt+Space：Alt+Space 會開啟前景視窗的系統選單（稽核 E D2）。
OLD_DEFAULT_HOTKEYS = {'ask': (['RightAlt+Space'],)}
HOTKEYS_VERSION = 2   # settings['hotkeys_version']：已做過預設值遷移；之後使用者自行設定的值不再被取代


def migrate_hotkeys(action, names, defaults, version=1):
    """已儲存的組合名稱若等於舊版預設值，換成 defaults[action]；其他（使用者自訂）原樣保留（純函式）。

    version >= HOTKEYS_VERSION：設定已遷移過，使用者刻意設成 RightAlt+Space 要保留，不再換。
    """
    names = list(names)
    if version >= HOTKEYS_VERSION:
        return names
    for old in OLD_DEFAULT_HOTKEYS.get(action, ()):
        if names == list(old):
            return list(defaults[action])
    return names


def _max_match(elements, keys):
    """combo 元素與實際按鍵的最大一對一配對數（元素最多數個，暴力即可）。"""
    elements, keys = list(elements), list(keys)
    best = 0
    if len(elements) <= len(keys):
        for perm in itertools.permutations(keys, len(elements)):
            best = max(best, sum(1 for e, k in zip(elements, perm) if _matches(e, k)))
    else:
        for perm in itertools.permutations(elements, len(keys)):
            best = max(best, sum(1 for e, k in zip(perm, keys) if _matches(e, k)))
    return best


# 實體狀態校正：該鍵至少這麼久沒有任何 key-down（含 auto-repeat），且 GetAsyncKeyState 說已放開，才補做 key-up。
# 要大於 Windows auto-repeat 的最長起始延遲（約 1 s）；被下游 hook 吞掉的鍵不會更新 GetAsyncKeyState，
# 但 auto-repeat 的 key-down 仍會持續到達本 hook，所以不能只看 GetAsyncKeyState。
PHYSICAL_CHECK_SECONDS = 1.2
CONTINUATION_SECONDS = 1.5     # 補做 key-up 之後這麼久內同一鍵又 key-down：視為持續按住，不是新的按下
WATCHDOG_SECONDS = 10.0
LIVENESS_SECONDS = 10.0        # 這麼久沒有任何 hook callback -> 注入探測用的 no-op
LIVENESS_WAIT_SECONDS = 0.15   # 探測送出後等這麼久仍沒被 hook 看到 -> 重裝
LIVENESS_WARNING = '快捷鍵監聽已失效，請重新啟動 App。'
TYPELESS_PROCESS = 'typeless.exe'
TYPELESS_WARNING = '偵測到 Typeless 正在執行，Right Alt 會被它攔截；請改設其他快捷鍵或關閉 Typeless。'


def paste_decision(pending_count, held_keys):
    """自動貼上的時機（純函式）：'none' 沒有待貼結果；'defer' 還有快捷鍵按住 -> 先暫存；'now' 可以貼。"""
    if not pending_count:
        return 'none'
    return 'defer' if held_keys else 'now'


def watchdog_due(now, last_callback, any_held, timeout=WATCHDOG_SECONDS):
    """有鍵被視為按住、卻超過 timeout 秒沒有任何 hook callback -> 該重裝 hook（純函式）。"""
    return bool(any_held) and now - last_callback >= timeout


def liveness_decision(now, last_callback, probe_sent_at, probe_seen, last_user_input,
                      interval=LIVENESS_SECONDS, wait=LIVENESS_WAIT_SECONDS):
    """hook 存活判斷（純函式，與是否有鍵按住無關）。last_user_input 與 now 使用同一個時鐘。

    回傳 'idle'（使用者閒置，什麼都不做）、'probe'（該送探測 no-op）、'wait'（探測已送出，等待觀察）、
    'ok'（探測已被 hook 看到，或使用者活躍且 hook 近期有 callback）、'reinstall'（探測送出超過 wait 秒仍沒被看到）。

    注入鍵盤事件會重設系統閒置計時器（螢幕保護、自動鎖定、睡眠），所以使用者閒置時絕不探測也不重裝；
    只在使用者最近 interval 秒內有輸入（閒置計時器本來就在歸零）而 hook 同時 interval 秒沒有 callback 時才探測。
    """
    if probe_sent_at is not None:
        if probe_seen:
            return 'ok'
        return 'reinstall' if now - probe_sent_at >= wait else 'wait'
    if now - last_user_input >= interval:
        return 'idle'
    return 'probe' if now - last_callback >= interval else 'ok'


def conflicting_combos(process_names, combos):
    """Typeless 在執行時會攔截 Right Alt：回傳含 Right Alt（單獨或組合內）的已設定組合（純函式）。

    process_names：執行中的程序映像名稱；combos：vk tuple 的可迭代物件。
    """
    if not any(str(name).lower() == TYPELESS_PROCESS for name in process_names):
        return []
    return [tuple(c) for c in combos if 0xA5 in tuple(c)]


class PushToTalk:
    def __init__(self, combos, hold_seconds=HOLD_SECONDS, grace_seconds=GRACE_SECONDS, is_physically_down=None):
        self.hold_seconds = hold_seconds
        self.grace_seconds = grace_seconds
        self.is_physically_down = is_physically_down  # callable(vk) -> bool；None 表示不校正
        self.swallow_released = []                    # 被吞掉的鍵因 repeat 逾時而補做 key-up 的 vk
        self.recovered = []                           # 因實體上已放開而補做 key-up 的 vk
        self._lock = threading.RLock()
        self._pressed = []        # 目前按住且與任一組合相關的 vk（reset 不清除）
        self._foreign = set()     # 目前按住且與任何組合無關的 vk（reset 不清除）
        self._down_at = {}
        self._last_seen = {}      # vk -> 最近一次 key-down（含 auto-repeat）的時間
        self._dropped_at = {}     # vk -> 被實體校正補做 key-up 的時間
        self._seen_physical_down = {}  # vk -> 自 key-down 起實體狀態是否曾被觀察到為按下
        self._synthetic = set()   # 由我們以 MARKER 合成放開的 vk：實體取樣無效，直到真正的 key-up 或新的 key-down
        self._swallow_repeated = set()  # 被吞鍵中，吞掉之後已觀察到至少一次 auto-repeat 的 vk（只有這些適用 repeat 逾時）
        self._swallowed = set()   # 初次 key-down 被吞掉的非修飾鍵：對應的 key-up 也要吞（reset/set_combos 不清除）
        self.set_combos(combos)

    def set_combos(self, combos):
        """combos: {'dictate': [(vk, ...), ...], 'translate': [...]}；每個動作最多 2 組。"""
        cleaned = []
        for action, items in combos.items():
            items = [tuple(c) for c in items if c]
            if len(items) > MAX_COMBOS:
                raise ValueError(f'{action} 最多只能設定 {MAX_COMBOS} 組快捷鍵')
            cleaned.extend((action, c) for c in items)
        with self._lock:
            self._combos = cleaned
            self._relevant = [e for _, c in cleaned for e in c]
            held = list(self._pressed) + list(self._foreign)
            self.reset()
            # 組合改變後依新的相關性重新分類仍按住的鍵。
            self._pressed = [vk for vk in held if self._is_relevant(vk)]
            self._foreign = {vk for vk in held if not self._is_relevant(vk)}

    def reset(self):
        """回到閒置，但保留目前按住的鍵：停止後的 auto-repeat key-down 不能被當成新的按下。"""
        with self._lock:
            self._pending = None      # (action, combo, keys, t_press)
            self._active = None       # dict(action, keys, t, stopper)
            self._recording = False
            self._session = None      # (action, combo)：以快捷鍵開始的這一段由哪組合開始；None＝非快捷鍵開始

    def set_recording(self, flag):
        """錄音由按鈕（非快捷鍵）開始時通知狀態機：此時任何已設定的組合 tap 都能停止。"""
        with self._lock:
            self._recording = bool(flag)
            self._session = None
            self._active = None
            self._pending = None

    def mark_synthetic_release(self, vks):
        """呼叫端用 MARKER key-up 合成放開了 vks（隨便問／貼上前放開修飾鍵）：GetAsyncKeyState 現在會回報放開，
        但使用者其實還按著。清掉「曾觀察到實體按下」旗標並忽略之後的實體取樣，直到真正的 key-up 或新的 key-down，
        T12 規則（從未觀察到實體按下 -> 不被校正放開）就會讓狀態機繼續認為鍵按住。"""
        with self._lock:
            for vk in vks:
                if vk in self._pressed or vk in self._foreign:
                    self._synthetic.add(vk)
                    self._seen_physical_down[vk] = False

    def held_keys(self):
        """目前按住且屬於已設定快捷鍵的 vk（frozenset）。"""
        with self._lock:
            return frozenset(self._pressed)

    def relevant_keys(self):
        """已設定組合內的所有元素 vk（含泛用 Alt/Shift/Ctrl，frozenset）。"""
        with self._lock:
            return frozenset(self._relevant)

    def any_held(self):
        with self._lock:
            return bool(self._pressed or self._foreign)

    @property
    def recording(self):
        return self._recording

    def _is_relevant(self, vk):
        return any(_matches(e, vk) for e in self._relevant)

    def _member(self, vk):
        if self._pending is not None and vk in self._pending[2]:
            return True
        return self._active is not None and vk in self._active['keys']

    def _activate(self, action, combo, keys, t_press):
        if self._recording:
            self._active = {'action': action, 'keys': set(keys), 't': t_press, 'stopper': True}
            if self._session is not None and self._session != (action, tuple(combo)):
                return []  # 只有開始這一段的同一組合 tap 才能停止（按鈕開始的錄音則任何組合都可以）
            self._recording = False
            self._session = None
            return [('stop', None)]
        self._recording = True
        self._session = (action, tuple(combo))
        self._active = {'action': action, 'keys': set(keys), 't': t_press, 'stopper': False}
        return [('start', action)]

    def _evaluate(self, now):
        self._pending = None
        if self._foreign or not self._pressed:
            return []
        exact = [(action, combo) for action, combo in self._combos
                 if len(combo) == len(self._pressed) and _max_match(combo, self._pressed) == len(combo)]
        if not exact:
            return []
        action, combo = max(exact, key=lambda item: len(item[1]))
        keys = list(self._pressed)
        longer = any(len(c) > len(keys) and _max_match(c, keys) == len(keys) for _, c in self._combos)
        if longer:
            self._pending = (action, combo, keys, now)
            return []
        return self._activate(action, combo, keys, now)

    def key(self, vk, is_down, now):
        """回傳 (events, consumed)。events: [('start', action) | ('stop', None)]。"""
        return self.handle(vk, is_down, now)[:2]

    def handle(self, vk, is_down, now):
        """同 key()，另外回傳 swallow：hook 是否該吞掉這個事件（不交給前景視窗）。

        只有非修飾鍵、且按下後「目前按住的鍵剛好完成一組含 Alt 的已設定組合」（沒有其他無關的鍵）時，
        key-down（含 auto-repeat）才吞；初次 key-down 被吞的鍵，其 key-up 也吞。修飾鍵永遠不吞。
        初次 key-down 已放行的鍵，key-up 也放行（否則系統會以為該鍵一直按著）。
        """
        with self._lock:
            if not is_down:
                swallow = vk in self._swallowed
                self._swallowed.discard(vk)
                self._swallow_repeated.discard(vk)
                events, consumed = self._key(vk, False, now)
                return events, consumed, swallow
            is_new = vk not in self._pressed and vk not in self._foreign
            events, consumed = self._key(vk, True, now)
            if vk in self._swallowed:
                if not is_new:
                    self._swallow_repeated.add(vk)
                return events, consumed, True
            swallow = self._completes_alt_combo(vk)
            if swallow and is_new:
                self._swallowed.add(vk)
            return events, consumed, swallow

    def take_swallowed(self, vk):
        """設定介面擷取期間 hook 不呼叫 handle()：key-up 仍要依先前的吞鍵紀錄處理。回傳是否該吞。"""
        with self._lock:
            if vk in self._swallowed:
                self._swallowed.discard(vk)
                self._swallow_repeated.discard(vk)
                return True
            return False

    def _completes_alt_combo(self, vk):
        if vk in NEVER_SWALLOW_VKS or vk not in self._pressed or self._foreign:
            return False
        pressed = self._pressed
        return any(len(combo) == len(pressed) and any(e in ALT_ELEMENTS for e in combo)
                   and _max_match(combo, pressed) == len(combo) for _, combo in self._combos)

    def _key(self, vk, is_down, now):
        with self._lock:
            events = []
            if is_down:
                if vk in self._pressed or vk in self._foreign:
                    self._last_seen[vk] = now
                    # 合成放開之後又收到真正的 key-down（hook 不會收到 MARKER 事件）：實體狀態已重新為按下，恢復取樣。
                    self._synthetic.discard(vk)
                    self._observe_physical(vk)
                    return events, self._member(vk)  # auto-repeat
                self._last_seen[vk] = now
                self._synthetic.discard(vk)
                self._seen_physical_down[vk] = False  # key-down 當下系統實體狀態可能還沒更新，不在此取樣
                dropped = self._dropped_at.pop(vk, None)
                if dropped is not None and now - dropped < CONTINUATION_SECONDS:
                    # 剛被實體校正誤判放開的鍵又來了 key-down：它其實一直按著（例如被下游 hook 吞掉），
                    # 放回按住集合，但不算新的按下。
                    # 取捨（已接受）：這 1.5 秒內若使用者真的放開又重按，會被當成持續按住而漏掉一次新的按下。
                    self._seen_physical_down[vk] = True  # 它先前已被觀察到實體按下過
                    if self._is_relevant(vk):
                        self._pressed.append(vk)
                    else:
                        self._foreign.add(vk)
                    return events, False
                self._down_at[vk] = now
                if not self._is_relevant(vk):
                    self._foreign.add(vk)
                    self._pending = None
                    return events, False
                self._pressed.append(vk)
                if self._active is None:
                    events = self._evaluate(now)
                return events, self._member(vk)
            # key up
            self._down_at.pop(vk, None)
            self._last_seen.pop(vk, None)
            self._seen_physical_down.pop(vk, None)
            self._synthetic.discard(vk)
            self._dropped_at.pop(vk, None)
            if vk in self._foreign:
                self._foreign.discard(vk)
                return events, False
            if vk not in self._pressed:
                return events, False
            consumed = self._member(vk)
            if self._pending is not None and vk in self._pending[2]:
                action, combo, keys, t_press = self._pending
                self._pending = None
                events += self._activate(action, combo, keys, t_press)
            self._pressed.remove(vk)
            active = self._active
            if active is not None and vk in active['keys']:
                self._active = None
                if not active['stopper'] and now - active['t'] >= self.hold_seconds:
                    self._recording = False
                    events.append(('stop', None))
                # 短按：維持錄音（tap-to-toggle）。
            return events, consumed

    def _observe_physical(self, vk):
        """取樣實體狀態；只要看過一次按下，就代表下游 hook 沒有吞掉這個鍵，之後才適用放開校正。"""
        check = self.is_physically_down
        if check is None or vk in self._synthetic or self._seen_physical_down.get(vk, True):
            return
        try:
            if check(vk):
                self._seen_physical_down[vk] = True
        except Exception:
            pass

    def _sync_physical(self, now):
        """遺失 key-up 的復原：實體上已放開的鍵補做 key-up。只在有注入 is_physically_down 時作用。

        只處理「曾被觀察到實體按下」的鍵；從未觀察到實體按下的鍵（被下游 hook 吞掉，例如 Typeless 吞掉 Right Alt）
        不會被校正放開，即使它沒有 auto-repeat。
        """
        events = []
        # 被我們吞掉的鍵不更新 GetAsyncKeyState：只能用 auto-repeat 判斷（且需曾觀察到 repeat）。超過 PHYSICAL_CHECK_SECONDS 沒有任何
        # key-down（含 repeat）也沒有 key-up -> 視為 key-up 遺失，補做放開並清掉吞鍵紀錄。
        for vk in list(self._swallowed):
            seen = self._last_seen.get(vk)
            if vk not in self._pressed and vk not in self._foreign:
                self._swallowed.discard(vk)
                self._swallow_repeated.discard(vk)
            elif vk in self._swallow_repeated and seen is not None and now - seen >= PHYSICAL_CHECK_SECONDS:
                # 只對「吞掉之後確實出現過 auto-repeat」的鍵適用；從未 repeat 的鍵（滑鼠鍵/巨集/FilterKeys）不逾時。
                self._swallowed.discard(vk)
                self._swallow_repeated.discard(vk)
                self.swallow_released.append(vk)
                events += self.key(vk, False, now)[0]
        check = self.is_physically_down
        if check is None:
            return events
        for vk in list(self._pressed) + list(self._foreign):
            self._observe_physical(vk)
            if not self._seen_physical_down.get(vk, False):
                continue
            if now - self._last_seen.get(vk, self._down_at.get(vk, now)) < PHYSICAL_CHECK_SECONDS:
                continue
            try:
                down = check(vk)
            except Exception:
                continue
            if not down:
                self.recovered.append(vk)
                events += self.key(vk, False, now)[0]
                self._dropped_at[vk] = now
        return events

    def tick(self, now):
        with self._lock:
            events = self._sync_physical(now)
            if self._pending is not None and now - self._pending[3] >= self.grace_seconds:
                action, combo, keys, t_press = self._pending
                self._pending = None
                events += self._activate(action, combo, keys, t_press)
            return events


class ComboCapture:
    """設定介面用：記錄依序按下的鍵，全部放開後確認。key() 回傳 ('live'|'done', combo) 或 None。"""
    MAX_KEYS = 4

    def __init__(self):
        self.held = set()
        self.order = []

    def key(self, vk, is_down):
        if is_down:
            if vk in self.held or len(self.order) >= self.MAX_KEYS:
                return None
            self.held.add(vk)
            self.order.append(vk)
            return ('live', tuple(self.order))
        if vk not in self.held:
            return None
        self.held.discard(vk)
        if not self.held and self.order:
            combo = tuple(self.order)
            self.order = []
            return ('done', combo)
        return ('live', tuple(self.order))


# ---- Win32 hook -------------------------------------------------------------

NOOP_VK = 0xFF
MARKER = 0x56325454  # dwExtraInfo：自己注入的 no-op，hook 要略過
PROBE_MARKER = 0x56325455  # 存活探測用的 no-op：hook 只計數，不交給狀態機
_ALT_VKS = (0xA4, 0xA5, 0x12)


def _win32():
    import ctypes
    from ctypes import wintypes

    class KBDLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [('vkCode', wintypes.DWORD), ('scanCode', wintypes.DWORD), ('flags', wintypes.DWORD),
                    ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.c_size_t)]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [('wVk', wintypes.WORD), ('wScan', wintypes.WORD), ('dwFlags', wintypes.DWORD),
                    ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.c_size_t)]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [('dx', wintypes.LONG), ('dy', wintypes.LONG), ('mouseData', wintypes.DWORD),
                    ('dwFlags', wintypes.DWORD), ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.c_size_t)]

    class _U(ctypes.Union):
        _fields_ = [('ki', KEYBDINPUT), ('mi', MOUSEINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ('u',)
        _fields_ = [('type', wintypes.DWORD), ('u', _U)]

    user32 = ctypes.WinDLL('user32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, ctypes.c_size_t, ctypes.c_ssize_t)
    user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, ctypes.c_void_p, wintypes.DWORD]
    user32.SetWindowsHookExW.restype = ctypes.c_void_p
    user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
    user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t, ctypes.c_ssize_t]
    user32.CallNextHookEx.restype = ctypes.c_ssize_t
    user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), ctypes.c_void_p, wintypes.UINT, wintypes.UINT]
    user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), ctypes.c_void_p, wintypes.UINT,
                                    wintypes.UINT, wintypes.UINT]
    user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]
    user32.SetTimer.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.UINT, ctypes.c_void_p]
    user32.SetTimer.restype = ctypes.c_size_t
    user32.KillTimer.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
    user32.SendInput.restype = wintypes.UINT
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = ctypes.c_void_p
    return ctypes, wintypes, user32, kernel32, HOOKPROC, KBDLLHOOKSTRUCT, INPUT


_USER32_STATE = None


def physical_key_down(vk):
    """GetAsyncKeyState：此鍵目前實體上是否按著。"""
    global _USER32_STATE
    if _USER32_STATE is None:
        import ctypes
        user32 = ctypes.windll.user32
        user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        user32.GetAsyncKeyState.restype = ctypes.c_short
        _USER32_STATE = user32
    return bool(_USER32_STATE.GetAsyncKeyState(vk) & 0x8000)


MODIFIER_VKS = (0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5)  # L/R Shift、Ctrl、Alt


def user_idle_seconds():
    """距離上一次使用者輸入（鍵盤或滑鼠，含他人注入的事件）的秒數；取不到時回傳 None。"""
    try:
        import ctypes
        from ctypes import wintypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [('cbSize', wintypes.UINT), ('dwTime', wintypes.DWORD)]

        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return None
        kernel32 = ctypes.windll.kernel32
        kernel32.GetTickCount.restype = wintypes.DWORD
        return ((kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000.0
    except Exception:
        return None


def release_held_modifiers(is_down=physical_key_down, sender=None, keys=None):
    """貼上前把仍按著、且屬於已設定快捷鍵的修飾鍵用 SendInput key-up 放開，事件帶 MARKER（hook 會略過）。
    Alt 的 key-up 前會先送一組 no-op（VK 0xFF）。

    keys：已設定組合的元素 vk（PushToTalk.relevant_keys()；泛用 Alt/Shift/Ctrl 代表左右兩側）。
    與快捷鍵無關的修飾鍵（使用者正拿來打字的 Shift 等）不會被放開；keys=None 表示不限制（僅供舊呼叫端）。
    不會在之後恢復。回傳被放開的 vk 清單。
    """
    sender = sender or send_key
    released = []
    for vk in MODIFIER_VKS:
        if keys is not None and not any(_matches(e, vk) for e in keys):
            continue
        if is_down(vk):
            if vk in _ALT_VKS:
                # Alt 放開前先插入無作用按鍵，避免目標視窗把「單獨按放 Alt」當成啟動選單。
                sender(NOOP_VK, False, MARKER)
                sender(NOOP_VK, True, MARKER)
            sender(vk, True, MARKER)
            released.append(vk)
    return released


def running_process_names():
    """目前執行中的程序映像名稱（Toolhelp32 快照）；非 Windows 或失敗時回傳空 list。"""
    try:
        import ctypes
        from ctypes import wintypes

        class PROCESSENTRY32W(ctypes.Structure):
            _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD), ('th32ProcessID', wintypes.DWORD),
                        ('th32DefaultHeapID', ctypes.c_size_t), ('th32ModuleID', wintypes.DWORD),
                        ('cntThreads', wintypes.DWORD), ('th32ParentProcessID', wintypes.DWORD),
                        ('pcPriClassBase', wintypes.LONG), ('dwFlags', wintypes.DWORD),
                        ('szExeFile', wintypes.WCHAR * 260)]

        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
        kernel32.Process32FirstW.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESSENTRY32W)]
        kernel32.Process32NextW.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESSENTRY32W)]
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        snapshot = kernel32.CreateToolhelp32Snapshot(0x2, 0)  # TH32CS_SNAPPROCESS
        if not snapshot or snapshot == ctypes.c_void_p(-1).value:
            return []
        names = []
        try:
            entry = PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
            ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
            while ok:
                names.append(entry.szExeFile)
                ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
        finally:
            kernel32.CloseHandle(snapshot)
        return names
    except Exception:
        return []


def send_key(vk, is_up, extra=0):
    """用 SendInput 注入單一按鍵事件。"""
    ctypes, _, user32, _, _, _, INPUT = _win32()
    flags = (0x2 if is_up else 0) | (0x1 if vk in (0xA5, 0xA3, 0x5C) else 0)
    item = INPUT(type=1)
    item.ki.wVk = vk
    item.ki.dwFlags = flags
    item.ki.dwExtraInfo = extra
    return user32.SendInput(1, ctypes.byref(item), ctypes.sizeof(INPUT))


class LowLevelKeyboardHook:
    """WH_KEYBOARD_LL。callback(kind, value) 在 hook 執行緒呼叫，只應 queue.put。

    kind: 'start'/'stop'（value 為動作或 None）、'capture_live'/'capture_done'（value 為 combo tuple）。
    hook procedure 只有兩個出口：吞掉（return 1，僅限完成含 Alt 組合的非修飾鍵）或 return CallNextHookEx。
    """

    def __init__(self, machine, callback, clock=time.monotonic):
        self.machine = machine
        self.callback = callback
        self.clock = clock
        self.capture = None
        self.noop_count = 0
        self.swallowed_count = 0   # 被吞掉的事件數（Alt 組合的完成鍵 down/repeat/up）
        self._alt_masked = {}      # vk -> Event：no-op 注入完成時設定
        self.noop_waits = 0        # Alt key-up 到達時 no-op 尚未完成而等待的次數
        self.noop_wait_satisfied = 0
        self.watchdog_seconds = WATCHDOG_SECONDS
        self.idle_seconds = user_idle_seconds  # callable() -> 距上次使用者輸入的秒數或 None（可注入）
        self.last_callback = clock()
        self.reinstalls = 0
        self.liveness_seconds = LIVENESS_SECONDS
        self.liveness_wait_seconds = LIVENESS_WAIT_SECONDS
        self.probes_sent = 0           # 閒置存活探測：送出幾次
        self.probes_observed = 0       # hook 實際看到幾次
        self.liveness_reinstalls = 0
        self._probe_sent_at = None
        self._probe_seen = False
        self._w32 = None
        if getattr(machine, 'is_physically_down', 1) is None:
            machine.is_physically_down = physical_key_down
        self.error = None
        self.thread = None
        self.thread_id = None
        self._ready = threading.Event()
        self._proc_ref = None  # 保存 ctypes callback，避免被 GC
        self._noop_jobs = queue.Queue()
        self._noop_thread = None

    def start(self, timeout=3.0):
        self._noop_thread = threading.Thread(target=self._noop_worker, name='keyboard-hook-noop', daemon=True)
        self._noop_thread.start()
        self.thread = threading.Thread(target=self._run, name='keyboard-hook', daemon=True)
        self.thread.start()
        self._ready.wait(timeout)
        return self.error is None and self.thread_id is not None

    def stop(self):
        if self.thread is not None and self.thread.is_alive() and self.thread_id:
            user32 = _win32()[2]
            user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0)  # WM_QUIT
            self.thread.join(2.0)
        self.thread = None
        if self._noop_thread is not None:
            self._noop_jobs.put(None)
            self._noop_thread.join(2.0)
            self._noop_thread = None

    def begin_capture(self):
        self.capture = ComboCapture()

    def cancel_capture(self):
        self.capture = None

    def _emit(self, kind, value):
        try:
            self.callback(kind, value)
        except Exception:
            pass

    def _handle(self, wparam, info):
        """處理一個 hook 事件；回傳 True 表示要吞掉（只有 PushToTalk.handle 判定的組合完成鍵）。"""
        if info.dwExtraInfo == PROBE_MARKER:
            if info.vkCode == NOOP_VK:
                self.probes_observed += 1
                self._probe_seen = True
            return False
        if info.dwExtraInfo == MARKER or wparam not in (0x100, 0x101, 0x104, 0x105):
            return False  # 自己注入的 no-op，或非按鍵訊息
        vk = info.vkCode
        is_down = wparam in (0x100, 0x104)
        capture = self.capture
        if capture is not None:
            swallow = (not is_down) and self.machine.take_swallowed(vk)
            result = capture.key(vk, is_down)
            if result is not None:
                if result[0] == 'done':
                    self.capture = None
                    self.machine.reset()
                self._emit('capture_' + result[0], result[1])
            return swallow
        events, consumed, swallow = self.machine.handle(vk, is_down, self.clock())
        if is_down and (consumed or swallow):
            # 避免單獨按放 Alt 時啟動前景視窗的選單列：Alt 仍按住時插入無作用的按鍵。
            # 吞掉 Alt+Space 的 Space 時也一樣：前景視窗只會看到 Alt 按下、放開，會被當成「單獨按放 Alt」。
            # 不能在 hook procedure 內呼叫 SendInput（會等 hook 逾時而卡約 0.3 秒），改交給輔助執行緒。
            alts = [vk] if vk in _ALT_VKS else []
            if swallow:
                alts = [k for k in self.machine.held_keys() if k in _ALT_VKS]
            for alt in alts:
                if alt not in self._alt_masked:
                    done = threading.Event()
                    self._alt_masked[alt] = done
                    self._noop_jobs.put((alt, done))
        elif not is_down:
            done = self._alt_masked.pop(vk, None)
            if done is not None:
                self._wait_noop(done)  # Alt key-up 要放行了，no-op 還沒送出就最多等 25 ms
        if swallow:
            self.swallowed_count += 1
        for kind, value in events:
            self._emit(kind, value)
        return swallow

    NOOP_WAIT_SECONDS = 0.025
    NOOP_DELAY_SECONDS = 0.01

    def _wait_noop(self, done):
        if done.is_set():
            return
        self.noop_waits += 1
        deadline = time.monotonic() + self.NOOP_WAIT_SECONDS
        w32 = self._w32
        while not done.is_set() and time.monotonic() < deadline:
            if w32 is not None:
                # no-op 的注入事件會以「送入訊息」叫用本 hook；取訊息函式會處理它們，否則輔助執行緒要等到逾時。
                ctypes, wintypes, user32 = w32
                user32.PeekMessageW(ctypes.byref(wintypes.MSG()), None, 0, 0, 0)
            done.wait(0.001)
        if done.is_set():
            self.noop_wait_satisfied += 1

    def _noop_worker(self):
        while True:
            job = self._noop_jobs.get()
            if job is None:
                return
            # 稍等一下，讓觸發它的 Alt key-down 先走完 hook 鏈；否則 no-op 可能比 Alt key-down 先到達前景視窗，
            # 那樣 Alt 放開時仍會被當成「單獨按放 Alt」而啟動選單。
            if job[0] == 'probe':
                send_key(NOOP_VK, False, PROBE_MARKER)
                send_key(NOOP_VK, True, PROBE_MARKER)
                self.probes_sent += 1
                continue
            time.sleep(self.NOOP_DELAY_SECONDS)
            send_key(NOOP_VK, False, MARKER)
            send_key(NOOP_VK, True, MARKER)
            self.noop_count += 1
            job[1].set()

    def _run(self):
        try:
            ctypes, wintypes, user32, kernel32, HOOKPROC, KBDLLHOOKSTRUCT, _ = _win32()

            self._w32 = (ctypes, wintypes, user32)

            def proc(code, wparam, lparam):
                self.last_callback = self.clock()
                swallow = False
                try:
                    if code == 0:
                        swallow = bool(self._handle(wparam, ctypes.cast(lparam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents))
                except Exception:
                    swallow = False
                if swallow:
                    return 1  # 吞掉：完成含 Alt 組合的非修飾鍵（Alt+Space 不會開啟系統選單）
                return user32.CallNextHookEx(None, code, wparam, lparam)

            self._proc_ref = HOOKPROC(proc)
            msg = wintypes.MSG()
            user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)  # 建立執行緒訊息佇列
            self.thread_id = kernel32.GetCurrentThreadId()
            hook = user32.SetWindowsHookExW(13, self._proc_ref, kernel32.GetModuleHandleW(None), 0)
            if not hook:
                self.error = f'SetWindowsHookExW 失敗（錯誤 {ctypes.get_last_error()}）'
                return
            timer = user32.SetTimer(None, 0, 20, None)
            self._ready.set()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == 0x0113:  # WM_TIMER
                    now = self.clock()
                    for kind, value in self.machine.tick(now):
                        self._emit(kind, value)
                    # 按著鍵卻長時間沒有任何 callback：hook 可能被系統靜默移除，重裝。
                    reinstall = watchdog_due(now, self.last_callback, self.machine.any_held(), self.watchdog_seconds)
                    idle = self.idle_seconds()
                    # 取不到閒置時間：視為使用者閒置（寧可不探測，也不要去重設系統閒置計時器）。
                    last_user_input = now - idle if idle is not None else float('-inf')
                    decision = liveness_decision(now, self.last_callback, self._probe_sent_at, self._probe_seen,
                                                 last_user_input,
                                                 self.liveness_seconds, self.liveness_wait_seconds)
                    if decision == 'probe':
                        # 閒置時也要確認 hook 還在：由輔助執行緒注入帶 PROBE_MARKER 的 no-op（hook 執行緒內不能 SendInput）。
                        self._probe_seen = False
                        self._probe_sent_at = now
                        self._noop_jobs.put(('probe',))
                    elif decision == 'ok':
                        self._probe_sent_at = None
                    elif decision == 'reinstall':
                        self.liveness_reinstalls += 1
                        reinstall = True
                    if reinstall:
                        user32.UnhookWindowsHookEx(hook)
                        hook = user32.SetWindowsHookExW(13, self._proc_ref, kernel32.GetModuleHandleW(None), 0)
                        self.last_callback = now
                        self._probe_sent_at = None
                        self.reinstalls += 1
                        if not hook:
                            self.error = 'hook 重新安裝失敗'
                            self._emit('warning', LIVENESS_WARNING)
                            break
            if timer:
                user32.KillTimer(None, timer)
            user32.UnhookWindowsHookEx(hook)
        except Exception as error:
            self.error = str(error)
        finally:
            self._ready.set()
