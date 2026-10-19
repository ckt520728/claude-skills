"""Behavioural checks for the Life OS layer. No key, no network, stdlib unittest only.

These pin the *decision matrix* — which input at which confidence produces which verdict —
not merely that the code runs. That is the difference that makes a threshold change safe:
if someone lowers AUTO_FILE_CONFIDENCE below the stub's confidence, several tests here go
red rather than the system quietly starting to auto-file on fiction.

Run: python eval/test_smoke.py
"""

import datetime
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from lifeos import config as cfgmod          # noqa: E402
from lifeos import (clinical, gtd, jev, metrics, triage,  # noqa: E402
                    unlock, vault)
from lifeos.jev import Exit, calibration                     # noqa: E402
from lifeos.layer import COLD_CONFIDENCE, Layer, make_stub   # noqa: E402

CONFIG_PATH = os.path.join(ROOT, "vault-src", "_seed", "Meta", "Compass Config.md")


def make_config(**over):
    data = {
        "start_date": "2026-09-29",
        "daily_note_folder": "每日筆記",
        "clinical_access": "never",
        "clinical_heading": "🏥 臨床",
        "reflection_heading": "💡 今日反思",
        "dq_questions": [{"id": "dq_read", "prompt": "p"}, {"id": "dq_body", "prompt": "p"}],
        "habits": [{"id": "habit_move", "name": "n"}],
        "wheel_areas": [{"id": "wheel_health", "name": "n"}, {"id": "wheel_career", "name": "n"}],
        "unlock_days": {"journal": 1, "habits_weekly": 31, "retreat": 61, "tasks": 91,
                        "writing": 121},
        "display_bands": {"good": 8, "watch": 6},
    }
    data.update(over)
    return cfgmod.Config(data)


# ---------------------------------------------------------------- config ----
class TestConfigParser(unittest.TestCase):
    def test_parses_the_real_shipped_config(self):
        c = cfgmod.load_config(CONFIG_PATH)
        self.assertTrue(c.start_date, "shipped config must carry a start_date")
        self.assertEqual(c.validate(), [], "shipped config must be healthy")
        # Activated by the user 2026-09-29. Pinned so an accidental widening to `full`
        # (raw patient text into prompts) fails here rather than shipping quietly.
        self.assertEqual(c.clinical_access, "derived")
        self.assertTrue(c.clinical_derived_ok)
        self.assertFalse(c.clinical_full_ok, "shipped config must not be `full`")

    def test_list_of_mappings(self):
        fm = "a: 1\nitems:\n  - id: x\n    prompt: hello\n  - id: y\n    prompt: world\n"
        got = cfgmod.parse_frontmatter(fm)
        self.assertEqual(got["a"], 1)
        self.assertEqual(got["items"][1], {"id": "y", "prompt": "world"})

    def test_nested_map_and_bools(self):
        got = cfgmod.parse_frontmatter("u:\n  daily: 1\n  weekly: 31\nflag: true\nname: 每日\n")
        self.assertEqual(got["u"], {"daily": 1, "weekly": 31})
        self.assertIs(got["flag"], True)
        self.assertEqual(got["name"], "每日")

    def test_inline_comment_stripped_but_hash_value_kept(self):
        got = cfgmod.parse_frontmatter('a: 5   # trailing\nb: "#1 thing"\n')
        self.assertEqual(got["a"], 5)
        self.assertEqual(got["b"], "#1 thing")

    def test_raises_rather_than_guess(self):
        # Outside the documented subset: must raise, never silently mis-read.
        with self.assertRaises(cfgmod.ConfigError):
            cfgmod.parse_frontmatter("- top level list\n")
        with self.assertRaises(cfgmod.ConfigError):
            cfgmod.parse_frontmatter("key without colon\n")

    def test_prefix_is_enforced(self):
        bad = make_config(dq_questions=[{"id": "read", "prompt": "p"}])
        with self.assertRaises(cfgmod.ConfigError):
            bad.dq_ids  # noqa: B018 — property access is the call

    def test_validate_flags_too_many_questions(self):
        many = [{"id": "dq_%d" % i, "prompt": "p"} for i in range(8)]
        problems = make_config(dq_questions=many).validate()
        self.assertTrue(any("30-second" in p for p in problems), problems)

    def test_validate_flags_duplicate_ids_and_clinical_change(self):
        # Prefix enforcement makes cross-group collisions impossible, so a duplicate
        # can only occur within one group.
        dup = make_config(dq_questions=[{"id": "dq_read", "prompt": "a"},
                                        {"id": "dq_read", "prompt": "b"}])
        self.assertTrue(any("duplicate" in p for p in dup.validate()))

    def test_validate_reports_prefix_violation_instead_of_raising(self):
        bad = make_config(habits=[{"id": "dq_read", "name": "n"}])
        problems = bad.validate()   # must not raise
        self.assertTrue(any("must start with" in p for p in problems), problems)
        # An unrecognised level must be reported and must fall back to `never`.
        typo = make_config(clinical_access="read")
        self.assertEqual(typo.clinical_access, "never")
        self.assertTrue(any("not one of" in p for p in typo.validate()))


# ------------------------------------------------- upstream Compass interop ----
# Verbatim from github.com/AgriciDaniel/compass, Meta/Compass Config.md, fetched
# 2026-09-29 (UNKNOWNS.md U1 resolved). Upstream uses `questions`/`key`/`text` and flat
# string lists; this repo uses `dq_questions`/`id`/`prompt` and mappings with a `name`.
# Both must parse, so an upstream config can be dropped in while a 繁中 config keeps labels.
UPSTREAM_COMPASS = """birthdate: 1980-04-02
life_expectancy: 80
daily_folder: 01 Journal/Daily
weekly_folder: 01 Journal/Weekly
retreat_folder: 02 Retreats
dq_prefix: dq_
habit_prefix: habit_
wheel_prefix: wheel_
board_done_lanes: Done,Published,Archive
questions:
  - key: dq_goals
    text: Did I do my best to set clear goals today?
  - key: dq_progress
    text: Did I do my best to make progress toward my goals?
habits:
  - habit_journal
  - habit_exercise
wheel_areas:
  - wheel_health
  - wheel_meaning
"""


