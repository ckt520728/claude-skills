import sqlite3
import tempfile
import tkinter as tk
import unittest
from datetime import date, timedelta
from pathlib import Path
from tkinter import ttk
from unittest import mock

from voice2txt import insights, theme
from voice2txt.core import MODES, Store

TODAY = date(2026, 11, 13)


def row(days_ago, text, seconds=10, mode='zh'):
    d = TODAY - timedelta(days=days_ago)
    return (d.isoformat() + ' 09:00:00', mode, seconds, text)


class InsightsTests(unittest.TestCase):
    def test_count_words_mixed(self):
        self.assertEqual(insights.count_words('今天開會 meeting at 3pm, don\'t be late'), 4 + 6)
        self.assertEqual(insights.count_words(''), 0)
        self.assertEqual(insights.count_words('，。!?'), 0)

    def test_compute_totals_wpm_and_floor(self):
        r = insights.compute([row(0, 'a b c d e f g h i j', 30, 'en')], TODAY)
        self.assertEqual(r['total_words'], 10)
        self.assertAlmostEqual(r['dictation_wpm'], 20.0)
        self.assertEqual(r['time_saved_seconds'], 0)  # 10/40*60=15 < 30s
        r = insights.compute([row(0, 'x ' * 80, 20)], TODAY)
        self.assertAlmostEqual(r['time_saved_seconds'], 80 / 40 * 60 - 20)
        self.assertEqual(insights.compute([], TODAY)['dictation_wpm'], 0)

    def test_streaks_with_gaps(self):
        rows = [row(d, '你好') for d in (0, 1, 2, 5, 6, 7, 8, 9)]
        r = insights.compute(rows, TODAY)
        self.assertEqual(r['current_streak'], 3)
        self.assertEqual(r['longest_streak'], 5)
        self.assertEqual(r['active_days'], 8)

    def test_streak_today_not_active(self):
        r = insights.compute([row(1, '你好'), row(2, '你好')], TODAY)
        self.assertEqual(r['current_streak'], 2)
        r = insights.compute([row(2, '你好')], TODAY)
        self.assertEqual(r['current_streak'], 0)
        self.assertEqual(r['longest_streak'], 1)

    def test_by_day_window_and_mode(self):
        r = insights.compute([row(0, '你好', mode='en'), row(181, '你好'), row(182, '你好')], TODAY)
        self.assertEqual(len(r['by_day']), 2)
        self.assertNotIn((TODAY - timedelta(days=182)).isoformat(), r['by_day'])
        self.assertEqual(r['total_words'], 6)
        self.assertEqual(r['by_mode'], {'en': 2, 'zh': 4})

    def test_heatmap_levels_and_layout(self):
        by_day = {(TODAY - timedelta(days=i)).isoformat(): w
                  for i, w in enumerate((40, 30, 20, 10))}
        cells = insights.heatmap_cells(by_day, TODAY)
        lv = {c[2]: c[4] for c in cells}
        self.assertEqual([lv[(TODAY - timedelta(days=i)).isoformat()] for i in range(4)], [4, 3, 2, 1])
        self.assertEqual(max(c[0] for c in cells), 25)
        today_cell = [c for c in cells if c[2] == TODAY.isoformat()][0]
        self.assertEqual((today_cell[0], today_cell[1]), (25, TODAY.weekday()))
        self.assertTrue(all(c[2] <= TODAY.isoformat() for c in cells))
        self.assertEqual(sum(1 for c in cells if c[4] == 0), len(cells) - 4)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / 'h.sqlite3'

    def tearDown(self):
        self.dir.cleanup()

    def test_ask_mode_last(self):
        self.assertEqual(MODES['ask'], '隨便問')
        self.assertEqual(list(MODES)[:3], ['zh', 'en', 'translate'])

    def test_old_schema_prune_and_stats(self):
        db = sqlite3.connect(str(self.path))
        db.execute("CREATE TABLE history (id INTEGER PRIMARY KEY, created TEXT DEFAULT "
                   "(datetime('now','localtime')), mode TEXT, text TEXT, seconds REAL)")
        db.execute("INSERT INTO history(created,mode,text,seconds) VALUES "
                   "(datetime('now','localtime','-40 days'),'zh','舊',1)")
        db.execute("INSERT INTO history(mode,text,seconds) VALUES ('en','new',2)")
        db.commit()
        db.close()
        s = Store(self.path)
        self.assertEqual(len(s.rows_for_stats()), 2)
        self.assertEqual(s.prune(None), 0)
        self.assertEqual(s.prune(30), 1)
        rows = s.rows_for_stats()
        self.assertEqual([r[3] for r in rows], ['new'])
        self.assertEqual(len(rows[0]), 4)
        s.close()

    def test_update_text(self):
        s = Store(self.path)
        s.add('zh', 'old', 1.0, 'src')
        rid = s.history()[0][0]
        s.update_text(rid, 'new')
        self.assertEqual(s.history()[0][2], 'new')
        self.assertEqual(s.source(rid), 'src')
        s.close()


class ThemeTests(unittest.TestCase):
    def test_palette_keys(self):
        keys = {'bg', 'panel', 'fg', 'muted', 'accent', 'text_bg', 'text_fg', 'list_bg', 'select_bg'}
        self.assertEqual(set(theme.LIGHT), keys)
        self.assertEqual(set(theme.DARK), keys)

    def test_resolve(self):
        self.assertIs(theme.resolve('淺色'), theme.LIGHT)
        self.assertIs(theme.resolve('深色'), theme.DARK)
        with mock.patch.object(theme, 'system_prefers_dark', return_value=True):
            self.assertIs(theme.resolve('系統'), theme.DARK)
        with mock.patch.object(theme, 'system_prefers_dark', return_value=False):
            self.assertIs(theme.resolve('系統'), theme.LIGHT)

    def test_apply_switches_on_withdrawn_root(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(str(exc))
        root.withdraw()
        try:
            style = ttk.Style(root)
            text, lst, cv = tk.Text(root), tk.Listbox(root), tk.Canvas(root)
            for pal in (theme.LIGHT, theme.DARK, theme.LIGHT):
                theme.apply(style, root, pal, [text, lst, cv])
                self.assertEqual(str(text.cget('bg')), pal['text_bg'])
                self.assertEqual(str(lst.cget('bg')), pal['list_bg'])
                self.assertEqual(style.lookup('TLabel', 'background'), pal['bg'])
        finally:
            root.destroy()


if __name__ == '__main__':
    unittest.main()
