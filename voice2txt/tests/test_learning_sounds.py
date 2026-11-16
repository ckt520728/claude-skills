import io
import unittest
import wave

from voice2txt import learning, sounds


class LearningTests(unittest.TestCase):
    def test_cjk_replacement(self):
        out = learning.candidates(["我在用語音輸入法"], "我在用語音輸入法", [])
        self.assertEqual(out, [])
        out = learning.candidates(["請找王小民來開會"], "請找汪小敏來開會", [])
        terms = [c["term"] for c in out]
        self.assertIn("汪", terms)
        out = learning.candidates(["他是黃偉人"], "他是黃威仁", [])
        self.assertEqual(out[0]["term"], "威仁")
        self.assertEqual(out[0]["replaced"], "偉人")

    def test_latin_proper_noun(self):
        out = learning.candidates(["we use open eye today"], "we use OpenAI today", [])
        self.assertEqual(out[0]["term"], "OpenAI")
        self.assertEqual(out[0]["replaced"], "open eye")

    def test_ignores_punctuation_and_digits(self):
        out = learning.candidates(["price is 10 dollars."], "price is 20 dollars!", [])
        self.assertEqual(out, [])

    def test_respects_known_terms(self):
        out = learning.candidates(["use open eye"], "use OpenAI", ["openai"])
        self.assertEqual(out, [])

    def test_counts_repeats(self):
        out = learning.candidates(["open eye is good", "ask open eye again"],
                                  "OpenAI is good ask OpenAI again", [])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["count"], 2)

    def test_ranking_capitalised_first(self):
        out = learning.candidates(["the cat sat on open eye"], "the dog sat on OpenAI", [])
        self.assertEqual(out[0]["term"], "OpenAI")
        self.assertIn("dog", [c["term"] for c in out])

    def test_merge_order_and_dedupe(self):
        self.assertEqual(learning.merge_vocabulary("Alpha, Beta", ["beta", "Gamma"]),
                         "Alpha, Beta, Gamma")

    def test_merge_cap(self):
        manual = ", ".join("m%03d" % i for i in range(300))
        auto = ["auto%03d" % i for i in range(300)]
        merged = learning.merge_vocabulary(manual, auto)
        self.assertLessEqual(len(merged), 1000)
        self.assertTrue(merged.startswith("m000, m001"))


class SoundTests(unittest.TestCase):
    def _parse(self, data):
        with wave.open(io.BytesIO(data)) as w:
            return w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()

    def test_riff_header_and_duration(self):
        for name, (freq, ms) in sounds.TONES.items():
            data = sounds.tone_wav(freq, ms)
            self.assertEqual(data[:4], b"RIFF")
            self.assertEqual(data[8:12], b"WAVE")
            ch, width, rate, n = self._parse(data)
            self.assertEqual((ch, width), (1, 2))
            self.assertLessEqual(abs(n / rate * 1000 - ms), 5)

    def test_fades_start_and_end_silent(self):
        data = sounds.tone_wav(880, 90)
        with wave.open(io.BytesIO(data)) as w:
            frames = w.readframes(w.getnframes())
        self.assertEqual(frames[:2], b"\x00\x00")
        self.assertLess(abs(int.from_bytes(frames[-2:], "little", signed=True)), 400)

    def test_play_disabled_never_raises(self):
        self.assertFalse(sounds.play("start", enabled=False))


if __name__ == "__main__":
    unittest.main()
