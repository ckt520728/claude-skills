import unittest

from voice2txt.hotkeys import (ComboCapture, MARKER, PushToTalk, TYPELESS_WARNING, combo_name,
                               conflicting_combos, format_combo, paste_decision, parse_combo,
                               liveness_decision, release_held_modifiers, watchdog_due)

RALT, LALT, RSHIFT, LSHIFT, SPACE, A = 0xA5, 0xA4, 0xA1, 0xA0, 0x20, 0x41
DEFAULT = {'dictate': [parse_combo('RightAlt'), parse_combo('Alt+Shift+Space')],
           'translate': [parse_combo('RightAlt+RightShift')]}


def run(machine, steps):
    """steps: (time, vk, is_down) 或 (time, None, None) 代表 tick。回傳 (事件列表, consumed 列表)。"""
    events, consumed = [], []
    for now, vk, down in steps:
        if vk is None:
            events += machine.tick(now)
        else:
            got, used = machine.key(vk, down, now)
            events += got
            consumed.append(used)
    return events, consumed


class HotkeyTests(unittest.TestCase):
    def test_parse_format_round_trip(self):
        combo = parse_combo('RightAlt+RightShift')
        self.assertEqual(combo, (RALT, RSHIFT))
        self.assertEqual(format_combo(combo), 'Right Alt + Right Shift')
        self.assertEqual(parse_combo(format_combo(combo)), combo)
        self.assertEqual(combo_name(combo), 'RightAlt+RightShift')
        for text in ('Alt+Shift+Space', 'F9', 'CapsLock', 'LeftCtrl+A', 'RightCtrl+F12'):
            self.assertEqual(combo_name(parse_combo(text)), text)
            self.assertEqual(parse_combo(format_combo(parse_combo(text))), parse_combo(text))
        with self.assertRaises(ValueError):
            parse_combo('NoSuchKey')
        with self.assertRaises(ValueError):
            parse_combo('')

    def test_hold_to_talk_starts_after_grace_and_stops_on_release(self):
        machine = PushToTalk(DEFAULT)
        events, _ = run(machine, [(0.0, RALT, True), (0.1, None, None), (0.16, None, None), (0.6, RALT, False)])
        self.assertEqual(events, [('start', 'dictate'), ('stop', None)])

    def test_hold_without_longer_combo_starts_immediately(self):
        machine = PushToTalk({'dictate': [parse_combo('F9')]})
        got, _ = machine.key(0x78, True, 0.0)
        self.assertEqual(got, [('start', 'dictate')])
        got, _ = machine.key(0x78, False, 0.5)
        self.assertEqual(got, [('stop', None)])

    def test_tap_toggles_recording_on_and_off(self):
        machine = PushToTalk(DEFAULT)
        events, _ = run(machine, [(0.0, RALT, True), (0.1, RALT, False)])
        self.assertEqual(events, [('start', 'dictate')])  # 在 grace 內放開：立即補送 start，維持錄音
        self.assertTrue(machine.recording)
        events, _ = run(machine, [(2.0, RALT, True), (2.1, RALT, False)])
        self.assertEqual(events, [('stop', None)])
        self.assertFalse(machine.recording)

    def test_tap_longer_than_grace_but_shorter_than_hold_stays_on(self):
        machine = PushToTalk(DEFAULT)
        events, _ = run(machine, [(0.0, RALT, True), (0.16, None, None), (0.3, RALT, False)])
        self.assertEqual(events, [('start', 'dictate')])
        self.assertTrue(machine.recording)

    def test_longer_combo_wins_over_prefix(self):
        machine = PushToTalk(DEFAULT)
        events, _ = run(machine, [(0.0, RALT, True), (0.05, RSHIFT, True), (0.2, None, None),
                                  (0.7, RSHIFT, False), (0.72, RALT, False)])
        self.assertEqual(events, [('start', 'translate'), ('stop', None)])

    def test_prefix_grace_expiry_then_second_key_does_not_retrigger(self):
        machine = PushToTalk(DEFAULT)
        events, _ = run(machine, [(0.0, RALT, True), (0.2, None, None), (0.3, RSHIFT, True),
                                  (0.6, RSHIFT, False), (0.8, RALT, False)])
        # RightAlt 已先於 grace 後啟動；其後加按 Shift 不會另起一次，放開 RightAlt 時才停止。
        self.assertEqual(events, [('start', 'dictate'), ('stop', None)])

    def test_auto_repeat_and_unrelated_keys_are_ignored(self):
        machine = PushToTalk(DEFAULT)
        run(machine, [(0.0, RALT, True), (0.2, None, None)])
        events, consumed = run(machine, [(0.3, RALT, True), (0.4, RALT, True), (0.45, A, True), (0.5, A, False)])
        self.assertEqual(events, [])
        self.assertEqual(consumed, [True, True, False, False])
        events, _ = run(machine, [(0.6, RALT, False)])
        self.assertEqual(events, [('stop', None)])
        self.assertEqual(run(PushToTalk(DEFAULT), [(0.0, A, True), (0.1, A, False)]), ([], [False, False]))

    def test_unrelated_key_held_blocks_start(self):
        machine = PushToTalk(DEFAULT)
        events, _ = run(machine, [(0.0, A, True), (0.1, RALT, True), (0.5, None, None), (0.6, RALT, False)])
        self.assertEqual(events, [])

    def test_generic_alt_matches_either_side(self):
        for alt in (LALT, RALT):
            machine = PushToTalk({'dictate': [parse_combo('Alt+Shift+Space')]})
            events, _ = run(machine, [(0.0, alt, True), (0.05, LSHIFT, True), (0.1, SPACE, True),
                                      (0.9, SPACE, False)])
            self.assertEqual(events, [('start', 'dictate'), ('stop', None)], alt)
        machine = PushToTalk(DEFAULT)  # 只按 Alt+Shift（切換輸入法）不應觸發任何動作
        events, _ = run(machine, [(0.0, LALT, True), (0.05, LSHIFT, True), (0.5, None, None),
                                  (0.6, LSHIFT, False), (0.7, LALT, False)])
        self.assertEqual(events, [])

    def test_legacy_combo_works_alongside_default(self):
        machine = PushToTalk(DEFAULT)
        events, _ = run(machine, [(0.0, LALT, True), (0.1, LSHIFT, True), (0.2, SPACE, True), (0.25, SPACE, False)])
        self.assertEqual(events, [('start', 'dictate')])  # 短按 -> 維持錄音

    def test_consumed_flag_for_bare_alt(self):
        machine = PushToTalk(DEFAULT)
        _, consumed = run(machine, [(0.0, RALT, True), (0.3, RALT, False)])
        self.assertEqual(consumed, [True, True])

    def test_max_two_combos_per_action(self):
        with self.assertRaises(ValueError):
            PushToTalk({'dictate': [parse_combo('F8'), parse_combo('F9'), parse_combo('F10')]})
        machine = PushToTalk({'dictate': [parse_combo('F8'), parse_combo('F9')]})
        machine.key(0x78, True, 0.0)
        self.assertTrue(machine.recording)

    def test_combo_capture_shows_live_and_confirms_on_full_release(self):
        capture = ComboCapture()
        self.assertEqual(capture.key(RALT, True), ('live', (RALT,)))
        self.assertEqual(capture.key(RSHIFT, True), ('live', (RALT, RSHIFT)))
        self.assertEqual(capture.key(RSHIFT, False), ('live', (RALT, RSHIFT)))
        self.assertEqual(capture.key(RALT, False), ('done', (RALT, RSHIFT)))


