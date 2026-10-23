"""The safe input layer. EVERY key press and mouse action goes through this file.

Rules enforced here (CLAUDE.md section 0a):
  * Only keys on ALLOWED_KEYS can ever be sent.  Number keys, "/", Tab, Esc, `,
    Enter, r and anything else are refused.
  * Key "2" (Supreme Saturator) is NOT on the allowlist.  It can only be sent by
    SprinklerGuard.place_sprinkler(), which checks its own conditions and is limited
    to one press per session (two if the retry setting is on and the first visibly failed).
  * The mouse only ever uses the LEFT button and only inside the click-safe zone,
    a central rectangle that can be shrunk but never stretched into the left
    inventory panel, the bottom hotbar or the top bar.
  * release_all() lets go of every key and the mouse button.  It is called on every stop.
  * Once the stop flag is set (Stop button / F3 / any stop condition) every further
    input is refused with EmergencyStop.
"""

from __future__ import annotations

import logging
import subprocess
import threading
from dataclasses import dataclass

from .clock import Clock

log = logging.getLogger("beeline.input")

# Friendly key name -> X11 keysym.  This dict IS the allowlist.
ALLOWED_KEYS = {
    "w": "w",
    "a": "a",
    "s": "s",
    "d": "d",
    "space": "space",
    "e": "e",
    "shift": "Shift_L",
    ",": "comma",
    ".": "period",
    "i": "i",
    "o": "o",
}
ALLOWED_KEYSYMS = frozenset(ALLOWED_KEYS.values())

# Only used by SprinklerGuard.  Deliberately not in ALLOWED_KEYS.
SPRINKLER_KEY = "2"
_SPRINKLER_KEYSYM = "2"
# A private object.  The backends refuse "2" unless this exact object is passed.
_SPRINKLER_TOKEN = object()

# Never sent, ever.  (Anything not in ALLOWED_KEYS is refused anyway; this list is for
# documentation, the GUI's "what this macro will never press" box, and the tests.)
BLOCKED_EXAMPLES = (
    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
    + ["/", "slash", "Tab", "tab", "Escape", "Esc", "esc", "`", "grave", "Return", "Enter", "enter",
       "KP_Enter", "r", "R", "W", "A", "S", "D", "E", "q", "f", "g", "m", "c", "x", "z", "l",
       "ctrl", "Control_L", "alt", "Alt_L", "super", "Super_L", "F1", "F11", "Delete", "BackSpace"]
)


class InputRefused(Exception):
    """Raised when something asks for an input that the safety rules forbid."""


class EmergencyStop(Exception):
    """Raised when input is attempted after the stop flag was set."""


# ---------------------------------------------------------------------------
# Click-safe zone
# ---------------------------------------------------------------------------

