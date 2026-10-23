import os
import shutil
import subprocess
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from beeline.display import HiddenScreen  # noqa: E402
from beeline.hotkey import GlobalHotkey, xlib_available  # noqa: E402


@unittest.skipUnless(xlib_available() and shutil.which("Xvfb") and shutil.which("xdotool"),
                     "needs python3-xlib, Xvfb and xdotool")
class HotkeyTests(unittest.TestCase):
    def test_f3_on_hidden_screen_triggers_stop(self):
        screen = HiddenScreen(":12", mode="xvfb")
        screen.start()
        try:
            fired = threading.Event()
            hk = GlobalHotkey(fired.set, displays=())
            hk.add_display(":12")
            for _ in range(40):
                if hk.active_on:
                    break
                time.sleep(0.05)
            self.assertEqual(hk.active_on, [":12"])
            # (the test itself presses F3 the way Jacob would; the macro never sends F3)
            subprocess.run(["xdotool", "key", "F3"], env={"DISPLAY": ":12", "PATH": os.environ["PATH"]})
            self.assertTrue(fired.wait(3), "F3 didn't trigger the emergency stop")
            hk.stop()
        finally:
            screen.stop()


if __name__ == "__main__":
    unittest.main()
