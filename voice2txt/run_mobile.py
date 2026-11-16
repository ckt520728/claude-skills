"""啟動手機網頁版；不讀取桌面雲端 API keys 或歷史紀錄。"""
import io
import json
import secrets
from dataclasses import asdict
from pathlib import Path

from faster_whisper.audio import decode_audio
from voice2txt.core import RATE, WhisperEngine
from voice2txt.mobile_server import MobileServer
from voice2txt.translation import build_translator, decode_segment, ollama_models, pick_ollama_model


def main():
    runtime = Path(__file__).resolve().parent / 'mobile-runtime'
    runtime.mkdir(exist_ok=True)
    pairing = runtime / 'pairing.json'
    token = json.loads(pairing.read_text(encoding='utf-8'))['token'] if pairing.exists() else secrets.token_urlsafe(32)
    pairing.write_text(json.dumps({'token': token}), encoding='utf-8')
    engine = WhisperEngine('small', device='cpu')
    local_model = pick_ollama_model(ollama_models())
    translator = build_translator(local_model)[0] if local_model else None

    def transcribe(data, mode, refine):
        try:
            audio = decode_audio(io.BytesIO(data), sampling_rate=RATE)
        except Exception as error:
            raise ValueError('無法讀取這段錄音，請改用 Safari 錄製或上傳音訊檔。') from error
        if not 0 < len(audio) <= RATE * 95:
            raise ValueError('每段請錄製 90 秒以內。')
        result = decode_segment(engine, audio, mode, translator=translator if refine else None)
        if result.error:
            raise RuntimeError(result.error)
        if refine and translator is None:
            result.warning = '桌機沒有可用的本機 LLM，本段使用 Whisper。'
        return asdict(result)

    server = MobileServer(('127.0.0.1', 8765), token, transcribe)
    (runtime / 'ready.json').write_text(json.dumps({'ready': True, 'port': 8765}), encoding='utf-8')
    print('Voice2Txt 手機網頁服務已啟動：http://127.0.0.1:8765', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
