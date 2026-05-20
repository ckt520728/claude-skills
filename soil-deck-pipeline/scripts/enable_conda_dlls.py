# -*- coding: utf-8 -*-
"""
enable_conda_dlls.py — 治本版修復 Anaconda PIL/ssl 的 `DLL load failed`。

根因：Pillow 的 _imaging 等 C 擴充依賴 <anaconda>\Library\bin 裡的原生 DLL
（libjpeg / zlib / libpng / libssl ...），但該目錄只有在 `conda activate` 時才會
掛到 PATH。直接跑 python（未啟用環境）就找不到 DLL。

用法：在 `import PIL` / `import pptx` 之前最前面加一行：
    import enable_conda_dlls          # 自動偵測並掛上 conda 的 DLL 目錄
    from PIL import Image             # OK
    from pptx import Presentation     # OK

也可手動指定：
    import enable_conda_dlls
    enable_conda_dlls.enable(r"D:\miniconda3")

行為：找得到就 add_dll_directory 並回傳 True；找不到任何 conda 安裝則回傳 False
（不 raise，讓呼叫端可自行決定要不要退回 stub / System.Drawing 路線）。
僅在 Windows + Python 3.8+ 生效，其他平台直接 no-op 回傳 True。
"""
import os
import sys
from pathlib import Path

# Python 3.8+ 才有 os.add_dll_directory；其他平台不需要這招
_CAN = hasattr(os, "add_dll_directory") and sys.platform == "win32"

# conda 安裝的子目錄（activate 時會加進 PATH 的順序）
_SUBDIRS = [
    "",                       # <env>
    r"Library\mingw-w64\bin",
    r"Library\usr\bin",
    r"Library\bin",
    "Scripts",
    "bin",
]

def _candidate_roots():
    """猜可能的 conda 根目錄，優先用環境變數，再掃常見路徑。"""
    seen = []
    def add(p):
        if p:
            p = Path(p)
            if p not in seen:
                seen.append(p)
    # 1) 正在用的 python 就在某個 conda env 底下（最可靠）
    add(Path(sys.prefix))
    add(Path(sys.exec_prefix))
    # 2) 環境變數
    add(os.environ.get("CONDA_PREFIX"))
    add(os.environ.get("CONDA_PYTHON_EXE") and Path(os.environ["CONDA_PYTHON_EXE"]).parent)
    # 3) 常見安裝位置
    home = Path(os.path.expanduser("~"))
    for name in ("anaconda3", "miniconda3", "Anaconda3", "Miniconda3"):
        add(home / name)
        add(Path(r"C:\ProgramData") / name)
        add(Path(r"C:") / name)
    return seen

def enable(root=None, verbose=False):
    """掛上 conda 的 DLL 目錄。回傳 True 表示成功（或非 Windows no-op）。

    同時做兩件事（缺一不可）：
      (1) os.add_dll_directory()  — 給 Python 3.8+ 的安全 DLL 搜尋
      (2) 注入 os.environ['PATH'] — 給 OS 傳統 loader 解析「DLL 的相依 DLL」
          （Pillow 的 _imaging 會傳遞相依 libjpeg/zlib...，光靠 (1) 不夠，
           實測必須同時 prepend PATH 才會成功）
    """
    if not _CAN:
        return True  # 非 Windows / 舊 Python：不需要
    roots = [Path(root)] if root else _candidate_roots()
    for r in roots:
        # 認得出是 conda 根目錄的特徵：底下要有 Library\bin
        if not (r / "Library" / "bin").is_dir():
            continue
        dirs = []
        for sub in _SUBDIRS:
            d = (r / sub) if sub else r
            if d.is_dir():
                dirs.append(str(d))
        if not dirs:
            continue
        for d in dirs:
            try:
                os.add_dll_directory(d)            # (1)
            except (OSError, FileNotFoundError):
                pass
        os.environ["PATH"] = os.pathsep.join(dirs) + os.pathsep + os.environ.get("PATH", "")  # (2)
        if verbose:
            for d in dirs:
                print(f"[enable_conda_dlls] + {d}")
        return True
    if verbose:
        print("[enable_conda_dlls] 找不到 conda 安裝（含 Library\\bin），未掛任何目錄。")
    return False

# import 即自動執行（最常見用法）
_OK = enable()

if __name__ == "__main__":
    ok = enable(verbose=True)
    print("enabled:", ok)
    try:
        from PIL import Image  # noqa
        print("PIL import: OK")
    except Exception as e:  # noqa
        print("PIL import 仍失敗:", e)