F8, F9, F10, LCTRL = 0x77, 0x78, 0x79, 0xA2


class SessionAndRecoveryTests(unittest.TestCase):
    def test_reset_keeps_held_keys_so_auto_repeat_after_stop_is_not_a_new_press(self):
        machine = PushToTalk(DEFAULT)
        events, _ = run(machine, [(0.0, RALT, True), (0.1, RALT, False)])
        self.assertEqual(events, [('start', 'dictate')])  # tap 開始
        events, _ = run(machine, [(2.0, RALT, True), (2.2, None, None)])
        self.assertEqual(events, [('stop', None)])        # 長按到 grace 後停止
        machine.reset()                                   # desktop.stop() 會呼叫
        self.assertEqual(machine.held_keys(), frozenset({RALT}))
        events, _ = run(machine, [(2.4, RALT, True), (2.6, RALT, True), (2.8, RALT, True), (3.0, None, None)])
        self.assertEqual(events, [])                      # auto-repeat 不是新的按下
        self.assertFalse(machine.recording)
        events, _ = run(machine, [(3.2, RALT, False)])
        self.assertEqual(events, [])
        self.assertEqual(machine.held_keys(), frozenset())
        events, _ = run(machine, [(4.0, RALT, True), (4.2, None, None)])
        self.assertEqual(events, [('start', 'dictate')])  # 放開後的下一次按下才是新的開始

    def test_held_keys_accessor_tracks_relevant_keys_only(self):
        machine = PushToTalk(DEFAULT)
        self.assertEqual(machine.held_keys(), frozenset())
        run(machine, [(0.0, RALT, True), (0.05, A, True)])
        self.assertEqual(machine.held_keys(), frozenset({RALT}))
        run(machine, [(0.1, RALT, False), (0.2, A, False)])
        self.assertEqual(machine.held_keys(), frozenset())

    def test_only_the_combo_that_started_the_session_can_stop_it_by_tap(self):
        machine = PushToTalk({'dictate': [parse_combo('F8'), parse_combo('F9')], 'translate': [parse_combo('F10')]})
        events, _ = run(machine, [(0.0, F8, True), (0.1, F8, False)])
        self.assertEqual(events, [('start', 'dictate')])
        events, _ = run(machine, [(1.0, F9, True), (1.1, F9, False)])    # 同動作的另一組合
        self.assertEqual(events, [])
        events, _ = run(machine, [(2.0, F10, True), (2.1, F10, False)])  # 翻譯組合
        self.assertEqual(events, [])
        self.assertTrue(machine.recording)
        events, _ = run(machine, [(3.0, F8, True), (3.1, F8, False)])
        self.assertEqual(events, [('stop', None)])
        self.assertFalse(machine.recording)

    def test_long_press_of_another_combo_does_not_stop_the_session(self):
        machine = PushToTalk({'dictate': [parse_combo('F8')], 'translate': [parse_combo('F9')]})
        events, _ = run(machine, [(0.0, F8, True), (0.1, F8, False)])
        self.assertEqual(events, [('start', 'dictate')])
        events, _ = run(machine, [(1.0, F9, True), (2.0, F9, False)])
        self.assertEqual(events, [])
        self.assertTrue(machine.recording)

    def test_recording_started_by_button_can_be_stopped_by_any_configured_combo_tap(self):
        for combo in (F8, F9, F10):
            machine = PushToTalk({'dictate': [parse_combo('F8'), parse_combo('F9')], 'translate': [parse_combo('F10')]})
            machine.set_recording(True)  # 錄音按鈕開始
            events, _ = run(machine, [(0.0, combo, True), (0.1, combo, False)])
            self.assertEqual(events, [('stop', None)], hex(combo))
            self.assertFalse(machine.recording)

    def test_missed_key_up_is_recovered_from_physical_state_on_tick(self):
        physical = {F9: True}
        machine = PushToTalk({'dictate': [parse_combo('F9')]}, is_physically_down=lambda vk: physical.get(vk, False))
        events, _ = run(machine, [(0.0, F9, True)])
        self.assertEqual(events, [('start', 'dictate')])
        self.assertEqual(run(machine, [(0.05, None, None), (0.5, None, None)])[0], [])  # 實體仍按著：不動
        physical[F9] = False                                                            # key-up 遺失
        self.assertEqual(run(machine, [(0.55, None, None), (1.19, None, None)])[0], [])  # 未滿 1.2 s 無任何 key-down：先不動
        self.assertEqual(run(machine, [(1.21, None, None)])[0], [('stop', None)])
        self.assertEqual(machine.recovered, [F9])
        self.assertEqual(machine.held_keys(), frozenset())
        physical[F9] = True
        # 補做 key-up 之後超過 1.5 s 才出現的 key-down 是新的按下。
        self.assertEqual(run(machine, [(3.0, F9, True)])[0], [('start', 'dictate')])

    def test_genuine_missed_key_up_without_repeats_recovers_after_1_2_seconds(self):
        physical = {F9: True}
        machine = PushToTalk({'dictate': [parse_combo('F9')]}, is_physically_down=lambda vk: physical.get(vk, False))
        run(machine, [(0.0, F9, True), (0.02, None, None)])      # tick 觀察到實體按下過
        physical[F9] = False                                      # 之後實體放開、key-up 遺失、沒有 repeat
        ticks = [(0.02 * i, None, None) for i in range(1, 70)]   # 到 1.38 s，每 20 ms 一次
        events, _ = run(machine, ticks)
        self.assertEqual(events, [('stop', None)])
        self.assertEqual(machine.recovered, [F9])
        self.assertEqual(machine.held_keys(), frozenset())

    def test_swallowed_key_hold_with_auto_repeat_is_one_start_and_one_stop(self):
        # 稽核 C2 情境：下游 hook 吞掉設定鍵 -> GetAsyncKeyState 永遠說放開；auto-repeat 每 33 ms 到達本 hook。
        for combo in (F9, RALT):
            machine = PushToTalk(DEFAULT if combo == RALT else {'dictate': [parse_combo('F9')]},
                                 is_physically_down=lambda vk: False)
            steps = [(0.0, combo, True)]
            t = 0.0
            while t < 1.5:
                t = round(t + 0.033, 3)
                steps.append((t, combo, True))        # auto-repeat key-down
                steps.append((t + 0.001, None, None))  # tick
            events, _ = run(machine, steps)
            self.assertEqual(events, [('start', 'dictate')], hex(combo))
            self.assertEqual(machine.recovered, [], hex(combo))
            events, _ = run(machine, [(1.6, combo, False)])
            self.assertEqual(events, [('stop', None)], hex(combo))
            self.assertFalse(machine.recording)

    def test_key_down_shortly_after_a_sync_drop_is_a_continuation_not_a_new_press(self):
        physical = {F9: True}
        machine = PushToTalk({'dictate': [parse_combo('F9')]}, is_physically_down=lambda vk: physical.get(vk, False))
        run(machine, [(0.0, F9, True), (0.02, None, None)])
        physical[F9] = False
        self.assertEqual(run(machine, [(1.3, None, None)])[0], [('stop', None)])  # 靜默超過 1.2 s -> 補做 key-up
        events, _ = run(machine, [(1.8, F9, True), (1.83, F9, True)])  # 1.5 s 內的 key-down：放回按住集合，不再 start
        self.assertEqual(events, [])
        self.assertEqual(machine.held_keys(), frozenset({F9}))
        self.assertEqual(run(machine, [(2.0, F9, False)])[0], [])  # 真正放開：不再 stop（早已停止）
        self.assertEqual(machine.held_keys(), frozenset())
        self.assertEqual(run(machine, [(2.2, F9, True)])[0], [('start', 'dictate')])  # 真正的新按下

    def test_never_physically_seen_key_is_never_dropped_even_without_repeats(self):
        # 單鍵被下游 hook 吞掉、且沒有 auto-repeat：從未被觀察到實體按下 -> 不補做 key-up。
        machine = PushToTalk({'dictate': [parse_combo('F9')]}, is_physically_down=lambda vk: False)
        run(machine, [(0.0, F9, True)])
        events, _ = run(machine, [(0.02 * i, None, None) for i in range(1, 400)])  # 到 8 s
        self.assertEqual(events, [])
        self.assertEqual(machine.recovered, [])
        self.assertEqual(machine.held_keys(), frozenset({F9}))
        self.assertEqual(run(machine, [(8.1, F9, False)])[0], [('stop', None)])

    def test_swallowed_right_alt_with_repeating_right_shift_is_one_start_translate_held_3_seconds(self):
        # 稽核 C3 major 1：RightAlt 被吞（實體狀態永遠放開），RightShift 實體按著並持續 auto-repeat。
        physical = {RSHIFT: True}                       # RALT 永遠 False
        machine = PushToTalk(DEFAULT, is_physically_down=lambda vk: physical.get(vk, False))
        steps = [(0.0, RALT, True), (0.01, RSHIFT, True)]
        t = 0.01
        while t < 3.0:
            t = round(t + 0.033, 3)
            steps.append((t, RSHIFT, True))             # RightShift auto-repeat
            steps.append((t + 0.001, None, None))
        events, _ = run(machine, steps)
        self.assertEqual(events, [('start', 'translate')])   # 3 s 內沒有 stop、沒有第二個 start
        self.assertEqual(machine.recovered, [])
        self.assertEqual(machine.held_keys(), frozenset({RALT, RSHIFT}))
        physical[RSHIFT] = False
        events, _ = run(machine, [(3.1, RSHIFT, False), (3.12, RALT, False)])
        self.assertEqual(events, [('stop', None)])           # 真正放開時才 stop
        self.assertFalse(machine.recording)

    def test_key_seen_physically_down_is_still_dropped_when_other_key_swallowed(self):
        physical = {RSHIFT: True}
        machine = PushToTalk(DEFAULT, is_physically_down=lambda vk: physical.get(vk, False))
        run(machine, [(0.0, RALT, True), (0.01, RSHIFT, True), (0.03, None, None)])
        physical[RSHIFT] = False                            # RightShift 的 key-up 遺失；RightAlt 仍是吞掉的
        events, _ = run(machine, [(0.05 * i, None, None) for i in range(1, 40)])
        self.assertIn(RSHIFT, machine.recovered)
        self.assertNotIn(RALT, machine.recovered)

    def test_physical_check_waits_for_a_short_settle_time(self):
        machine = PushToTalk({'dictate': [parse_combo('F9')]}, is_physically_down=lambda vk: False)
        run(machine, [(0.0, F9, True)])
        self.assertEqual(run(machine, [(0.05, None, None), (1.0, None, None)])[0], [])
        self.assertEqual(machine.held_keys(), frozenset({F9}))

    def test_set_combos_keeps_held_keys_reclassified(self):
        machine = PushToTalk({'dictate': [parse_combo('F9')]})
        run(machine, [(0.0, F9, True)])
        machine.set_combos({'dictate': [parse_combo('F8')]})
        self.assertEqual(machine.held_keys(), frozenset())  # F9 不再相關
        self.assertTrue(machine.any_held())
        events, _ = run(machine, [(0.5, F9, True)])         # 仍視為按住（auto-repeat），不觸發
        self.assertEqual(events, [])