class TestUpstreamCompassInterop(unittest.TestCase):
    def setUp(self):
        self.c = cfgmod.Config(cfgmod.parse_frontmatter(UPSTREAM_COMPASS))

    def test_upstream_questions_key_and_text(self):
        self.assertEqual(self.c.dq_ids, ["dq_goals", "dq_progress"])
        self.assertEqual(self.c.dq_questions[0]["prompt"],
                         "Did I do my best to set clear goals today?")

    def test_upstream_flat_habit_list(self):
        self.assertEqual(self.c.habit_ids, ["habit_journal", "habit_exercise"])
        # With no separate label upstream, the key doubles as the name.
        self.assertEqual(self.c.habits[0]["name"], "habit_journal")

    def test_upstream_flat_wheel_list(self):
        self.assertEqual(self.c.wheel_ids, ["wheel_health", "wheel_meaning"])

    def test_upstream_daily_folder_key(self):
        self.assertEqual(self.c.daily_note_folder, "01 Journal/Daily")

    def test_memento_fields(self):
        self.assertTrue(self.c.memento_ok)
        self.assertEqual(self.c.birthdate, "1980-04-02")
        self.assertEqual(self.c.life_expectancy, 80)

    def test_memento_absent_is_disabled_not_broken(self):
        c = make_config()
        self.assertFalse(c.memento_ok)
        self.assertEqual(c.life_expectancy, 80)

    def test_prefix_still_enforced_on_upstream_shape(self):
        bad = cfgmod.Config(cfgmod.parse_frontmatter(
            "questions:\n  - key: goals\n    text: x\n"))
        with self.assertRaises(cfgmod.ConfigError):
            bad.dq_ids

    def test_both_shapes_yield_the_same_interface(self):
        for c in (make_config(), self.c):
            for q in c.dq_questions:
                self.assertIn("id", q)
                self.assertIn("prompt", q)
                self.assertIn("name", q)


# ---------------------------------------------------------------- unlock ----
class TestUnlock(unittest.TestCase):
    """Compass Build Order (upstream Guide/11), plus its 80% consistency rule."""

    def setUp(self):
        self.c = make_config()
        self.start = datetime.date(2026, 9, 29)

    def d(self, n):
        return self.start + datetime.timedelta(days=n - 1)

    def test_day_one_is_start_date(self):
        self.assertEqual(unlock.day_number("2026-09-29", self.d(1)), 1)
        self.assertEqual(unlock.day_number("2026-09-29", self.d(31)), 31)

    def test_layers_follow_upstream_build_order(self):
        self.assertEqual(unlock.LAYERS,
                         ("journal", "habits_weekly", "retreat", "tasks", "writing"))
        self.assertEqual(self.c.unlock_days,
                         {"journal": 1, "habits_weekly": 31, "retreat": 61,
                          "tasks": 91, "writing": 121})

    def test_only_journal_on_day_one(self):
        on = unlock.active_layers(self.c, self.d(1))
        self.assertTrue(on["journal"])
        self.assertFalse(any(v for k, v in on.items() if k != "journal"))

    def test_boundaries_are_exact(self):
        for layer, day in (("habits_weekly", 31), ("retreat", 61), ("tasks", 91), ("writing", 121)):
            self.assertFalse(unlock.is_unlocked(self.c, layer, self.d(day - 1)), layer)
            self.assertTrue(unlock.is_unlocked(self.c, layer, self.d(day)), layer)

    def test_low_consistency_holds_the_next_layer(self):
        # Upstream: "Do not add a layer while the previous one is below 80% consistency."
        self.assertFalse(unlock.is_unlocked(self.c, "habits_weekly", self.d(40), consistency=0.5))
        self.assertTrue(unlock.is_unlocked(self.c, "habits_weekly", self.d(40), consistency=0.8))
        self.assertTrue(unlock.is_unlocked(self.c, "journal", self.d(40), consistency=0.0),
                        "the foundation layer is never gated")

    def test_status_reports_why_a_layer_is_closed(self):
        rows = dict((r[0], r) for r in unlock.status_table(self.c, self.d(40), consistency=0.5))
        self.assertEqual(rows["habits_weekly"][5], "consistency")
        self.assertEqual(rows["tasks"][5], "days")
        self.assertEqual(rows["journal"][5], "")

    def test_journal_consistency_counts_only_days_since_start(self):
        scored = [self.d(i) for i in range(1, 11)]
        frac, n, denom = unlock.journal_consistency(scored, "2026-09-29", self.d(10))
        self.assertEqual((n, denom), (10, 10))
        self.assertAlmostEqual(frac, 1.0)
        frac, n, denom = unlock.journal_consistency(scored[:5], "2026-09-29", self.d(40))
        self.assertEqual(denom, 30)
        self.assertEqual(n, 0, "days outside the 30-day window do not count")

    def test_legacy_unlock_keys_still_parse(self):
        c = make_config(unlock_days={"daily": 1, "weekly": 20, "quarterly": 50})
        self.assertEqual(c.unlock_days["habits_weekly"], 20)
        self.assertEqual(c.unlock_days["retreat"], 50)

    def test_missing_start_date_fails_closed(self):
        c = make_config(start_date=None)
        self.assertTrue(unlock.is_unlocked(c, "journal"))
        for layer in unlock.LAYERS[1:]:
            self.assertFalse(unlock.is_unlocked(c, layer), layer)

    def test_status_table_reports_dates_and_countdown(self):
        rows = dict((r[0], r) for r in unlock.status_table(self.c, self.d(1)))
        self.assertEqual(rows["habits_weekly"][3], "2026-10-29")
        self.assertEqual(rows["habits_weekly"][4], 30)
        self.assertEqual(rows["tasks"][3], "2026-12-28")


