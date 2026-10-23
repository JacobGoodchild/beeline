import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from helpers import Sim, calibrated, fake_routes  # noqa: E402

from beeline.clock import FakeClock  # noqa: E402
from beeline.config import Calibration, Settings  # noqa: E402
from beeline.macro import Runner  # noqa: E402
from beeline.routes import Route  # noqa: E402
from beeline.safety import ALLOWED_KEYS, RecordingBackend, SafeInput  # noqa: E402
from beeline import synth  # noqa: E402


def keys_held_at_end(sim):
    return sim.world.held or sim.world.mouse_held


class HappyPathTests(unittest.TestCase):
    def test_full_run_gathers_converts_and_stops_on_time(self):
        sim = Sim(minutes=20)
        reason = sim.run()
        w = sim.world
        self.assertTrue(reason.startswith("Finished"), reason)
        self.assertGreaterEqual(sim.runner.stats.trips, 5)
        self.assertEqual(w.sprinkler_presses, 1, "Saturator placed exactly once")
        self.assertEqual(w.e_presses, sim.runner.stats.trips, "E pressed once per trip, never spammed")
        self.assertEqual(w.left_mid_convert, 0, "never left the hive while bag or balloon converting")
        self.assertEqual(w.blocked_seen, [])
        self.assertLess(w.bag, 5, "final convert done")
        self.assertEqual(w.balloon, 0, "balloon fully converted at the end")
        self.assertTrue(w.on_pad())
        self.assertFalse(keys_held_at_end(sim))
        # time limit: stops shortly after the limit (one final trip home + convert)
        self.assertLess(sim.runner.elapsed(), 20 * 60 + 5 * 60)
        self.assertGreaterEqual(sim.runner.elapsed(), 20 * 60)

    def test_only_allowed_keys_and_2_reach_the_game(self):
        sim = Sim(minutes=10)
        sim.run()
        names = {n for (_, n) in sim.world.keys_log}
        self.assertTrue(names <= set(ALLOWED_KEYS) | {"2"}, names)
        self.assertEqual(sum(1 for (_, n) in sim.world.keys_log if n == "2"), 1)

    def test_saturator_placed_in_middle_of_field(self):
        sim = Sim(minutes=5)
        sim.run()
        sx, sy = sim.world.saturator
        self.assertAlmostEqual(sx, 20.0, delta=1.0)
        self.assertAlmostEqual(sy, 0.0, delta=1.0)

    def test_saturator_not_placed_again_if_already_there(self):
        sim = Sim(minutes=5)
        sim.world.saturator = (20.0, 0.0)  # Jacob placed it himself earlier
        reason = sim.run()
        self.assertTrue(reason.startswith("Finished"), reason)
        self.assertEqual(sim.world.sprinkler_presses, 0)

    def test_converts_existing_bag_before_leaving(self):
        sim = Sim(minutes=5)
        sim.world.bag = 60
        sim.run()
        first_e = min(t for (t, n) in sim.world.keys_log if n == "e")
        first_d = min(t for (t, n) in sim.world.keys_log if n == "d")
        self.assertLess(first_e, first_d)

    def test_no_input_gap_longer_than_two_minutes_even_with_huge_balloon(self):
        sim = Sim(minutes=15, balloon_max_wait_min=15)
        sim.world.balloon = 300
        sim.world.balloon_rate = 0.6   # ~8 minutes of balloon converting
        reason = sim.run()
        self.assertTrue(reason.startswith("Finished"), reason)
        self.assertLessEqual(sim.world.max_gap, 120)
        nudges = [n for (_, n) in sim.world.keys_log if n in (",", ".")]
        self.assertGreater(len(nudges), 4)
        self.assertEqual(nudges.count(","), nudges.count("."), "camera nudges cancel out")

    def test_drift_compensation_keeps_us_in_the_field(self):
        sim = Sim(minutes=30)
        sim.world.drift = 0.4  # every step forward also slides right
        reason = sim.run()
        self.assertTrue(reason.startswith("Finished"), reason)
        self.assertEqual(sim.world.sprinkler_presses, 1)

    def test_patterns_end_where_they_start(self):
        from beeline.macro import PATTERNS, pattern_offset
        for name, pat in PATTERNS.items():
            self.assertEqual(pattern_offset(pat), (0, 0), name)
            self.assertTrue(all(k in ("w", "a", "s", "d") for k, _ in pat))

    def test_medium_loops(self):
        sim = Sim(minutes=10, loop_size="medium")
        self.assertTrue(sim.run().startswith("Finished"))

    def test_max_trip_time_backstop(self):
        sim = Sim(minutes=20, max_trip_minutes=2)
        sim.world.fill_rate = 0.2   # bag fills very slowly
        reason = sim.run()
        self.assertTrue(reason.startswith("Finished"), reason)
        self.assertGreaterEqual(sim.runner.stats.trips, 4)


