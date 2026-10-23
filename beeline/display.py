"""The hidden screen: a separate X display (Xephyr window or invisible Xvfb) that
Sober runs inside, so Jacob's real desktop stays free.

Only screenshots are READ from it, and only xdotool window commands (find / resize /
focus the Sober window) are used here.  Game input goes through safety.py only.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time

from .safety import is_main_desktop

log = logging.getLogger("beeline.display")

SOBER_APP_ID = "org.vinegarhq.Sober"


class DisplayError(Exception):
    """Something about the hidden screen is wrong.  The message is plain English."""


def tool_status() -> dict:
    """Which helper programs are installed.  Shown on the Setup tab."""
    return {
        "Xephyr (visible hidden screen)": bool(shutil.which("Xephyr")),
        "Xvfb (invisible hidden screen)": bool(shutil.which("Xvfb")),
        "xdotool (sends keys to the hidden screen)": bool(shutil.which("xdotool")),
        "flatpak (runs Sober)": bool(shutil.which("flatpak")),
    }


def _display_socket(display: str) -> str:
    return "/tmp/.X11-unix/X" + display.lstrip(":").split(".")[0]


def display_is_up(display: str) -> bool:
    if not os.path.exists(_display_socket(display)):
        return False
    if shutil.which("xdpyinfo"):
        r = subprocess.run(["xdpyinfo", "-display", display], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=5)
        return r.returncode == 0
    return True


def grab_screenshot(display: str, size: tuple | None = None):
    """Return a PIL RGB image of the whole hidden display."""
    from PIL import Image, ImageGrab
    try:
        img = ImageGrab.grab(xdisplay=display)
        return img.convert("RGB")
    except Exception as exc:
        # Fallback: ImageMagick's `import` (installed on Mint by default).
        if shutil.which("import"):
            try:
                out = subprocess.run(["import", "-display", display, "-window", "root", "ppm:-"],
                                     capture_output=True, timeout=10, check=True).stdout
                import io
                return Image.open(io.BytesIO(out)).convert("RGB")
            except Exception:
                pass
        raise DisplayError("Couldn't take a screenshot of the hidden screen %s (%s)" % (display, exc))


class HiddenScreen:
    def __init__(self, display: str = ":5", size: tuple = (1280, 720), mode: str = "xephyr",
                 glamor: bool = False) -> None:
        if is_main_desktop(display):
            raise DisplayError("The hidden screen must not be your main desktop (%s). Use :5." % display)
        self.display = display
        self.size = tuple(size)
        self.mode = mode  # "xephyr" (a window you can see) or "xvfb" (fully hidden)
        self.glamor = glamor
        self.server_proc: subprocess.Popen | None = None
        self.sober_proc: subprocess.Popen | None = None

    # -- the X server ------------------------------------------------------
    def start(self) -> None:
        if display_is_up(self.display):
            log.info("hidden screen %s is already running; reusing it", self.display)
            return
        w, h = self.size
        if self.mode == "xephyr":
            exe = shutil.which("Xephyr")
            if not exe:
                raise DisplayError("Xephyr isn't installed. Run: sudo apt install xserver-xephyr "
                                   "(or switch 'Hidden screen type' to Xvfb).")
            cmd = [exe, self.display, "-screen", "%dx%d" % (w, h), "-ac", "-br", "-noreset",
                   "-resizeable", "-title", "Beeline hidden screen"]
            if self.glamor:
                cmd.append("-glamor")
        else:
            exe = shutil.which("Xvfb")
            if not exe:
                raise DisplayError("Xvfb isn't installed. Run: sudo apt install xvfb")
            cmd = [exe, self.display, "-screen", "0", "%dx%dx24" % (w, h), "-ac", "-nolisten", "tcp"]
        log.info("starting hidden screen: %s", " ".join(cmd))
        self.server_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            if display_is_up(self.display):
                return
            if self.server_proc.poll() is not None:
                break
            time.sleep(0.1)
        raise DisplayError("The hidden screen %s didn't start. Is another program already using "
                           "that display number? Try a different number in Settings." % self.display)

    def stop(self) -> None:
        for proc in (self.sober_proc, self.server_proc):
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        self.sober_proc = None
        self.server_proc = None

    # -- Sober ---------------------------------------------------------------
    def launch_sober(self) -> None:
        """Open Sober inside the hidden screen.  Jacob then joins Bee Swarm himself."""
        if not display_is_up(self.display):
            raise DisplayError("Start the hidden screen first.")
        if not shutil.which("flatpak"):
            raise DisplayError("flatpak isn't installed, so Sober can't be started.")
        env = dict(os.environ)
        env["DISPLAY"] = self.display
        env.pop("WAYLAND_DISPLAY", None)
        log.info("launching Sober on %s", self.display)
        self.sober_proc = subprocess.Popen(["flatpak", "run", SOBER_APP_ID], env=env,
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _xdotool(self, args: list) -> str:
        if not shutil.which("xdotool"):
            raise DisplayError("xdotool isn't installed. Run: sudo apt install xdotool")
        env = {"DISPLAY": self.display, "PATH": "/usr/bin:/bin:/usr/local/bin"}
        r = subprocess.run(["xdotool"] + args, env=env, capture_output=True, text=True, timeout=5)
        return r.stdout.strip()

    def find_game_window(self) -> str | None:
        """Return the X window id of Sober (or the fake game) on the hidden screen."""
        for pattern in ("sober", "Sober", "Roblox", "Beeline fake game"):
            out = self._xdotool(["search", "--onlyvisible", "--name", pattern])
            if not out:
                out = self._xdotool(["search", "--onlyvisible", "--class", pattern])
            if out:
                return out.splitlines()[-1]
        return None

    def fit_game_window(self) -> str:
        """Make the game window fill the hidden screen exactly and give it focus.

        Window management only (move / resize / focus) - not game input.
        """
        wid = self.find_game_window()
        if not wid:
            raise DisplayError("Couldn't find the Sober window on the hidden screen. "
                               "Is Sober open and showing the game?")
        w, h = self.size
        self._xdotool(["windowmove", wid, "0", "0"])
        self._xdotool(["windowsize", wid, str(w), str(h)])
        self._xdotool(["windowfocus", wid])
        return wid

    def set_xephyr_window_visible(self, visible: bool) -> None:
        """Minimise / restore the Xephyr window on the real desktop (window management only)."""
        if self.mode != "xephyr" or not shutil.which("xdotool"):
            return
        host = os.environ.get("DISPLAY", ":0")
        env = {"DISPLAY": host, "PATH": "/usr/bin:/bin:/usr/local/bin"}
        r = subprocess.run(["xdotool", "search", "--name", "Beeline hidden screen"], env=env,
                           capture_output=True, text=True, timeout=5)
        for wid in r.stdout.split():
            cmd = ["windowminimize", wid] if not visible else ["windowactivate", wid]
            subprocess.run(["xdotool"] + cmd, env=env, capture_output=True, timeout=5)

    def screenshot(self):
        if not display_is_up(self.display):
            raise DisplayError("The hidden screen isn't running.")
        return grab_screenshot(self.display)
