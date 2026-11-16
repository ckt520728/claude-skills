import unittest

from voice2txt.context import categorize
from voice2txt.translation import RULES, TASKS, DecodeResult, decode_segment, instructions


class Engine:
    def __init__(self, raw='幫我把這段改得更正式'):
        self.raw, self.modes = raw, []

    def transcribe(self, audio, mode, vocabulary):
        self.modes.append(mode)
        return self.raw


class Chain:
    name = 'stub'
    last_backend = 'stub'
    errors = []

    def __init__(self, fail=False):
        self.fail, self.calls = fail, []

    def refine(self, text, mode, vocabulary='', context=None):
        self.calls.append((text, mode, context))
        if self.fail:
            raise TimeoutError('逾時')
        return '回答：' + text


class OldStyleLLM:
    """舊介面替身：只接受三個參數。"""

    def refine(self, text, mode, vocabulary=''):
        return 'ok:' + text


class ContextTests(unittest.TestCase):
    def test_categorize_table(self):
        cases = [('chrome.exe', '', 'browser'), ('msedge', 'x', 'browser'), ('firefox', '', 'browser'),
                 ('OUTLOOK.EXE', '', 'email'), ('thunderbird', '', 'email'),
                 ('Code', '', 'code'), ('devenv', '', 'code'), ('WindowsTerminal', '', 'code'),
                 ('powershell', '', 'code'), ('cmd', '', 'code'), ('pycharm64', '', 'code'),
                 ('Teams', '', 'chat'), ('slack', '', 'chat'), ('LINE', '', 'chat'), ('Discord', '', 'chat'),
                 ('WINWORD', '', 'document'), ('notepad', '', 'document'), ('Notion', '', 'document'),
                 ('foo', '', 'other'), ('', '', 'other')]
        for process, title, expected in cases:
            self.assertEqual(categorize(process, title), expected, process)

    def test_categorize_mail_titles(self):
        self.assertEqual(categorize('chrome', 'Inbox - Gmail - mail'), 'email')
        self.assertEqual(categorize('', '收件匣 - 郵件'), 'email')
        self.assertEqual(categorize('chrome', 'Wikipedia'), 'browser')

    def test_instructions_without_context_is_unchanged(self):
        for mode in ('zh', 'en', 'translate'):
            self.assertEqual(instructions(mode, 'Foo'), instructions(mode, 'Foo', None))
            self.assertEqual(instructions(mode), f'{RULES}\n{TASKS[mode]}')
            self.assertEqual(instructions(mode, context={}), instructions(mode))

    def test_context_block_rendering(self):
        text = instructions('zh', context={'app': 'chrome', 'title': 'Gmail', 'category': 'email',
                                           'selection': 'hello world'})
        self.assertIn('Output destination: chrome (email) — window: Gmail', text)
        self.assertIn('Selected text in the target field:\nhello world', text)
        self.assertIn('keep paragraphs', text)
        self.assertIn('keep plain text without markdown',
                      instructions('en', context={'app': 'Code', 'title': 't', 'category': 'code'}))
        self.assertIn('keep it short', instructions('translate', context={'app': 'Line', 'title': 't',
                                                                           'category': 'chat'}))
        self.assertNotIn('Selected text', instructions('zh', context={'app': 'a', 'title': 't',
                                                                        'category': 'other'}))

    def test_selection_truncated_to_2000_chars(self):
        text = instructions('ask', context={'app': 'a', 'title': 't', 'category': 'other',
                                            'selection': 'x' * 2500})
        self.assertIn('x' * 2000, text)
        self.assertNotIn('x' * 2001, text)

    def test_ask_task_present_and_used(self):
        self.assertIn('ask', TASKS)
        text = instructions('ask')
        self.assertTrue(text.startswith(RULES))
        self.assertIn(TASKS['ask'], text)
        self.assertIn('ready to paste', TASKS['ask'])
        self.assertNotIn('keep paragraphs', instructions('ask', context={'app': 'a', 'title': 't',
                                                                         'category': 'email'}))

    def test_decode_segment_ask_passes_context_to_chain(self):
        engine, chain = Engine(), Chain()
        context = {'app': 'winword', 'title': 'Doc', 'category': 'document', 'selection': '原文'}
        result = decode_segment(engine, b'', 'ask', '', chain, context=context)
        self.assertEqual(engine.modes, ['zh'])
        self.assertEqual(chain.calls, [('幫我把這段改得更正式', 'ask', context)])
        self.assertEqual(result.text, '回答：幫我把這段改得更正式')
        self.assertEqual(result.source, '幫我把這段改得更正式')
        self.assertEqual(result.error, '')

    def test_decode_segment_ask_language_en(self):
        engine = Engine('summarise this')
        decode_segment(engine, b'', 'ask', '', Chain(), ask_language='en')
        self.assertEqual(engine.modes, ['en'])

    def test_decode_segment_ask_failing_chain_returns_transcript_with_warning(self):
        engine = Engine()
        result = decode_segment(engine, b'', 'ask', '', Chain(fail=True))
        self.assertEqual(engine.modes, ['zh'])  # 沒有 Whisper translate 備援
        self.assertEqual(result.text, engine.raw)
        self.assertEqual(result.source, engine.raw)
        self.assertEqual(result.error, '')
        self.assertEqual(result.backend, 'Whisper')
        self.assertEqual(result.warning, '沒有可用的 LLM，顯示原始轉錄')

    def test_ask_task_says_cleanup_rules_do_not_limit_the_answer(self):
        self.assertIn('The clean-up rules above apply only to understanding the spoken transcript; '
                      'they do not limit the answer.', TASKS['ask'])
        self.assertIn('they do not limit the answer.', instructions('ask'))

    def test_capture_is_skipped_for_non_text_clipboard_or_open_failure(self):
        from voice2txt.context import capture_skip_reason
        self.assertEqual(capture_skip_reason(True, False), '')
        self.assertEqual(capture_skip_reason(True, True), 'non_text')
        self.assertEqual(capture_skip_reason(False, False), 'busy')
        self.assertEqual(capture_skip_reason(False, True), 'busy')

    def test_capture_selection_returns_empty_without_injecting_for_non_text_clipboard(self):
        from unittest import mock
        from voice2txt import context, hotkeys

        class User32:
            def GetForegroundWindow(self):
                return 5

            def GetClipboardSequenceNumber(self):
                return 1

        sent = []
        with mock.patch.object(context, '_api', lambda: (None, None, User32(), None)), \
             mock.patch.object(context, '_read_clipboard', lambda: (True, None, True)), \
             mock.patch.object(hotkeys, 'send_key', lambda *a: sent.append(a)):
            self.assertEqual(context.capture_selection(5), ('', False))
        self.assertEqual(sent, [])
        self.assertEqual(context.last_skip_reason, 'non_text')
        with mock.patch.object(context, '_api', lambda: (None, None, User32(), None)), \
             mock.patch.object(context, '_read_clipboard', lambda: (False, None, False)), \
             mock.patch.object(hotkeys, 'send_key', lambda *a: sent.append(a)):
            self.assertEqual(context.capture_selection(5), ('', False))
        self.assertEqual((sent, context.last_skip_reason), ([], 'busy'))

    def test_capture_selection_timeout_returns_false_with_late_reason(self):
        from unittest import mock
        from voice2txt import context, hotkeys

        class User32:
            def GetForegroundWindow(self):
                return 5

            def GetClipboardSequenceNumber(self):
                return 7

        started = []
        with mock.patch.object(context, '_api', lambda: (None, None, User32(), None)),              mock.patch.object(context, '_read_clipboard', lambda: (True, 'prior', False)),              mock.patch.object(context, '_late_watch', lambda *a, **k: started.append(a)),              mock.patch.object(hotkeys, 'send_key', lambda *a: None):
            self.assertEqual(context.capture_selection(5, timeout=0.05), ('', False))
        self.assertEqual(context.last_skip_reason, 'late')
        import time
        time.sleep(0.05)
        self.assertEqual(len(started), 1)
        self.assertIn('目標未回應或無選取', context.SKIP_MESSAGES['late'])
        self.assertEqual(started[0][5], 0)  # 第 6 個參數是 target_pid（此替身 _api 取不到 -> 0）

    def _watch(self, schedule, saved='prior', target_pid=7, owner=7):
        """schedule: [(秒, 序號)]，依時間回傳最近一個已到時間的序號（模擬剪貼簿序號）。"""
        import threading
        import time
        from voice2txt import context
        start, writes = time.monotonic(), []

        def get_sequence():
            elapsed, value = time.monotonic() - start, 10
            for at, seq in schedule:
                if elapsed >= at:
                    value = seq
            return value

        context.last_late_restore = False
        context._late_watch(threading.Event(), get_sequence, lambda t: writes.append(t) or True, saved, 10,
                            target_pid=target_pid, owner_pid=lambda: owner, grace=1.0, settle=0.15, merge=0.04, poll=0.002)
        return writes, context.last_late_restore

    def test_late_watch_restores_on_single_advance(self):
        self.assertEqual(self._watch([(0.1, 15)]), (['prior'], True))  # 一次寫入連跳多個序號仍算一次
        self.assertEqual(self._watch([(0.1, 11)], saved=None), ([None], True))
        self.assertEqual(self._watch([(0.1, 11), (0.11, 12), (0.12, 13)]), (['prior'], True))

    def test_late_watch_restores_only_when_owner_pid_matches_target(self):
        self.assertEqual(self._watch([(0.1, 11)], target_pid=7, owner=7), (['prior'], True))
        self.assertEqual(self._watch([(0.1, 11)], target_pid=7, owner=8), ([], False))  # 使用者在別的程式複製
        self.assertEqual(self._watch([(0.1, 11)], target_pid=7, owner=0), ([], False))  # 取不到擁有者
        self.assertEqual(self._watch([(0.1, 11)], target_pid=0, owner=0), ([], False))  # 取不到目標 pid

    def test_late_watch_does_nothing_on_double_advance(self):
        self.assertEqual(self._watch([(0.1, 11), (0.2, 12)]), ([], False))

    def test_late_watch_does_nothing_without_advance(self):
        self.assertEqual(self._watch([]), ([], False))

    def test_late_watch_cancel_and_exceptions(self):
        import threading
        from voice2txt import context
        cancel = threading.Event()
        cancel.set()
        writes = []
        context._late_watch(cancel, lambda: 11, writes.append, 'x', 10, 7, lambda: 7, grace=0.2)
        self.assertEqual(writes, [])

        def boom():
            raise OSError('x')
        context._late_watch(threading.Event(), boom, writes.append, 'x', 10, 7, lambda: 7, grace=0.2)  # 不得拋出
        self.assertEqual(writes, [])

    def test_decode_segment_ask_zh_output_is_converted_but_en_is_not(self):
        class Converter:
            def convert(self, text):
                return text.replace('简', '簡')

        class Simplified(Chain):
            def refine(self, text, mode, vocabulary='', context=None):
                return '简体回答'

        engine = Engine()
        engine.converter = Converter()
        self.assertEqual(decode_segment(engine, b'', 'ask', '', Simplified()).text, '簡体回答')
        self.assertEqual(decode_segment(engine, b'', 'ask', '', Simplified(), ask_language='en').text, '简体回答')

    def test_decode_segment_ask_without_translator_has_same_warning(self):
        result = decode_segment(Engine(), b'', 'ask', '', None)
        self.assertEqual(result.warning, '沒有可用的 LLM，顯示原始轉錄')
        self.assertEqual(result.error, '')

    def test_decode_segment_without_context_keeps_old_call_shape(self):
        result = decode_segment(Engine('嗯你好'), b'', 'zh', '', OldStyleLLM())
        self.assertEqual(result.text, 'ok:嗯你好')
        self.assertIsInstance(result, DecodeResult)

    def test_decode_segment_dictation_passes_context(self):
        chain = Chain()
        context = {'app': 'Code', 'title': 't', 'category': 'code'}
        decode_segment(Engine('hi'), b'', 'en', '', chain, context=context)
        self.assertEqual(chain.calls[0][2], context)


if __name__ == '__main__':
    unittest.main()