# --------------------------------------------------------------- metrics ----
class TestMetrics(unittest.TestCase):
    def rows(self, seq):
        """seq is newest-first list of dicts."""
        base = datetime.date(2026, 9, 29)
        return [(base - datetime.timedelta(days=i), fm) for i, fm in enumerate(seq)]

    def test_missing_is_not_zero(self):
        r = self.rows([{"dq_read": 8}, {}, {"dq_read": 6}])
        m = metrics.mean_of(r, "dq_read", window=3)
        self.assertEqual(m.n, 2)
        self.assertAlmostEqual(m.value, 7.0)

    def test_mean_carries_its_denominator(self):
        m = metrics.mean_of(self.rows([{"dq_read": 9}]), "dq_read", window=7)
        self.assertEqual((m.n, m.window), (1, 7))
        self.assertIn("n=1/7", repr(m))

    def test_empty_mean_is_none_not_zero(self):
        m = metrics.mean_of(self.rows([{}, {}]), "dq_read", window=7)
        self.assertTrue(m.is_empty)
        self.assertIsNone(m.value)

    def test_bool_is_not_counted_as_a_score(self):
        m = metrics.mean_of(self.rows([{"habit_move": True}]), "habit_move")
        self.assertTrue(m.is_empty)

    def test_streak_breaks_on_missing_day(self):
        s = metrics.streak_of(self.rows([{"habit_move": True}, {}, {"habit_move": True}]), "habit_move")
        self.assertEqual(s.current, 1)
        self.assertEqual(s.hits, 2)

    def test_streak_counts_run_from_newest(self):
        s = metrics.streak_of(
            self.rows([{"habit_move": True}, {"habit_move": True}, {"habit_move": False}]),
            "habit_move",
        )
        self.assertEqual(s.current, 2)
        self.assertAlmostEqual(s.rate, 2.0 / 3.0)

    def test_delta_vs_mean(self):
        m = metrics.mean_of(self.rows([{"dq_read": 6}, {"dq_read": 8}]), "dq_read")
        self.assertAlmostEqual(metrics.delta_vs_mean(4, m), -3.0)
        self.assertIsNone(metrics.delta_vs_mean(None, m))

    def test_band_is_presentation_only(self):
        b = {"good": 8, "watch": 6}
        self.assertEqual(metrics.band(9, b), "good")
        self.assertEqual(metrics.band(7, b), "watch")
        self.assertEqual(metrics.band(3, b), "low")
        self.assertEqual(metrics.band(None, b), "none")

    def test_read_daily_ignores_body_and_nesting(self):
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "2026-09-29.md")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("---\ndq_read: 7\nnested:\n  a: 1\n---\n\n## 🏥 臨床\n\n- secret\n")
            fm = metrics.read_daily(p)
            self.assertEqual(fm.get("dq_read"), 7)
            self.assertNotIn("a", fm)
            self.assertNotIn("secret", str(fm))
        finally:
            shutil.rmtree(tmp)

    def test_collect_skips_absent_days(self):
        tmp = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmp, "2026-09-29.md"), "w", encoding="utf-8") as fh:
                fh.write("---\ndq_read: 5\n---\n")
            rows = metrics.collect(tmp, window=7, today=datetime.date(2026, 9, 29))
            self.assertEqual(len(rows), 1)
        finally:
            shutil.rmtree(tmp)


# ------------------------------------------------------------------- gtd ----
class TestGtdGate(unittest.TestCase):
    """The decision matrix, driven through the skill's decide() with a stub provider."""

    def setUp(self):
        self.c = make_config()

    def test_threshold_sits_above_the_default_stub(self):
        self.assertGreater(gtd.AUTO_FILE_CONFIDENCE, 0.34)

    def test_low_confidence_lands_everything_on_ask(self):
        out = gtd.clarify("買牛奶", self.c, layer=make_stub())
        self.assertTrue(out)
        for name, d in out.items():
            self.assertEqual(d.verdict, gtd.ASK, "%s should ask: %s" % (name, d.explain()))

    def test_high_confidence_can_auto_file(self):
        out = gtd.clarify("買牛奶", self.c, layer=make_stub(confidence=0.97))
        self.assertEqual(out["bucket"].verdict, gtd.AUTO,
                         "a confident, unguarded decision must be able to auto-file")
        self.assertIs(out["bucket"].exit, Exit.ACT)

    def test_other_is_never_auto_filed(self):
        out = gtd.clarify("買牛奶", self.c, layer=make_stub(0.99, picks={"bucket": "other"}))
        self.assertEqual(out["bucket"].verdict, gtd.ASK)
        self.assertIs(out["bucket"].exit, Exit.HUMAN)
        self.assertTrue(any("invariant 4" in r for r in out["bucket"].reasons))

    def test_per_label_thresholds(self):
        # project needs more than next_action (blast radius differs within one question).
        self.assertGreater(gtd.BUCKET_TAU["project"], gtd.BUCKET_TAU["next_action"])
        out = gtd.clarify("x", self.c, layer=make_stub(0.80, picks={"bucket": "project"}))
        self.assertEqual(out["bucket"].verdict, gtd.ASK)
        out = gtd.clarify("x", self.c, layer=make_stub(0.80, picks={"bucket": "next_action"}))
        self.assertEqual(out["bucket"].verdict, gtd.AUTO)

    def test_kb_and_clippings_are_never_auto_filed(self):
        for folder in ("知識庫", "Clippings"):
            out = gtd.assess("x", self.c, make_stub(0.999, picks={"folder": folder}), ("folder",))
            self.assertEqual(out["folder"].verdict, gtd.ASK, folder)

    def test_hard_rules_outrank_confidence(self):
        for text in ("這個病人的處方要改", "幫我匯款給房東", "老婆的生日禮物"):
            out = gtd.clarify(text, self.c, layer=make_stub(confidence=0.99))
            self.assertEqual(out["bucket"].verdict, gtd.ASK, text)
            self.assertIs(out["bucket"].exit, Exit.HUMAN, text)
            self.assertTrue(any("guard" in r for r in out["bucket"].reasons), text)

    def test_hard_rules_match_english_too(self):
        self.assertTrue(gtd.hard_rules("update the patient chart"))
        self.assertTrue(gtd.hard_rules("pay the invoice"))
        self.assertFalse(gtd.hard_rules("read a paper about attention"))

    def test_noul_midband_reports_unclear(self):
        out = gtd.clarify("something vague", self.c, layer=make_stub(noul=0.5))
        self.assertEqual(out["actionable"].label, "unclear")
        self.assertEqual(out["actionable"].verdict, gtd.ASK)

    def test_layer_error_fails_to_ask(self):
        class Boom(Layer):
            def decide(self, state, questions):
                raise RuntimeError("network blip")
        out = gtd.clarify("x", self.c, layer=Boom())
        self.assertTrue(all(d.verdict == gtd.ASK for d in out.values()))

    def test_every_choice_has_an_exit(self):
        for q in gtd.questions(self.c).values():
            if isinstance(q, jev.Choice):
                self.assertIn("other", q.criteria)

    def test_organize_carries_the_index_duty(self):
        out = gtd.organize("x", self.c, make_stub(0.9, picks={"folder": "知識庫"}),
                           kb_index_path="")
        self.assertTrue(any("index.md" in r for r in out["folder"].reasons))

    def test_duplicate_check_is_code_not_a_guess(self):
        idx = "- [[腎絲球過濾率估算公式比較]] eGFR CKD-EPI MDRD\n- [[睡眠與記憶鞏固]]\n"
        self.assertTrue(gtd.kb_candidates("CKD-EPI 和 MDRD 的 eGFR 公式比較", idx))
        self.assertFalse(gtd.kb_candidates("買牛奶", idx))

    def test_summarize_puts_auto_first(self):
        ds = {"a": gtd.Decision(gtd.ASK, "x", 0.4, "a"),
              "b": gtd.Decision(gtd.AUTO, "y", 0.9, "b")}
        self.assertTrue(gtd.summarize(ds)[0].startswith("b"))


