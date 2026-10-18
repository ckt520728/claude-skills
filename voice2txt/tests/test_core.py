import tempfile
import unittest
from pathlib import Path

import numpy as np

from voice2txt.core import Chunker, Store, WhisperEngine


class CoreTests(unittest.TestCase):
    def test_pause_ends_a_phrase_before_the_maximum_duration(self):
        chunker = Chunker(rate=10, seconds=8, silence_seconds=0.5, min_seconds=1)
        audio = np.concatenate((np.ones(20), np.zeros(10), np.ones(12)))
        chunks = chunker.feed(audio)
        self.assertEqual([len(c) for c in chunks], [25])
        chunks.extend(chunker.flush())
        np.testing.assert_array_equal(np.concatenate(chunks), audio)

    def test_continuous_speech_is_bounded_and_tail_is_preserved(self):
        chunker = Chunker(rate=10, seconds=8, silence_seconds=0.5, min_seconds=1)
        audio = np.ones(193)
        chunks = []
        for start in range(0, len(audio), 7):
            chunks.extend(chunker.feed(audio[start:start + 7]))
        chunks.extend(chunker.flush())
        self.assertEqual([len(c) for c in chunks], [80, 80, 33])
        np.testing.assert_array_equal(np.concatenate(chunks), audio)

    def test_chunker_preserves_every_sample_and_flushes_tail(self):
        chunker = Chunker(rate=10, seconds=1)
        chunks = []
        for block in [np.arange(7), np.arange(7, 24)]:
            chunks.extend(chunker.feed(block))
        chunks.extend(chunker.flush())
        np.testing.assert_array_equal(np.concatenate(chunks), np.arange(24))
        self.assertEqual([len(c) for c in chunks], [10, 10, 4])
        self.assertEqual(chunker.flush(), [])

    def test_history_survives_reopen_and_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'data.sqlite3'
            store = Store(path)
            store.add('zh', '腎臟病與 diabetes', 1.2)
            store.close()
            store = Store(path)
            rows = store.history()
            self.assertEqual(rows[0][2], '腎臟病與 diabetes')
            store.clear()
            self.assertEqual(store.history(), [])
            store.close()

    def test_modes_use_translation_task_and_traditional_conversion(self):
        class FakeModel:
            def transcribe(self, audio, **kwargs):
                self.options = kwargs
                segment = type('Segment', (), {'text': '肾脏和糖尿病'})()
                return iter([segment]), None

        model = FakeModel()
        engine = WhisperEngine(model=model)
        self.assertEqual(engine.transcribe(np.ones(16000), 'zh'), '腎臟和糖尿病')
        self.assertEqual(model.options['language'], 'zh')
        engine.transcribe(np.ones(16000), 'translate')
        self.assertEqual(model.options['task'], 'translate')
        self.assertEqual(model.options['language'], 'zh')
        engine.transcribe(np.ones(16000), 'en')
        self.assertEqual(model.options['task'], 'transcribe')
        self.assertEqual(model.options['language'], 'en')
        with self.assertRaises(ValueError):
            engine.transcribe(np.ones(16000), 'invalid')

    def test_silence_does_not_invent_text(self):
        engine = WhisperEngine(model=object())
        self.assertEqual(engine.transcribe(np.zeros(16000), 'zh'), '')


if __name__ == '__main__':
    unittest.main()
