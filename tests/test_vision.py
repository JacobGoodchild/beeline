import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from beeline import synth, vision  # noqa: E402
from beeline.config import Calibration, Settings  # noqa: E402
from beeline.safety import SafeZone  # noqa: E402
from beeline.senses import Senses  # noqa: E402

FIELD = "Pine Tree Forest"


def calibrated(with_fill=True, balloon=True) -> Calibration:
    """Calibrate exactly the way Jacob would on the Setup tab, using synthetic screens."""
    cal = Calibration()
    cal.capture_bag(synth.draw_scene(bag=0), synth.BAG_LEFT, synth.BAG_RIGHT, "empty")
    if with_fill:
        cal.capture_bag(synth.draw_scene(bag=100), synth.BAG_LEFT, synth.BAG_RIGHT, "full")
    cal.capture_eprompt(synth.draw_scene(eprompt=True), synth.EPROMPT_BOX)
    if balloon:
        cal.capture_balloon(synth.draw_scene(eprompt=True, balloon=True), synth.BALLOON_BOX, present=True)
        cal.capture_balloon(synth.draw_scene(eprompt=True, balloon=False), synth.BALLOON_BOX, present=False)
    cal.capture_saturator(synth.draw_scene(in_field=True, saturator_at=(700, 330)), (670, 300, 60, 60))
    cal.capture_field(synth.draw_scene(in_field=True), synth.FIELD_BOX, FIELD)
    return cal


class BagTests(unittest.TestCase):
    """The simple bar reader (still used when Jacob clicks the bar ends to fine-tune)."""
    def test_bag_reading_matches_synthetic_fill(self):
        empty = vision.sample_bag_colours(synth.draw_scene(bag=0), synth.BAG_LEFT, synth.BAG_RIGHT)
        for pct in (0, 5, 20, 50, 80, 95, 100):
            got = vision.read_bag_percent(synth.draw_scene(bag=pct), synth.BAG_LEFT, synth.BAG_RIGHT, empty,
                                          synth.BAG_FILL)
            self.assertAlmostEqual(got, pct, delta=4)


class TemplateTests(unittest.TestCase):
    def test_template_found_and_not_found(self):
        x, y, w, h = synth.EPROMPT_BOX
        tpl = synth.draw_scene(eprompt=True).crop((x, y, x + w, y + h))
        self.assertGreater(vision.match_template(synth.draw_scene(eprompt=True), tpl, synth.EPROMPT_BOX).score, 0.95)
        shifted = synth.draw_scene(eprompt=True).crop((-12, -8, 1280 - 12, 720 - 8))
        self.assertGreater(vision.match_template(shifted, tpl, synth.EPROMPT_BOX).score, 0.95)
        self.assertLess(vision.match_template(synth.draw_scene(eprompt=False), tpl, synth.EPROMPT_BOX).score, 0.88)


class BalloonTests(unittest.TestCase):
    def test_balloon_present_and_gone(self):
        s = Senses(calibrated())
        self.assertEqual(s.balloon_state(synth.draw_scene(eprompt=True, balloon=True)), "present")
        self.assertEqual(s.balloon_state(synth.draw_scene(eprompt=True, balloon=False)), "gone")

    def test_balloon_with_only_present_sample(self):
        cal = calibrated()
        cal.balloon_gone_img = None
        s = Senses(cal)
        self.assertEqual(s.balloon_state(synth.draw_scene(balloon=True)), "present")
        self.assertEqual(s.balloon_state(synth.draw_scene(balloon=False)), "gone")

    def test_uncalibrated_balloon_unknown(self):
        self.assertEqual(Senses(Calibration()).balloon_state(synth.draw_scene(balloon=True)), "unknown")


