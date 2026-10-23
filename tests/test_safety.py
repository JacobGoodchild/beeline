import inspect
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from beeline import safety  # noqa: E402
from beeline.clock import FakeClock  # noqa: E402
from beeline.safety import (  # noqa: E402
    ALLOWED_KEYS, BLOCKED_EXAMPLES, EmergencyStop, InputRefused, RecordingBackend,
    SafeInput, SafeZone, SprinklerGuard, XdotoolBackend,
)


def make_input(**kw):
    backend = RecordingBackend()
    inp = SafeInput(backend, clock=FakeClock(), **kw)
    return inp, backend


class KeyAllowlistTests(unittest.TestCase):
    def test_allowlist_is_exactly_the_brief(self):
        self.assertEqual(set(ALLOWED_KEYS), {"w", "a", "s", "d", "space", "e", "shift", ",", ".", "i", "o"})

    def test_allowed_keys_work(self):
        inp, backend = make_input()
        for k in ALLOWED_KEYS:
            inp.tap(k)
        self.assertEqual(len(backend.keys_pressed()), len(ALLOWED_KEYS))

    def test_blocked_keys_are_refused_by_every_method(self):
        for k in BLOCKED_EXAMPLES + ["", " ", "ww", "Shift_L", "comma", None, 2, "2 "]:
            inp, backend = make_input()
            for method in (inp.key_down, inp.key_up, inp.tap):
                with self.assertRaises(InputRefused, msg="%r via %s" % (k, method.__name__)):
                    method(k)
            with self.assertRaises(InputRefused):
                inp.hold(k, 1.0)
            self.assertEqual(backend.events, [], "nothing at all may be sent for %r" % (k,))

    def test_every_number_key_blocked(self):
        inp, backend = make_input()
        for n in "1234567890":
            with self.assertRaises(InputRefused):
                inp.tap(n)
        self.assertEqual(backend.events, [])

    def test_backend_double_checks_allowlist(self):
        backend = RecordingBackend()
        for keysym in ["Escape", "Return", "r", "slash", "Tab", "grave", "1", "2", "3", "0"]:
            with self.assertRaises(InputRefused):
                backend.key_down(keysym)
            with self.assertRaises(InputRefused):
                backend.key_up(keysym)
        self.assertEqual(backend.events, [])

    def test_backend_refuses_2_with_wrong_token(self):
        backend = RecordingBackend()
        with self.assertRaises(InputRefused):
            backend.key_down("2", token=object())
        with self.assertRaises(InputRefused):
            backend.key_down("2", token=True)

    def test_xdotool_backend_refuses_main_desktop(self):
        for d in ("", ":0", ":0.0", None):
            with self.assertRaises(InputRefused):
                XdotoolBackend(d)

    def test_no_code_outside_safety_sends_keys_directly(self):
        """Only safety.py may call backend.key_down/key_up or xdotool key commands."""
        pkg = os.path.join(os.path.dirname(__file__), "..", "beeline")
        offenders = []
        for fn in os.listdir(pkg):
            if not fn.endswith(".py") or fn == "safety.py":
                continue
            with open(os.path.join(pkg, fn)) as f:
                src = f.read()
            if re.search(r"backend\.key_(down|up)|_SPRINKLER_TOKEN|_SPRINKLER_KEYSYM", src):
                offenders.append(fn)
            if re.search(r"""["'](key|keydown|keyup|type)["']""", src) and "xdotool" in src:
                offenders.append(fn + " (xdotool key command)")
        self.assertEqual(offenders, [])


