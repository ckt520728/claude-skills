"""手機網頁橋接；只提供指定靜態檔，錄音在記憶體處理。"""
import hmac
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

WEB = Path(__file__).resolve().parent.parent / 'mobile'
ASSETS = {'/': ('index.html', 'text/html; charset=utf-8'),
          '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
          '/style.css': ('style.css', 'text/css; charset=utf-8'),
          '/manifest.webmanifest': ('manifest.webmanifest', 'application/manifest+json'),
          '/icon.png': ('icon.png', 'image/png')}
MAX_AUDIO = 15 * 1024 * 1024


class MobileServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, token, transcribe):
        self.token = token
        self.transcribe = transcribe
        self.inference_lock = threading.Lock()
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(30)

    def log_message(self, *args):
        pass  # 不記錄配對資料、錄音或轉錄內容。

    def respond(self, status, data, mime='application/json; charset=utf-8'):
        if not isinstance(data, bytes):
            data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Permissions-Policy', 'microphone=(self), camera=()')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(data)
        self.close_connection = True

    def authorized(self):
        supplied = self.headers.get('Authorization', '')
        return hmac.compare_digest(supplied.encode(), ('Bearer ' + self.server.token).encode())

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/status':
            if not self.authorized():
                return self.respond(401, {'error': '請用完整配對連結開啟，或輸入配對碼。'})
            return self.respond(200, {'ready': True, 'busy': self.server.inference_lock.locked(),
                                      'max_seconds': 90})
        if path not in ASSETS:
            return self.respond(404, {'error': '找不到頁面。'})
        name, mime = ASSETS[path]
        self.respond(200, (WEB / name).read_bytes(), mime)

    def do_POST(self):
        parsed = urlsplit(self.path)
        if parsed.path != '/api/transcribe':
            return self.respond(404, {'error': '找不到頁面。'})
        if not self.authorized():
            return self.respond(401, {'error': '配對碼無效，請重新配對。'})
        query = parse_qs(parsed.query)
        mode = query.get('mode', ['zh'])[0]
        if mode not in ('zh', 'en', 'translate'):
            return self.respond(400, {'error': '不支援的模式。'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            return self.respond(400, {'error': '錄音長度無效。'})
        if size > MAX_AUDIO:
            return self.respond(413, {'error': '錄音過大，請分段錄製。'})
        if size < 1 or self.headers.get('Transfer-Encoding'):
            return self.respond(400, {'error': '沒有收到完整錄音。'})
        if not self.server.inference_lock.acquire(blocking=False):
            return self.respond(429, {'error': '桌機正在處理另一段錄音，請稍後重試。'})
        try:
            audio = self.rfile.read(size)
            if len(audio) != size:
                return self.respond(400, {'error': '錄音傳送不完整。'})
            result = self.server.transcribe(audio, mode, query.get('refine', ['0'])[0] == '1')
            self.respond(200, result)
        except ValueError as error:
            self.respond(400, {'error': str(error)})
        except Exception:
            self.respond(500, {'error': '轉錄失敗，請確認音訊格式並稍後重試。'})
        finally:
            self.server.inference_lock.release()