class DecisionFunctionTests(unittest.TestCase):
    def test_paste_decision_defers_while_any_hotkey_key_is_held(self):
        self.assertEqual(paste_decision(0, frozenset()), 'none')
        self.assertEqual(paste_decision(0, frozenset({RALT})), 'none')
        self.assertEqual(paste_decision(1, frozenset({RALT})), 'defer')
        self.assertEqual(paste_decision(3, {LALT, LSHIFT}), 'defer')
        self.assertEqual(paste_decision(1, frozenset()), 'now')
        self.assertEqual(paste_decision(2, ()), 'now')

    def test_watchdog_due_only_when_keys_held_and_callbacks_silent(self):
        self.assertFalse(watchdog_due(100.0, 95.0, True))
        self.assertTrue(watchdog_due(100.0, 90.0, True))
        self.assertFalse(watchdog_due(100.0, 50.0, False))
        self.assertTrue(watchdog_due(10.0, 9.0, True, timeout=1.0))

    def test_conflicting_combos_flags_right_alt_when_typeless_runs(self):
        combos = [parse_combo('RightAlt'), parse_combo('Alt+Shift+Space'), parse_combo('RightAlt+RightShift'),
                  parse_combo('LeftAlt'), parse_combo('F9')]
        running = ['explorer.exe', 'Typeless.exe']
        self.assertEqual(conflicting_combos(running, combos), [(RALT,), (RALT, RSHIFT)])
        self.assertEqual(conflicting_combos(['typeless.EXE'], [parse_combo('RightAlt')]), [(RALT,)])
        self.assertEqual(conflicting_combos(running, [parse_combo('LeftAlt'), parse_combo('Alt+Shift+Space')]), [])
        self.assertEqual(conflicting_combos(['explorer.exe', 'python.exe'], combos), [])
        self.assertEqual(conflicting_combos([], combos), [])
        self.assertIn('Typeless', TYPELESS_WARNING)
        self.assertIn('Right Alt', TYPELESS_WARNING)

    def test_release_held_modifiers_sends_marked_key_ups_for_held_modifiers_only(self):
        sent = []
        released = release_held_modifiers(is_down=lambda vk: vk in (LALT, LSHIFT, A),
                                          sender=lambda vk, is_up, extra: sent.append((vk, is_up, extra)))
        self.assertEqual(released, [LSHIFT, LALT])
        self.assertEqual(sent, [(LSHIFT, True, MARKER), (0xFF, False, MARKER), (0xFF, True, MARKER),
                                (LALT, True, MARKER)])  # Alt 的 key-up 前先送 no-op
        self.assertEqual(release_held_modifiers(is_down=lambda vk: False, sender=lambda *a: sent.append(a)), [])

    def test_release_held_modifiers_ignores_modifiers_outside_configured_combos(self):
        sent = []
        sender = lambda vk, is_up, extra: sent.append((vk, is_up, extra))
        keys = PushToTalk({'dictate': [parse_combo('LeftAlt')]}).relevant_keys()
        released = release_held_modifiers(is_down=lambda vk: vk in (LALT, LSHIFT), sender=sender, keys=keys)
        self.assertEqual(released, [LALT])                       # 無關的 Shift 沒有被放開
        self.assertNotIn(LSHIFT, [vk for vk, _, _ in sent])
        sent.clear()
        self.assertEqual(release_held_modifiers(is_down=lambda vk: vk == LSHIFT, sender=sender, keys=keys), [])
        self.assertEqual(sent, [])
        # 泛用 Alt+Shift+Space 代表左右兩側都屬於快捷鍵
        generic = PushToTalk(DEFAULT).relevant_keys()
        released = release_held_modifiers(is_down=lambda vk: vk in (LSHIFT, RSHIFT, LALT, 0xA2),
                                          sender=sender, keys=generic)
        self.assertEqual(released, [LSHIFT, RSHIFT, LALT])       # Left Ctrl 不在任何組合內

    def test_liveness_decision_is_independent_of_held_keys(self):
        # last_user_input=now-1：使用者活躍
        self.assertEqual(liveness_decision(5.0, 0.0, None, False, 4.0), 'ok')      # 活躍但 callback 還新（未滿 interval）
        self.assertEqual(liveness_decision(10.0, 0.0, None, False, 9.0), 'probe')
        self.assertEqual(liveness_decision(10.05, 0.0, 10.0, False, 10.0), 'wait')
        self.assertEqual(liveness_decision(10.14, 0.0, 10.0, False, 10.0), 'wait')
        self.assertEqual(liveness_decision(10.15, 0.0, 10.0, False, 10.0), 'reinstall')
        self.assertEqual(liveness_decision(10.2, 0.0, 10.0, True, 10.0), 'ok')
        self.assertEqual(liveness_decision(2.0, 0.0, None, False, 1.5, interval=1.0), 'probe')

    def test_liveness_never_probes_when_user_is_idle(self):
        # 稽核 C3 major 2：注入鍵盤事件會重設系統閒置計時器 -> 使用者閒置時不探測、不重裝。
        for now in (10.0, 60.0, 3600.0):
            self.assertEqual(liveness_decision(now, 0.0, None, False, 0.0), 'idle')
            self.assertEqual(liveness_decision(now, 0.0, None, False, now - 10.0), 'idle')  # 剛好 interval 秒沒輸入
        self.assertEqual(liveness_decision(10.0, 0.0, None, False, float('-inf')), 'idle')
        self.assertEqual(liveness_decision(10.0, 0.0, None, False, 9.0), 'probe')   # 活躍且 callback 超過 interval

    def test_liveness_ok_when_user_active_and_hook_has_callbacks(self):
        self.assertEqual(liveness_decision(10.0, 9.5, None, False, 9.9), 'ok')
        self.assertEqual(liveness_decision(100.0, 99.0, None, False, 99.5), 'ok')

    # ---- 稽核 E D2：Alt+Space 吞鍵規則 --------------------------------------------------------------
    def _ask_machine(self):
        return PushToTalk({'ask': [parse_combo('LeftAlt+Space')], 'dictate': [parse_combo('VK0x86')]})

    def test_swallow_only_for_non_modifier_completing_an_alt_combo(self):
        machine = self._ask_machine()
        self.assertFalse(machine.handle(LALT, True, 0.0)[2])        # 修飾鍵永不吞
        self.assertTrue(machine.handle(SPACE, True, 0.05)[2])       # 完成 Alt+Space -> 吞
        self.assertTrue(machine.handle(SPACE, True, 0.08)[2])       # auto-repeat 也吞
        self.assertTrue(machine.handle(SPACE, False, 0.6)[2])       # 對應的 key-up 也吞
        self.assertFalse(machine.handle(LALT, False, 0.7)[2])       # Alt key-up 不吞

    def test_modifiers_are_never_swallowed_even_in_alt_combo(self):
        for combo, order in (('RightAlt+RightCtrl', (RALT, 0xA3)), ('Alt+Shift+Space', (LALT, LSHIFT, SPACE))):
            machine = PushToTalk({'ask': [parse_combo(combo)]})
            flags = [machine.handle(vk, True, 0.01 * i)[2] for i, vk in enumerate(order)]
            for vk in order:
                if vk in (RALT, LALT, LSHIFT, 0xA3):
                    self.assertFalse(flags[order.index(vk)], (combo, vk))

    def test_bare_space_and_unrelated_keys_are_not_swallowed(self):
        machine = self._ask_machine()
        self.assertFalse(machine.handle(SPACE, True, 0.0)[2])       # 沒有 Alt：Space 照常送出
        self.assertFalse(machine.handle(SPACE, False, 0.1)[2])      # 放行的 key-down 對應的 key-up 也放行
        machine.handle(LALT, True, 1.0)
        self.assertFalse(machine.handle(A, True, 1.05)[2])          # 無關鍵
        self.assertFalse(machine.handle(SPACE, True, 1.1)[2])       # Alt+A+Space 不是已設定組合

    def test_combo_without_alt_is_never_swallowed(self):
        machine = PushToTalk({'translate': [parse_combo('LeftShift+VK0x86')]})
        machine.handle(LSHIFT, True, 0.0)
        self.assertFalse(machine.handle(0x86, True, 0.05)[2])

    def test_take_swallowed_matches_key_up_during_capture(self):
        machine = self._ask_machine()
        machine.handle(LALT, True, 0.0)
        self.assertTrue(machine.handle(SPACE, True, 0.05)[2])
        self.assertTrue(machine.take_swallowed(SPACE))
        self.assertFalse(machine.take_swallowed(SPACE))

    def test_old_ask_default_is_migrated_but_custom_value_is_kept(self):
        from voice2txt.hotkeys import migrate_hotkeys
        defaults = {'ask': ['RightAlt+RightCtrl'], 'dictate': ['RightAlt']}
        self.assertEqual(migrate_hotkeys('ask', ['RightAlt+Space'], defaults), ['RightAlt+RightCtrl'])
        self.assertEqual(migrate_hotkeys('ask', ['LeftAlt+F23'], defaults), ['LeftAlt+F23'])
        self.assertEqual(migrate_hotkeys('ask', ['RightAlt+Space', 'F23'], defaults), ['RightAlt+Space', 'F23'])
        self.assertEqual(migrate_hotkeys('dictate', ['RightAlt+Space'], defaults), ['RightAlt+Space'])

    def test_desktop_default_ask_hotkey_has_no_space(self):
        import voice2txt.desktop as desktop
        self.assertEqual(desktop.DEFAULT_HOTKEYS['ask'], ['RightAlt+RightCtrl'])

    # ---- 稽核 E2 N1/N2/nits ---------------------------------------------------------------------
    def _synthetic_machine(self, physical):
        machine = PushToTalk({'ask': [parse_combo('LeftAlt+VK0x86')]},
                             is_physically_down=lambda vk: physical.get(vk, False))
        events = []
        events += machine.key(LALT, True, 0.0)[0]
        events += machine.key(0x86, True, 0.05)[0]
        events += machine.tick(0.1)                    # 觀察到實體按下
        self.assertEqual(events, [('start', 'ask')])
        return machine

    def test_synthetic_release_keeps_key_held_for_5_seconds_and_stops_only_on_real_key_up(self):
        physical = {LALT: True, 0x86: True}
        machine = self._synthetic_machine(physical)
        physical[LALT] = physical[0x86] = False        # _begin_ask 以 MARKER 合成放開，GetAsyncKeyState 回報放開
        machine.mark_synthetic_release([LALT])
        events = []
        t = 0.1
        while t < 5.0:                                 # F23 持續 auto-repeat；LeftAlt 不再 repeat
            t += 0.033
            events += machine.key(0x86, True, t)[0]
            events += machine.tick(t)
        self.assertEqual(events, [])
        self.assertEqual(machine.recovered, [])
        self.assertIn(LALT, machine.held_keys())
        self.assertEqual(machine.key(0x86, False, 5.1)[0], [('stop', None)])   # 真正的 key-up 才停止
        machine.key(LALT, False, 5.12)
        self.assertEqual(machine.held_keys(), frozenset())

    def test_real_key_down_after_synthetic_release_reenables_physical_sampling(self):
        physical = {LALT: True, 0x86: True}
        machine = self._synthetic_machine(physical)
        physical[LALT] = False
        machine.mark_synthetic_release([LALT])
        run(machine, [(2.0, None, None)])
        self.assertEqual(machine.recovered, [])
        physical[LALT] = True                          # 使用者重新按下（真正的 key-down 到達 hook）
        machine.key(LALT, True, 2.1)
        run(machine, [(2.2, None, None)])              # 取樣：實體按下 -> 恢復校正
        physical[LALT] = False                         # 之後 key-up 遺失
        machine.key(0x86, True, 3.0)
        events, _ = run(machine, [(3.4, None, None)])
        self.assertEqual(machine.recovered, [LALT])

    def test_swallowed_key_with_lost_key_up_is_released_after_repeat_timeout(self):
        machine = self._ask_machine()
        machine.handle(LALT, True, 0.0)
        self.assertTrue(machine.handle(SPACE, True, 0.05)[2])        # 初次 key-down 被吞
        self.assertTrue(machine.handle(SPACE, True, 0.5)[2])         # auto-repeat 持續：不動
        self.assertEqual(machine.tick(1.6), [])                      # 距最後一次 repeat 1.1 s：未逾時
        self.assertIn(SPACE, machine.held_keys())
        machine.tick(1.75)                                  # 逾時 1.25 s 且沒有 key-up -> 視為放開
        self.assertEqual(machine.swallow_released, [SPACE])
        self.assertNotIn(SPACE, machine.held_keys())
        self.assertFalse(machine.take_swallowed(SPACE))              # 吞鍵紀錄已清
        machine.handle(LALT, False, 1.8)
        self.assertFalse(machine.handle(SPACE, True, 5.0)[2])        # 之後單獨按 Space 不會被吞

    def test_swallowed_key_without_repeat_is_never_timed_out(self):
        machine = self._ask_machine()
        machine.handle(LALT, True, 0.0)
        self.assertTrue(machine.handle(SPACE, True, 0.05)[2])        # 吞掉，之後完全沒有 repeat
        for t in (1.5, 3.05, 12.0):
            machine.tick(t)
        self.assertEqual(machine.swallow_released, [])
        self.assertIn(SPACE, machine.held_keys())
        self.assertTrue(machine.handle(SPACE, False, 12.5)[2])       # 真正的 key-up 照常處理並吞掉
        self.assertNotIn(SPACE, machine.held_keys())

    def test_swallowed_key_with_repeats_then_silence_is_released(self):
        machine = self._ask_machine()
        machine.handle(LALT, True, 0.0)
        machine.handle(SPACE, True, 0.05)
        machine.handle(SPACE, True, 0.5)                             # 觀察到 repeat
        machine.tick(1.6)
        self.assertEqual(machine.swallow_released, [])
        machine.tick(1.75)
        self.assertEqual(machine.swallow_released, [SPACE])

    def test_safe_int_coerces_hand_edited_hotkeys_version(self):
        from voice2txt.desktop import _safe_int
        from voice2txt.hotkeys import migrate_hotkeys
        defaults = {'ask': ['RightAlt+RightCtrl']}
        self.assertEqual(_safe_int('2'), 2)
        for bad in ('x', None, [], {}, True):
            self.assertEqual(_safe_int(bad), 1)
        self.assertEqual(migrate_hotkeys('ask', ['RightAlt+Space'], defaults, _safe_int('2')), ['RightAlt+Space'])
        self.assertEqual(migrate_hotkeys('ask', ['RightAlt+Space'], defaults, _safe_int('oops')), ['RightAlt+RightCtrl'])

    def test_hotkeys_version_marker_keeps_deliberate_old_default_after_migration(self):
        from voice2txt.hotkeys import HOTKEYS_VERSION, migrate_hotkeys
        defaults = {'ask': ['RightAlt+RightCtrl']}
        self.assertEqual(HOTKEYS_VERSION, 2)
        self.assertEqual(migrate_hotkeys('ask', ['RightAlt+Space'], defaults, 1), ['RightAlt+RightCtrl'])
        self.assertEqual(migrate_hotkeys('ask', ['RightAlt+Space'], defaults, 2), ['RightAlt+Space'])


    def test_merge_pastes_joins_same_target_in_order(self):
        from voice2txt.desktop import merge_pastes
        pending = [('SEG-ONE', 7), ('X', 9), ('SEG-TWO', 7), ('SEG-THREE', 7)]
        self.assertEqual(merge_pastes(pending), [('SEG-ONE\nSEG-TWO\nSEG-THREE', 7), ('X', 9)])
        self.assertEqual(merge_pastes([]), [])
        self.assertEqual(merge_pastes([('a', 1)]), [('a', 1)])


if __name__ == '__main__':
    unittest.main()
