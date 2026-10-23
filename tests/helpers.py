import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from beeline import synth  # noqa: E402
from beeline.clock import FakeClock  # noqa: E402
from beeline.config import Calibration, Settings  # noqa: E402
from beeline.fakeworld import FakeWorld, make_backend  # noqa: E402
from beeline.macro import Runner  # noqa: E402
from beeline.routes import Route  # noqa: E402
from beeline.safety import SafeInput  # noqa: E402

FIELD = "Pine Tree Forest"


def calibrated() -> Calibration:
    """Calibrate the way Jacob would on the Setup tab, using synthetic screens."""
    cal = Calibration()
    cal.capture_bag(synth.draw_scene(bag=0), synth.BAG_LEFT, synth.BAG_RIGHT, "empty")
    cal.capture_bag(synth.draw_scene(bag=100), synth.BAG_LEFT, synth.BAG_RIGHT, "full")
    cal.capture_eprompt(synth.draw_scene(eprompt=True), synth.EPROMPT_BOX)
    cal.capture_balloon(synth.draw_scene(eprompt=True, balloon=True), synth.BALLOON_BOX, present=True)
    cal.capture_balloon(synth.draw_scene(eprompt=True, balloon=False), synth.BALLOON_BOX, present=False)
    cal.capture_saturator(synth.draw_scene(in_field=True, saturator_at=(640, 400)), (610, 370, 60, 60))
    cal.capture_field(synth.draw_scene(in_field=True), synth.FIELD_BOX, FIELD)
    return cal


def fake_routes(slot=1):
    """Hive pad is at x=0, the middle of the field at x=20, speed 4/s -> hold d for 5 s."""
    to_field = Route("hive_to_field", slot, FIELD, [[0.0, "down", "d"], [5.0, "up", "d"]], 5.0)
    to_hive = Route("field_to_hive", slot, FIELD, [[0.0, "down", "a"], [5.0, "up", "a"]], 5.0)
    return {"hive_to_field": to_field, "field_to_hive": to_hive}


def use_fake_ocr(runner, world):
    """Long simulated runs read the text the fake world knows is on screen instead of
    running Tesseract thousands of times.  (Real OCR is tested on real screenshots and in
    the end-to-end tests.)"""
    runner.senses.reader.use_ocr = True
    runner.senses.reader.ocr_text = world.fake_ocr


class Sim:
    def __init__(self, minutes=30, **settings_kw):
        self.world = FakeWorld()
        self.clock = FakeClock()
        self.clock.on_sleep = self.world.advance
        settings_kw.setdefault("dry_run", False)
        self.settings = Settings(run_hours=0, run_minutes=minutes, **settings_kw)
        self.cal = Calibration()   # no calibration needed: defaults come from Jacob's screenshots
        self.inp = SafeInput(make_backend(self.world), self.world.size, clock=self.clock, zone=self.cal.zone())
        self.statuses = []
        self.tmp = tempfile.mkdtemp()
        self.runner = Runner(self.settings, self.cal, self.inp, self.world.screenshot, fake_routes(),
                             clock=self.clock, status=self.statuses.append,
                             stops_dir=os.path.join(self.tmp, "stops"))
        use_fake_ocr(self.runner, self.world)

    def run(self):
        return self.runner.run()
