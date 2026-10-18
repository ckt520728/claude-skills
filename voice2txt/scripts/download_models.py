"""下載完整推論所需設定；large-v3 必須包含 128 mel 前處理設定。"""
import argparse
import os
from pathlib import Path

root = Path(__file__).resolve().parent.parent
os.environ.setdefault('HF_HOME', str(root / 'tools' / 'hf-cache'))
from huggingface_hub import snapshot_download

parser = argparse.ArgumentParser()
parser.add_argument('models', nargs='+', choices=['base', 'small', 'medium', 'large-v3'])
args = parser.parse_args()
for size in args.models:
    print(snapshot_download('Systran/faster-whisper-' + size,
                            local_dir=str(root / 'models' / ('whisper-' + size)),
                            allow_patterns=['model.bin', '*.json', '*.txt', 'README.md', 'LICENSE*']))