# ------------------------------------------- the jev skill, as Life OS uses it ----
class TestUsesTheJevSkill(unittest.TestCase):
    """Sessions 1-4 reimplemented the skill. These fail if that ever happens again."""

    def test_no_private_decision_layer_remains(self):
        for gone in ("decide.py", "calibrate.py", "jev_stub.py"):
            self.assertFalse(os.path.exists(os.path.join(ROOT, "lifeos", gone)), gone)

    def test_questions_are_the_skills_primitives(self):
        for qid, q in gtd.questions(make_config()).items():
            self.assertIsInstance(q, (jev.Choice, jev.Score, jev.Noul), qid)

    def test_every_option_carries_criteria_text(self):
        # Rule 1: the question id never reaches the model; meaning lives in criteria.
        # Checked against the SHIPPED config: wheel-area criteria are the user's to edit.
        for qid, q in gtd.questions(cfgmod.load_config(CONFIG_PATH)).items():
            crit = q.criteria.values() if isinstance(q.criteria, dict) else q.criteria
            for text in crit:
                self.assertGreater(len(text), 8, "%s has a bare option: %r" % (qid, text))

    def test_one_decide_call_per_capture(self):
        # Rule 5: every question shares the state, so ask them all at once.
        calls = []

        class Counting(Layer):
            def decide(self, state, questions):
                calls.append(sorted(questions))
                return Layer.decide(self, state, questions)
        layer = Counting(provider="local", calibrator=calibration.Calibrator())
        triage.propose("明天打電話預約牙醫", make_config(), layer=layer, kb_index_path="")
        self.assertEqual(len(calls), 1, calls)
        self.assertEqual(calls[0], sorted(gtd.questions(make_config())))

    def test_bare_numeric_score_is_rejected_by_the_skill(self):
        with self.assertRaises(jev.QuestionSpecError):
            jev.Score(instructions="How urgent is this capture?", criteria=["0", "1", "2"])

    def test_local_provider_costs_nothing(self):
        r = Layer("local", calibrator=calibration.Calibrator()).decide(
            "有空想學日文", {"bucket": gtd.BUCKET})
        self.assertEqual(r.usage, {"input_tokens": 0, "output_tokens": 0})
        self.assertEqual(r.cost_usd, 0.0)


