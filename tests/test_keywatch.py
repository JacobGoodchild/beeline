import os
import shutil
import subprocess
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from beeline.display import HiddenScreen  # noqa: E402
from beeline.hotkey import xlib_available  # noqa: E402
from beeline.keywatch import KeyWatcher  # noqa: E402


@unittest.skipUnless(xlib_available() and shutil.which("Xvfb") and shutil.which("xdotool"),
                     "needs python3-xlib, Xvfb and xdotool")
class KeyWatcherTests(unittest.TestCase):
    def test_sees_allowed_keys_and_ignores_others(self):
        screen = HiddenScreen(":13", mode="xvfb")
        screen.start()
        events = []
        w = KeyWatcher(":13", lambda k, d: events.append((k, d)))
        try:
            self.assertTrue(w.start())
            self.assertTrue(w.ready.wait(3))
            env = {"DISPLAY": ":13", "PATH": os.environ["PATH"]}
            # (the test plays the part of Jacob's keyboard)
            for args in (["keydown", "w"], ["keydown", "Escape"], ["keydown", "1"]):
                subprocess.run(["xdotool"] + args, env=env)
            time.sleep(0.3)
            for args in (["keyup", "w"], ["keyup", "Escape"], ["keyup", "1"]):
                subprocess.run(["xdotool"] + args, env=env)
            time.sleep(0.3)
        finally:
            w.stop()
            screen.stop()
        self.assertEqual(events, [("w", True), ("w", False)])


if __name__ == "__main__":
    unittest.main()
