import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from beeline.clock import FakeClock  # noqa: E402
from beeline.routes import Route, RouteRecorder, replay  # noqa: E402
from beeline.safety import EmergencyStop, InputRefused, RecordingBackend, SafeInput  # noqa: E402


class RecorderTests(unittest.TestCase):
    def test_records_allowed_keys_with_timing(self):
        clock = FakeClock()
        rec = RouteRecorder("hive_to_field", 3, clock=clock)
        rec.key("w", True)
        clock.sleep(2.0)
        rec.key("w", True)      # auto-repeat: ignored
        rec.key("d", True)
        clock.sleep(1.0)
        rec.key("w", False)
        rec.key("d", False)
        clock.sleep(0.5)
        r = rec.stop()
        self.assertEqual(r.events, [[0.0, "down", "w"], [2.0, "down", "d"], [3.0, "up", "w"], [3.0, "up", "d"]])
        self.assertEqual(r.duration, 3.5)
        self.assertIn("2 key presses", r.summary())

    def test_blocked_keys_never_recorded(self):
        rec = RouteRecorder("hive_to_field", 1, clock=FakeClock())
        for k in ["1", "2", "Escape", "Return", "r", "slash", "Tab", "q"]:
            self.assertFalse(rec.key(k, True))
        self.assertEqual(rec.stop().events, [])

    def test_keys_still_held_are_released_at_stop(self):
        clock = FakeClock()
        rec = RouteRecorder("field_to_hive", 1, clock=clock)
        rec.key("a", True)
        clock.sleep(1)
        r = rec.stop()
        self.assertEqual(r.events[-1], [1.0, "up", "a"])

    def test_save_load_per_slot(self):
        with tempfile.TemporaryDirectory() as d:
            r = Route("hive_to_field", 4, events=[[0, "down", "w"], [1.5, "up", "w"]], duration=1.5)
            r.save(d)
            self.assertIsNone(Route.load(3, "hive_to_field", d=d))
            back = Route.load(4, "hive_to_field", d=d)
            self.assertEqual(back.events, r.events)

    def test_tampered_route_file_with_blocked_key_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Route.path_for(1, "hive_to_field", d=d)
            with open(p, "w") as f:
                json.dump({"name": "hive_to_field", "slot": 1, "duration": 1,
                           "events": [[0, "down", "Escape"], [1, "up", "Escape"]]}, f)
            with self.assertRaises(InputRefused):
                Route.load(1, "hive_to_field", d=d)


class ReplayTests(unittest.TestCase):
    def test_replay_sends_same_keys_at_same_times(self):
        clock = FakeClock()
        backend = RecordingBackend()
        inp = SafeInput(backend, clock=clock)
        times = []
        backend_key = backend._key

        def spy(action, keysym):
            times.append((round(clock.now() - 1000.0, 2), action, keysym))
            backend_key(action, keysym)
        backend._key = spy
        r = Route("hive_to_field", 1, events=[[0, "down", "w"], [2.0, "down", "d"], [3.0, "up", "w"],
                                              [3.5, "up", "d"]], duration=4.0)
        replay(r, inp)
        self.assertEqual(times, [(0.0, "keydown", "w"), (2.0, "keydown", "d"), (3.0, "keyup", "w"),
                                 (3.5, "keyup", "d")])
        self.assertAlmostEqual(clock.now() - 1000.0, 4.0, places=2)

    def test_replay_releases_keys_on_stop(self):
        clock = FakeClock()
        backend = RecordingBackend()
        inp = SafeInput(backend, clock=clock)
        r = Route("hive_to_field", 1, events=[[0, "down", "w"], [10.0, "up", "w"]], duration=10)

        def check():
            if clock.now() > 1003:
                inp.stop_event.set()
        with self.assertRaises(EmergencyStop):
            replay(r, inp, check=check)
        self.assertEqual(backend.events[-1], ("keyup", "w"))
        self.assertEqual(inp.held_keys(), set())


if __name__ == "__main__":
    unittest.main()