# ------------------------------------------- local decision layer + calibration ----
class TestLocalDecisionLayer(unittest.TestCase):
    def setUp(self):
        self.c = make_config()
        self.cal = calibration.Calibrator()
        self.layer = Layer("local", calibrator=self.cal)

    def pick(self, text, q="bucket"):
        r = self.layer.decide(text, {q: gtd.questions(self.c)[q]})
        return r.answers[q].choice

    def test_classifies_representative_captures(self):
        cases = [
            ("回覆張醫師的 email", "two_minute"),
            ("重構 Life OS 的儀表板系統，然後接著寫測試", "project"),
            ("有空想學日文", "someday"),
            ("JAMA 那篇糖尿病文獻", "reference"),
            ("someday maybe learn to sail", "someday"),
            ("明天打電話預約牙醫", "next_action"),
        ]
        for text, expected in cases:
            self.assertEqual(self.pick(text), expected, text)

    def test_unmatched_text_takes_the_exit(self):
        self.assertEqual(self.pick("asdfgh qwerty zxcvbn"), "other")

    def test_folder_criteria(self):
        self.assertEqual(self.pick("https://example.com/paper", "folder"), "Clippings")
        self.assertEqual(self.pick("我的投影片草稿", "folder"), "創作庫")

    def test_urgency_score_ordering(self):
        u = {"urgency": gtd.URGENCY}
        overdue = self.layer.decide("這件已經逾期了，今天要", u).answers["urgency"].score
        later = self.layer.decide("下個月再說", u).answers["urgency"].score
        self.assertGreater(overdue, later)

    def test_flat_score_makes_no_proposal(self):
        out = gtd.clarify("asdfgh qwerty", self.c, layer=self.layer)
        self.assertIsNone(out["urgency"].label)

    def test_cold_layer_asks_about_everything(self):
        out = gtd.clarify("重構儀表板系統然後寫測試", self.c, layer=self.layer)
        for name, d in out.items():
            self.assertEqual(d.verdict, gtd.ASK, "%s must ask while cold: %s" % (name, d.explain()))

    def test_cold_confidence_is_below_every_gate(self):
        self.assertLess(COLD_CONFIDENCE, gtd.AUTO_FILE_CONFIDENCE)
        self.assertLess(COLD_CONFIDENCE, gtd.ESCALATE_FLOOR)

    def test_cold_decision_says_why(self):
        out = gtd.clarify("重構儀表板系統", self.c, layer=self.layer)
        self.assertTrue(any("cold" in r for r in out["bucket"].reasons), out["bucket"].reasons)

    def test_layer_warms_up_and_earns_the_right_to_auto_file(self):
        text = "重構 Life OS 的儀表板系統，然後接著寫測試"
        first = gtd.clarify(text, self.c, layer=self.layer)["bucket"]
        self.assertEqual(first.confidence, COLD_CONFIDENCE)
        for _ in range(calibration.MIN_OBSERVATIONS):
            self.layer.record("bucket", first.raw_confidence, True, save=False)
        after = gtd.clarify(text, self.c, layer=self.layer)["bucket"]
        self.assertTrue(after.warm)
        self.assertGreaterEqual(after.confidence, gtd.BUCKET_TAU[after.label])
        self.assertEqual(after.verdict, gtd.AUTO)

    def test_a_band_that_is_usually_wrong_never_unlocks(self):
        text = "重構 Life OS 的儀表板系統，然後接著寫測試"
        raw = gtd.clarify(text, self.c, layer=self.layer)["bucket"].raw_confidence
        for i in range(40):
            self.layer.record("bucket", raw, i % 4 == 0, save=False)
        after = gtd.clarify(text, self.c, layer=self.layer)["bucket"]
        self.assertTrue(after.warm)
        self.assertEqual(after.verdict, gtd.ASK)

    def test_noul_is_calibrated_by_life_os(self):
        # The local provider returns no confidence for a Noul (spec). Life OS calibrates
        # its decisiveness, so a cold Noul still asks.
        out = gtd.clarify("明天打電話預約牙醫", self.c, layer=self.layer)
        self.assertEqual(out["actionable"].label, "yes")
        self.assertEqual(out["actionable"].confidence, COLD_CONFIDENCE)

    def test_each_question_calibrates_separately(self):
        for _ in range(calibration.MIN_OBSERVATIONS):
            self.layer.record("bucket", 0.75, True, save=False)
        self.assertTrue(self.cal.is_warm("bucket", 0.75))
        self.assertFalse(self.cal.is_warm("folder", 0.75))

    def test_hard_rules_still_outrank_a_warm_layer(self):
        for raw in [i / 20.0 for i in range(21)]:
            for _ in range(calibration.MIN_OBSERVATIONS):
                self.layer.record("bucket", raw, True, save=False)
        out = gtd.clarify("幫我匯款給房東", self.c, layer=self.layer)
        self.assertEqual(out["bucket"].verdict, gtd.ASK)

    def test_env_calibration_does_not_leak_in(self):
        os.environ["JEV_CALIBRATION"] = os.path.join(tempfile.gettempdir(), "nope.json")
        try:
            out = gtd.clarify("有空想學日文", self.c, layer=self.layer)
            self.assertEqual(out["bucket"].confidence, COLD_CONFIDENCE)
        finally:
            del os.environ["JEV_CALIBRATION"]

    def test_corrupt_calibration_file_starts_cold(self):
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "calibration.json")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("{ not json at all")
            self.assertEqual(Layer("local", path=p).cal.observations(), 0)
        finally:
            shutil.rmtree(tmp)

    def test_calibration_round_trips_to_disk(self):
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "sub", "calibration.json")
            layer = Layer("local", path=p)
            for _ in range(calibration.MIN_OBSERVATIONS):
                layer.record("bucket", 0.8, True)
            self.assertTrue(Layer("local", path=p).cal.is_warm("bucket", 0.8))
        finally:
            shutil.rmtree(tmp)

    def test_layer_selection(self):
        self.assertEqual(gtd.layer_for_env({}).name, "local")
        self.assertTrue(gtd.layer_for_env({}).live)
        self.assertEqual(gtd.layer_for_env({"LIFEOS_PROVIDER": "jev"}).name, "jev")


# ----------------------------------------------------------------- vault ----
class TestAppendOnly(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "2026-09-29.md")
        self.original = (
            "---\ndate: 2026-09-29\n---\n\n"
            "## 🏥 臨床\n\n- 個案 A 待追蹤\n\n"
            "## 💡 今日反思\n\n> 原本就有的一行\n"
        )
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write(self.original)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def read(self):
        with open(self.path, encoding="utf-8") as fh:
            return fh.read()

    def test_append_preserves_everything(self):
        vault.append_under_heading(self.path, "💡 今日反思", "- 新增一行", clinical_heading="🏥 臨床")
        after = self.read()
        self.assertIn("原本就有的一行", after)
        self.assertIn("個案 A 待追蹤", after)
        self.assertIn("新增一行", after)

    def test_clinical_section_is_refused(self):
        with self.assertRaises(vault.ClinicalSectionBlocked):
            vault.append_under_heading(self.path, "🏥 臨床", "- 不該寫進去", clinical_heading="🏥 臨床")
        self.assertEqual(self.read(), self.original, "file must be untouched after refusal")

    def test_missing_heading_is_created_at_eof(self):
        vault.append_under_heading(self.path, "AI Coach", "- note", clinical_heading="🏥 臨床")
        after = self.read()
        self.assertIn("## AI Coach", after)
        self.assertIn("原本就有的一行", after)

    def test_superset_check_catches_deletion(self):
        with self.assertRaises(vault.AppendOnlyViolation):
            vault._assert_superset("keep this text", "keep")

    def test_superset_check_allows_midfile_insert(self):
        vault._assert_superset("abc", "aXbc")  # must not raise

    def test_empty_block_is_a_noop(self):
        self.assertFalse(vault.append_under_heading(self.path, "💡 今日反思", "  ", clinical_heading="🏥 臨床"))
        self.assertEqual(self.read(), self.original)

    def test_read_body_strips_clinical_section(self):
        body = vault.read_body_without_clinical(self.path, "🏥 臨床")
        self.assertNotIn("個案 A 待追蹤", body)
        self.assertIn("原本就有的一行", body)

    def test_set_frontmatter_updates_and_appends(self):
        vault.set_frontmatter(self.path, {"date": "2026-09-30", "dq_read": 8})
        after = self.read()
        self.assertIn("date: 2026-09-30", after)
        self.assertIn("dq_read: 8", after)
        self.assertIn("個案 A 待追蹤", after, "body must survive a frontmatter write")
        self.assertEqual(after.count("date:"), 1, "key must be replaced, not duplicated")