class StopConditionTests(unittest.TestCase):
    def assertStopped(self, sim, reason, words):
        self.assertIn(words.lower(), reason.lower())
        self.assertFalse(keys_held_at_end(sim), "keys must be released on stop")
        self.assertTrue(os.listdir(os.path.join(sim.tmp, "stops")), "stop screenshot saved")

    def test_death_in_field_stops(self):
        sim = Sim(minutes=30)
        orig = sim.world.advance

        def adv(s):
            orig(s)
            if sim.world.bag > 50 and sim.world.dead_count == 0:
                sim.world.die()
        sim.clock.on_sleep = adv
        reason = sim.run()
        self.assertStopped(sim, reason, "died")

    def test_disconnect_dialog_stops(self):
        sim = Sim(minutes=30)
        orig = sim.world.advance

        def adv(s):
            orig(s)
            if sim.world.t > 200:
                sim.world.dialog = True
        sim.clock.on_sleep = adv
        reason = sim.run()
        self.assertTrue("disconnect" in reason.lower() or "hasn't changed" in reason.lower(), reason)
        self.assertFalse(keys_held_at_end(sim))
        self.assertLess(sim.world.t, 200 + 90)

    def test_frozen_screen_stops(self):
        sim = Sim(minutes=30)
        orig_shot = sim.world.screenshot
        frozen = {}

        def shot():
            if sim.world.t > 100:
                if "img" not in frozen:
                    frozen["img"] = orig_shot()
                return frozen["img"]
            return orig_shot()
        sim.runner.screen = shot
        reason = sim.run()
        self.assertStopped(sim, reason, "hasn't changed")

    def test_route_too_slow_stops(self):
        sim = Sim(minutes=30)
        sim.world.speed = 1.5   # e.g. something slowing us down: never reaches the field
        reason = sim.run()
        self.assertStopped(sim, reason, "route to the field took too long")
        self.assertEqual(sim.world.sprinkler_presses, 0, "never place the Saturator outside the field")

    def test_speed_buff_overshoot_stops(self):
        sim = Sim(minutes=30)
        sim.world.speed = 9.0   # haste: overshoots the field
        reason = sim.run()
        self.assertStopped(sim, reason, "took too long")
        self.assertEqual(sim.world.sprinkler_presses, 0)

    def test_walking_home_too_long_stops(self):
        sim = Sim(minutes=30)
        orig = sim.world.advance

        def adv(s):
            orig(s)
            if sim.world.bag > 90:
                sim.world.speed = 2.0
        sim.clock.on_sleep = adv
        reason = sim.run()
        self.assertStopped(sim, reason, "walking home took too long")

    def test_not_on_pad_at_start(self):
        sim = Sim(minutes=30)
        sim.world.x = 5
        reason = sim.run()
        self.assertStopped(sim, reason, "make honey")
        self.assertEqual(sim.world.keys_log, [])

    def test_missing_calibration(self):
        sim = Sim(minutes=30)
        sim.runner.cal = Calibration()
        sim.runner.senses.cal = sim.runner.cal
        reason = sim.run()
        self.assertIn("setup isn't finished", reason.lower())
        self.assertEqual(sim.world.keys_log, [])

    def test_missing_route(self):
        sim = Sim(minutes=30)
        sim.runner.routes = {"hive_to_field": fake_routes()["hive_to_field"]}
        reason = sim.run()
        self.assertIn("no recorded route", reason.lower())
        self.assertEqual(sim.world.keys_log, [])

    def test_zero_time(self):
        sim = Sim(minutes=0)
        self.assertIn("run time is zero", sim.run().lower())

    def test_emergency_stop_midway_releases_everything(self):
        sim = Sim(minutes=30)
        orig = sim.world.advance

        def adv(s):
            orig(s)
            if sim.world.t > 150:
                sim.inp.stop_event.set()
        sim.clock.on_sleep = adv
        reason = sim.run()
        self.assertIn("stopped by you", reason.lower())
        self.assertFalse(keys_held_at_end(sim))
        t_stop = sim.world.t
        self.assertFalse([t for (t, n) in sim.world.keys_log if t > t_stop])

    def test_balloon_taking_too_long_stops_at_hive_without_leaving(self):
        sim = Sim(minutes=30, balloon_max_wait_min=2)
        sim.world.balloon = 1000
        reason = sim.run()
        self.assertStopped(sim, reason, "balloon was still converting")
        self.assertTrue(sim.world.on_pad(), "stayed on the hive pad")
        self.assertEqual(sim.world.left_mid_convert, 0)

    def test_game_window_disappearing_stops(self):
        sim = Sim(minutes=30)
        sim.runner.window_alive = lambda: sim.world.t < 120
        reason = sim.run()
        self.assertStopped(sim, reason, "game window disappeared")

    def test_converting_not_starting_stops(self):
        sim = Sim(minutes=30)
        sim.world.convert_rate = 0.0
        reason = sim.run()
        self.assertStopped(sim, reason, "converting didn't start")

    def test_wandering_out_of_field_stops(self):
        sim = Sim(minutes=30, drift_compensation=False)
        sim.world.drift = 3.0
        reason = sim.run()
        self.assertStopped(sim, reason, "no longer in")