@dataclass
class SafeZone:
    """A rectangle of the game screen, stored as fractions (0..1) of width/height.

    The mouse may only be moved / clicked inside it.  HARD_LIMITS is the biggest the
    zone can ever be: it keeps clear of the inventory panel on the left, the hotbar at
    the bottom and the top bar.  Calibration may shrink the zone but never grow it past these.
    """

    left: float = 0.35
    top: float = 0.28
    right: float = 0.72
    bottom: float = 0.68

    HARD_LEFT = 0.25
    HARD_TOP = 0.15
    HARD_RIGHT = 0.85
    HARD_BOTTOM = 0.80
    MIN_SIZE = 0.05

    def __post_init__(self) -> None:
        self.left, self.top, self.right, self.bottom = self.clamped(
            self.left, self.top, self.right, self.bottom)

    @classmethod
    def clamped(cls, left: float, top: float, right: float, bottom: float):
        left = max(cls.HARD_LEFT, min(float(left), cls.HARD_RIGHT))
        right = max(cls.HARD_LEFT, min(float(right), cls.HARD_RIGHT))
        top = max(cls.HARD_TOP, min(float(top), cls.HARD_BOTTOM))
        bottom = max(cls.HARD_TOP, min(float(bottom), cls.HARD_BOTTOM))
        if left > right:
            left, right = right, left
        if top > bottom:
            top, bottom = bottom, top
        if right - left < cls.MIN_SIZE or bottom - top < cls.MIN_SIZE:
            # Too small / broken: fall back to the default zone.
            return 0.35, 0.28, 0.72, 0.68
        return left, top, right, bottom

    def contains(self, x: float, y: float, screen_w: int, screen_h: int) -> bool:
        fx = x / float(screen_w)
        fy = y / float(screen_h)
        return self.left <= fx <= self.right and self.top <= fy <= self.bottom

    def centre(self, screen_w: int, screen_h: int) -> tuple[int, int]:
        return (int((self.left + self.right) / 2 * screen_w),
                int((self.top + self.bottom) / 2 * screen_h))

    def to_pixels(self, screen_w: int, screen_h: int) -> tuple[int, int, int, int]:
        return (int(self.left * screen_w), int(self.top * screen_h),
                int(self.right * screen_w), int(self.bottom * screen_h))

    def to_dict(self) -> dict:
        return {"left": self.left, "top": self.top, "right": self.right, "bottom": self.bottom}

    @classmethod
    def from_dict(cls, d: dict | None) -> "SafeZone":
        d = d or {}
        return cls(d.get("left", 0.35), d.get("top", 0.28), d.get("right", 0.72), d.get("bottom", 0.68))


# ---------------------------------------------------------------------------
# Backends: the only code that actually talks to X.  They double-check the
# allowlist too, so even a bug elsewhere can't send a blocked key.
# ---------------------------------------------------------------------------

def _check_keysym(keysym: str, token: object) -> None:
    if keysym in ALLOWED_KEYSYMS:
        return
    if keysym == _SPRINKLER_KEYSYM and token is _SPRINKLER_TOKEN:
        return
    raise InputRefused("backend refused key %r (not on the allowlist)" % (keysym,))


class Backend:
    """Base class.  Subclasses implement _key/_mouse.  Do not call _key directly."""

    def key_down(self, keysym: str, token: object = None) -> None:
        _check_keysym(keysym, token)
        self._key("keydown", keysym)

    def key_up(self, keysym: str, token: object = None) -> None:
        _check_keysym(keysym, token)
        self._key("keyup", keysym)

    def mouse_move(self, x: int, y: int) -> None:
        self._mouse("move", int(x), int(y))

    def mouse_down(self) -> None:
        self._mouse("down")

    def mouse_up(self) -> None:
        self._mouse("up")

    def _key(self, action: str, keysym: str) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def _mouse(self, action: str, *args) -> None:  # pragma: no cover - abstract
        raise NotImplementedError


