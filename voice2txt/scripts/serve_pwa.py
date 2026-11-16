"""Serve the independent PWA (sites/voice2txt-independent/dist) on this PC.

Usage: python scripts/serve_pwa.py [--port 8787] [--open]

Why this exists: http://127.0.0.1:8787/recording.html only works while a server is running;
earlier sessions started `python -m http.server` by hand during tests, so the URL failed later.
This server also sends Cache-Control: no-cache for HTML and the service worker, so a rebuilt
version is picked up on the next reload instead of an old cached page. Hashed JS/CSS/WASM
files can be cached because their names change with each build.

127.0.0.1 is only this PC. An iPhone/iPad cannot reach it; phones use the deployed site.
"""
import argparse
import functools
import http.server
import mimetypes
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / 'sites' / 'voice2txt-independent' / 'dist'
mimetypes.add_type('application/wasm', '.wasm')
mimetypes.add_type('text/javascript', '.mjs')
mimetypes.add_type('text/javascript', '.js')
mimetypes.add_type('application/manifest+json', '.webmanifest')
NO_CACHE = ('.html', '/sw.js', '.webmanifest', '/')


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        path = self.path.split('?', 1)[0]
        if path.endswith(NO_CACHE):
            self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def log_message(self, fmt, *args):  # keep the console quiet except for errors
        if args and str(args[1])[:1] in '45':
            super().log_message(fmt, *args)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--port', type=int, default=8787)
    parser.add_argument('--open', action='store_true', help='open the recording page in the default browser')
    args = parser.parse_args()
    if not (ROOT / 'recording.html').exists():
        sys.exit(f'找不到 {ROOT / "recording.html"}；請先在 sites/voice2txt-independent 執行 npm run build。')
    handler = functools.partial(Handler, directory=str(ROOT))
    try:
        server = http.server.ThreadingHTTPServer(('127.0.0.1', args.port), handler)
    except OSError:
        url = f'http://127.0.0.1:{args.port}/recording.html'
        print(f'連接埠 {args.port} 已被使用（可能已在執行）。直接開啟 {url}')
        if args.open:
            webbrowser.open(url)
        return
    url = f'http://127.0.0.1:{args.port}/recording.html'
    print(f'Voice2Txt 網頁版：{url}\n關閉此視窗即停止。')
    if args.open:
        threading.Timer(0.5, webbrowser.open, (url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
