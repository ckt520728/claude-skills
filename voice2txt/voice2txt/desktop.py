import ctypes
import inspect
import json
import logging
import os
import queue
import sys
import threading
import time
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import numpy as np
import sounddevice as sd

from voice2txt.core import Chunker, MODES, RATE, Store, WhisperEngine, preferred_settings
from voice2txt import audiofocus, insights, keystore, learning, sounds, startup, theme, tray
from voice2txt import context as window_context
from voice2txt.hotkeys import (LowLevelKeyboardHook, PushToTalk, TYPELESS_WARNING, combo_name, conflicting_combos,
                               format_combo, HOTKEYS_VERSION, migrate_hotkeys, paste_decision, parse_combo, release_held_modifiers,
                               running_process_names)
from voice2txt.translation import CLOUD, EFFORTS, build_translator, decode_segment, ollama_models, pick_ollama_model

DATA = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Voice2Txt'
LLM_REFINE, WHISPER_ONLY = 'Whisper + LLM 整理', '僅 Whisper'
LEGACY_BACKENDS = {'本機 Ollama': LLM_REFINE, 'Whisper': WHISPER_ONLY}
DICTATION_LANGUAGES = {'繁體中文': 'zh', 'English': 'en'}
DEFAULT_HOTKEYS = {'dictate': ['RightAlt', 'Alt+Shift+Space'], 'translate': ['RightAlt+RightShift'],
                   'ask': ['RightAlt+RightCtrl']}  # 舊預設 RightAlt+Space 會開啟系統選單，載入時遷移
HOTKEY_TITLES = {'dictate': '口述', 'translate': '中文 → English', 'ask': '隨便問'}
INDICATOR_MODES = {'zh': '口述（繁體中文）', 'en': '口述（English）', 'translate': '翻譯', 'ask': '隨便問'}
RETENTION_CHOICES = {'1 週': 7, '1 個月': 30, '3 個月': 90, '永久': None}
HISTORY_FILTERS = {'全部': None, '口述': ('zh', 'en'), '翻譯': ('translate',), '隨便問': ('ask',)}
INSIGHT_LABELS = (('words', '口述字數'), ('saved', '節省時間'), ('wpm', '平均口述速度'), ('time', '總口述時間'),
                  ('active', '活躍天數'), ('streak', '目前連續天數'), ('longest', '最長連續天數'))
HEAT_COLORS = {'light': ('#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39'),
               'dark': ('#2d333b', '#0e4429', '#006d32', '#26a641', '#39d353')}
HEAT_STEP, HEAT_CELL, HEAT_WEEKS = 18, 15, 26
PASTE_RESTORE_MS = 700  # 貼上後等目標程式讀完剪貼簿，再還原原本的文字
GWL_EXSTYLE, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW, GA_ROOT = -20, 0x08000000, 0x00000080, 2
SINGLE_INSTANCE_MUTEX = 'Local\\Voice2Txt-SingleInstance'
ERROR_ALREADY_EXISTS, HWND_BROADCAST = 183, 0xFFFF
TRAY_CLASS_PREFIX = 'Voice2TxtTray'  # tray.TrayIcon 的視窗類別名稱前綴（後面接執行個體位址，無法直接 FindWindowW）
_instance_mutex = None  # 具名 mutex handle：保存到程序結束，才能持續宣告「已有執行個體」


def _safe_int(value, default=1):
    """手改 settings.json 可能是字串/None/布林等：轉不成整數就用預設值，避免啟動崩潰。"""
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def format_duration(seconds):
    """秒數 -> '2 小時 5 分' / '12 分' / '30 秒'。"""
    seconds = max(0, float(seconds or 0))
    if seconds < 60:
        return f'{int(seconds)} 秒'
    hours, minutes = divmod(int(round(seconds / 60)), 60)
    return f'{hours} 小時 {minutes} 分' if hours else f'{minutes} 分'


def clean_terms(value):
    return [t.strip() for t in value if isinstance(t, str) and t.strip()] if isinstance(value, list) else []


def merge_pastes(pending):
    """把等待貼上的 (text, target) 依目標視窗合併成一段（'\n' 連接，保持順序）；各目標依首次出現順序（純函式）。"""
    order, texts = [], {}
    for text, target in pending:
        if target not in texts:
            order.append(target)
            texts[target] = []
        texts[target].append(text)
    return [('\n'.join(texts[target]), target) for target in order]


def accepts_context(translator):
    """舊式／替身翻譯後端的 refine 若不接受 context 參數，就不傳（維持相容）。"""
    if translator is None:
        return True
    try:
        params = inspect.signature(translator.refine).parameters.values()
    except (TypeError, ValueError, AttributeError):
        return False
    return any(p.name == 'context' or p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD) for p in params)


def find_tray_window():
    """列舉視窗，找類別名稱以 TRAY_CLASS_PREFIX 開頭的系統匣視窗（其他執行個體）；找不到回傳 0。"""
    if sys.platform != 'win32':
        return 0
    from ctypes import wintypes
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    found = []

    def visit(hwnd, _):
        buffer = ctypes.create_unicode_buffer(256)
        if user32.GetClassNameW(hwnd, buffer, 256) and buffer.value.startswith(TRAY_CLASS_PREFIX):
            found.append(hwnd)
            return False
        return True
    user32.EnumWindows(enum_proc(visit), 0)
    return found[0] if found else 0


def _post_show(user32, target):
    """要求第一個執行個體顯示視窗；PostMessageW 失敗只記錄警告（呼叫端仍照常結束）。"""
    if not user32.PostMessageW(target, user32.RegisterWindowMessageW(tray.SHOW_MESSAGE_NAME), 0, 0):
        logging.getLogger('voice2txt').warning('PostMessageW 要求第一個執行個體顯示視窗失敗（錯誤 %s）', ctypes.get_last_error())


def claim_single_instance():
    """True＝這是第一個執行個體；False＝已有執行個體在跑，已廣播要求它顯示視窗（呼叫端應結束）。"""
    global _instance_mutex
    if sys.platform != 'win32':
        return True
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    user32.RegisterWindowMessageW.argtypes = [ctypes.c_wchar_p]
    user32.RegisterWindowMessageW.restype = ctypes.c_uint
    user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
    user32.PostMessageW.restype = ctypes.c_int
    ctypes.set_last_error(0)
    handle = kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX)
    error = ctypes.get_last_error()
    if not handle:
        # 例如已有以較高權限執行的執行個體而得到 ERROR_ACCESS_DENIED：改找系統匣視窗；找到就當作已有執行個體。
        window = find_tray_window()
        if window:
            _post_show(user32, window)
            return False
        return True  # 找不到才不擋啟動
    _instance_mutex = handle
    if error == ERROR_ALREADY_EXISTS:
        _post_show(user32, HWND_BROADCAST)
        return False
    return True


class RecordingIndicator:
    """螢幕下方置中的小膠囊：錄音中／整理中。永遠不取得焦點（WS_EX_NOACTIVATE｜WS_EX_TOOLWINDOW）。"""

    def __init__(self, root):
        self.root = root
        self.window = tk.Toplevel(root)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.attributes('-alpha', 0.92)
        self.window.configure(background='#161a23')
        self.text = tk.StringVar()
        self.label = tk.Label(self.window, textvariable=self.text, background='#161a23', foreground='#ffffff',
                              font=('Microsoft JhengHei UI', 13), padx=22, pady=9)
        self.label.pack()
        self.visible = False
        self.ex_styles = []
        self._make_noactivate()

    def _make_noactivate(self):
        if sys.platform != 'win32':
            return
        user32 = ctypes.windll.user32
        user32.GetAncestor.restype = ctypes.c_void_p
        user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        user32.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
        user32.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]
        self.window.update_idletasks()
        inner = self.window.winfo_id()
        for hwnd in {inner, user32.GetAncestor(inner, GA_ROOT) or inner}:
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
            self.ex_styles.append(user32.GetWindowLongW(hwnd, GWL_EXSTYLE))

    def apply_palette(self, palette):
        self.window.configure(background=palette['panel'])
        self.label.configure(background=palette['panel'], foreground=palette['fg'])

    def show(self, text):
        self.text.set(text)
        self.window.update_idletasks()
        width, height = self.window.winfo_reqwidth(), self.window.winfo_reqheight()
        x = (self.window.winfo_screenwidth() - width) // 2
        y = self.window.winfo_screenheight() - height - 110
        self.window.geometry(f'{width}x{height}+{x}+{y}')
        if not self.visible:
            self.window.deiconify()
            self.window.attributes('-topmost', True)
            self.visible = True

    def set_text(self, text):
        if self.visible:
            self.show(text)

    def hide(self):
        if self.visible:
            self.window.withdraw()
            self.visible = False

    def destroy(self):
        try:
            self.window.destroy()
        except tk.TclError:
            pass