# -------------------------------------------------------------- clinical ----
# Activated 2026-09-29 at level `derived`. UNKNOWNS.md U4 resolved.
#
# The purity test below is the real guarantee behind "the coach never sees patient text".
# Everything else in this class is supporting detail.

CLINICAL_NOTE = """---
date: 2026-09-29
---

# 2026-09-29

## 🏥 臨床

- 陳先生 Cr 2.8 持續上升，明日追 BUN
- 林女士 HbA1c 9.1，調整 basal insulin
- 王先生 K+ 6.2 已給 calcium gluconate

**待處理個案**：

- 顧問門診 3 位需回電
-

## 💡 今日反思

> 今天很累
"""

# Tokens that must never appear in anything transmittable.
SECRETS = ("陳先生", "林女士", "王先生", "Cr", "HbA1c", "insulin",
           "calcium gluconate", "BUN", "回電", "2.8", "9.1", "6.2")


class TestClinicalBoundary(unittest.TestCase):
    def setUp(self):
        self.derived = make_config(clinical_access="derived")
        self.local = make_config(clinical_access="local")
        self.never = make_config(clinical_access="never")
        self.full = make_config(clinical_access="full")

    # -- the guarantee -------------------------------------------------
    def test_no_clinical_text_reaches_the_transmittable_surface(self):
        d = clinical.digest_from_text(CLINICAL_NOTE, self.derived)
        payload = clinical.coach_context(d, self.derived)
        blob = repr(payload) + "|" + d.as_context_line() + "|" + repr(d)
        for secret in SECRETS:
            self.assertNotIn(secret, blob,
                             "LEAK: %r reached the transmittable surface" % secret)

    def test_digest_values_are_all_numeric(self):
        d = clinical.digest_from_text(CLINICAL_NOTE, self.derived)
        for key, value in d.as_dict().items():
            self.assertTrue(value is None or isinstance(value, (int, float, bool)),
                            "%s is %r, not numeric" % (key, type(value).__name__))

    def test_digest_cannot_hold_a_string(self):
        # __slots__ means there is nowhere to put one.
        d = clinical.ClinicalDigest()
        with self.assertRaises(AttributeError):
            d.raw_text = "陳先生"

    def test_assert_transmittable_rejects_strings(self):
        with self.assertRaises(clinical.ClinicalAccessDenied):
            clinical.assert_transmittable({"clinical_note": "陳先生 Cr 2.8"})
        clinical.assert_transmittable({"a": 1, "b": 2.5, "c": True, "d": None})

    # -- access levels -------------------------------------------------
    def test_never_refuses_to_read(self):
        with self.assertRaises(clinical.ClinicalAccessDenied):
            clinical.digest_from_text(CLINICAL_NOTE, self.never)

    def test_local_reads_but_transmits_nothing(self):
        d = clinical.digest_from_text(CLINICAL_NOTE, self.local)
        self.assertEqual(d.pending_cases, 4)
        self.assertEqual(clinical.coach_context(d, self.local), {},
                         "local must transmit nothing, not even counts")

    def test_derived_transmits_numbers(self):
        d = clinical.digest_from_text(CLINICAL_NOTE, self.derived)
        ctx = clinical.coach_context(d, self.derived)
        self.assertEqual(set(ctx), {"clinical_pending", "clinical_load"})

    def test_full_still_does_not_return_raw_text(self):
        # Widening to `full` must be a separate deliberate change, not a side effect.
        d = clinical.digest_from_text(CLINICAL_NOTE, self.full)
        ctx = clinical.coach_context(d, self.full)
        blob = repr(ctx)
        for secret in SECRETS:
            self.assertNotIn(secret, blob)

    def test_unknown_level_falls_back_to_never(self):
        c = make_config(clinical_access="everything")
        self.assertEqual(c.clinical_access, "never")
        self.assertFalse(c.clinical_local_ok)
        self.assertTrue(any("not one of" in p for p in c.validate()))

    def test_full_is_flagged_in_validate(self):
        self.assertTrue(any("full" in p for p in self.full.validate()))

    # -- counting ------------------------------------------------------
    def test_counts_cases_and_ignores_empty_bullets(self):
        d = clinical.digest_from_text(CLINICAL_NOTE, self.derived)
        self.assertEqual(d.pending_cases, 4)   # 3 cases + 1 consult line
        self.assertEqual(d.case_lines, 5)      # includes the bare "-"
        self.assertTrue(d.has_content)

    def test_empty_section_is_zero_not_none(self):
        text = "---\nd: 1\n---\n\n## 🏥 臨床\n\n\n## 💡 今日反思\n\n> x\n"
        d = clinical.digest_from_text(text, self.derived)
        self.assertEqual(d.pending_cases, 0)
        self.assertFalse(d.has_content)

    def test_absent_section_is_handled(self):
        d = clinical.digest_from_text("---\nd: 1\n---\n\n## 其他\n\n- x\n", self.derived)
        self.assertEqual(d.pending_cases, 0)

    def test_load_bands(self):
        self.assertEqual(clinical.load_band(0), 1)
        self.assertEqual(clinical.load_band(2), 2)
        self.assertEqual(clinical.load_band(5), 3)
        self.assertEqual(clinical.load_band(9), 4)
        self.assertEqual(clinical.load_band(20), 5)
        self.assertIsNone(clinical.load_band(None))

    def test_extract_section_stops_at_next_h2(self):
        sec = clinical.extract_section(CLINICAL_NOTE, "🏥 臨床")
        self.assertIn("陳先生", sec, "local extraction must work")
        self.assertNotIn("今天很累", sec, "must stop at the next H2")

    def test_context_line_is_numeric_only(self):
        d = clinical.digest_from_text(CLINICAL_NOTE, self.derived)
        line = d.as_context_line()
        self.assertIn("4", line)
        for secret in SECRETS:
            self.assertNotIn(secret, line)

    def test_digest_from_file(self):
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "2026-09-29.md")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(CLINICAL_NOTE)
            d = clinical.digest_from_file(p, self.derived)
            self.assertEqual(d.pending_cases, 4)
            missing = clinical.digest_from_file(os.path.join(tmp, "nope.md"), self.derived)
            self.assertFalse(missing.has_content)
        finally:
            shutil.rmtree(tmp)

    # -- the append-only guard still blocks writing into the section ----
    def test_activation_does_not_permit_writing_into_the_section(self):
        # Reading is now allowed. Writing never was, and still is not.
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "d.md")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(CLINICAL_NOTE)
            with self.assertRaises(vault.ClinicalSectionBlocked):
                vault.append_under_heading(p, "🏥 臨床", "- injected",
                                           clinical_heading="🏥 臨床")
        finally:
            shutil.rmtree(tmp)


