"""Watches which allowlisted keys are held down on the hidden screen, so a route can be
recorded while Jacob walks directly in the hidden screen window.

This only LOOKS at the keyboard state of the hidden screen (needs python3-xlib).  It never
sends anything.  Keys that aren't on the allowlist are ignored completely.
"""

from __future__ import annotations

import logging
import threading

from .safety import ALLOWED_KEYS

log = logging.getLogger("beeline.keywatch")

# X keysym names -> Beeline key names
WATCHED = {v: k for k, v in ALLOWED_KEYS.items()}
WATCHED["Shift_R"] = "shift"


class KeyWatcher:
    def __init__(self, display: str, callback, poll: float = 0.015, release_polls: int = 2) -> None:
        self.display = display
        self.callback = callback          # callback(key_name, is_down)
        self.poll = poll
        self.release_polls = release_polls  # a key must look "up" this many polls in a row (ignores auto-repeat blips)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.ready = threading.Event()
        self.error: str | None = None

    def start(self) -> bool:
        try:
            import Xlib  # noqa: F401
        except Exception:
            self.error = "python3-xlib isn't installed"
            return False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        try:
            from Xlib import XK
            from Xlib.display import Display
            disp = Display(self.display)
            codes = {}
            for keysym_name, key in WATCHED.items():
                code = disp.keysym_to_keycode(XK.string_to_keysym(keysym_name))
                if code:
                    codes.setdefault(code, key)
        except Exception as exc:
            self.error = str(exc)
            log.warning("can't watch keys on %s: %s", self.display, exc)
            self.ready.set()
            return
        self.ready.set()
        down: set = set()
        up_count: dict = {}
        while not self._stop.is_set():
            try:
                bitmap = disp.query_keymap()
            except Exception as exc:
                log.warning("key watching stopped: %s", exc)
                return
            now_down = set()
            for code, key in codes.items():
                if bitmap[code // 8] & (1 << (code % 8)):
                    now_down.add(key)
            for key in now_down - down:
                down.add(key)
                self.callback(key, True)
            for key in list(down):
                if key in now_down:
                    up_count.pop(key, None)
                    continue
                up_count[key] = up_count.get(key, 0) + 1
                if up_count[key] >= self.release_polls:
                    down.discard(key)
                    up_count.pop(key, None)
                    self.callback(key, False)
            self._stop.wait(self.poll)
        for key in sorted(down):
            self.callback(key, False)