class SafeZoneTests(unittest.TestCase):
    def test_default_zone_avoids_left_panel_hotbar_and_top(self):
        z = SafeZone()
        self.assertGreaterEqual(z.left, SafeZone.HARD_LEFT)
        self.assertLessEqual(z.bottom, SafeZone.HARD_BOTTOM)
        self.assertGreaterEqual(z.top, SafeZone.HARD_TOP)

    def test_zone_can_never_be_expanded_past_hard_limits(self):
        z = SafeZone(0.0, 0.0, 1.0, 1.0)
        self.assertEqual((z.left, z.top, z.right, z.bottom),
                         (SafeZone.HARD_LEFT, SafeZone.HARD_TOP, SafeZone.HARD_RIGHT, SafeZone.HARD_BOTTOM))
        z2 = SafeZone.from_dict({"left": -5, "top": -1, "right": 9, "bottom": 9})
        self.assertGreaterEqual(z2.left, SafeZone.HARD_LEFT)
        self.assertLessEqual(z2.bottom, SafeZone.HARD_BOTTOM)

    def test_tiny_or_broken_zone_falls_back_to_default(self):
        z = SafeZone(0.5, 0.5, 0.5, 0.5)
        self.assertEqual(z.to_dict(), SafeZone().to_dict())

    def test_clicks_outside_zone_refused(self):
        inp, backend = make_input()
        w, h = 1280, 720
        bad_points = [
            (10, 360),        # inventory panel, far left
            (200, 300),       # left side
            (640, 700),       # bottom hotbar
            (640, 650),       # just above hotbar (outside default zone)
            (640, 10),        # top bar
            (1270, 360),      # far right
            (-5, -5), (5000, 5000),
        ]
        for (x, y) in bad_points:
            for fn in (inp.click, inp.mouse_down, inp.move_mouse):
                with self.assertRaises(InputRefused, msg="%s at %r" % (fn.__name__, (x, y))):
                    fn(x, y)
        self.assertEqual(backend.events, [])
        cx, cy = inp.zone.centre(w, h)
        inp.click(cx, cy)
        self.assertIn(("mouse_down",), backend.events)

    def test_even_max_zone_never_reaches_left_panel_or_hotbar(self):
        inp, backend = make_input(zone=SafeZone(0, 0, 1, 1))
        with self.assertRaises(InputRefused):
            inp.click(int(0.2 * 1280), 360)
        with self.assertRaises(InputRefused):
            inp.click(640, int(0.85 * 720))


class StopTests(unittest.TestCase):
    def test_release_all_releases_everything(self):
        inp, backend = make_input()
        inp.key_down("w")
        inp.key_down("shift")
        inp.mouse_down(640, 360)
        backend.events.clear()
        inp.release_all()
        released = {k for (a, *rest) in backend.events if a == "keyup" for k in rest}
        self.assertTrue(set(ALLOWED_KEYS.values()) <= released)
        self.assertIn(("mouse_up",), backend.events)
        self.assertEqual(inp.held_keys(), set())
        self.assertFalse(inp.mouse_held)

    def test_emergency_stop_blocks_all_further_input(self):
        inp, backend = make_input()
        inp.key_down("w")
        inp.emergency_stop()
        backend.events.clear()
        for fn, args in ((inp.key_down, ("a",)), (inp.tap, ("e",)), (inp.click, (640, 360)),
                         (inp.mouse_down, (640, 360)), (inp.sleep, (1,))):
            with self.assertRaises(EmergencyStop):
                fn(*args)
        self.assertFalse([e for e in backend.events if e[0] in ("keydown", "mouse_down")])

    def test_hold_releases_key_when_stopped_midway(self):
        inp, backend = make_input()

        def stop_soon(_s):
            if inp.clock.now() > 1002:
                inp.stop_event.set()
        inp.clock.on_sleep = stop_soon
        with self.assertRaises(EmergencyStop):
            inp.hold("w", 10)
        self.assertEqual(backend.events[-1], ("keyup", "w"))
        self.assertEqual(inp.held_keys(), set())


