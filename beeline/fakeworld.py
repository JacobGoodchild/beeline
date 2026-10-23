"""A tiny pretend Bee Swarm, for testing without Roblox.

It reacts to key presses / mouse like the real game would (very roughly) and draws
screenshots with synth.draw_scene.  Used by the unit tests (with a FakeClock) and by
fakegame.py (a real window on a virtual screen, driven by real xdotool input).
"""

from __future__ import annotations

import math

from . import synth

KEYSYM_TO_NAME = {"w": "w", "a": "a", "s": "s", "d": "d", "space": "space", "e": "e",
                  "Shift_L": "shift", "comma": ",", "period": ".", "i": "i", "o": "o", "2": "2"}

FIELD_CENTRE = (20.0, 0.0)


class FakeWorld:
    def __init__(self) -> None:
        self.x, self.y = 0.0, 0.0       # 0,0 = standing on the hive pad
        self.speed = 4.0                # units per second
        self.drift = 0.0                # extra sideways slide per second of 'w' (to test drift)
        self.held: set = set()
        self.mouse_held = False
        self.bag = 0.0
        self.fill_rate = 2.5            # % per second while swinging in the field
        self.convert_rate = 4.0         # % per second
        self.converting = False
        self.balloon = 20.0             # seconds of balloon converting left (0 = no balloon)
        self.balloon_rate = 1.0
        self.saturator = None           # (x, y) once placed
        self.sprinkler_presses = 0
        self.e_presses = 0
        self.keys_log: list = []        # (time, name) for every key down
        self.t = 0.0
        self.tick = 0
        self.dialog = False
        self.frozen = False
        self.dead_count = 0
        self.max_gap = 0.0              # longest time with no input at all
        self._last_input = 0.0
        self.blocked_seen: list = []
        self.left_mid_convert = 0       # times the player walked off while bag/balloon converting

    # -- where am I --------------------------------------------------------------
    def on_pad(self) -> bool:
        return math.hypot(self.x, self.y) <= 1.5

    def in_field(self) -> bool:
        return abs(self.x - FIELD_CENTRE[0]) <= 7.5 and abs(self.y - FIELD_CENTRE[1]) <= 5.5

    # -- input from the macro -------------------------------------------------
    def key(self, action: str, keysym: str) -> None:
        name = KEYSYM_TO_NAME.get(keysym)
        if name is None:
            self.blocked_seen.append(keysym)
            return
        self._input()
        if action == "keydown":
            if name in self.held:
                return
            self.held.add(name)
            self.keys_log.append((self.t, name))
            if name == "e" and self.on_pad():
                self.e_presses += 1
                self.converting = not self.converting  # pressing again toggles it off, like the game
            if name == "2":
                self.sprinkler_presses += 1
                if self.in_field():
                    self.saturator = (self.x, self.y)
        else:
            self.held.discard(name)

    def mouse(self, action: str, *args) -> None:
        self._input()
        if action == "down":
            self.mouse_held = True
        elif action == "up":
            self.mouse_held = False

    def _input(self) -> None:
        self.max_gap = max(self.max_gap, self.t - self._last_input)
        self._last_input = self.t

    # -- time passing ------------------------------------------------------------
    def advance(self, seconds: float) -> None:
        steps = max(1, int(seconds / 0.05))
        dt = seconds / steps
        for _ in range(steps):
            self._step(dt)

    def _step(self, dt: float) -> None:
        old_tick = int(self.t * 2)
        self.t += dt
        if not self.frozen and int(self.t * 2) != old_tick:
            self.tick += 1
        self.max_gap = max(self.max_gap, self.t - self._last_input)
        if self.dialog:
            return
        vx = (1 if "d" in self.held else 0) - (1 if "a" in self.held else 0)
        vy = (1 if "w" in self.held else 0) - (1 if "s" in self.held else 0)
        if vx or vy:
            self.x += vx * self.speed * dt
            self.y += vy * self.speed * dt
            if vy > 0:
                self.x += self.drift * dt
            if self.converting and not self.on_pad():
                self.converting = False  # walking off the pad stops converting
                if self.bag > 0 or self.balloon > 0:
                    self.left_mid_convert += 1
        if self.mouse_held and self.in_field():
            self.bag = min(100.0, self.bag + self.fill_rate * dt)
            self.balloon += 0.3 * dt
        if self.converting:
            if self.bag > 0:
                self.bag = max(0.0, self.bag - self.convert_rate * dt)
            elif self.balloon > 0:
                self.balloon = max(0.0, self.balloon - self.balloon_rate * dt)
            else:
                self.converting = False

    # -- things going wrong (for the stop-condition tests) ----------------------
    def die(self) -> None:
        self.dead_count += 1
        self.x, self.y = 3.0, 0.0       # respawn near the hive, not on the pad
        self.bag = 0.0
        self.saturator = None
        self.converting = False

    # -- what the screen shows ---------------------------------------------------
    def saturator_screen_pos(self):
        if self.saturator is None or not self.in_field():
            return None
        sx = 640 + (self.saturator[0] - self.x) * 40
        sy = 400 - (self.saturator[1] - self.y) * 25
        if not (260 <= sx <= 1200 and 120 <= sy <= 580):
            return None
        return (int(sx), int(sy))

    def screenshot(self):
        return synth.draw_scene(
            bag=self.bag,
            eprompt=self.on_pad() and not self.converting,
            balloon=self.balloon > 0,
            in_field=self.in_field(),
            saturator_at=self.saturator_screen_pos(),
            dialog=self.dialog,
            tick=self.tick,
        )


def make_backend(world: FakeWorld):
    from .safety import Backend

    class _B(Backend):
        def _key(self, action, keysym):
            world.key(action, keysym)

        def _mouse(self, action, *args):
            world.mouse(action, *args)

    return _B()
