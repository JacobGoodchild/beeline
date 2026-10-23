"""End-to-end dry run: the REAL macro (real xdotool input, real screenshots) against the
fake game window on a virtual screen.  Takes about 2-3 minutes, so it only runs when
BEELINE_E2E=1 is set:

    BEELINE_E2E=1 python3 -m unittest tests.test_e2e_fakegame -v
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

from helpers import calibrated, fake_routes  # noqa: E402

from beeline.config import Settings  # noqa: E402
from beeline.display import HiddenScreen  # noqa: E402
from beeline.macro import Runner  # noqa: E402
from beeline.safety import SafeInput, XdotoolBackend  # noqa: E402

NEEDED = all(shutil.which(t) for t in ("Xvfb", "xdotool"))


@unittest.skipUnless(os.environ.get("BEELINE_E2E") == "1" and NEEDED, "set BEELINE_E2E=1 (needs Xvfb + xdotool)")
class FakeGameEndToEnd(unittest.TestCase):
    DISPLAY = ":9"

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.state_file = os.path.join(self.tmp, "state.json")
        self.screen = HiddenScreen(self.DISPLAY, (1280, 720), mode="xvfb")
        self.screen.start()
        env = dict(os.environ, DISPLAY=self.DISPLAY)
        self.game = subprocess.Popen([sys.executable, os.path.join(ROOT, "beeline.py"), "--fake-game", "--fast",
                                      "--state", self.state_file], env=env)
        for _ in range(50):
            if self.screen.find_game_window():
                break
            time.sleep(0.2)
        self.screen.fit_game_window()
        time.sleep(1.5)

    def tearDown(self):
        self.game.terminate()
        self.game.wait(timeout=5)
        self.screen.stop()

    def state(self):
        time.sleep(1.5)
        with open(self.state_file) as f:
            return json.load(f)

    def test_real_macro_against_fake_game(self):
        s = Settings(run_hours=0, run_minutes=2, dry_run=False, display=self.DISPLAY)
        cal = calibrated()
        inp = SafeInput(XdotoolBackend(self.DISPLAY), (1280, 720), cal.zone())
        runner = Runner(s, cal, inp, self.screen.screenshot, fake_routes(),
                        stops_dir=os.path.join(self.tmp, "stops"),
                        window_alive=lambda: self.screen.find_game_window() is not None)
        reason = runner.run()
        st = self.state()
        print("\nE2E result:", reason, "| trips:", runner.stats.trips, "| game state:",
              {k: v for k, v in st.items() if k != "keys"})
        self.assertTrue(reason.startswith("Finished"), reason)
        self.assertGreaterEqual(runner.stats.trips, 2)
        self.assertEqual(st["sprinkler_presses"], 1)
        self.assertEqual(st["e_presses"], runner.stats.trips)
        self.assertEqual(st["left_mid_convert"], 0)
        self.assertEqual(st["blocked_seen"], [])
        self.assertEqual(st["held"], [])
        self.assertFalse(st["mouse_held"])
        self.assertLess(st["bag"], 5)
        self.assertEqual(st["balloon"], 0)


if __name__ == "__main__":
    unittest.main()