class DryRunTests(unittest.TestCase):
    def test_dry_run_reports_missing_eprompt(self):
        cal = calibrated()
        clock = FakeClock()
        backend = RecordingBackend()
        inp = SafeInput(backend, clock=clock, zone=cal.zone(), dry_run=True)
        s = Settings(run_hours=0, run_minutes=30, dry_run=True)
        tick = [0]

        def screen():
            tick[0] += 1
            return synth.draw_scene(eprompt=False, tick=tick[0])
        reason = Runner(s, cal, inp, screen, fake_routes(), clock=clock).run()
        self.assertIn("E-prompt NOT seen", reason)
        self.assertIn("Would have stopped because", reason)

    def test_dry_run_presses_nothing_real(self):
        cal = calibrated()
        clock = FakeClock()
        backend = RecordingBackend()
        inp = SafeInput(backend, clock=clock, zone=cal.zone(), dry_run=True)
        s = Settings(run_hours=0, run_minutes=30, dry_run=True)
        tick = [0]

        def screen():
            tick[0] += 1
            return synth.draw_scene(eprompt=True, tick=tick[0])
        runner = Runner(s, cal, inp, screen, fake_routes(), clock=clock)
        reason = runner.run()
        self.assertIn("dry run finished", reason.lower())
        self.assertIn("E-prompt SEEN", reason)
        self.assertIn("No problems found", reason)
        self.assertNotIn(("keydown", "2"), backend.events)
        # it rehearsed the walk and the convert press
        self.assertIn(("keydown", "d"), backend.events)
        self.assertIn(("keydown", "e"), backend.events)


if __name__ == "__main__":
    unittest.main()
