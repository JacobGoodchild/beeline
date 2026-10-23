"""Recorded walking routes (hive -> field, field -> hive), saved per hive slot.

A route is just a list of "key down / key up at time t" events using allowlisted
keys only.  Recording happens in the GUI: Jacob clicks the preview and walks with
W A S D etc.; each key goes through the safe input layer to the hidden screen and is
written down here.  Replaying sends the same keys at the same times.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field as dc_field

from .clock import Clock
from .config import ROUTES_DIR
from .safety import ALLOWED_KEYS, InputRefused, SafeInput

ROUTE_NAMES = {
    "hive_to_field": "Hive to field",
    "field_to_hive": "Field to hive",
}


@dataclass
class Route:
    name: str
    slot: int
    field: str = "Pine Tree Forest"
    events: list = dc_field(default_factory=list)   # [[t, "down"|"up", key], ...]
    duration: float = 0.0

    def validate(self) -> None:
        if self.name not in ROUTE_NAMES:
            raise ValueError("unknown route name %r" % self.name)
        last_t = 0.0
        held = set()
        for ev in self.events:
            t, action, key = ev
            if key not in ALLOWED_KEYS:
                raise InputRefused("route contains blocked key %r" % (key,))
            if action not in ("down", "up"):
                raise ValueError("bad action %r" % (action,))
            if t < last_t:
                raise ValueError("route events out of order")
            last_t = t
            (held.add if action == "down" else held.discard)(key)
        if held:
            raise ValueError("route ends with keys still held: %s" % ", ".join(sorted(held)))
        if self.duration < last_t:
            self.duration = last_t

    def summary(self) -> str:
        presses = sum(1 for e in self.events if e[1] == "down")
        return "%.1f seconds, %d key presses" % (self.duration, presses)

    @staticmethod
    def path_for(slot: int, name: str, field_name: str = "Pine Tree Forest", d: str = ROUTES_DIR) -> str:
        f = field_name.lower().replace(" ", "_")
        return os.path.join(d, "slot%d_%s_%s.json" % (int(slot), f, name))

    def save(self, d: str = ROUTES_DIR) -> str:
        self.validate()
        os.makedirs(d, exist_ok=True)
        p = self.path_for(self.slot, self.name, self.field, d)
        with open(p, "w") as fh:
            json.dump({"name": self.name, "slot": self.slot, "field": self.field,
                       "duration": self.duration, "events": self.events}, fh, indent=1)
        return p

    @classmethod
    def load(cls, slot: int, name: str, field_name: str = "Pine Tree Forest", d: str = ROUTES_DIR):
        p = cls.path_for(slot, name, field_name, d)
        if not os.path.exists(p):
            return None
        with open(p) as fh:
            data = json.load(fh)
        r = cls(data["name"], int(data["slot"]), data.get("field", field_name),
                [list(e) for e in data["events"]], float(data.get("duration", 0)))
        r.validate()
        return r


class RouteRecorder:
    """Collects key events while Jacob walks.  Keys not on the allowlist are ignored
    (they are never sent either)."""

    def __init__(self, name: str, slot: int, field_name: str = "Pine Tree Forest",
                 clock: Clock | None = None) -> None:
        self.clock = clock or Clock()
        self.route = Route(name, int(slot), field_name)
        self.t0 = self.clock.now()
        self.held = set()

    def key(self, key: str, down: bool, at: float | None = None) -> bool:
        """Record one key event (`at` = when it happened, default now).
        Returns False if it was ignored."""
        if key not in ALLOWED_KEYS:
            return False
        if down and key in self.held:      # keyboard auto-repeat
            return False
        if not down and key not in self.held:
            return False
        (self.held.add if down else self.held.discard)(key)
        t = self.clock.now() if at is None else at
        self.route.events.append([round(max(0.0, t - self.t0), 3), "down" if down else "up", key])
        return True

    def stop(self) -> Route:
        t = round(self.clock.now() - self.t0, 3)
        self.route.events.sort(key=lambda e: e[0])  # stable: keeps order of same-time events
        for k in sorted(self.held):
            self.route.events.append([t, "up", k])
        self.held.clear()
        self.route.duration = t
        self.route.validate()
        return self.route


def replay(route: Route, inp: SafeInput, check=None, check_every: float = 0.5, before_down=None) -> None:
    """Walk a recorded route.  `check()` is called about every check_every seconds and
    may raise to stop (e.g. the stuck-screen check).  `before_down(key)` is called just before
    each key goes down and may raise to refuse it (used to only press E at the cannon).
    Keys are always released at the end."""
    route.validate()
    clock = inp.clock
    t0 = clock.now()
    last_check = t0
    try:
        for t, action, key in route.events:
            while True:
                now = clock.now()
                wait = (t0 + t) - now
                if check is not None and now - last_check >= check_every:
                    check()
                    last_check = now
                if wait <= 0:
                    break
                inp.sleep(min(wait, check_every))
            if action == "down":
                if before_down is not None:
                    before_down(key)
                inp.key_down(key)
            else:
                inp.key_up(key)
        rest = (t0 + route.duration) - clock.now()
        if rest > 0:
            inp.sleep(rest)
    finally:
        for k in list(inp.held_keys()):
            inp.key_up(k)
