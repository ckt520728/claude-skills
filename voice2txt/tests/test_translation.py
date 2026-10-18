import json
import sys
import tempfile
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from voice2txt import keystore
from voice2txt.core import Store
from voice2txt.translation import (CloudTranslator, LocalTranslator, TranslatorChain, build_translator,
                                   decode_segment, instructions, pick_ollama_model)


class FakeEngine:
    """Whisper 替身：zh/en 回傳原始轉錄，translate 回傳直接翻譯。"""

    def __init__(self, raw='嗯，明天上午九點到醫院。', direct='Hospital at nine tomorrow.', fail_translate=False):
        self.raw, self.direct, self.fail_translate, self.modes = raw, direct, fail_translate, []

    def transcribe(self, audio, mode, vocabulary):
        self.modes.append(mode)
        if mode == 'translate':
            if self.fail_translate:
                raise RuntimeError('Whisper 失敗')
            return self.direct
        return self.raw


class FailingLLM:
    def refine(self, text, mode, vocabulary=''):
        raise TimeoutError('測試逾時')


class TranslationTests(unittest.TestCase):
    def test_cloud_alias_is_rejected(self):
        with self.assertRaises(ValueError):
            LocalTranslator('model:cloud')

    def test_remote_alias_metadata_is_rejected_before_model_load(self):
        translator = LocalTranslator('local-alias')
        with patch.object(translator, '_post', return_value={'remote_host': 'https://example.test'}) as post:
            with self.assertRaises(ValueError):
                translator.prepare()
            self.assertEqual(post.call_count, 1)

    def test_truncated_output_is_not_accepted_as_complete(self):
        translator = LocalTranslator('local-alias')
        with patch.object(translator, '_post', side_effect=[{}, {'done': True},
                          {'message': {'content': 'partial'}, 'done_reason': 'length'}]):
            translator.prepare()
            with self.assertRaises(RuntimeError):
                translator.refine('完整原句', 'translate')

    def test_whisper_transcribes_first_then_llm_refines_every_mode(self):
        class Echo:
            def refine(self, text, mode, vocabulary=''):
                self.call = (text, mode, vocabulary)
                return f'[{mode}] cleaned'

        for mode, whisper_mode in (('zh', 'zh'), ('en', 'en'), ('translate', 'zh')):
            engine, llm = FakeEngine(), Echo()
            result = decode_segment(engine, np.ones(16000), mode, 'Voice2Txt', translator=llm)
            self.assertEqual(engine.modes, [whisper_mode])
            self.assertEqual(llm.call, (engine.raw, mode, 'Voice2Txt'))
            self.assertEqual((result.text, result.source), (f'[{mode}] cleaned', engine.raw))

    def test_refined_chinese_is_forced_to_traditional(self):
        class Simplified:
            def refine(self, text, mode, vocabulary=''):
                return '明天上午九点到医院。'

        from opencc import OpenCC
        engine = FakeEngine()
        engine.converter = OpenCC('s2twp')
        result = decode_segment(engine, np.ones(16000), 'zh', translator=Simplified())
        self.assertEqual(result.text, '明天上午九點到醫院。')

    def test_refine_failure_keeps_raw_whisper_transcript(self):
        engine = FakeEngine()
        result = decode_segment(engine, np.ones(16000), 'zh', translator=FailingLLM())
        self.assertEqual((result.text, result.source, result.backend), (engine.raw, engine.raw, 'Whisper'))
        self.assertIn('逾時', result.warning)
        self.assertEqual(engine.modes, ['zh'])

    def test_translate_failure_falls_back_to_whisper_translation(self):
        engine = FakeEngine()
        result = decode_segment(engine, np.ones(16000), 'translate', translator=FailingLLM())
        self.assertEqual(engine.modes, ['zh', 'translate'])
        self.assertEqual((result.text, result.source, result.backend), (engine.direct, engine.raw, 'Whisper'))
        self.assertIn('逾時', result.warning)
        self.assertEqual(result.error, '')

    def test_every_fallback_failing_reports_error_with_source(self):
        result = decode_segment(FakeEngine(fail_translate=True), np.ones(16000), 'translate', translator=FailingLLM())
        self.assertEqual((result.text, result.source), ('', '嗯，明天上午九點到醫院。'))
        self.assertIn('逾時', result.error)
        self.assertIn('Whisper 失敗', result.error)

    def test_instructions_describe_cleanup_task_and_glossary(self):
        zh = instructions('zh', '林口長庚')
        self.assertIn('filler', zh)
        self.assertIn('self-corrections', zh)
        self.assertIn('Traditional Chinese', zh)
        self.assertIn('林口長庚', zh)
        self.assertIn('translate it into natural English', instructions('translate'))
        self.assertNotIn('Glossary', instructions('en'))

    def test_chain_uses_backup_and_pauses_failed_translator(self):
        now = [0.0]

        class Fake:
            def __init__(self, name, fail):
                self.name, self.fail, self.calls = name, fail, 0

            def refine(self, text, mode, vocabulary=''):
                self.calls += 1
                if self.fail:
                    raise OSError('connection refused')
                return self.name + ':' + text

        ollama, openai, gemini = Fake('Ollama', True), Fake('OpenAI', True), Fake('Gemini', False)
        chain = TranslatorChain([ollama, openai, gemini], cooldown=60, clock=lambda: now[0])
        self.assertEqual(chain.refine('甲', 'zh'), 'Gemini:甲')
        self.assertEqual(chain.last_backend, 'Gemini')
        self.assertEqual(len(chain.errors), 2)
        chain.refine('乙', 'zh')
        self.assertEqual((ollama.calls, openai.calls), (1, 1))  # 冷卻期間不再等待
        ollama.fail = False
        now[0] = 61
        self.assertEqual(chain.refine('丙', 'zh'), 'Ollama:丙')
        self.assertEqual(chain.errors, [])

    def test_chain_order_is_ollama_openai_gemini(self):
        with patch.object(LocalTranslator, 'prepare', side_effect=OSError('refused')):
            chain, warnings = build_translator('gemma4:latest', [('Gemini', '', 'g-key', ''),
                                                                 ('OpenAI', '', 'o-key', '')])
        self.assertEqual(chain.name, 'Ollama gemma4:latest → OpenAI gpt-6-luna (high) → Gemini gemini-3.8-flash (low)')
        self.assertIn('refused', warnings[0])
        self.assertIn('Ollama gemma4:latest', chain.paused)

    def test_cloud_backup_requires_a_key(self):
        with self.assertRaises(ValueError):
            CloudTranslator('Gemini', '', '  ')

    def test_gemini_request_and_response_shape(self):
        translator = CloudTranslator('Gemini', '', 'secret')
        request = translator.request('今天開會', 'translate')
        body = json.loads(request.data)
        self.assertTrue(request.full_url.endswith('/models/gemini-3.8-flash:generateContent'))
        self.assertEqual(request.get_header('X-goog-api-key'), 'secret')
        self.assertEqual(body['generationConfig']['thinkingConfig']['thinkingLevel'], 'low')
        self.assertEqual(body['contents'][0]['parts'][0]['text'], '今天開會')
        self.assertIn('translate', body['systemInstruction']['parts'][0]['text'])
        reply = {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [
            {'text': 'plan', 'thought': True}, {'text': 'Meeting today.'}]}}]}
        self.assertEqual(translator.parse(reply), 'Meeting today.')
        with self.assertRaises(RuntimeError):
            translator.parse({'candidates': [{'finishReason': 'MAX_TOKENS', 'content': {'parts': [{'text': 'Meet'}]}}]})

    def test_openai_request_and_response_shape(self):
        translator = CloudTranslator('OpenAI', '', 'secret')
        request = translator.request('今天開會', 'zh')
        body = json.loads(request.data)
        self.assertEqual(request.full_url, 'https://api.openai.com/v1/responses')
        self.assertEqual(request.get_header('Authorization'), 'Bearer secret')
        self.assertEqual((body['model'], body['reasoning']['effort']), ('gpt-6-luna', 'high'))
        self.assertIn('Traditional Chinese', body['instructions'])
        reply = {'status': 'completed', 'output': [{'type': 'reasoning', 'summary': []}, {'type': 'message',
                 'content': [{'type': 'output_text', 'text': '今天開會。'}]}]}
        self.assertEqual(translator.parse(reply), '今天開會。')
        with self.assertRaises(RuntimeError):
            translator.parse({'status': 'incomplete', 'output': []})

    def test_preferred_ollama_model_is_picked_when_installed(self):
        self.assertEqual(pick_ollama_model(['llama3:8b', 'gemma4:latest']), 'gemma4:latest')
        self.assertEqual(pick_ollama_model(['llama3:8b']), 'llama3:8b')
        self.assertEqual(pick_ollama_model([]), '')

    @unittest.skipUnless(sys.platform == 'win32', 'DPAPI 僅限 Windows')
    def test_api_key_round_trips_through_dpapi(self):
        token = keystore.protect('sk-測試')
        self.assertNotIn('sk-', token)
        self.assertEqual(keystore.unprotect(token), 'sk-測試')
        self.assertEqual(keystore.unprotect('損壞'), '')

    def test_source_transcript_survives_history_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'history.sqlite3'
            store = Store(path)
            store.add('translate', 'Tomorrow at nine.', 2, source='明天九點。')
            row_id = store.history()[0][0]
            store.close()
            store = Store(path)
            self.assertEqual(store.source(row_id), '明天九點。')
            store.close()

    def test_legacy_history_is_retained_when_adding_source_column(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'history.sqlite3'
            connection = sqlite3.connect(str(path))
            connection.execute('CREATE TABLE history (id INTEGER PRIMARY KEY, created TEXT, mode TEXT, text TEXT, seconds REAL)')
            connection.execute("INSERT INTO history VALUES (1,'2026-10-18','zh','既有紀錄',1)")
            connection.commit()
            connection.close()
            store = Store(path)
            self.assertEqual(store.history()[0][2], '既有紀錄')
            self.assertEqual(store.source(1), '')
            store.close()