class XdotoolBackend(Backend):
    """Sends input to ONE X display (the hidden screen) using xdotool."""

    def __init__(self, display: str) -> None:
        if not display or display in (":0", ":0.0"):
            # Never type into Jacob's real desktop.
            raise InputRefused("refusing to send input to the main desktop display %r" % display)
        self.display = display

    def _run(self, args: list) -> None:
        env = {"DISPLAY": self.display, "PATH": "/usr/bin:/bin:/usr/local/bin"}
        subprocess.run(["xdotool"] + args, env=env, check=False, timeout=5,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _key(self, action: str, keysym: str) -> None:
        self._run([action, keysym])

    def _mouse(self, action: str, *args) -> None:
        if action == "move":
            self._run(["mousemove", str(args[0]), str(args[1])])
        elif action == "down":
            self._run(["mousedown", "1"])  # left button only
        elif action == "up":
            self._run(["mouseup", "1"])


class RecordingBackend(Backend):
    """Records what would be sent.  Used for dry runs and tests."""

    def __init__(self) -> None:
        self.events: list = []

    def _key(self, action: str, keysym: str) -> None:
        self.events.append((action, keysym))

    def _mouse(self, action: str, *args) -> None:
        self.events.append(("mouse_" + action,) + tuple(args))

    def keys_pressed(self) -> list:
        return [k for (a, *rest) in self.events if a == "keydown" for k in rest]


# ---------------------------------------------------------------------------
# SafeInput: the one place the rest of the macro uses to press things.
# ---------------------------------------------------------------------------

class SafeInput:
    def __init__(self, backend: Backend, screen_size: tuple = (1280, 720),
                 zone: SafeZone | None = None, clock: Clock | None = None,
                 stop_event: threading.Event | None = None, dry_run: bool = False) -> None:
        self.backend = backend
        self.screen_w, self.screen_h = screen_size
        self.zone = zone or SafeZone()
        self.clock = clock or Clock()
        self.stop_event = stop_event or threading.Event()
        self.dry_run = dry_run
        self._held: set = set()
        self._mouse_held = False
        self._mouse_pos = None  # last place we put the pointer (None = never moved it)
        self._lock = threading.RLock()
        self.last_input_time = self.clock.now()
        self.on_input = None  # optional callback(description) e.g. for the GUI's dry-run view

    # -- helpers ---------------------------------------------------------
    def _guard(self) -> None:
        if self.stop_event.is_set():
            raise EmergencyStop("stop requested")

    def _note(self, what: str) -> None:
        self.last_input_time = self.clock.now()
        if self.on_input is not None:
            try:
                self.on_input(what)
            except Exception:  # never let a GUI hiccup break input safety
                pass

    @staticmethod
    def keysym_for(name: str) -> str:
        if not isinstance(name, str) or name not in ALLOWED_KEYS:
            raise InputRefused("key %r is blocked (not on the allowlist)" % (name,))
        return ALLOWED_KEYS[name]

    def held_keys(self) -> set:
        return set(self._held)

    # -- keys --------------------------------------------------------------
    def key_down(self, name: str) -> None:
        keysym = self.keysym_for(name)  # refuse first, before anything else
        with self._lock:
            self._guard()
            self.backend.key_down(keysym)
            self._held.add(name)
            self._note("hold " + name)

    def key_up(self, name: str) -> None:
        keysym = self.keysym_for(name)
        with self._lock:
            self.backend.key_up(keysym)  # releasing is always allowed, even after stop
            self._held.discard(name)

    def tap(self, name: str, hold: float = 0.06) -> None:
        self.key_down(name)
        try:
            self.clock.sleep(hold, self.stop_event)
        finally:
            self.key_up(name)
        self._guard()

    def hold(self, name: str, seconds: float) -> None:
        self.key_down(name)
        try:
            self.sleep(seconds)
        finally:
            self.key_up(name)

    def sleep(self, seconds: float, slice_s: float = 0.1) -> None:
        """Interruptible wait: raises EmergencyStop as soon as the stop flag is set."""
        end = self.clock.now() + seconds
        while True:
            self._guard()
            left = end - self.clock.now()
            if left <= 0:
                return
            self.clock.sleep(min(slice_s, left), self.stop_event)

    # -- mouse (left button only, safe zone only) ----------------------------
    def _check_point(self, x: int, y: int) -> None:
        if not self.zone.contains(x, y, self.screen_w, self.screen_h):
            raise InputRefused("mouse position (%d, %d) is outside the click-safe zone" % (x, y))

    def hold_point(self) -> tuple:
        """Where to hold the left button: the exact screen centre (with shift lock on, Roblox
        keeps the pointer there, so 'moving' to it doesn't turn the camera).  Only if the
        safe zone was shrunk away from the centre is the zone's own centre used instead."""
        cx, cy = self.screen_w // 2, self.screen_h // 2
        if self.zone.contains(cx, cy, self.screen_w, self.screen_h):
            return cx, cy
        log.warning("safe zone doesn't include the screen centre; holding the mouse at the zone centre")
        return self.zone.centre(self.screen_w, self.screen_h)

    def _move(self, x: int, y: int) -> None:
        """Move only if the pointer isn't already there: any real movement turns the camera
        when shift lock is on."""
        if self._mouse_pos != (x, y):
            self.backend.mouse_move(x, y)
            self._mouse_pos = (x, y)

    def move_mouse(self, x: int, y: int) -> None:
        self._check_point(x, y)
        with self._lock:
            self._guard()
            self._move(x, y)

    def click(self, x: int, y: int) -> None:
        self._check_point(x, y)
        with self._lock:
            self._guard()
            self._move(x, y)
            self.backend.mouse_down()
            self._mouse_held = True
        try:
            self.clock.sleep(0.05, self.stop_event)
        finally:
            self.mouse_up()
        self._note("click")

    def mouse_down(self, x: int, y: int) -> None:
        """Hold the left button (swing the tool) at a point inside the safe zone."""
        self._check_point(x, y)
        with self._lock:
            self._guard()
            self._move(x, y)
            self.backend.mouse_down()
            self._mouse_held = True
            self._note("hold left mouse")

    def mouse_up(self) -> None:
        with self._lock:
            self.backend.mouse_up()
            self._mouse_held = False

    @property
    def mouse_held(self) -> bool:
        return self._mouse_held

    # -- stopping ---------------------------------------------------------------
    def release_all(self) -> None:
        """Let go of everything.  Safe to call any time, any number of times."""
        with self._lock:
            for name in list(ALLOWED_KEYS):
                try:
                    self.backend.key_up(ALLOWED_KEYS[name])
                except Exception:  # keep releasing the rest no matter what
                    log.exception("releasing %s failed", name)
            self._held.clear()
            try:
                self.backend.mouse_up()
            except Exception:
                log.exception("releasing mouse failed")
            self._mouse_held = False

    def emergency_stop(self) -> None:
        self.stop_event.set()
        self.release_all()


# ---------------------------------------------------------------------------
# The ONE way key "2" (Supreme Saturator) can be pressed.
# ---------------------------------------------------------------------------

class SprinklerGuard:
    """Guards key "2".

    place_sprinkler() presses "2" only when ALL of these are true:
      * it is the start of a grind (grind_start=True),
      * confirm_in_field() says we are standing in the middle of the field,
      * saturator_visible() says the Saturator is NOT already on screen,
      * it has not already been placed this session.
    A retry (at most one, only when allow_retry is on) is allowed only after
    report_result(seen=False) says the first placement visibly failed.
    """

    def __init__(self, inp: SafeInput, allow_retry: bool = False) -> None:
        self.inp = inp
        self.allow_retry = bool(allow_retry)
        self.presses = 0
        self.placed = False
        self._last_failed = False

    @property
    def max_presses(self) -> int:
        return 2 if self.allow_retry else 1

    def can_press(self) -> bool:
        if self.placed or self.presses >= self.max_presses:
            return False
        if self.presses == 0:
            return True
        return self._last_failed  # retry only after a visible failure

    def place_sprinkler(self, *, grind_start: bool, confirm_in_field, saturator_visible) -> bool:
        if not grind_start:
            raise InputRefused("Saturator can only be placed at the start of a grind")
        if not self.can_press():
            raise InputRefused("Saturator already placed / no presses left this session")
        if not confirm_in_field():
            raise InputRefused("not confirmed standing in the middle of the field")
        if saturator_visible():
            raise InputRefused("Saturator is already visible; not placing another")
        self.inp._guard()
        self.presses += 1
        self._last_failed = False
        log.warning("PRESSING KEY 2 (Supreme Saturator), press %d of max %d this session",
                    self.presses, self.max_presses)
        with self.inp._lock:
            self.inp.backend.key_down(_SPRINKLER_KEYSYM, token=_SPRINKLER_TOKEN)
            try:
                self.inp.clock.sleep(0.06)
            finally:
                self.inp.backend.key_up(_SPRINKLER_KEYSYM, token=_SPRINKLER_TOKEN)
        self.inp._note("press 2 (Saturator)")
        return True

    def report_result(self, seen: bool) -> None:
        if seen:
            self.placed = True
            self._last_failed = False
        else:
            self._last_failed = True
            log.warning("Saturator not seen after pressing 2")
