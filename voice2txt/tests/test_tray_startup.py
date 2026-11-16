import importlib.util
import struct
import unittest
from pathlib import Path

from voice2txt import startup, tray

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('make_icon', ROOT / 'scripts' / 'make_icon.py')
make_icon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(make_icon)


def parse_ico(data):
    reserved, kind, count = struct.unpack_from('<HHH', data, 0)
    entries = []
    for i in range(count):
        w, h, colors, res, planes, bpp, size, offset = struct.unpack_from('<BBBBHHII', data, 6 + 16 * i)
        entries.append((w, h, planes, bpp, size, offset))
    return reserved, kind, entries


class StartupCommandTests(unittest.TestCase):
    def test_frozen_command_quotes_exe(self):
        self.assertEqual(startup.build_run_command(r'C:\Program Files\Voice2Txt\Voice2Txt.exe', True),
                         r'"C:\Program Files\Voice2Txt\Voice2Txt.exe" --minimized')

    def test_source_command_uses_python_and_script(self):
        command = startup.build_run_command(r'C:\Py\pythonw.exe', False, r'D:\2026 Voice2Txt\run_desktop.py')
        self.assertEqual(command, r'"C:\Py\pythonw.exe" "D:\2026 Voice2Txt\run_desktop.py" --minimized')

    def test_source_command_default_script_is_run_desktop(self):
        command = startup.build_run_command('python.exe', False)
        self.assertTrue(command.startswith('"python.exe" "'))
        self.assertTrue(command.endswith('run_desktop.py" --minimized'))

    def test_registry_location_is_current_user_run_key(self):
        self.assertEqual(startup.RUN_KEY_PATH, r'Software\Microsoft\Windows\CurrentVersion\Run')
        self.assertEqual(startup.VALUE_NAME, 'Voice2Txt')


class IconTests(unittest.TestCase):
    def test_generated_ico_has_two_valid_images(self):
        data = make_icon.build_ico()
        reserved, kind, entries = parse_ico(data)
        self.assertEqual((reserved, kind, len(entries)), (0, 1, 2))
        self.assertEqual([(e[0], e[1]) for e in entries], [(16, 16), (32, 32)])
        for w, h, planes, bpp, size, offset in entries:
            self.assertEqual((planes, bpp), (1, 32))
            self.assertLessEqual(offset + size, len(data))
            header = struct.unpack_from('<IiiHH', data, offset)
            self.assertEqual(header, (40, w, h * 2, 1, 32))
            mask_bytes = ((w + 31) // 32) * 4 * h
            self.assertEqual(size, 40 + w * h * 4 + mask_bytes)
        self.assertEqual(entries[1][5] + entries[1][4], len(data))

    def test_icon_is_transparent_in_corners_and_opaque_in_center(self):
        data = make_icon.build_ico()
        _, _, entries = parse_ico(data)
        w, h, _, _, _, offset = entries[1]
        pixels = offset + 40

        def alpha(x, y):  # BMP 由下往上
            return data[pixels + ((h - 1 - y) * w + x) * 4 + 3]
        self.assertEqual(alpha(0, 0), 0)
        self.assertEqual(alpha(w // 2, h // 2), 255)

    def test_shipped_icon_matches_generator(self):
        self.assertEqual((ROOT / 'voice2txt' / 'assets' / 'voice2txt.ico').read_bytes(), make_icon.build_ico())


class TrayMenuTests(unittest.TestCase):
    def test_menu_ids_map_to_actions(self):
        self.assertEqual(tray.action_for_menu_id(tray.ID_SHOW), 'show')
        self.assertEqual(tray.action_for_menu_id(tray.ID_TOGGLE), 'toggle')
        self.assertEqual(tray.action_for_menu_id(tray.ID_QUIT), 'quit')

    def test_cancelled_or_unknown_menu_returns_none(self):
        self.assertIsNone(tray.action_for_menu_id(0))
        self.assertIsNone(tray.action_for_menu_id(9999))

    def test_menu_labels_and_unique_ids(self):
        labels = [label for _, _, label in tray.MENU_ITEMS]
        self.assertEqual(labels, ['開啟視窗', '開始・停止錄音', '結束'])
        ids = [i for i, _, _ in tray.MENU_ITEMS]
        self.assertEqual(len(set(ids)), len(ids))


class TaskbarCreatedTests(unittest.TestCase):
    def _icon(self, results):
        icon = tray.TrayIcon(lambda action: None)
        calls = []

        def notify(message):
            calls.append(message)
            return results.get(message, False)
        icon._notify = notify
        return icon, calls

    def test_add_success_does_not_try_modify(self):
        icon, calls = self._icon({tray.NIM_ADD: True})
        self.assertTrue(icon._add())
        self.assertEqual(calls, [tray.NIM_ADD])
        self.assertTrue(icon.added)

    def test_add_failure_falls_back_to_modify_and_stays_added(self):
        icon, calls = self._icon({tray.NIM_ADD: False, tray.NIM_MODIFY: True})
        self.assertTrue(icon._add())
        self.assertEqual(calls, [tray.NIM_ADD, tray.NIM_MODIFY])
        self.assertTrue(icon.added)
        self.assertIsNone(icon.error)

    def test_both_fail_reports_error(self):
        icon, _ = self._icon({})
        self.assertFalse(icon._add())
        self.assertFalse(icon.added)
        self.assertIn('NIM_ADD', icon.error)

    def test_show_message_name_is_registered_name(self):
        self.assertEqual(tray.SHOW_MESSAGE_NAME, 'Voice2TxtShowWindow')


if __name__ == '__main__':
    unittest.main()