# --------------------------------------------- the ask-resolution flow (triage) ----
# This is the wiring that was missing: without it the layer learns nothing and stays cold
# forever. The most important test here is the last one — the loop actually closing.

INBOX_MD = """---
title: 任務總表
---

# 任務總表

## 收件匣

- [ ] 回覆張醫師的 email
- 重構儀表板，然後接著寫測試
- [x] 這則已經處理過了
-
- [ ] 有空想學日文

## 將來也許

- 這一段不是收件，是另一個清單
"""


class TestTriageInbox(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.inbox = os.path.join(self.tmp, "任務總表.md")
        with open(self.inbox, "w", encoding="utf-8") as fh:
            fh.write(INBOX_MD)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_parses_only_the_capture_section(self):
        got = triage.parse_inbox(self.inbox)
        self.assertEqual(got, ["回覆張醫師的 email", "重構儀表板，然後接著寫測試", "有空想學日文"])

    def test_skips_completed_and_empty_bullets(self):
        got = triage.parse_inbox(self.inbox)
        self.assertNotIn("這則已經處理過了", " ".join(got))
        self.assertTrue(all(g.strip() for g in got))

    def test_explanatory_bullets_outside_the_heading_are_ignored(self):
        self.assertNotIn("這一段不是收件", " ".join(triage.parse_inbox(self.inbox)))

    def test_absent_inbox_is_empty_not_an_error(self):
        self.assertEqual(triage.parse_inbox(os.path.join(self.tmp, "nope.md")), [])

    def test_parse_never_writes(self):
        before = open(self.inbox, encoding="utf-8").read()
        triage.parse_inbox(self.inbox)
        self.assertEqual(open(self.inbox, encoding="utf-8").read(), before)


class TestTriageResolution(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.log = os.path.join(self.tmp, "decisions.jsonl")
        self.c = make_config()
        self.cal = calibration.Calibrator()
        self.b = Layer("local", calibrator=self.cal)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    # -- what counts as evidence ---------------------------------------
    def test_only_escalated_decisions_are_put_to_a_human(self):
        p = triage.propose("重構儀表板，然後接著寫測試", self.c, layer=self.b, kb_index_path="")
        # Cold layer -> everything escalates.
        self.assertIn("bucket", p.questions_for_human())

    def test_auto_decisions_are_not_asked_by_default(self):
        d = gtd.Decision(gtd.AUTO, "project", 0.95, "bucket")
        self.assertFalse(triage.needs_human(d))

    def test_resolving_teaches_the_layer(self):
        p = triage.propose("重構儀表板，然後接著寫測試", self.c, layer=self.b, kb_index_path="")
        before = self.cal.observations("bucket")
        triage.resolve(self.b, p, "bucket", "project", log_path=self.log, save=False)
        self.assertEqual(self.cal.observations("bucket"), before + 1)

    def test_a_correction_is_recorded_as_a_miss(self):
        p = triage.propose("重構儀表板，然後接著寫測試", self.c, layer=self.b, kb_index_path="")
        proposed = p.decisions["bucket"].label
        wrong = "reference" if proposed != "reference" else "someday"
        res = triage.resolve(self.b, p, "bucket", wrong, log_path=self.log, save=False)
        self.assertFalse(res.agreed)
        raw = p.decisions["bucket"].raw_confidence
        cell = self.cal.data["bucket"][calibration._bin_index(raw)]
        self.assertEqual(cell, [0, 1], "a correction must count as an observation and a miss")

    def test_agreement_is_recorded_as_a_hit(self):
        p = triage.propose("重構儀表板，然後接著寫測試", self.c, layer=self.b, kb_index_path="")
        proposed = p.decisions["bucket"].label
        res = triage.resolve(self.b, p, "bucket", proposed, log_path=self.log, save=False)
        self.assertTrue(res.agreed)
        raw = p.decisions["bucket"].raw_confidence
        self.assertEqual(self.cal.data["bucket"][calibration._bin_index(raw)], [1, 1])

    def test_resolving_an_unknown_question_raises(self):
        p = triage.propose("x", self.c, layer=self.b, kb_index_path="")
        with self.assertRaises(KeyError):
            triage.resolve(self.b, p, "nonexistent", "y", save=False)

    # -- audit sampling: the anti-drift mechanism -----------------------
    def test_audit_sampling_never_fires_on_an_ask(self):
        d = gtd.Decision(gtd.ASK, "project", 0.4, "bucket")

        class AlwaysDraw(object):
            def random(self):
                return 0.0
        self.assertFalse(triage.sample_for_audit(d, rng=AlwaysDraw()))

    def test_audit_sampling_fires_on_auto_within_the_rate(self):
        d = gtd.Decision(gtd.AUTO, "project", 0.95, "bucket")

        class Draw(object):
            def __init__(self, v):
                self.v = v

            def random(self):
                return self.v
        self.assertTrue(triage.sample_for_audit(d, rng=Draw(0.0)))
        self.assertFalse(triage.sample_for_audit(d, rng=Draw(0.99)))

    def test_audit_rate_is_nonzero(self):
        # A warm band that stops being adjudicated can never be corrected downward.
        self.assertGreater(triage.AUDIT_SAMPLE_RATE, 0.0)

    # -- the log --------------------------------------------------------
    def test_log_round_trips(self):
        p = triage.propose("有空想學日文", self.c, layer=self.b, kb_index_path="")
        triage.resolve(self.b, p, "bucket", "someday", log_path=self.log, save=False)
        rows = triage.load_log(self.log)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["chosen"], "someday")
        self.assertIn("at", rows[0])

    def test_log_is_append_only(self):
        p = triage.propose("有空想學日文", self.c, layer=self.b, kb_index_path="")
        for _ in range(3):
            triage.resolve(self.b, p, "bucket", "someday", log_path=self.log, save=False)
        self.assertEqual(len(triage.load_log(self.log)), 3)

    def test_malformed_log_line_is_skipped_not_fatal(self):
        with open(self.log, "w", encoding="utf-8") as fh:
            fh.write('{"question": "bucket", "agreed": true}\n')
            fh.write("{ not json\n")
            fh.write('{"question": "bucket", "agreed": false}\n')
        self.assertEqual(len(triage.load_log(self.log)), 2)

    def test_capture_text_can_be_withheld_from_the_log(self):
        p = triage.propose("病人 X 的追蹤", self.c, layer=self.b, kb_index_path="")
        triage.resolve(self.b, p, "bucket", "next_action", log_path=self.log,
                       save=False, include_text=False)
        self.assertEqual(triage.load_log(self.log)[0]["text"], "")

    def test_summarize_log_reports_agreement_rate(self):
        p = triage.propose("有空想學日文", self.c, layer=self.b, kb_index_path="")
        proposed = p.decisions["bucket"].label
        other = "project" if proposed != "project" else "reference"
        for chosen in (proposed, proposed, other):
            triage.resolve(self.b, p, "bucket", chosen, log_path=self.log, save=False)
        s = triage.summarize_log(self.log)
        self.assertEqual(s["bucket"]["total"], 3)
        self.assertEqual(s["bucket"]["agreed"], 2)
        self.assertAlmostEqual(s["bucket"]["rate"], 2.0 / 3.0)

    # -- the unlock gate ------------------------------------------------
    def test_filing_is_locked_before_the_tasks_layer(self):
        start = datetime.date(2026, 9, 29)
        self.assertFalse(triage.filing_allowed(self.c, start))
        self.assertFalse(triage.filing_allowed(self.c, start + datetime.timedelta(days=89)))

    def test_filing_unlocks_on_day_91(self):
        start = datetime.date(2026, 9, 29)
        self.assertTrue(triage.filing_allowed(self.c, start + datetime.timedelta(days=90)))
        self.assertFalse(triage.filing_allowed(self.c, start + datetime.timedelta(days=90),
                                               consistency=0.4),
                         "the day alone is not enough when the journal is below 80%")

    def test_shadow_mode_still_records(self):
        # The point of the locked month: labelling is safe from day 1.
        p = triage.propose("重構儀表板，然後接著寫測試", self.c, layer=self.b, kb_index_path="")
        triage.resolve(self.b, p, "bucket", "project", log_path=self.log, save=False)
        self.assertEqual(self.cal.observations("bucket"), 1)

    # -- the whole point ------------------------------------------------
    def test_resolution_loop_closes_and_the_layer_graduates(self):
        """Cold -> escalates -> human resolves -> warms -> files without asking."""
        text = "重構 Life OS 儀表板，然後接著寫測試"

        first = triage.propose(text, self.c, layer=self.b, kb_index_path="")
        self.assertEqual(first.decisions["bucket"].verdict, gtd.ASK)
        truth = first.decisions["bucket"].label

        for _ in range(calibration.MIN_OBSERVATIONS):
            p = triage.propose(text, self.c, layer=self.b, kb_index_path="")
            triage.resolve(self.b, p, "bucket", truth, log_path=self.log, save=False)

        after = triage.propose(text, self.c, layer=self.b, kb_index_path="")
        self.assertEqual(after.decisions["bucket"].verdict, gtd.AUTO,
                         "after consistent agreement the band must stop asking")
        # Only `bucket` was warmed, so the other questions correctly still ask —
        # each question calibrates separately, and an easy one must not graduate a hard one.
        still_asked = after.questions_for_human(rng=_NeverDraw())
        self.assertNotIn("bucket", still_asked,
                         "the graduated question must stop being put to a human")
        self.assertIn("folder", still_asked,
                      "a question with no observations of its own must still ask")

    def test_a_band_the_user_keeps_correcting_never_graduates(self):
        text = "重構 Life OS 儀表板，然後接著寫測試"
        for i in range(40):
            p = triage.propose(text, self.c, layer=self.b, kb_index_path="")
            proposed = p.decisions["bucket"].label
            chosen = proposed if i % 4 == 0 else "reference"
            triage.resolve(self.b, p, "bucket", chosen, log_path=self.log, save=False)
        after = triage.propose(text, self.c, layer=self.b, kb_index_path="")
        self.assertEqual(after.decisions["bucket"].verdict, gtd.ASK,
                         "a proposal the user keeps overriding must keep asking")


class _NeverDraw(object):
    def random(self):
        return 1.0


if __name__ == "__main__":
    unittest.main(verbosity=2)
