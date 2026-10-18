import ctypes
import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import numpy as np
import sounddevice as sd

from voice2txt.core import Chunker, MODES, RATE, Store, WhisperEngine, preferred_settings
from voice2txt import keystore
from voice2txt.translation import CLOUD, EFFORTS, build_translator, decode_segment, ollama_models, pick_ollama_model

DATA = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Voice2Txt'
LLM_REFINE, WHISPER_ONLY = 'Whisper + LLM 整理', '僅 Whisper'
LEGACY_BACKENDS = {'本機 Ollama': LLM_REFINE, 'Whisper': WHISPER_ONLY}


class App:
    def __init__(self, root):
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
        self.mic = tk.StringVar()
        self.vocabulary = ''
        self._ui()
        self._load_settings()
        self._backend_changed()
        self._history()
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        threading.Thread(target=self._decode, daemon=True).start()
        if sys.platform == 'win32':
            threading.Thread(target=self._hotkey, daemon=True).start()
        self.root.after(50, self._poll)

    def _ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', font=('Microsoft JhengHei UI', 11))
        style.configure('TButton', padding=9)
        shell = ttk.Frame(self.root, padding=24)
        shell.pack(fill='both', expand=True)
        ttk.Label(shell, text='Voice2Txt', font=('Segoe UI', 30, 'bold')).pack(anchor='w')
        ttk.Label(shell, text='讓想法流動。Whisper 轉錄 + LLM 整理 · 繁體中文 / English · 無訂閱').pack(anchor='w', pady=(0, 18))
        tabs = ttk.Notebook(shell)
        tabs.pack(fill='both', expand=True)
        live, history = [ttk.Frame(tabs, padding=16) for _ in range(2)]
        settings_page = ttk.Frame(tabs)
        for frame, title in zip((live, history, settings_page), ('即時語音', '歷史紀錄', '字典與設定')):
            tabs.add(frame, text=title)
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
        self.source_panel = ttk.Frame(live)
        ttk.Label(self.source_panel, text='Whisper 原始轉錄（LLM 整理前，供核對）').pack(anchor='w')
        self.source_text = tk.Text(self.source_panel, height=3, wrap='word', state='disabled', font=('Microsoft JhengHei UI', 11))
        self.source_text.pack(fill='x')
        row = ttk.Frame(live)
        row.pack(fill='x')
        ttk.Button(row, text='匯出 TXT', command=self.export).pack(side='left')
        ttk.Button(row, text='清空畫面', command=self.clear_text).pack(side='left', padx=8)
        ttk.Checkbutton(row, text='完成後貼入原視窗', variable=self.paste).pack(side='right')
        ttk.Label(live, text='Alt + Shift + Space：開始 / 停止。停頓約半秒時處理一段；連續語音最長 8 秒，停止後處理尾段。').pack(anchor='w', pady=(10, 0))
        ttk.Label(shell, textvariable=self.status, wraplength=900).pack(anchor='w', pady=(14, 0))
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
        ttk.Label(settings, text='LLM 順序：本機 Ollama → OpenAI → Gemini → 只用 Whisper 結果。偵測到本機 Ollama 時預設啟用；'
                  '啟用時 Whisper 固定用 CPU，建議 small。', wraplength=660).pack(anchor='w')
        ollama_row = ttk.Frame(settings)
        ollama_row.pack(anchor='w', pady=8)
        ttk.Label(ollama_row, text='① 本機 Ollama 模型', width=18).pack(side='left')
        ttk.Entry(ollama_row, textvariable=self.llm_model, width=24).pack(side='left', padx=6)
        for number, provider in zip('②③', CLOUD):
            values = self.cloud[provider]
            cloud_row = ttk.Frame(settings)
            cloud_row.pack(anchor='w', pady=4)
            ttk.Checkbutton(cloud_row, text=f'{number} {provider} 備援', variable=values['enabled'], width=16).pack(side='left')
            ttk.Entry(cloud_row, textvariable=values['model'], width=18).pack(side='left', padx=6)
            ttk.Label(cloud_row, text='推理強度').pack(side='left', padx=(8, 0))
            ttk.Combobox(cloud_row, textvariable=values['effort'], values=list(EFFORTS), state='readonly', width=7).pack(side='left', padx=6)
            ttk.Label(cloud_row, text='API key').pack(side='left', padx=(8, 0))
            ttk.Entry(cloud_row, textvariable=values['key'], show='•', width=22).pack(side='left', padx=6)
        ttk.Label(settings, text='雲端備援只在前一個 LLM 失敗時使用，只送出 Whisper 轉錄文字（不含錄音）到 OpenAI／Google，依用量計費。'
                  'API key 以 Windows DPAPI 加密保存；留空時改讀環境變數 OPENAI_API_KEY／GEMINI_API_KEY，都沒有就略過。',
                  wraplength=660).pack(anchor='w', pady=(4, 8))
        self.load_button = ttk.Button(settings, text='載入 / 下載模型', command=self.load_model)
        self.load_button.pack(anchor='w')
        ttk.Label(settings, text='base / small 較省資源；medium / large-v3 建議搭配 NVIDIA GPU。').pack(anchor='w', pady=10)
        self.devices = {f'{i} · {d["name"]}': i for i, d in enumerate(sd.query_devices()) if d['max_input_channels'] > 0}
        ttk.Label(settings, text='麥克風').pack(anchor='w')
        self.mic_box = ttk.Combobox(settings, textvariable=self.mic, values=['系統預設'] + list(self.devices), state='readonly', width=65)
        self.mic_box.pack(anchor='w', pady=8)
        self.mic.set('系統預設')
        ttk.Label(settings, text='個人字典：以逗號分隔專有名詞，協助辨識；不是強制文字替換。').pack(anchor='w', pady=(14, 6))
        self.dictionary = tk.Text(settings, height=5, wrap='word', font=('Microsoft JhengHei UI', 12))
        self.dictionary.pack(fill='x')
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
            self.dictionary.insert('1.0', settings.get('dictionary', ''))
            self.vocabulary = settings.get('dictionary', '')
        except (OSError, ValueError):
            pass
        if not getattr(self, 'backend_chosen', False):
            # 尚未自行選擇引擎：偵測到本機 Ollama 就預設使用。
            names = ollama_models()
            if names:
                self.translation_backend.set(LLM_REFINE)
                self.llm_model.set(pick_ollama_model(names, self.llm_model.get()))
                self.model.set('small')

    def save_settings(self):
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
            'cloud': cloud, 'dictionary': self.vocabulary}, ensure_ascii=False), encoding='utf-8')
        self.backend_chosen = True
        self.status.set(message)

    def _cloud_settings(self):
        """回傳已啟用且有 API key 的雲端備援，依固定順序 OpenAI → Gemini。"""
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

    def toggle(self):
        if self.recording:
            self.stop()
            return
        if self.engine is None or self.draining or self.loading:
            return
        if sys.platform == 'win32':
            ctypes.windll.user32.GetForegroundWindow.restype = ctypes.c_void_p
        self.target_window = ctypes.windll.user32.GetForegroundWindow() if sys.platform == 'win32' else 0
        self.session_mode = next(k for k, v in MODES.items() if v == self.mode.get())
        self.session_paste = self.paste.get()
        self.session_vocab = self.vocabulary
        self.session_translator = self.translator
        self.session_error = None
        self.chunker = Chunker(seconds=8, silence_seconds=0.5)
        self.recording = True
        def callback(indata, frames, timing, status):
            if status:
                self.events.put(('warning', f'音訊裝置：{status}'))
            try:
                self.audio.put_nowait(indata[:, 0].copy())
            except queue.Full:
                self.events.put(('overflow', '處理速度不足，錄音已停止；請改用較小模型。'))
        try:
            self.stream = sd.InputStream(samplerate=RATE, channels=1, dtype='float32',
                                         blocksize=1600, device=self.devices.get(self.mic.get()), callback=callback)
            self.stream.start()
        except Exception as error:
            self.recording = False
            if self.stream:
                self.stream.close()
                self.stream = None
            self.status.set(f'無法開啟麥克風：{error}')
            return
        self.mode_box.configure(state='disabled')
        self.mic_box.configure(state='disabled')
        self.load_button.configure(state='disabled')
        self.start_button.configure(text='■ 停止錄音')
        self.status.set('錄音中…請保持此 App 開啟。')

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

    def _collect_audio(self):
        while not self.audio.empty():
            for chunk in self.chunker.feed(self.audio.get_nowait()):
                self._enqueue(chunk)

    def _decode(self):
        while True:
            audio, mode, vocabulary = self.jobs.get()
            try:
                started = time.monotonic()
                result = decode_segment(self.engine, audio, mode, vocabulary, self.session_translator)
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
        while not self.events.empty():
            kind, value = self.events.get_nowait()
            if kind == 'hotkey':
                self.toggle()
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
                    self.store.add(mode, text, seconds, source=source)
                    if source:
                        self._show_source(source)
                    self._history()
                    if self.session_paste:
                        self._paste(text)
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
                    self.session_error = '部分音訊辨識失敗：' + value
                    messagebox.showerror('辨識失敗', value)
        if self.draining and self.jobs.unfinished_tasks == 0 and not self.pending_chunks:
            self.draining = False
            self.start_button.configure(state='normal', text='● 開始錄音')
            self.mode_box.configure(state='readonly')
            self.mic_box.configure(state='readonly')
            self.load_button.configure(state='normal')
            self.status.set(self.session_error or '已完成。內容已儲存於本機歷史紀錄。')
        self.root.after(50, self._poll)

    def _hotkey(self):
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        self.hotkey_thread = ctypes.windll.kernel32.GetCurrentThreadId()
        if not user32.RegisterHotKey(None, 1, 0x4000 | 0x1 | 0x4, 0x20):
            self.events.put(('warning', '快捷鍵已被其他程式使用，請使用錄音按鈕。'))
            return
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == 0x0312:
                self.events.put(('hotkey', None))
        user32.UnregisterHotKey(None, 1)

    def _paste(self, text):
        if sys.platform != 'win32':
            return
        user32 = ctypes.windll.user32
        user32.GetForegroundWindow.restype = ctypes.c_void_p
        # 僅在原視窗仍有焦點時貼上，避免將內容貼進別的視窗。
        if user32.GetForegroundWindow() != self.target_window:
            self.status.set('原視窗焦點已變更，略過自動貼上；文字仍保留於 App。')
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update_idletasks()
        user32.keybd_event(0x11, 0, 0, 0)
        user32.keybd_event(0x56, 0, 0, 0)
        user32.keybd_event(0x56, 0, 2, 0)
        user32.keybd_event(0x11, 0, 2, 0)

    def _history(self):
        self.rows = self.store.history()
        self.history.delete(0, 'end')
        for _, created, text, mode, seconds in self.rows:
            self.history.insert('end', f'{created}  {MODES.get(mode, mode)}  {text[:80]}')

    def show_history(self, event=None):
        selected = self.history.curselection()
        if selected:
            self.text.delete('1.0', 'end')
            self.text.insert('1.0', self.rows[selected[0]][2])
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
        self._show_source('', replace=True)

    def clear_history(self):
        if messagebox.askyesno('刪除歷史紀錄', '確定刪除所有本機歷史紀錄？'):
            self.store.clear()
            self._history()

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
        if hasattr(self, 'hotkey_thread'):
            ctypes.windll.user32.PostThreadMessageW(self.hotkey_thread, 0x0012, 0, 0)
        self.store.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
