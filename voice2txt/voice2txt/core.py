import sqlite3
import sys
import os
import ctypes
from pathlib import Path

import numpy as np
from opencc import OpenCC

MODES = {'zh': '繁體中文', 'en': 'English', 'translate': '中文 → English'}
RATE = 16000


def configure_cuda():
    """只調整目前 App 的 DLL 搜尋路徑，不修改系統設定。"""
    handles = []
    if sys.platform == 'win32':
        root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
        directories = list((root / 'gpu' / 'nvidia').glob('*/bin'))
        for directory in directories:
            handles.append(os.add_dll_directory(str(directory)))
        if directories:
            os.environ['PATH'] = os.pathsep.join(str(p) for p in directories) + os.pathsep + os.environ['PATH']
        try:
            handles.extend(ctypes.WinDLL(name) for name in ('cublas64_12.dll', 'cudnn64_9.dll'))
        except OSError as error:
            raise RuntimeError('無法載入 NVIDIA GPU 函式庫，請改選 cpu 或安裝 GPU 套件。') from error
    return handles


def bundled_model(size):
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
    path = root / 'models' / ('whisper-' + size)
    return path if (path / 'model.bin').exists() else size


def preferred_settings():
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
    if (root / 'gpu' / 'nvidia').exists():
        try:
            import ctranslate2
            if ctranslate2.get_cuda_device_count() > 0:
                for size in ('medium', 'large-v3'):
                    if isinstance(bundled_model(size), Path):
                        return size, 'cuda'
        except (ImportError, RuntimeError, OSError):
            pass
    return 'small', 'cpu'


class Chunker:
    """可選擇依停頓分段；設長度上限並完整保留尾段。"""

    def __init__(self, rate=RATE, seconds=5, silence_seconds=None, min_seconds=1):
        self.size = int(rate * seconds)
        if self.size < 1:
            raise ValueError('分段長度必須大於零')
        self.frame_size = max(1, int(rate * 0.02))
        self.silence_size = int(rate * silence_seconds) if silence_seconds is not None else None
        self.minimum = int(rate * min_seconds)
        if self.silence_size is not None and (self.silence_size < 1 or not 0 < self.minimum <= self.size):
            raise ValueError('停頓與最短分段長度無效')
        self.pending = np.empty(0, dtype=np.float32)

    def feed(self, block):
        self.pending = np.concatenate((self.pending, np.asarray(block).reshape(-1)))
        chunks = []
        while len(self.pending):
            cut = self._pause_boundary() if self.silence_size is not None else None
            if cut is None:
                if len(self.pending) < self.size:
                    break
                cut = self.size
            chunks.append(self.pending[:cut].copy())
            self.pending = self.pending[cut:]
        return chunks

    def _pause_boundary(self):
        count = min(len(self.pending), self.size) // self.frame_size
        if len(self.pending) < self.minimum or not count:
            return None
        frames = self.pending[:count * self.frame_size].reshape(count, self.frame_size)
        quiet = np.mean(frames ** 2, axis=1) < 0.006 ** 2
        run = 0
        for index, is_quiet in enumerate(quiet):
            run = run + self.frame_size if is_quiet else 0
            boundary = (index + 1) * self.frame_size
            if run >= self.silence_size and boundary >= self.minimum:
                return boundary
        return None

    def flush(self):
        chunks = [self.pending.copy()] if len(self.pending) else []
        self.pending = np.empty(0, dtype=np.float32)
        return chunks


class WhisperEngine:
    def __init__(self, size='base', model=None, model_dir=None, device='cpu'):
        if device not in ('cpu', 'cuda'):
            raise ValueError('運算裝置必須是 cpu 或 cuda')
        self.device = device
        self.size = size
        self.cuda_handles = configure_cuda() if model is None and device == 'cuda' else []
        if model is None:
            from faster_whisper import WhisperModel
            model = WhisperModel(str(bundled_model(size)), device=device,
                                 compute_type='float16' if device == 'cuda' else 'int8',
                                 download_root=str(model_dir) if model_dir else None)
        self.model = model
        self.converter = OpenCC('s2twp')

    def transcribe(self, audio, mode, vocabulary=''):
        if mode not in MODES:
            raise ValueError('不支援的模式')
        audio = np.asarray(audio, dtype=np.float32)
        if len(audio) < RATE // 5 or np.sqrt(np.mean(audio ** 2)) < 0.002:
            return ''
        segments, _ = self.model.transcribe(
            audio, language='en' if mode == 'en' else 'zh',
            task='translate' if mode == 'translate' else 'transcribe',
            beam_size=5, vad_filter=True, condition_on_previous_text=False,
            initial_prompt=vocabulary[:1000] or None,
        )
        text = ''.join(segment.text for segment in segments).strip()
        return self.converter.convert(text) if mode == 'zh' else text


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path))
        self.db.execute('CREATE TABLE IF NOT EXISTS history '
                        '(id INTEGER PRIMARY KEY, created TEXT DEFAULT (datetime(\'now\',\'localtime\')),'
                        'mode TEXT, text TEXT, seconds REAL)')
        if 'source' not in {row[1] for row in self.db.execute('PRAGMA table_info(history)')}:
            self.db.execute("ALTER TABLE history ADD COLUMN source TEXT NOT NULL DEFAULT ''")
        self.db.commit()

    def add(self, mode, text, seconds, source=''):
        self.db.execute('INSERT INTO history(mode,text,seconds,source) VALUES (?,?,?,?)',
                        (mode, text, seconds, source))
        self.db.commit()

    def source(self, row_id):
        row = self.db.execute('SELECT source FROM history WHERE id=?', (row_id,)).fetchone()
        return row[0] if row else ''

    def history(self):
        return self.db.execute('SELECT id,created,text,mode,seconds FROM history '
                               'ORDER BY id DESC').fetchall()

    def clear(self):
        self.db.execute('DELETE FROM history')
        self.db.commit()

    def close(self):
        self.db.close()