class SprinklerGuardTests(unittest.TestCase):
    def guard(self, retry=False):
        inp, backend = make_input()
        return SprinklerGuard(inp, allow_retry=retry), inp, backend

    @staticmethod
    def presses_of_2(backend):
        return [e for e in backend.events if e == ("keydown", "2")]

    def test_places_once_when_all_conditions_true(self):
        g, inp, b = self.guard()
        self.assertTrue(g.place_sprinkler(grind_start=True, confirm_in_field=lambda: True,
                                          saturator_visible=lambda: False))
        self.assertEqual(len(self.presses_of_2(b)), 1)
        self.assertEqual(b.events[-1], ("keyup", "2"))

    def test_cannot_send_2_twice(self):
        for seen in (True, False):
            g, inp, b = self.guard(retry=False)
            g.place_sprinkler(grind_start=True, confirm_in_field=lambda: True, saturator_visible=lambda: False)
            g.report_result(seen=seen)
            with self.assertRaises(InputRefused):
                g.place_sprinkler(grind_start=True, confirm_in_field=lambda: True,
                                  saturator_visible=lambda: False)
            self.assertEqual(len(self.presses_of_2(b)), 1)

    def test_retry_setting_allows_at_most_one_retry_and_only_after_visible_failure(self):
        g, inp, b = self.guard(retry=True)
        ok = dict(grind_start=True, confirm_in_field=lambda: True, saturator_visible=lambda: False)
        g.place_sprinkler(**ok)
        # no result reported yet -> no retry
        with self.assertRaises(InputRefused):
            g.place_sprinkler(**ok)
        g.report_result(seen=False)
        g.place_sprinkler(**ok)
        g.report_result(seen=False)
        with self.assertRaises(InputRefused):
            g.place_sprinkler(**ok)
        self.assertEqual(len(self.presses_of_2(b)), 2)

    def test_retry_not_allowed_after_success(self):
        g, inp, b = self.guard(retry=True)
        ok = dict(grind_start=True, confirm_in_field=lambda: True, saturator_visible=lambda: False)
        g.place_sprinkler(**ok)
        g.report_result(seen=True)
        with self.assertRaises(InputRefused):
            g.place_sprinkler(**ok)
        self.assertEqual(len(self.presses_of_2(b)), 1)

    def test_cannot_send_2_outside_field(self):
        g, inp, b = self.guard()
        with self.assertRaises(InputRefused):
            g.place_sprinkler(grind_start=True, confirm_in_field=lambda: False, saturator_visible=lambda: False)
        self.assertEqual(b.events, [])

    def test_cannot_send_2_when_not_grind_start(self):
        g, inp, b = self.guard()
        with self.assertRaises(InputRefused):
            g.place_sprinkler(grind_start=False, confirm_in_field=lambda: True, saturator_visible=lambda: False)
        self.assertEqual(b.events, [])

    def test_cannot_send_2_when_saturator_already_visible(self):
        g, inp, b = self.guard()
        with self.assertRaises(InputRefused):
            g.place_sprinkler(grind_start=True, confirm_in_field=lambda: True, saturator_visible=lambda: True)
        self.assertEqual(b.events, [])

    def test_cannot_send_2_after_emergency_stop(self):
        g, inp, b = self.guard()
        inp.emergency_stop()
        b.events.clear()
        with self.assertRaises(EmergencyStop):
            g.place_sprinkler(grind_start=True, confirm_in_field=lambda: True, saturator_visible=lambda: False)
        self.assertEqual(self.presses_of_2(b), [])

    def test_2_cannot_be_sent_through_normal_key_function(self):
        inp, b = make_input()
        for fn in (inp.key_down, inp.tap, inp.key_up):
            with self.assertRaises(InputRefused):
                fn("2")
        self.assertEqual(b.events, [])

    def test_only_place_sprinkler_uses_the_token(self):
        src = inspect.getsource(safety)
        uses = [m.start() for m in re.finditer(r"token=_SPRINKLER_TOKEN", src)]
        place_src = inspect.getsource(SprinklerGuard.place_sprinkler)
        self.assertEqual(len(uses), place_src.count("token=_SPRINKLER_TOKEN"))
        self.assertEqual(len(uses), 2)  # one key_down, one key_up


if __name__ == "__main__":
    unittest.main()
