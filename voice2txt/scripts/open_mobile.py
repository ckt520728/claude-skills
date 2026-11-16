"""啟動或重用手機服務，顯示目前的配對連結。"""
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / 'mobile-runtime'
RUNTIME.mkdir(exist_ok=True)
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def reachable(url, token):
    request = urllib.request.Request(url + '/api/status', headers={'Authorization': 'Bearer ' + token})
    try:
        with OPENER.open(request, timeout=5) as response:
            return response.status == 200
    except Exception:
        return False


def launch(args, name):
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    with (RUNTIME / (name + '-stdout.log')).open('ab') as out, (RUNTIME / (name + '-stderr.log')).open('ab') as err:
        process = subprocess.Popen(args, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                   env=env, creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
    (RUNTIME / (name + '.pid')).write_text(str(process.pid))
    return process


def main():
    pairing = RUNTIME / 'pairing.json'
    token = json.loads(pairing.read_text())['token'] if pairing.exists() else ''
    local = 'http://127.0.0.1:8765'
    if not token or not reachable(local, token):
        print('正在載入桌機 Whisper，請稍候…', flush=True)
        service = launch([sys.executable, 'run_mobile.py'], 'server')
        for _ in range(90):
            if pairing.exists():
                token = json.loads(pairing.read_text())['token']
                if reachable(local, token):
                    break
            if service.poll() is not None:
                raise RuntimeError('桌機服務啟動失敗，請查看 mobile-runtime/server-stderr.log。')
            time.sleep(1)
        else:
            raise RuntimeError('模型載入逾時，請查看 mobile-runtime/server-stderr.log。')
    log = RUNTIME / 'tunnel.log'
    matches = re.findall(r'https://[a-z0-9-]+\.trycloudflare\.com', log.read_text(encoding='utf-8') if log.exists() else '')
    public = matches[-1] if matches else ''
    if not public or not reachable(public, token):
        binary = ROOT / 'tools/mobile/cloudflared.exe'
        if not binary.exists():
            raise RuntimeError('缺少 tools/mobile/cloudflared.exe，請先取得官方 Cloudflare Tunnel 工具。')
        print('正在建立手機 HTTPS 連結…', flush=True)
        log.write_text('', encoding='utf-8')
        tunnel = launch([str(binary), 'tunnel', '--no-autoupdate', '--url', local,
                         '--protocol', 'http2', '--logfile', str(log)], 'tunnel')
        for _ in range(60):
            matches = re.findall(r'https://[a-z0-9-]+\.trycloudflare\.com', log.read_text(encoding='utf-8'))
            if matches and reachable(matches[-1], token):
                public = matches[-1]
                break
            if tunnel.poll() is not None:
                raise RuntimeError('HTTPS 連線失敗，請查看 mobile-runtime/tunnel-stderr.log。')
            time.sleep(1)
        else:
            raise RuntimeError('HTTPS 連線逾時，請稍後重試。')
    link = public + '/#key=' + token
    (RUNTIME / 'current-link.txt').write_text(link, encoding='utf-8')
    page = RUNTIME / '手機連結.html'
    page.write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                    '<title>Voice2Txt 手機連結</title><body style="font:18px system-ui;max-width:760px;margin:60px auto;padding:24px;line-height:1.8">'
                    '<h1>Voice2Txt 手機入口</h1><p>把下方完整連結複製到 iPhone／iPad 的 Safari，再點「分享 → 加入主畫面」。</p>'
                    '<p style="overflow-wrap:anywhere"><a href="' + html.escape(link, quote=True) + '">' + html.escape(link) + '</a></p>'
                    '<p>配對碼（加入主畫面後若要求重新配對，可貼上）：</p><code>' + html.escape(token) + '</code>'
                    '<p>此連結僅供你使用，請勿公開分享。桌機須開機，服務重啟後網址可能改變。</p></body></html>', encoding='utf-8')
    print(link, flush=True)
    webbrowser.open(page.as_uri())


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