class SaturatorTests(unittest.TestCase):
    def test_saturator_detected_with_position(self):
        s = Senses(calibrated())
        for pos in ((700, 330), (400, 300), (1000, 500)):
            b = s.saturator(synth.draw_scene(in_field=True, saturator_at=pos))
            self.assertTrue(b.visible(s.cal.saturator_min_count), pos)
            self.assertAlmostEqual(b.cx, pos[0], delta=12)
            self.assertAlmostEqual(b.cy, pos[1], delta=12)

    def test_saturator_not_confused_with_blue_flowers(self):
        s = Senses(calibrated())
        self.assertFalse(s.saturator_visible(synth.draw_scene(in_field=True)))
        self.assertFalse(s.saturator_visible(synth.draw_scene(in_field=False)))

    def test_saturator_position_not_pulled_off_by_bubbles(self):
        from PIL import ImageDraw
        s = Senses(calibrated())
        img = synth.draw_scene(in_field=True, saturator_at=(700, 330))
        d = ImageDraw.Draw(img)
        for (bx, by) in ((350, 500), (1000, 250), (1100, 520), (450, 260)):
            d.ellipse((bx - 8, by - 8, bx + 8, by + 8), fill=synth.SATURATOR_COLOUR)  # bubbles
        b = s.saturator(img)
        self.assertAlmostEqual(b.cx, 700, delta=12)
        self.assertAlmostEqual(b.cy, 330, delta=12)

    def test_saturator_in_ui_areas_ignored(self):
        s = Senses(calibrated())
        # only in the left panel area / hotbar: ignored
        self.assertFalse(s.saturator_visible(synth.draw_scene(in_field=True, saturator_at=(60, 400))))


class ScreenChecks(unittest.TestCase):
    def test_frame_change(self):
        a = synth.draw_scene(in_field=True, tick=0)
        b = synth.draw_scene(in_field=True, tick=1)
        self.assertLess(vision.frame_change(a, a), 0.5)
        self.assertGreater(vision.frame_change(a, b), 2)

    def test_disconnect_dialog(self):
        self.assertTrue(vision.looks_like_disconnect_dialog(synth.draw_scene(dialog=True)))
        self.assertTrue(vision.looks_like_disconnect_dialog(synth.draw_scene(in_field=True, dialog=True)))
        for kw in ({}, {"in_field": True}, {"eprompt": True, "balloon": True},
                   {"in_field": True, "saturator_at": (640, 400)}):
            self.assertFalse(vision.looks_like_disconnect_dialog(synth.draw_scene(**kw)), kw)


class PersistenceTests(unittest.TestCase):
    def test_calibration_round_trip(self):
        cal = calibrated()
        cal.layout["pollen_bar"] = [0.53, 0.63, 0.047]
        with tempfile.TemporaryDirectory() as d:
            cal.save(d)
            back = Calibration.load(d)
        self.assertEqual(back.layout["pollen_bar"], [0.53, 0.63, 0.047])
        self.assertEqual(back.saturator_hue, cal.saturator_hue)
        self.assertIsNotNone(back.balloon_present_img)
        self.assertEqual(back.zone().to_dict(), cal.zone().to_dict())

    def test_tampered_safe_zone_in_file_is_clamped(self):
        cal = calibrated()
        cal.safe_zone = {"left": 0.0, "top": 0.0, "right": 1.0, "bottom": 1.0}
        with tempfile.TemporaryDirectory() as d:
            cal.save(d)
            back = Calibration.load(d)
        self.assertEqual(back.safe_zone["left"], SafeZone.HARD_LEFT)
        self.assertEqual(back.safe_zone["bottom"], SafeZone.HARD_BOTTOM)

    def test_missing_list(self):
        self.assertEqual(len(Calibration().missing(FIELD, True)), 5)
        self.assertEqual(len(Calibration().missing(FIELD, False)), 4)

    def test_settings_round_trip_and_validation(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.json")
            s = Settings(hive_slot=9, convert_percent=500, display=":0", loop_size="huge")
            s.save(p)
            back = Settings.load(p)
        self.assertEqual(back.hive_slot, 6)
        self.assertEqual(back.convert_percent, 100)
        self.assertEqual(back.display, ":5")
        self.assertEqual(back.loop_size, "small")
        self.assertTrue(Settings().dry_run, "dry run must be the default")


if __name__ == "__main__":
    unittest.main()
