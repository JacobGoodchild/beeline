"""Time helpers.

Everything that waits goes through a Clock so tests can run hours of "game time"
in milliseconds with FakeClock.
"""

from __future__ import annotations

import threading
import time


class Clock:
    """Real wall-clock time."""

    def now(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float, stop_event: threading.Event | None = None) -> None:
        """Sleep, waking early if stop_event gets set."""
        if seconds <= 0:
            return
        if stop_event is None:
            time.sleep(seconds)
        else:
            stop_event.wait(seconds)


class FakeClock(Clock):
    """A clock that only moves when something sleeps. Used by the tests."""

    def __init__(self, start: float = 1000.0) -> None:
        self.t = start
        self.on_sleep = None  # optional hook(seconds) so fakes can react to time passing

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float, stop_event: threading.Event | None = None) -> None:
        if seconds <= 0:
            return
        self.t += seconds
        if self.on_sleep is not None:
            self.on_sleep(seconds)
