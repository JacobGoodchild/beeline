"""Drives the real GUI (Setup tab calibration, route recording, dry run, real run, Stop)
against the fake game, on a pretend desktop with a Xephyr hidden screen inside it.
About 4 minutes.  Only runs with BEELINE_E2E=1."""

import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
NEEDED = all(shutil.which(t) for t in ("Xvfb", "Xephyr", "xdotool"))


@unittest.skipUnless(os.environ.get("BEELINE_E2E") == "1" and NEEDED, "set BEELINE_E2E=1 (needs Xvfb, Xephyr, xdotool)")
class GuiEndToEnd(unittest.TestCase):
    def test_drive_gui(self):
        data = tempfile.mkdtemp()
        shots = os.environ.get("BEELINE_SHOTS") or data
        desk = subprocess.Popen(["Xvfb", ":21", "-screen", "0", "2400x1000x24"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(1)
            env = dict(os.environ, DISPLAY=":21", BEELINE_DATA=data)
            r = subprocess.run([sys.executable, os.path.join(HERE, "gui_drive.py"), shots], env=env,
                               capture_output=True, text=True, timeout=900)
            out = "\n".join(l for l in (r.stdout + r.stderr).splitlines()
                            if "keysym" not in l and "xkbcomp" not in l and not l.startswith(">"))
            print(out[-4000:])
            self.assertEqual(r.returncode, 0)
            self.assertIn("ALL GUI CHECKS PASSED", r.stdout)
        finally:
            desk.terminate()


if __name__ == "__main__":
    unittest.main()
