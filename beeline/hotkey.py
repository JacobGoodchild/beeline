"""Global F3 emergency-stop hotkey.

Grabs F3 on the real desktop AND on the hidden screen, so pressing F3 stops the
macro whichever window has focus.  Needs the python3-xlib package
(`sudo apt install python3-xlib`).  If it's missing, the GUI still has its big
Stop button and F3 works while the Beeline window is focused.

This only *listens* for F3.  It never sends anything anywhere.
"""

from __future__ import annotations

import logging
import threading

log = logging.getLogger("beeline.hotkey")


def xlib_available() -> bool:
    try:
        import Xlib  # noqa: F401
        return True
    except Exception:
        return False


class GlobalHotkey:
    def __init__(self, callback, displays=(None,), keysym_name: str = "F3") -> None:
        self.callback = callback
        self.displays = [d for d in displays]
        self.keysym_name = keysym_name
        self._threads: list = []
        self._running = False
        self.active_on: list = []
        self._started: set = set()

    def start(self) -> bool:
        """Start listening on every display given to the constructor."""
        if not xlib_available():
            log.warning("python3-xlib not installed: F3 only works while Beeline is focused")
            return False
        self._running = True
        for d in self.displays:
            self.add_display(d)
        return True

    def add_display(self, display_name) -> None:
        """Listen on one more display (e.g. the hidden screen once it is running).
        Safe to call again for a display that is already being watched."""
        if not xlib_available():
            return
        self._running = True
        key = display_name or "desktop"
        if key in self._started:
            return
        self._started.add(key)
        t = threading.Thread(target=self._listen, args=(display_name,), daemon=True)
        t.start()
        self._threads.append(t)

    def stop(self) -> None:
        self._running = False

    def _listen(self, display_name) -> None:
        try:
            from Xlib import X, XK
            from Xlib.display import Display
            disp = Display(display_name) if display_name else Display()
            root = disp.screen().root
            keycode = disp.keysym_to_keycode(XK.string_to_keysym(self.keysym_name))
            # Grab with every combination of NumLock / CapsLock so it always fires.
            for mods in (0, X.Mod2Mask, X.LockMask, X.Mod2Mask | X.LockMask):
                root.grab_key(keycode, mods, True, X.GrabModeAsync, X.GrabModeAsync)
            disp.sync()
            self.active_on.append(display_name or "desktop")
            log.info("F3 emergency stop active on %s", display_name or "desktop")
            while self._running:
                if disp.pending_events() == 0:
                    threading.Event().wait(0.05)
                    continue
                ev = disp.next_event()
                if ev.type == X.KeyPress and ev.detail == keycode:
                    log.warning("F3 pressed: emergency stop")
                    try:
                        self.callback()
                    except Exception:
                        log.exception("emergency stop callback failed")
        except Exception as exc:  # display not up yet, F3 already grabbed, etc.
            self._started.discard(display_name or "desktop")  # allow a retry later
            log.warning("F3 hotkey not available on %s: %s", display_name or "desktop", exc)