class App:
    def __init__(self, root, enable_tray=False):
        self.root = root
        self.root.title('Voice2Txt · 自在說，本機寫')
        self.root.geometry('1000x720')
        self.root.minsize(780, 600)
        DATA.mkdir(parents=True, exist_ok=True)
        self.store = Store(DATA / 'history.sqlite3')
        self.events = queue.Queue()
        self.audio = queue.Queue(maxsize=240)  # 最多約 24 秒，超量時明確停止。
        self.jobs = queue.Queue(maxsize=6)
        self.pending_chunks = []
        self.engine = None
        self.translator = None
        self.recording = False
        self.draining = False
        self.stream = None
        self.closed = False
        self.mode = tk.StringVar(value=MODES['zh'])
        preferred_model, preferred_device = preferred_settings()
        self.model = tk.StringVar(value=preferred_model)
        self.compute = tk.StringVar(value=preferred_device)
        self.translation_backend = tk.StringVar(value=WHISPER_ONLY)
        self.llm_model = tk.StringVar(value='gemma4:latest')
        self.cloud = {provider: {'enabled': tk.BooleanVar(value=True), 'model': tk.StringVar(value=model),
                                 'effort': tk.StringVar(value=effort), 'key': tk.StringVar(value='')}
                      for provider, (model, effort) in CLOUD.items()}
        self.loading = False
        self.status = tk.StringVar(value='準備就緒。請先載入模型，再開始說話。')
        self.paste = tk.BooleanVar(value=False)
        self.context_aware = tk.BooleanVar(value=True)
        self.hotkey_paste = tk.BooleanVar(value=True)
        self.sounds_on = tk.BooleanVar(value=True)
        self.mute_others_on = tk.BooleanVar(value=False)
        self.appearance = tk.StringVar(value='系統')
        self.retention = tk.StringVar(value='永久')
        self.history_filter = tk.StringVar(value='全部')
        self.dictionary_auto = []
        self.dictionary_ignored = []
        self.candidates = []
        self.editor_outputs = []     # 目前編輯區內「模型原始輸出」的段落，供自動字典比對
        self.editor_snapshot = ''
        self.session_outputs = []
        self.session_context = None
        self.session_language = 'zh'
        self.session_paste = False
        self.target_window = 0
        self.mute_handle = None
        self.ask_pending = False
        self.ask_cancel = False
        self.clip_saved = None
        self.clip_after = None
        self.clip_seq = 0
        self.last_clipboard_restore = ''
        self.palette = theme.LIGHT
        self.insight_stats = {}
        self.insight_cells = []
        self.mic = tk.StringVar()
        self.vocabulary = ''
        self.dictation_language = tk.StringVar(value='繁體中文')
        self.hotkeys = {action: list(names) for action, names in DEFAULT_HOTKEYS.items()}
        self.hotkey_labels = {action: tk.StringVar() for action in DEFAULT_HOTKEYS}
        self.hotkey_help = tk.StringVar()
        self.hotkey_buttons = {}
        self.close_to_tray = tk.BooleanVar(value=True)
        self.start_at_login = tk.BooleanVar(value=False)
        self.tray = None
        self.indicator = None
        self.deferred_pastes = []   # (text, target_window)：快捷鍵還按住時先暫存，放開後才貼
        self.last_paste_released = []
        self.hotkey_warning = ''
        self._poll_id = None
        self.capture_target = None  # (action, replace)
        self.hook = None
        self.ptt = PushToTalk({})
        self._ui()
        try:
            self.root.iconbitmap(default=str(tray.asset_path('voice2txt.ico')))
        except tk.TclError:
            pass
        self.indicator = RecordingIndicator(root)
        self._load_settings()
        self._apply_theme()
        self._prune_history()
        self._render_candidates()
        self._render_auto_label()
        self._backend_changed()
        self._history()
        self._refresh_insights()
        self.root.protocol('WM_DELETE_WINDOW', self.on_window_close)
        threading.Thread(target=self._decode, daemon=True).start()
        self._apply_hotkeys()
        if sys.platform == 'win32':
            self.hook = LowLevelKeyboardHook(self.ptt, lambda kind, value: self.events.put(
                ('hotkey_capture', (kind[8:], value)) if kind.startswith('capture_')
                else ('warning', value) if kind == 'warning' else ('hotkey', (kind, value))))
            if not self.hook.start():
                self.status.set('無法安裝全域快捷鍵：' + str(self.hook.error) + '；請使用錄音按鈕。')
        if enable_tray and sys.platform == 'win32':
            self.tray = tray.TrayIcon(lambda action: self.events.put(('tray', action)))
            if not self.tray.start():
                self.status.set('無法建立系統匣圖示：' + str(self.tray.error) + '；關閉視窗將直接結束。')
            if self.start_at_login.get():
                try:
                    startup.enable()  # 資料夾搬移後把登錄的路徑更新成目前位置
                except OSError:
                    pass
        self._poll_id = self.root.after(50, self._poll)

    def _ui(self):
        style = self.style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', font=('Microsoft JhengHei UI', 11))
        style.configure('TButton', padding=9)
        shell = ttk.Frame(self.root, padding=24)
        shell.pack(fill='both', expand=True)
        ttk.Label(shell, text='Voice2Txt', font=('Segoe UI', 30, 'bold')).pack(anchor='w')
        ttk.Label(shell, text='讓想法流動。Whisper 轉錄 + LLM 整理 · 繁體中文 / English · 無訂閱').pack(anchor='w', pady=(0, 18))
        tabs = ttk.Notebook(shell)
        tabs.pack(fill='both', expand=True)
        insights_page, live, history = [ttk.Frame(tabs, padding=16) for _ in range(3)]
        settings_page = ttk.Frame(tabs)
        self.tabs, self.insights_tab = tabs, insights_page
        for frame, title in zip((insights_page, live, history, settings_page), ('洞察', '即時語音', '歷史紀錄', '字典與設定')):
            tabs.add(frame, text=title)
        tabs.select(live)
        tabs.bind('<<NotebookTabChanged>>', lambda event: self._refresh_insights() if tabs.select() == str(insights_page) else None)
        self._build_insights(insights_page)
        self.settings_canvas = tk.Canvas(settings_page, highlightthickness=0)
        settings_scrollbar = ttk.Scrollbar(settings_page, orient='vertical', command=self.settings_canvas.yview)
        settings_scrollbar.pack(side='right', fill='y')
        self.settings_canvas.pack(side='left', fill='both', expand=True)
        self.settings_canvas.configure(yscrollcommand=settings_scrollbar.set)
        settings = ttk.Frame(self.settings_canvas, padding=16)
        settings_window = self.settings_canvas.create_window((0, 0), window=settings, anchor='nw')
        settings.bind('<Configure>', lambda event: self.settings_canvas.configure(scrollregion=self.settings_canvas.bbox('all')))
        self.settings_canvas.bind('<Configure>', lambda event: self.settings_canvas.itemconfigure(settings_window, width=event.width))
        controls = ttk.Frame(live)
        controls.pack(fill='x')
        self.mode_box = ttk.Combobox(controls, textvariable=self.mode, values=list(MODES.values()), state='readonly', width=22)
        self.mode_box.pack(side='left')
        self.start_button = ttk.Button(controls, text='● 開始錄音', command=self.toggle, state='disabled')
        self.start_button.pack(side='left', padx=10)
        ttk.Button(controls, text='複製全文', command=self.copy).pack(side='right')
        self.text = tk.Text(live, wrap='word', font=('Microsoft JhengHei UI', 16),
                            background='#f5f7fb', foreground='#162235', relief='flat', padx=18, pady=18)
        self.text.pack(fill='both', expand=True, pady=16)
        self.text.bind('<FocusOut>', lambda event: self._learn_check())
        self.source_panel = ttk.Frame(live)
        ttk.Label(self.source_panel, text='Whisper 原始轉錄（LLM 整理前，供核對）').pack(anchor='w')
        self.source_text = tk.Text(self.source_panel, height=3, wrap='word', state='disabled', font=('Microsoft JhengHei UI', 11))
        self.source_text.pack(fill='x')
        row = ttk.Frame(live)
        row.pack(fill='x')
        ttk.Button(row, text='匯出 TXT', command=self.export).pack(side='left')
        ttk.Button(row, text='清空畫面', command=self.clear_text).pack(side='left', padx=8)
        ttk.Checkbutton(row, text='完成後貼入原視窗', variable=self.paste).pack(side='right')
        ttk.Label(live, textvariable=self.hotkey_help, wraplength=900).pack(anchor='w', pady=(10, 0))
        ttk.Label(shell, textvariable=self.status, wraplength=900).pack(anchor='w', pady=(14, 0))
        filter_bar = ttk.Frame(history)
        filter_bar.pack(fill='x', pady=(0, 8))
        for name in HISTORY_FILTERS:
            ttk.Radiobutton(filter_bar, text=name, value=name, variable=self.history_filter, style='Toolbutton',
                            command=self._history).pack(side='left', padx=(0, 6))
        self.history = tk.Listbox(history, font=('Microsoft JhengHei UI', 11), activestyle='none')
        self.history.pack(fill='both', expand=True)
        self.history.bind('<Double-Button-1>', self.show_history)
        ttk.Button(history, text='刪除所有歷史紀錄', command=self.clear_history).pack(anchor='e', pady=8)
        ttk.Label(settings, text='Whisper 模型（首次載入需下載；之後可離線使用）').pack(anchor='w')
        self.model_box = ttk.Combobox(settings, textvariable=self.model, values=['base', 'small', 'medium', 'large-v3'], state='readonly')
        self.model_box.pack(anchor='w', pady=8)
        ttk.Label(settings, text='運算裝置：cpu 通用；cuda 需要 NVIDIA 顯示卡與 GPU 套件。').pack(anchor='w')
        self.compute_box = ttk.Combobox(settings, textvariable=self.compute, values=['cpu', 'cuda'], state='readonly')
        self.compute_box.pack(anchor='w', pady=8)
        ttk.Label(settings, text='文字處理：Whisper 先把語音轉成文字，再由 LLM 去除贅詞與重複、套用口誤更正、修正錯字並加標點；'
                  '中翻英模式同時翻譯。', wraplength=660).pack(anchor='w')
        self.backend_box = ttk.Combobox(settings, textvariable=self.translation_backend, values=[LLM_REFINE, WHISPER_ONLY],
                                        state='readonly', width=22)
        self.backend_box.pack(anchor='w', pady=8)
        self.backend_box.bind('<<ComboboxSelected>>', self._backend_changed)
        ttk.Label(settings, text='LLM 順序：本機 Ollama → Anthropic → OpenAI → Gemini → 只用 Whisper 結果。偵測到本機 Ollama 時預設啟用；'
                  '啟用時 Whisper 固定用 CPU，建議 small。', wraplength=660).pack(anchor='w')
        ollama_row = ttk.Frame(settings)
        ollama_row.pack(anchor='w', pady=8)
        ttk.Label(ollama_row, text='① 本機 Ollama 模型', width=18).pack(side='left')
        ttk.Entry(ollama_row, textvariable=self.llm_model, width=24).pack(side='left', padx=6)
        for number, provider in zip('②③④', CLOUD):
            values = self.cloud[provider]
            cloud_row = ttk.Frame(settings)
            cloud_row.pack(anchor='w', pady=4)
            ttk.Checkbutton(cloud_row, text=f'{number} {provider} 備援', variable=values['enabled'], width=16).pack(side='left')
            ttk.Entry(cloud_row, textvariable=values['model'], width=18).pack(side='left', padx=6)
            ttk.Label(cloud_row, text='推理強度').pack(side='left', padx=(8, 0))
            ttk.Combobox(cloud_row, textvariable=values['effort'], values=list(EFFORTS), state='readonly', width=7).pack(side='left', padx=6)
            ttk.Label(cloud_row, text='API key').pack(side='left', padx=(8, 0))
            ttk.Entry(cloud_row, textvariable=values['key'], show='•', width=22).pack(side='left', padx=6)
        ttk.Label(settings, text='雲端備援只在前一個 LLM 失敗時使用，只送出 Whisper 轉錄文字（不含錄音）到 Anthropic／OpenAI／Google，依用量計費。'
                  'API key 以 Windows DPAPI 加密保存；留空時改讀環境變數 ANTHROPIC_API_KEY／OPENAI_API_KEY／GEMINI_API_KEY，都沒有就略過。',
                  wraplength=660).pack(anchor='w', pady=(4, 8))
        self.load_button = ttk.Button(settings, text='載入 / 下載模型', command=self.load_model)
        self.load_button.pack(anchor='w')
        ttk.Label(settings, text='base / small 較省資源；medium / large-v3 建議搭配 NVIDIA GPU。').pack(anchor='w', pady=10)
        self.devices = {f'{i} · {d["name"]}': i for i, d in enumerate(sd.query_devices()) if d['max_input_channels'] > 0}
        ttk.Label(settings, text='麥克風').pack(anchor='w')
        self.mic_box = ttk.Combobox(settings, textvariable=self.mic, values=['系統預設'] + list(self.devices), state='readonly', width=65)
        self.mic_box.pack(anchor='w', pady=8)
        self.mic.set('系統預設')
        ttk.Label(settings, text='口述語言（快捷鍵「口述」使用；錄音按鈕仍依上方模式選單）').pack(anchor='w', pady=(14, 0))
        ttk.Combobox(settings, textvariable=self.dictation_language, values=list(DICTATION_LANGUAGES),
                     state='readonly', width=14).pack(anchor='w', pady=8)
        ttk.Label(settings, text='快捷鍵').pack(anchor='w', pady=(10, 0))
        ttk.Label(settings, text='按住說話、放開即停止；快按一下則持續錄音，再快按一下停止。每個動作最多兩組；'
                  '按「設定」後依序按下組合鍵，全部放開即確認（會取代該動作原有的組合）。',
                  wraplength=660).pack(anchor='w')
        for action, title in HOTKEY_TITLES.items():
            row = ttk.Frame(settings)
            row.pack(anchor='w', pady=4, fill='x')
            ttk.Label(row, text=title, width=14).pack(side='left')
            ttk.Label(row, textvariable=self.hotkey_labels[action], width=44).pack(side='left')
            buttons = {}
            for key, text, command in (('set', '設定', lambda a=action: self._begin_capture(a, True)),
                                       ('add', '再加一個', lambda a=action: self._begin_capture(a, False)),
                                       ('clear', '清除', lambda a=action: self._clear_hotkey(a))):
                buttons[key] = ttk.Button(row, text=text, command=command)
                buttons[key].pack(side='left', padx=3)
            self.hotkey_buttons[action] = buttons
        ttk.Checkbutton(settings, text='關閉視窗時縮到系統匣', variable=self.close_to_tray).pack(anchor='w', pady=(14, 0))
        ttk.Checkbutton(settings, text='登入 Windows 時自動啟動（縮在系統匣）', variable=self.start_at_login,
                        command=self._login_toggled).pack(anchor='w', pady=(4, 0))
        ttk.Checkbutton(settings, text='依前景 App 調整格式（傳送視窗標題與 App 名稱給 LLM）',
                        variable=self.context_aware).pack(anchor='w', pady=(14, 0))
        ttk.Label(settings, text='開啟時，口述／翻譯會把前景視窗標題與程式名稱（不含內容）一併交給 LLM；若啟用雲端備援，這些文字也會送出。',
                  wraplength=660).pack(anchor='w', padx=24)
        ttk.Checkbutton(settings, text='快捷鍵錄音完成後貼回原視窗', variable=self.hotkey_paste).pack(anchor='w', pady=(8, 0))
        ttk.Checkbutton(settings, text='互動聲音', variable=self.sounds_on).pack(anchor='w', pady=(4, 0))
        ttk.Checkbutton(settings, text='語音輸入時靜音其他音訊', variable=self.mute_others_on).pack(anchor='w', pady=(4, 0))
        look_row = ttk.Frame(settings)
        look_row.pack(anchor='w', pady=(10, 0))
        ttk.Label(look_row, text='外觀', width=14).pack(side='left')
        appearance_box = ttk.Combobox(look_row, textvariable=self.appearance, values=list(theme.CHOICES), state='readonly', width=8)
        appearance_box.pack(side='left')
        appearance_box.bind('<<ComboboxSelected>>', lambda event: self._appearance_changed())
        ttk.Label(look_row, text='保留歷史紀錄', width=14).pack(side='left', padx=(24, 0))
        ttk.Combobox(look_row, textvariable=self.retention, values=list(RETENTION_CHOICES), state='readonly',
                     width=8).pack(side='left')
        ttk.Label(settings, text='個人字典：以逗號分隔專有名詞，協助辨識；不是強制文字替換。').pack(anchor='w', pady=(14, 6))
        self.dictionary = tk.Text(settings, height=5, wrap='word', font=('Microsoft JhengHei UI', 12))
        self.dictionary.pack(fill='x')
        ttk.Label(settings, text='自動新增（候選）：你在「即時語音」編輯區改字後，離開編輯區或儲存設定時偵測到的新字詞；'
                  '按「加入」才會進入字典。', wraplength=660).pack(anchor='w', pady=(14, 6))
        self.candidate_list = tk.Listbox(settings, height=4, font=('Microsoft JhengHei UI', 11), exportselection=False)
        self.candidate_list.pack(fill='x')
        candidate_row = ttk.Frame(settings)
        candidate_row.pack(anchor='w', pady=6)
        self.candidate_add_button = ttk.Button(candidate_row, text='加入', command=lambda: self._candidate_action(True))
        self.candidate_add_button.pack(side='left')
        self.candidate_ignore_button = ttk.Button(candidate_row, text='忽略', command=lambda: self._candidate_action(False))
        self.candidate_ignore_button.pack(side='left', padx=8)
        ttk.Button(candidate_row, text='清空已自動加入', command=self._clear_auto).pack(side='left')
        self.auto_label = tk.StringVar()
        ttk.Label(settings, textvariable=self.auto_label, wraplength=660).pack(anchor='w')
        self.themed_widgets = [self.text, self.source_text, self.dictionary, self.history, self.candidate_list,
                               self.settings_canvas, self.heatmap, self.heat_legend]
        ttk.Button(settings, text='儲存設定與字典', command=self.save_settings).pack(anchor='e', pady=10)

    def _load_settings(self):
        try:
            settings = json.loads((DATA / 'settings.json').read_text(encoding='utf-8'))
            if settings.get('model') in ('base', 'small', 'medium', 'large-v3'):
                self.model.set(settings['model'])
            if settings.get('compute') in ('cpu', 'cuda'):
                self.compute.set(settings['compute'])
            backend = LEGACY_BACKENDS.get(settings.get('translation_backend_v2'), settings.get('translation_backend_v2'))
            if backend in (LLM_REFINE, WHISPER_ONLY):
                self.translation_backend.set(backend)
                self.backend_chosen = True
            self.llm_model.set(settings.get('llm_model', 'gemma4:latest'))
            cloud = settings.get('cloud', {})
            if settings.get('cloud_provider') in CLOUD and not cloud:
                # 舊版只有一組雲端設定。
                cloud = {settings['cloud_provider']: {'model': settings.get('cloud_model', ''),
                                                      'key': settings.get('cloud_key', '')}}
            for provider, saved in cloud.items():
                if provider in self.cloud:
                    values = self.cloud[provider]
                    values['enabled'].set(saved.get('enabled', True))
                    values['model'].set(saved.get('model') or CLOUD[provider][0])
                    if saved.get('effort') in EFFORTS:
                        values['effort'].set(saved['effort'])
                    values['key'].set(keystore.unprotect(saved.get('key', '')))
            self.close_to_tray.set(bool(settings.get('close_to_tray', True)))
            self.start_at_login.set(bool(settings.get('start_at_login', False)))
            if settings.get('dictation_language') in DICTATION_LANGUAGES:
                self.dictation_language.set(settings['dictation_language'])
            self.context_aware.set(bool(settings.get('context_aware', True)))
            self.hotkey_paste.set(bool(settings.get('hotkey_paste', True)))
            self.sounds_on.set(bool(settings.get('sounds', True)))
            self.mute_others_on.set(bool(settings.get('mute_others', False)))
            if settings.get('appearance') in theme.CHOICES:
                self.appearance.set(settings['appearance'])
            if settings.get('retention') in RETENTION_CHOICES:
                self.retention.set(settings['retention'])
            self.dictionary_auto = clean_terms(settings.get('dictionary_auto'))
            self.dictionary_ignored = clean_terms(settings.get('dictionary_ignored'))
            saved_keys = settings.get('hotkeys')
            if isinstance(saved_keys, dict):
                for action in DEFAULT_HOTKEYS:
                    names = saved_keys.get(action)
                    if isinstance(names, list):
                        valid = []
                        for name in names[:2]:
                            try:
                                valid.append(combo_name(parse_combo(name)))
                            except (ValueError, TypeError):
                                pass
                        self.hotkeys[action] = migrate_hotkeys(action, valid, DEFAULT_HOTKEYS,
                                                               _safe_int(settings.get('hotkeys_version'), 1))
            self.dictionary.insert('1.0', settings.get('dictionary', ''))
            self.vocabulary = settings.get('dictionary', '')
        except (OSError, ValueError):
            pass
        if sys.platform == 'win32':
            # 勾選框以登錄實際狀態為準（勾選當下就寫登錄，settings.json 可能沒跟上）。
            try:
                self.start_at_login.set(startup.is_enabled())
            except OSError:
                pass
        if not getattr(self, 'backend_chosen', False):
            # 尚未自行選擇引擎：偵測到本機 Ollama 就預設使用。
            names = ollama_models()
            if names:
                self.translation_backend.set(LLM_REFINE)
                self.llm_model.set(pick_ollama_model(names, self.llm_model.get()))
                self.model.set('small')

    def save_settings(self):
        self._learn_check()
        self.vocabulary = self.dictionary.get('1.0', 'end').strip()
        message = '已儲存設定。'
        cloud = {}
        for provider, values in self.cloud.items():
            try:
                key = keystore.protect(values['key'].get().strip())
            except OSError as error:
                key = ''
                message = f'已儲存設定，但 API key 未保存：{error}'
            cloud[provider] = {'enabled': values['enabled'].get(), 'model': values['model'].get(),
                               'effort': values['effort'].get(), 'key': key}
        (DATA / 'settings.json').write_text(json.dumps({'model': self.model.get(), 'compute': self.compute.get(),
            'translation_backend_v2': self.translation_backend.get(), 'llm_model': self.llm_model.get(),
            'cloud': cloud, 'dictation_language': self.dictation_language.get(),
            'hotkeys': self.hotkeys, 'hotkeys_version': HOTKEYS_VERSION, 'close_to_tray': self.close_to_tray.get(),
            'start_at_login': self.start_at_login.get(), 'dictionary': self.vocabulary,
            'context_aware': self.context_aware.get(), 'hotkey_paste': self.hotkey_paste.get(),
            'sounds': self.sounds_on.get(), 'mute_others': self.mute_others_on.get(),
            'appearance': self.appearance.get(), 'retention': self.retention.get(),
            'dictionary_auto': self.dictionary_auto, 'dictionary_ignored': self.dictionary_ignored},
            ensure_ascii=False), encoding='utf-8')
        self.backend_chosen = True
        removed = self._prune_history()
        self.status.set(message + (f' 已刪除 {removed} 筆過期的歷史紀錄。' if removed else ''))

    def _login_toggled(self):
        wanted = self.start_at_login.get()
        try:
            startup.enable() if wanted else startup.disable()
            self.status.set('登入 Windows 時會自動啟動並縮在系統匣。' if wanted else '已取消登入時自動啟動。')
        except OSError as error:
            self.start_at_login.set(not wanted)
            self.status.set(f'無法變更登入時自動啟動：{error}')

    def _cloud_settings(self):
        """回傳已啟用且有 API key 的雲端備援，依固定順序 Anthropic → OpenAI → Gemini。"""
        clouds = []
        for provider, values in self.cloud.items():
            key = values['key'].get().strip() or os.environ.get(provider.upper() + '_API_KEY', '')
            if values['enabled'].get() and key:
                clouds.append((provider, values['model'].get(), key, values['effort'].get()))
        return clouds

    def _backend_changed(self, event=None):
        if self.translation_backend.get() == LLM_REFINE:
            self.compute.set('cpu')
            if event is not None:
                self.model.set('small')
            self.compute_box.configure(state='disabled')
        else:
            self.compute_box.configure(state='readonly')

    def load_model(self):
        if self.recording or self.draining:
            return
        size = self.model.get()
        device = self.compute.get()
        llm_enabled = self.translation_backend.get() == LLM_REFINE
        llm_name = self.llm_model.get().strip() if llm_enabled else ''
        clouds = self._cloud_settings() if llm_enabled else []
        if llm_enabled:
            device = 'cpu'
        self.loading = True
        self.load_button.configure(state='disabled')
        self.start_button.configure(state='disabled')
        self.status.set(f'載入 {size} 模型中…首次下載可能需要數分鐘。')
        def load():
            try:
                engine = WhisperEngine(size, device=device, model_dir=DATA / 'models')
                translator, warnings = build_translator(llm_name, clouds)
                self.events.put(('loaded', (engine, translator, warnings)))
            except Exception as error:
                self.events.put(('load_error', str(error)))
        threading.Thread(target=load, daemon=True).start()

    def _user32(self):
        user32 = ctypes.windll.user32
        user32.GetForegroundWindow.restype = ctypes.c_void_p
        user32.GetAncestor.restype = ctypes.c_void_p
        user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        return user32

    def _own_hwnd(self):
        """主視窗的最上層 hwnd（只能在 Tk 執行緒呼叫）。"""
        if sys.platform != 'win32':
            return 0
        user32 = self._user32()
        inner = self.root.winfo_id()
        return user32.GetAncestor(inner, GA_ROOT) or inner

    def _is_own_window(self, hwnd):
        return bool(hwnd) and hwnd == self._own_hwnd()

    def _editor_selection(self):
        try:
            return self.text.get('sel.first', 'sel.last')
        except tk.TclError:
            return ''

    def _glossary(self):
        """送給 Whisper／LLM 的詞彙：手動字典在前，已接受的自動新增字詞在後。"""
        return learning.merge_vocabulary(self.vocabulary, self.dictionary_auto)

    def _begin_ask(self, hotkey):
        """隨便問：先在背景執行緒讀取前景視窗與選取文字（最多約 0.9 秒），再回到 Tk 執行緒開始錄音。"""
        self.ask_pending = True
        self.ask_cancel = False
        self.status.set('正在讀取前景視窗與選取文字…')
        own = self._own_hwnd()
        editor_selection = self._editor_selection()
        # 放開「已設定快捷鍵」裡所有鍵（含兩側 Alt）：先 NOOP 再帶 MARKER 的 key-up，Ctrl+C 才不會變成 Ctrl+Alt+C；
        # hook 忽略 MARKER，狀態機仍認為鍵按住（與貼上路徑相同）。
        held_keys = frozenset(self.ptt.relevant_keys())
        ptt = self.ptt  # PushToTalk 自帶鎖；背景執行緒只呼叫它的 mark_synthetic_release

        def work():
            try:
                hwnd = window_context.foreground_window()
                if hwnd and hwnd == own:
                    # 前景是 Voice2Txt 自己：不注入 Ctrl+C，改用編輯區目前的選取文字。
                    info = {'app': '', 'title': '', 'selection': editor_selection, 'category': 'other',
                            'process_name': '', 'hwnd': hwnd, 'own': True}
                else:
                    # 先唯讀檢查剪貼簿格式：會略過擷取時完全不注入按鍵（不放開修飾鍵、不送 Ctrl+C）。
                    clip_ok, _saved, clip_other = window_context._read_clipboard()
                    skip = window_context.capture_skip_reason(clip_ok, clip_other)
                    if skip:
                        info = window_context.foreground_context(capture=False)
                        info['capture_skipped'] = skip
                    else:
                        if hotkey and held_keys:
                            released = release_held_modifiers(keys=held_keys)
                            # 實體上仍按著：告訴狀態機這些放開是合成的，不要被實體校正誤判成使用者放開。
                            ptt.mark_synthetic_release(released)
                        info = window_context.foreground_context(capture=True)
            except Exception:
                info = {'app': '', 'title': '', 'selection': '', 'category': 'other', 'process_name': '', 'hwnd': 0}
            self.events.put(('ask_context', (hotkey, info)))
        threading.Thread(target=work, daemon=True).start()

    def _session_context(self, mode, context):
        """依模式決定交給 LLM 的前景脈絡：隨便問用擷取結果；口述／翻譯只有視窗標題與 App（不含選取文字）。"""
        if mode == 'ask':
            if context is not None and not self.context_aware.get():
                return {'selection': context.get('selection') or ''}  # 關閉前景脈絡：只送選取文字，不送 app／標題
            return context
        if sys.platform != 'win32' or not self.context_aware.get() or self.translator is None:
            return None
        info = window_context.foreground_context(capture=False)
        if self._is_own_window(info.get('hwnd') or self.target_window) or not (info.get('app') or info.get('title')):
            return None
        return dict(info, selection='')

    def toggle(self, action_mode=None, context=None):
        """action_mode：快捷鍵啟動的模式（None＝按鈕／系統匣，依模式選單）；context：隨便問已擷取的前景脈絡。"""
        if self.recording:
            self.stop()
            return
        if self.engine is None or self.draining or self.loading or self.ask_pending:
            return
        mode = action_mode or next(k for k, v in MODES.items() if v == self.mode.get())
        if mode == 'ask' and context is None:
            self._begin_ask(hotkey=action_mode is not None)
            return
        foreground = 0
        if sys.platform == 'win32':
            foreground = self._user32().GetForegroundWindow() or 0
        self.target_window = (context or {}).get('hwnd') or foreground
        self.session_mode = mode
        self.session_paste = self.hotkey_paste.get() if action_mode is not None else self.paste.get()
        self.session_vocab = self._glossary()
        self.session_translator = self.translator
        self.session_language = DICTATION_LANGUAGES[self.dictation_language.get()]
        self.session_context = self._session_context(mode, context)
        self.session_error = None
        self.session_outputs = []
        self.chunker = Chunker(seconds=8, silence_seconds=0.5)
        self.recording = True
        def callback(indata, frames, timing, status):
            if status:
                self.events.put(('warning', f'音訊裝置：{status}'))
            try:
                self.audio.put_nowait(indata[:, 0].copy())
            except queue.Full:
                self.events.put(('overflow', '處理速度不足，錄音已停止；請改用較小模型。'))
        sounds.play('start', self.sounds_on.get())
        try:
            self.stream = sd.InputStream(samplerate=RATE, channels=1, dtype='float32',
                                         blocksize=1600, device=self.devices.get(self.mic.get()), callback=callback)
            self.stream.start()
        except Exception as error:
            self.recording = False
            if self.stream:
                self.stream.close()
                self.stream = None
            sounds.play('error', self.sounds_on.get())
            self.status.set(f'無法開啟麥克風：{error}')
            return
        if self.mute_others_on.get():
            try:
                self.mute_handle = audiofocus.mute_others(os.getpid())
            except Exception:
                self.mute_handle = None
        if action_mode is None:
            self.ptt.set_recording(True)  # 非快捷鍵開始：之後任何已設定組合的 tap 都能停止
        self.mode_box.configure(state='disabled')
        self.mic_box.configure(state='disabled')
        self.load_button.configure(state='disabled')
        self.start_button.configure(text='■ 停止錄音')
        self.status.set('錄音中…請保持此 App 開啟。')
        self.indicator.show('● 錄音中 · ' + INDICATOR_MODES.get(self.session_mode, self.session_mode))

    def _restore_audio(self):
        """還原被「靜音其他音訊」靜音的工作階段；可重複呼叫，失敗不丟例外（atexit 另有保險）。"""
        handle, self.mute_handle = self.mute_handle, None
        if handle is not None:
            try:
                audiofocus.restore(handle)
            except Exception:
                pass

    def _enqueue(self, audio):
        if self.pending_chunks:
            self.pending_chunks.append(audio)
            return
        try:
            self.jobs.put_nowait((audio, self.session_mode, self.session_vocab))
        except queue.Full:
            # 保留目前段落；停止後由 _poll 持續排入，避免靜默遺失。
            self.pending_chunks.append(audio)
            self.events.put(('overflow', '辨識速度跟不上錄音，已停止並保留待處理段落。'))

    def stop(self):
        if not self.recording:
            return
        self.recording = False
        self._restore_audio()
        sounds.play('stop', self.sounds_on.get())
        self.ptt.reset()  # 其他方式停止時，快捷鍵狀態機也回到閒置
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self._collect_audio()
        for chunk in self.chunker.flush():
            self._enqueue(chunk)
        self.draining = True
        self.start_button.configure(state='disabled', text='處理尾段…')
        self.status.set('正在完成剩餘音訊…')
        self.indicator.set_text('整理中…')

    def _collect_audio(self):
        while not self.audio.empty():
            for chunk in self.chunker.feed(self.audio.get_nowait()):
                self._enqueue(chunk)

    def _decode(self):
        while True:
            audio, mode, vocabulary = self.jobs.get()
            try:
                started = time.monotonic()
                context = self.session_context if accepts_context(self.session_translator) else None
                result = decode_segment(self.engine, audio, mode, vocabulary, self.session_translator,
                                        context=context, ask_language=self.session_language)
                if result.error:
                    self.events.put(('translation_error', (result.source, result.error, len(audio) / RATE)))
                else:
                    self.events.put(('result', (result.text, mode, len(audio) / RATE,
                                               time.monotonic() - started, result.source,
                                               result.backend, result.warning)))
            except Exception as error:
                self.events.put(('error', str(error)))
            finally:
                self.jobs.task_done()

    def _poll(self):
        if self.closed:
            return
        if self.recording:
            self._collect_audio()
        while self.pending_chunks and not self.jobs.full():
            self.jobs.put_nowait((self.pending_chunks.pop(0), self.session_mode, self.session_vocab))
        while not self.events.empty() and not self.closed:
            kind, value = self.events.get_nowait()
            if kind == 'hotkey':
                self._hotkey_event(*value)
            elif kind == 'hotkey_capture':
                self._capture_event(*value)
            elif kind == 'tray':
                self._tray_event(value)
            elif kind == 'ask_context':
                hotkey, info = value
                self.ask_pending = False
                if self.ask_cancel:
                    self.ask_cancel = False
                    self.ptt.reset()
                    self.status.set('已取消。')
                else:
                    self.toggle('ask' if hotkey else None, context=info)
                    skipped = info.get('capture_skipped') if isinstance(info, dict) else ''
                    if skipped and self.recording:
                        self.status.set(window_context.SKIP_MESSAGES.get(skipped, '這次未擷取選取文字。'))
                    if not self.recording and hotkey:
                        self.ptt.reset()
            elif kind == 'loaded':
                self.loading = False
                self.engine, self.translator, warnings = value
                self.load_button.configure(state='normal')
                self.start_button.configure(state='normal')
                chain = f'Whisper 轉錄 → {self.translator.name} → Whisper 結果' if self.translator else '僅 Whisper'
                self.status.set(f'{self.engine.size} / {self.engine.device} 已就緒；{chain}。'
                                + ''.join(' ' + w for w in warnings))
            elif kind == 'result':
                text, mode, seconds, elapsed, source, backend, warning = value
                if text:
                    self.text.insert('end', text + '\n')
                    self.text.see('end')
                    self.editor_outputs.append(text)
                    self.session_outputs.append(text)
                    self.store.add(mode, text, seconds, source=source)
                    if source:
                        self._show_source(source)
                    self._history()
                    # 隨便問沒有 LLM 時只是原始提問轉錄，不貼回別的視窗。
                    if mode == 'ask' and backend == 'Whisper':
                        self.session_error = '沒有可用的 LLM，顯示原始轉錄'
                    elif self.session_paste:
                        self.deferred_pastes.append((text, self.target_window))
                via = f'，整理：{backend}' if backend else ''
                note = f'（備援啟用：{warning}）' if warning else ''
                self.status.set(f'{"錄音中" if self.recording else "處理中"} · 最近 {seconds:.1f} 秒音訊，'
                                f'耗時 {elapsed:.1f} 秒{via}{note}')
            elif kind == 'translation_error':
                # 所有翻譯備援都失敗：不中斷錄音，保留中文原文。
                source, error, seconds = value
                self.session_error = '部分段落翻譯失敗，中文原文已保留於歷史紀錄：' + error
                if source:
                    self._show_source(source)
                    self.store.add('zh', source, seconds)
                    self._history()
                self.status.set(self.session_error)
            elif kind == 'overflow':
                self.stop()
                sounds.play('error', self.sounds_on.get())
                self.session_error = value
                self.status.set(value)
            elif kind == 'load_error':
                self.loading = False
                self.load_button.configure(state='normal')
                self.start_button.configure(state='normal' if self.engine else 'disabled')
                self.status.set('模型載入失敗：' + value)
            elif kind in ('error', 'warning'):
                self.status.set(value)
                if kind == 'error':
                    self.stop()
                    sounds.play('error', self.sounds_on.get())
                    self.session_error = '部分音訊辨識失敗：' + value
                    messagebox.showerror('辨識失敗', value)
        if self.closed:
            return
        self._flush_pastes()
        if self.draining and self.jobs.unfinished_tasks == 0 and not self.pending_chunks:
            self.draining = False
            self.indicator.hide()
            self.start_button.configure(state='normal', text='● 開始錄音')
            self.mode_box.configure(state='readonly')
            self.mic_box.configure(state='readonly')
            self.load_button.configure(state='normal')
            self.editor_snapshot = self.text.get('1.0', 'end-1c')
            self._refresh_insights()
            self.status.set(self.session_error or '已完成。內容已儲存於本機歷史紀錄。')
        self._poll_id = self.root.after(50, self._poll)

    def _build_insights(self, page):
        self.insight_vars = {key: tk.StringVar(value='—') for key, _ in INSIGHT_LABELS}
        grid = ttk.Frame(page)
        grid.pack(fill='x')
        for index, (key, title) in enumerate(INSIGHT_LABELS):
            cell = ttk.Frame(grid, padding=(0, 0, 32, 14))
            cell.grid(row=index // 4, column=index % 4, sticky='w')
            ttk.Label(cell, textvariable=self.insight_vars[key], font=('Segoe UI', 20, 'bold')).pack(anchor='w')
            ttk.Label(cell, text=title).pack(anchor='w')
        self.insight_modes = tk.StringVar()
        ttk.Label(page, textvariable=self.insight_modes, wraplength=860).pack(anchor='w')
        ttk.Label(page, text='近 26 週每天的口述字數（不含「隨便問」）；節省時間以每分鐘打字 40 字估算。',
                  wraplength=860).pack(anchor='w', pady=(8, 6))
        width, height = HEAT_WEEKS * HEAT_STEP + 4, 7 * HEAT_STEP + 4
        self.heatmap = tk.Canvas(page, width=width, height=height, highlightthickness=0)
        self.heatmap.pack(anchor='w')
        self.heat_hover = tk.StringVar(value=' ')
        ttk.Label(page, textvariable=self.heat_hover).pack(anchor='w', pady=(4, 0))
        legend = ttk.Frame(page)
        legend.pack(anchor='w', pady=(6, 0))
        ttk.Label(legend, text='較少').pack(side='left', padx=(0, 6))
        self.heat_legend = tk.Canvas(legend, width=5 * HEAT_STEP, height=HEAT_STEP, highlightthickness=0)
        self.heat_legend.pack(side='left')
        ttk.Label(legend, text='較多').pack(side='left', padx=(6, 0))

    def _heat_colors(self):
        return HEAT_COLORS['dark' if self.palette is theme.DARK else 'light']

    def _draw_heatmap(self):
        colors = self._heat_colors()
        self.heatmap.delete('all')
        self.heat_legend.delete('all')
        for level, color in enumerate(colors):
            self.heat_legend.create_rectangle(level * HEAT_STEP + 1, 1, level * HEAT_STEP + 1 + HEAT_CELL, 1 + HEAT_CELL,
                                              fill=color, outline='', tags=('legend',))
        for column, row, day, words, level in self.insight_cells:
            x, y = column * HEAT_STEP + 2, row * HEAT_STEP + 2
            item = self.heatmap.create_rectangle(x, y, x + HEAT_CELL, y + HEAT_CELL, fill=colors[level], outline='',
                                                 tags=('cell',))
            label = f'{day} · {words} 字'
            self.heatmap.tag_bind(item, '<Enter>', lambda event, text=label: self.heat_hover.set(text))
            self.heatmap.tag_bind(item, '<Leave>', lambda event: self.heat_hover.set(' '))

    def _refresh_insights(self):
        rows = [row for row in self.store.rows_for_stats() if row[1] != 'ask']
        today = date.today()
        stats = insights.compute(rows, today)
        self.insight_stats = stats
        v = self.insight_vars
        v['words'].set(f"{stats['total_words']:,}")
        v['saved'].set(format_duration(stats['time_saved_seconds']))
        v['wpm'].set(f"{stats['dictation_wpm']:.0f} 字/分")
        v['time'].set(format_duration(stats['total_seconds']))
        v['active'].set(f"{stats['active_days']} 天")
        v['streak'].set(f"{stats['current_streak']} 天")
        v['longest'].set(f"{stats['longest_streak']} 天")
        parts = [f'{MODES.get(mode, mode)} {words:,} 字' for mode, words in sorted(stats['by_mode'].items())]
        self.insight_modes.set('依模式：' + ('　'.join(parts) if parts else '尚無資料'))
        self.insight_cells = insights.heatmap_cells(stats['by_day'], today, HEAT_WEEKS)
        self._draw_heatmap()

    def _apply_theme(self):
        self.palette = theme.resolve(self.appearance.get())
        theme.apply(self.style, self.root, self.palette, self.themed_widgets)
        p = self.palette
        self.style.configure('Toolbutton', background=p['panel'], foreground=p['fg'], padding=(10, 4))
        self.style.map('Toolbutton', background=[('selected', p['accent']), ('active', p['select_bg'])],
                       foreground=[('selected', p['bg'])])
        if self.indicator is not None:
            self.indicator.apply_palette(p)
        self._draw_heatmap()

    def _appearance_changed(self):
        self._apply_theme()
        self.status.set(f'外觀：{self.appearance.get()}。按「儲存設定與字典」可保存。')

    def _prune_history(self):
        try:
            removed = self.store.prune(RETENTION_CHOICES.get(self.retention.get()))
        except Exception:
            removed = 0
        if removed:
            self._history()
            self._refresh_insights()
        return removed

    def _persist_keys(self, **values):
        """只更新 settings.json 的指定鍵（接受／忽略候選字詞時用，不連帶儲存畫面上其他尚未儲存的設定）。"""
        path = DATA / 'settings.json'
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            data = {}
        data.update(values)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

    def _known_terms(self):
        return (learning._split_terms(self.dictionary.get('1.0', 'end')) + self.dictionary_auto
                + self.dictionary_ignored + [c['term'] for c in self.candidates])

    def _learn_check(self):
        """離開編輯區或儲存設定時：拿模型原始輸出和編輯後的文字比對，找出使用者改過的新字詞。"""
        text = self.text.get('1.0', 'end-1c')
        if text == self.editor_snapshot or not self.editor_outputs:
            return
        self.editor_snapshot = text
        found = learning.candidates(self.editor_outputs, text, self._known_terms())
        self.editor_outputs = [text]  # 之後只比對往後的修改
        if found:
            self.candidates.extend(found)
            self._render_candidates()
            self.status.set(f'偵測到 {len(found)} 個可加入字典的候選字詞，請到「字典與設定」確認。')

    def _render_candidates(self):
        self.candidate_list.delete(0, 'end')
        for item in self.candidates:
            replaced = f'（原為「{item["replaced"]}」）' if item.get('replaced') else ''
            self.candidate_list.insert('end', f'{item["term"]}{replaced}　×{item["count"]}')

    def _render_auto_label(self):
        self.auto_label.set('已自動加入：' + ('、'.join(self.dictionary_auto) if self.dictionary_auto else '（無）'))

    def _candidate_action(self, accept):
        selected = self.candidate_list.curselection()
        if not selected:
            self.status.set('請先在候選清單選一個字詞。')
            return
        item = self.candidates.pop(selected[0])
        if accept:
            self.dictionary_auto.append(item['term'])
        else:
            self.dictionary_ignored.append(item['term'])
        self._persist_keys(dictionary_auto=self.dictionary_auto, dictionary_ignored=self.dictionary_ignored)
        self._render_candidates()
        self._render_auto_label()
        self.status.set(f'已加入字典：{item["term"]}。' if accept else f'已忽略：{item["term"]}。')

    def _clear_auto(self):
        self.dictionary_auto = []
        self._persist_keys(dictionary_auto=[])
        self._render_auto_label()
        self.status.set('已清空自動加入的字詞。')

    def _show_window(self):
        self.root.deiconify()
        self.root.lift()

    def _tray_event(self, action):
        if action == 'show':
            self._show_window()
        elif action == 'toggle':
            if self.recording:
                self.stop()
            elif self.engine is None:
                self.status.set('請先載入模型再開始錄音。')
                self._show_window()
            else:
                self.toggle()
        elif action == 'quit':
            self.close()
            if not self.closed:
                self._show_window()  # 仍在錄音／處理：把狀態訊息顯示出來

    def on_window_close(self):
        """視窗關閉鈕：有系統匣且設定允許時只隱藏視窗，否則等同結束。"""
        if self.close_to_tray.get() and self.tray is not None and self.tray.added:
            self.root.withdraw()
            self.status.set('Voice2Txt 仍在系統匣執行；右鍵系統匣圖示可結束。')
            return
        self.close()

    def _apply_hotkeys(self):
        """把 self.hotkeys 套用到狀態機並更新畫面上的說明文字。"""
        combos = {}
        for action, names in self.hotkeys.items():
            combos[action] = [parse_combo(n) for n in names[:2]]
            labels = [format_combo(c) for c in combos[action]]
            self.hotkey_labels[action].set('  ｜  '.join(labels) if labels else '（未設定）')
            if action in self.hotkey_buttons:
                self.hotkey_buttons[action]['add'].configure(state='normal' if 0 < len(labels) < 2 else 'disabled')
                self.hotkey_buttons[action]['clear'].configure(state='normal' if labels else 'disabled')
        self.ptt.set_combos(combos)
        parts = [f'{HOTKEY_TITLES[a]}：{self.hotkey_labels[a].get()}' for a in HOTKEY_TITLES]
        self.hotkey_warning = ''
        if sys.platform == 'win32':
            all_combos = [c for items in combos.values() for c in items]
            if conflicting_combos(running_process_names(), all_combos):
                self.hotkey_warning = TYPELESS_WARNING
                self.status.set(TYPELESS_WARNING)
        self.hotkey_help.set('快捷鍵（按住說話、放開停止；快按一下持續錄音、再快按一下停止）　' + '　'.join(parts)
                             + '。停頓約半秒時處理一段；連續語音最長 8 秒，停止後處理尾段。'
                             + ('　⚠ ' + self.hotkey_warning if self.hotkey_warning else ''))

    def _hotkey_event(self, command, action):
        if command == 'start':
            if self.recording or self.ask_pending:
                return
            if action == 'ask':
                if self.engine is None or self.draining or self.loading:
                    self.ptt.reset()
                    if self.engine is None:
                        self.status.set('請先載入模型再使用快捷鍵。')
                    return
                self._begin_ask(hotkey=True)
                return
            mode = DICTATION_LANGUAGES[self.dictation_language.get()] if action == 'dictate' else 'translate'
            self.toggle(mode)
            if not self.recording:
                self.ptt.reset()
                if self.engine is None:
                    self.status.set('請先載入模型再使用快捷鍵。')
        elif self.recording:
            self.stop()
        elif self.ask_pending:
            self.ask_cancel = True  # 還在讀取前景脈絡時就放開了：取消這次隨便問

    def _begin_capture(self, action, replace):
        if self.hook is None or self.hook.thread is None:
            self.status.set('全域快捷鍵未啟用，無法設定。')
            return
        if self.capture_target is not None:
            self._end_capture('已取消設定。')
            return
        self.capture_target = (action, replace)
        for buttons in self.hotkey_buttons.values():
            for button in buttons.values():
                button.configure(state='disabled')
        self.hotkey_buttons[action]['set' if replace else 'add'].configure(state='normal', text='取消')
        self.hotkey_labels[action].set('請按下組合鍵…（全部放開後確認）')
        self.hook.begin_capture()

    def _end_capture(self, message):
        if self.hook is not None:
            self.hook.cancel_capture()
        self.capture_target = None
        for buttons in self.hotkey_buttons.values():
            buttons['set'].configure(text='設定')
            buttons['add'].configure(text='再加一個')
            for button in buttons.values():
                button.configure(state='normal')
        self._apply_hotkeys()
        self.status.set(message + (' ' + self.hotkey_warning if self.hotkey_warning else ''))

    def _capture_event(self, kind, combo):
        if self.capture_target is None:
            return
        action, replace = self.capture_target
        if kind == 'live':
            self.hotkey_labels[action].set(format_combo(combo) + ' …')
            return
        name = combo_name(combo)
        names = [] if replace else list(self.hotkeys[action])
        if name not in names:
            names.append(name)
        self.hotkeys[action] = names[:2]
        self._end_capture(f'已設定 {HOTKEY_TITLES[action]} 快捷鍵：{format_combo(combo)}。按「儲存設定與字典」可保存。')

    def _clear_hotkey(self, action):
        self.hotkeys[action] = []
        self._apply_hotkeys()
        self.status.set(f'已清除 {HOTKEY_TITLES[action]} 快捷鍵。按「儲存設定與字典」可保存。')

    def _flush_pastes(self):
        """快捷鍵（任一組合的鍵）還按住時不貼，等全部放開；放開後依序貼出。"""
        if paste_decision(len(self.deferred_pastes), self.ptt.held_keys()) != 'now':
            return
        pending, self.deferred_pastes = self.deferred_pastes, []
        for text, target in merge_pastes(pending):
            self._paste(text, target)

    def _paste(self, text, target=None):
        if sys.platform != 'win32':
            return
        user32 = self._user32()
        target = self.target_window if target is None else target
        # 僅在原視窗仍有焦點時貼上，避免將內容貼進別的視窗。
        if user32.GetForegroundWindow() != target:
            self.status.set('原視窗焦點已變更，略過自動貼上；文字仍保留於 App。')
            return
        if self._is_own_window(target):
            return  # 前景就是 Voice2Txt：文字已在編輯區，不重複貼上
        # 先存下剪貼簿文字（只處理 CF_UNICODETEXT）；連續貼多段時只存第一次，最後一起還原。
        if self.clip_saved is None:
            count = user32.CountClipboardFormats()
            saved, other = window_context._read_text()
            self.clip_saved = (saved, other, count)
        if not window_context._write_text(text):
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update_idletasks()
        self.clip_seq = user32.GetClipboardSequenceNumber()
        # 還按著的修飾鍵（Alt/Shift/Ctrl）會讓 Ctrl+V 變成 Ctrl+Alt+V 等：先用帶 MARKER 的 key-up 放開，之後不恢復。
        self.last_paste_released = release_held_modifiers(keys=self.ptt.relevant_keys())
        self.ptt.mark_synthetic_release(self.last_paste_released)
        if self.last_paste_released:
            time.sleep(0.03)  # 讓目標視窗先處理完 key-up，再送 Ctrl+V
        user32.keybd_event(0x11, 0, 0, 0)
        user32.keybd_event(0x56, 0, 0, 0)
        user32.keybd_event(0x56, 0, 2, 0)
        user32.keybd_event(0x11, 0, 2, 0)
        if self.clip_after is not None:
            self.root.after_cancel(self.clip_after)
        # 不能在這裡 sleep：目標程式讀剪貼簿時可能要我們的執行緒回應；稍後用 after 還原。
        self.clip_after = self.root.after(PASTE_RESTORE_MS, self._restore_clipboard)

    def _restore_clipboard(self):
        """把貼上前的剪貼簿文字放回去；剪貼簿在貼上後被別人改過、或原本是非文字資料時略過並寫在狀態列。"""
        self.clip_after = None
        saved, self.clip_saved = self.clip_saved, None
        if saved is None or sys.platform != 'win32':
            return
        text, other, count = saved
        user32 = self._user32()
        note, result = '', 'restored'
        if user32.GetClipboardSequenceNumber() != self.clip_seq:
            note, result = '剪貼簿在貼上後被其他程式改變，未還原。', 'skipped'
        elif text is None and (other or count > 0):
            note, result = '剪貼簿原本是非文字內容（圖片、檔案等），無法還原，已保留貼上的文字。', 'skipped'
        elif not window_context._write_text(text):  # text 為 None 且原本是空的：清空剪貼簿
            note, result = '無法還原剪貼簿。', 'skipped'
        elif other:
            note = '剪貼簿文字已還原；其他格式（圖片等）無法還原。'
        self.last_clipboard_restore = result
        if note:
            self.status.set(note)

    def _history(self):
        allowed = HISTORY_FILTERS[self.history_filter.get()]
        self.rows = [row for row in self.store.history() if allowed is None or row[3] in allowed]
        self.history.delete(0, 'end')
        for _, created, text, mode, seconds in self.rows:
            self.history.insert('end', f'{created}  {MODES.get(mode, mode)}  {text[:80]}')

    def show_history(self, event=None):
        selected = self.history.curselection()
        if selected:
            self.text.delete('1.0', 'end')
            self.text.insert('1.0', self.rows[selected[0]][2])
            self.editor_outputs = [self.rows[selected[0]][2]]
            self.editor_snapshot = self.rows[selected[0]][2]
            self._show_source(self.store.source(self.rows[selected[0]][0]), replace=True)

    def _show_source(self, source, replace=False):
        self.source_text.configure(state='normal')
        if replace:
            self.source_text.delete('1.0', 'end')
        if source:
            self.source_text.insert('end', source + '\n')
            self.source_text.see('end')
            self.source_panel.pack(fill='x', before=self.text, pady=(10, 0))
        elif replace:
            self.source_panel.pack_forget()
        self.source_text.configure(state='disabled')

    def clear_text(self):
        self.text.delete('1.0', 'end')
        self.editor_outputs = []
        self.editor_snapshot = ''
        self._show_source('', replace=True)

    def clear_history(self):
        if messagebox.askyesno('刪除歷史紀錄', '確定刪除所有本機歷史紀錄？'):
            self.store.clear()
            self._history()
            self._refresh_insights()

    def copy(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.text.get('1.0', 'end').strip())
        self.status.set('已複製。')

    def export(self):
        path = filedialog.asksaveasfilename(defaultextension='.txt', filetypes=[('純文字', '*.txt')])
        if path:
            Path(path).write_text(self.text.get('1.0', 'end').strip(), encoding='utf-8-sig')
            self.status.set('已匯出。')

    def close(self):
        if self.recording or self.draining:
            self.stop()
            self.status.set('請等剩餘辨識完成後再關閉，避免遺失尾段。')
            return
        self.closed = True
        self._restore_audio()
        if self.clip_after is not None:
            self.root.after_cancel(self.clip_after)
            self._restore_clipboard()
        if self._poll_id is not None:
            try:
                self.root.after_cancel(self._poll_id)  # 否則 destroy 後 Tcl 會印出 invalid command name
            except tk.TclError:
                pass
            self._poll_id = None
        if self.hook is not None:
            self.hook.stop()
        if self.tray is not None:
            self.tray.close()
        if self.indicator is not None:
            self.indicator.destroy()
        self.store.close()
        self.root.destroy()


def main(minimized=False):
    if not claim_single_instance():
        return 0  # 已有執行個體：已廣播要求它顯示視窗
    root = tk.Tk()
    app = App(root, enable_tray=True)
    if minimized:
        if app.tray is not None and app.tray.added:
            root.withdraw()
        else:
            root.iconify()  # 沒有系統匣就不能藏起來，改最小化到工作列
    root.mainloop()
    return 0


if __name__ == '__main__':
    main()
