import argparse
import json
from pathlib import Path
import time


def verify(output, audio=None, mode='en', model='small', device='cpu', llm_model=None, clouds=(), vocabulary=''):
    report = {'stage': 'entry'}
    def checkpoint(stage):
        report['stage'] = stage
        Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    checkpoint('before_tk_import')
    try:
        import tkinter as tk
        checkpoint('before_sounddevice_import')
        import sounddevice as sd
        checkpoint('before_core_import')
        from voice2txt.core import WhisperEngine
        checkpoint('before_faster_whisper_import')
        from faster_whisper.audio import decode_audio
        checkpoint('before_tk_init')
        root = tk.Tk()
        root.withdraw()
        import os
        os.environ['LOCALAPPDATA'] = str(Path(output).resolve().parent / 'app-smoke')
        from voice2txt.desktop import App
        app = App(root)
        root.update()
        report['tk'] = root.tk.call('info', 'patchlevel')
        report['desktop_ui'] = bool(app.text.winfo_exists() and app.history.winfo_exists())
        app.close()
        report['input_devices'] = sum(d['max_input_channels'] > 0 for d in sd.query_devices())
        if audio:
            checkpoint('before_model_init')
            engine = WhisperEngine(model, device=device)
            report['model'] = model
            report['device'] = device
            translator = None
            if llm_model or clouds:
                import os
                from voice2txt.translation import build_translator
                checkpoint('before_llm_prepare')
                chain = []
                for item in clouds:
                    provider, _, effort = item.partition(':')
                    key = os.environ.get(provider.upper() + '_API_KEY', '')
                    if key:
                        chain.append((provider, '', key, effort))
                translator, warnings = build_translator(llm_model or '', chain)
                report['llm_model'] = llm_model
                report['translator_chain'] = 'Whisper 轉錄 → ' + translator.name + ' → Whisper 結果'
                report['prepare_warnings'] = warnings
            checkpoint('before_audio_decode')
            samples = decode_audio(audio, sampling_rate=16000)
            started = time.monotonic()
            from voice2txt.translation import decode_segment
            result = decode_segment(engine, samples, mode, vocabulary, translator=translator)
            report['text'] = result.text
            report['source'] = result.source
            report['backend'] = result.backend
            report['fallback_warning'] = result.warning
            if result.error:
                raise RuntimeError(result.error)
            report['inference_seconds'] = time.monotonic() - started
            report['mode'] = mode
        report['ok'] = True
        report['stage'] = 'completed'
    except Exception as error:
        report['ok'] = False
        report['error'] = repr(error)
    Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if report['ok'] else 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Voice2Txt 本機語音輸入')
    parser.add_argument('--self-test', metavar='JSON_PATH')
    parser.add_argument('--audio')
    parser.add_argument('--mode', choices=['zh', 'en', 'translate'], default='en')
    parser.add_argument('--model', choices=['base', 'small', 'medium', 'large-v3'], default='small')
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
    parser.add_argument('--llm-model')
    parser.add_argument('--cloud', action='append', default=[], metavar='PROVIDER:EFFORT',
                        choices=[f'{p}:{e}' for p in ('OpenAI', 'Gemini') for e in ('low', 'medium', 'high')],
                        help='可重複，例如 --cloud OpenAI:high --cloud Gemini:low；API key 讀取 OPENAI_API_KEY／GEMINI_API_KEY')
    parser.add_argument('--vocabulary', default='')
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(verify(args.self_test, args.audio, args.mode, args.model, args.device, args.llm_model,
                                args.cloud, args.vocabulary))
    from voice2txt.desktop import main
    main()
