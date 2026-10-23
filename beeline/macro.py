"""The main loop: gather -> walk home -> convert bag + balloon -> walk back -> repeat.

Fail safe, never guess: whenever something looks wrong the run stops, every key is
released, the reason is logged and a screenshot is saved.
"""

from __future__ import annotations

import datetime
import logging
import os
import traceback
from dataclasses import dataclass, field

from . import vision
from .display import DisplayError
from .clock import Clock
from .config import LOGS_DIR, Calibration, Settings
from .routes import Route, replay
from .safety import EmergencyStop, InputRefused, SafeInput, SprinklerGuard
from .senses import Senses

log = logging.getLogger("beeline.macro")

# Gathering loop patterns: (key, seconds).  Each pattern ends where it started, so
# the loops stay around the Saturator.  "small" is a tight square that sweeps tokens
# and bubbles (good for the Pop Star passive); "medium" is a wider snake that sweeps
# three rows side to side, like Natro's snake patterns.
PATTERNS = {
    "small": [("w", 0.7), ("d", 0.7), ("s", 0.7), ("a", 0.7),
              ("d", 0.5), ("w", 0.5), ("a", 0.5), ("s", 0.5)],
    "medium": [("a", 1.0), ("w", 0.35), ("d", 2.0), ("w", 0.35), ("a", 2.0),
               ("w", 0.35), ("d", 2.0), ("s", 1.05), ("a", 1.0)],
}


def pattern_offset(pattern) -> tuple:
    """Where a pattern ends relative to where it started (should be (0, 0))."""
    x = sum(t for k, t in pattern if k == "d") - sum(t for k, t in pattern if k == "a")
    y = sum(t for k, t in pattern if k == "w") - sum(t for k, t in pattern if k == "s")
    return round(x, 6), round(y, 6)


IDLE_NUDGE_AFTER = 40.0       # seconds without input before a camera nudge (also proves the game is alive)
CHECK_EVERY = 2.0             # seconds between screen checks while waiting
BAG_EMPTY_PCT = 3.0
CONVERT_START_TIMEOUT = 45.0  # bag must start dropping within this long after pressing E
CONVERT_MAX = 8 * 60.0        # bag must be empty within this long
FINAL_GRACE = 20 * 60.0       # absolute stop this long after the time limit


class StopMacro(Exception):
    """A stop condition.  The message is shown to Jacob."""


@dataclass
class Stats:
    trips: int = 0
    started: float = 0.0
    last_stop_reason: str = ""
    sprinkler_presses: int = 0
    events: list = field(default_factory=list)


class Runner:
    def __init__(self, settings: Settings, cal: Calibration, inp: SafeInput, screen,
                 routes: dict, clock: Clock | None = None, status=None,
                 stops_dir: str | None = None, window_alive=None) -> None:
        self.s = settings
        self.cal = cal
        self.inp = inp
        self.screen = screen           # callable -> PIL image of the hidden screen
        self.routes = routes           # {"hive_to_field": Route, "field_to_hive": Route}
        self.clock = clock or inp.clock
        self.status_cb = status
        self.stops_dir = stops_dir or os.path.join(LOGS_DIR, "stops")
        self.window_alive = window_alive  # optional callable: is the game window still there?
        self._last_window_check = -1e9
        self.senses = Senses(cal, settings.field)
        self.guard = SprinklerGuard(inp, allow_retry=settings.allow_sprinkler_retry)
        self.stats = Stats()
        self.start_time = 0.0
        self.deadline = 0.0
        self.anchor = None             # where the Saturator sits on screen when we're on the spot
        self._last_thumb = None
        self._last_change = 0.0
        self._dialog_since = None
        self._last_img = None
        self._last_bag = None
        self._outside_field_checks = 0
        self.state = "idle"
        self.dry = bool(settings.dry_run)
        self.dry_notes: list = []
        self.dry_report = ""
        self._disagree = 0
        self._wrong_field = 0

    # ------------------------------------------------------------------ helpers
    def status(self, text: str) -> None:
        self.state = text
        log.info("STATUS: %s", text)
        if self.status_cb is not None:
            try:
                self.status_cb(text)
            except Exception:
                pass

    def fail(self, msg: str) -> None:
        """A stop condition.  In a dry run it is only reported (nothing is being pressed
        for real, so the game won't have moved) and the rehearsal carries on."""
        if self.dry:
            log.warning("[dry run] would stop here: %s", msg)
            self.dry_notes.append(msg)
            return
        raise StopMacro(msg)

    def elapsed(self) -> float:
        return self.clock.now() - self.start_time

    def time_up(self) -> bool:
        return self.clock.now() >= self.deadline

    def look(self):
        try:
            img = self.screen()
        except DisplayError as e:
            raise StopMacro("Stopped: couldn't see the hidden screen (%s)" % e)
        if img is None:
            raise StopMacro("Couldn't see the game window (no screenshot)")
        self._last_img = img
        return img

    def safety_check(self, img=None) -> None:
        """Checks that apply all the time: stop button, disconnect, frozen screen, overtime."""
        self.inp._guard()
        if img is None:
            img = self.look()
        now = self.clock.now()
        if now > self.deadline + FINAL_GRACE:
            raise StopMacro("Stopped: ran %d minutes past the time limit (final trip took too long)"
                            % (FINAL_GRACE // 60))
        if self.window_alive is not None and now - self._last_window_check >= 10:
            self._last_window_check = now
            if not self.window_alive():
                raise StopMacro("Stopped: the game window disappeared (Sober closed or crashed?)")
        thumb = vision.thumbnail(img)
        if self._last_thumb is None or vision.frame_change(self._last_thumb, thumb) > 0.02:
            self._last_change = now
        self._last_thumb = thumb
        if now - self._last_change > self.s.stuck_screen_seconds:
            raise StopMacro("Stopped: the screen hasn't changed for %d seconds (game frozen or disconnected?)"
                            % self.s.stuck_screen_seconds)
        if vision.looks_like_disconnect_dialog(img):
            if self._dialog_since is None:
                self._dialog_since = now
            elif now - self._dialog_since >= 6:
                raise StopMacro("Stopped: Roblox disconnect / idle message on screen")
        else:
            self._dialog_since = None

    def idle_guard(self) -> None:
        """Never go long without input (Roblox kicks after ~20 min idle).  Nudge the
        camera left then right: harmless, doesn't move the character off the hive pad."""
        if self.clock.now() - self.inp.last_input_time >= IDLE_NUDGE_AFTER:
            log.info("anti-idle camera nudge")
            self.inp.tap(",")
            self.inp.sleep(0.3)
            self.inp.tap(".")

    def wait(self, seconds: float) -> None:
        end = self.clock.now() + seconds
        while self.clock.now() < end:
            self.idle_guard()
            self.inp.sleep(min(1.0, end - self.clock.now()))

    def bag(self, img) -> float:
        b = self.senses.bag(img)
        if b.percent is None:
            raise StopMacro("Stopped: couldn't read the bag (pollen bar)")
        if b.disagree:
            self._disagree += 1
            log.warning("bag reading: numbers and bar disagree a lot (%s)", b.source)
            if self._disagree >= 3:
                self.fail("Stopped: bag reading makes no sense (the numbers and the bar disagree)")
        else:
            self._disagree = 0
        return b.percent

    # ------------------------------------------------------------------ run
    def run(self) -> str:
        self.start_time = self.clock.now()
        self.deadline = self.start_time + self.s.run_seconds()
        self.stats.started = self.start_time
        self._last_change = self.start_time
        reason = "Finished"
        try:
            self._run()
            if self.dry:
                reason = "Dry run finished: nothing was pressed. At the start it saw: %s. %s" % (
                    self.dry_report,
                    ("Would have stopped because: " + self.dry_notes[0]) if self.dry_notes
                    else "No problems found.")
            else:
                reason = "Finished: time limit reached (final convert done)"
        except EmergencyStop:
            reason = "Stopped by you (Stop button or F3)"
        except StopMacro as e:
            reason = str(e)
        except InputRefused as e:
            reason = "Stopped: safety layer refused an input (%s)" % e
        except Exception as e:  # anything unexpected = stop safely
            log.error("unexpected error:\n%s", traceback.format_exc())
            reason = "Stopped: unexpected error (%s). Please send the log to Claude." % e
        finally:
            try:
                self.inp.release_all()
            except Exception:
                log.exception("release_all failed")
        self.stats.last_stop_reason = reason
        self.stats.sprinkler_presses = self.guard.presses
        log.warning("RUN ENDED: %s (trips=%d, %.0f min)", reason, self.stats.trips, self.elapsed() / 60)
        self.save_stop_screenshot(reason)
        self.status(reason)
        return reason

    def save_stop_screenshot(self, reason: str) -> str | None:
        img = self._last_img
        try:
            img = self.screen() or img
        except Exception:
            pass
        if img is None:
            return None
        try:
            os.makedirs(self.stops_dir, exist_ok=True)
            name = datetime.datetime.now().strftime("stop-%Y%m%d-%H%M%S.png")
            p = os.path.join(self.stops_dir, name)
            img.save(p)
            log.info("stop screenshot saved: %s", p)
            return p
        except Exception:
            log.exception("couldn't save stop screenshot")
            return None

    def preflight(self) -> None:
        if not self.senses.ocr_ready():
            raise StopMacro("The text reader (Tesseract) isn't installed, so Beeline can't read the "
                            "Make Honey banner or the pollen numbers. Run: sudo apt install tesseract-ocr")
        for name in ("hive_to_field", "field_to_hive"):
            r = self.routes.get(name)
            if r is None or not r.events:
                raise StopMacro("No recorded route '%s' for hive slot %d. Record it on the Setup tab."
                                % (name.replace("_", " "), self.s.hive_slot))
        if self.s.run_seconds() <= 0:
            raise StopMacro("Run time is zero. Set 'Run for' first.")
        img = self.look()
        self.safety_check(img)
        if self.dry:
            seen = self.senses.look(img)
            self.dry_report = "banner %s, bag %d%% (%s), field check: %s, Saturator %s" % (
                {"make_honey": "'Make Honey'", "collect": "'Collect Pollen' (at hive, nothing to convert)",
                 "cannon": "'Fire the Red Cannon' (NOT the hive)"}.get(seen.banner, "not readable"),
                seen.bag or 0, seen.bag_source, seen.in_field_reason,
                "visible" if seen.saturator else "not visible")
            log.info("[dry run] start check: %s", self.dry_report)
        if not self.senses.at_hive(img):
            self.fail("Couldn't see the 'Make Honey' prompt. Stand on your hive pad, then press Start.")

    def _run(self) -> None:
        self.status("Checking everything is ready")
        self.preflight()
        if self.s.zoom_out_at_start:
            # Calibration was done fully zoomed out; make sure the camera matches.
            self.status("Zooming the camera fully out")
            self.inp.hold("o", 2.0)
        img = self.look()
        if self.bag(img) > 10:
            self.status("Converting what's already in the bag first")
            self.convert()
        first = True
        while True:
            if self.time_up():
                return
            self.walk_to_field(first)
            if first:
                self.place_saturator()
                first = False
            self.gather()
            self.walk_to_hive()
            self.convert()
            self.stats.trips += 1
            if self.time_up() or self.dry:
                return

    # ------------------------------------------------------------------ walking
    def _walk(self, route: Route, label: str, arrived, fail_msg: str) -> None:
        self.status(label)
        self.inp.mouse_up()
        replay(route, self.inp, check=self.safety_check, check_every=CHECK_EVERY,
               before_down=self._route_key_allowed)
        if self.dry:
            log.info("[dry run] nothing really moved, so not checking arrival (%s)", label)
            return
        limit = max(10.0, route.duration * (self.s.route_slack - 1.0) + 10.0)
        end = self.clock.now() + limit
        while True:
            img = self.look()
            self.safety_check(img)
            if arrived(img):
                return
            if self.clock.now() >= end:
                raise StopMacro(fail_msg)
            self.inp.sleep(0.5)

    def _route_key_allowed(self, key: str) -> None:
        """A recorded route may press E only to fire the Red Cannon, and only if the banner
        says so at that exact moment.  Otherwise the run stops (E is never pressed blindly)."""
        if key != "e" or self.dry:
            return
        img = self.look()
        banner = self.senses.banner(img)
        if banner != "cannon":
            raise StopMacro("Stopped: the route wanted to press E, but the banner says %s, not "
                            "'Fire the Red Cannon'" % ({"make_honey": "'Make Honey'"}.get(banner, "nothing")))
        log.info("route: banner says Fire the Red Cannon, pressing E")

    def walk_to_field(self, first: bool) -> None:
        self._walk(self.routes["hive_to_field"], "Walking to " + self.s.field, self.senses.in_field,
                   "Stopped: route to the field took too long (didn't arrive in %s)" % self.s.field)
        self._last_bag = None
        self._outside_field_checks = 0

    def walk_to_hive(self) -> None:
        self.inp.mouse_up()
        self.recentre()
        self._walk(self.routes["field_to_hive"], "Walking to hive", self.senses.at_hive,
                   "Stopped: walking home took too long (no Make Honey prompt)")

    # ------------------------------------------------------------------ Saturator
    def place_saturator(self) -> None:
        img = self.look()
        if self.senses.saturator_visible(img):
            log.info("Saturator already visible; not pressing 2")
            self.guard.placed = True
            self._set_anchor(img)
            return
        self.status("Placing Supreme Saturator")
        if self.dry:
            ok = self.senses.in_field(img)
            log.warning("[dry run] would press 2 (Saturator) here: %s",
                        "in the field, OK" if ok else "NOT confirmed in the field, so it would refuse")
            return
        self.guard.place_sprinkler(
            grind_start=True,
            confirm_in_field=lambda: self.senses.in_field(self.look()),
            saturator_visible=lambda: self.senses.saturator_visible(self.look()),
        )
        seen = self._wait_for_saturator(6.0)
        self.guard.report_result(seen)
        if not seen and self.guard.can_press():
            log.warning("Saturator not seen; one retry allowed by settings")
            self.inp.sleep(1.5)
            self.guard.place_sprinkler(
                grind_start=True,
                confirm_in_field=lambda: self.senses.in_field(self.look()),
                saturator_visible=lambda: self.senses.saturator_visible(self.look()),
            )
            seen = self._wait_for_saturator(6.0)
            self.guard.report_result(seen)
        if seen:
            self._set_anchor(self.look())
        else:
            log.warning("Saturator not visible after placing; gathering with time-based loops only")

    def _wait_for_saturator(self, seconds: float) -> bool:
        end = self.clock.now() + seconds
        while self.clock.now() < end:
            self.inp.sleep(1.0)
            img = self.look()
            self.safety_check(img)
            if self.senses.saturator_visible(img):
                return True
        return False

    def _set_anchor(self, img) -> None:
        b = self.senses.saturator(img)
        if b is not None and b.visible(self.cal.saturator_min_count):
            self.anchor = (b.cx, b.cy)
            log.info("Saturator anchor on screen at (%.0f, %.0f)", b.cx, b.cy)

    def drift_correction(self, img, tol_x: float = 0.039, tol_y: float = 0.056) -> list:
        """Moves that bring us back towards the Saturator.  Screen right = 'd', screen
        up (further ahead with shift lock) = 'w'.  Moves are proportional to how far off
        we are, so repeated small corrections settle on the spot."""
        if not self.s.drift_compensation or self.anchor is None:
            return []
        b = self.senses.saturator(img)
        if b is None or not b.visible(self.cal.saturator_min_count):
            return []
        W, H = img.size   # work in fractions of the screen, so any size works
        dx = (b.cx - self.anchor[0]) / W
        dy = (b.cy - self.anchor[1]) / H
        moves = []
        if abs(dx) > tol_x:
            moves.append(("d" if dx > 0 else "a", min(0.8, abs(dx) * 4.3)))
        if abs(dy) > tol_y:
            moves.append(("w" if dy < 0 else "s", min(0.8, abs(dy) * 3.6)))
        return moves

    def recentre(self, max_steps: int = 6) -> None:
        """Before walking home, stand as close as possible to where the route home was
        recorded from (next to the Saturator), so the walk ends on the hive pad."""
        for _ in range(max_steps):
            img = self.look()
            moves = self.drift_correction(img, tol_x=0.0094, tol_y=0.014)
            if not moves:
                return
            for key, secs in moves:
                self.inp.hold(key, secs)
            self.inp.sleep(0.3)  # let the camera settle before looking again

    # ------------------------------------------------------------------ gathering
    def gather(self) -> None:
        trip_start = self.clock.now()
        threshold = float(self.s.convert_percent)
        pattern = PATTERNS.get(self.s.loop_size, PATTERNS["small"])
        cx, cy = self.inp.hold_point()
        self.inp.mouse_down(cx, cy)   # swing the Petal Wand
        cycles = 0
        try:
            while True:
                cycles += 1
                if self.dry and cycles > 2:
                    log.info("[dry run] stopping the gathering rehearsal after 2 loops")
                    return
                img = self.look()
                self.safety_check(img)
                bag = self.bag(img)
                self.status("Gathering in %s - bag %d%%" % (self.s.field, bag))
                if not self.dry:  # in a dry run we never actually got to the field
                    self.check_bag_sane(bag)
                    self.check_still_in_field(img)
                if bag >= threshold:
                    log.info("bag %.0f%% >= %.0f%%: heading home", bag, threshold)
                    return
                if self.time_up():
                    log.info("time limit reached: final trip home")
                    return
                if self.clock.now() - trip_start > self.s.max_trip_minutes * 60:
                    log.info("max trip time reached (bag reads %.0f%%): heading home", bag)
                    return
                for key, secs in self.drift_correction(img):
                    self.inp.hold(key, secs)
                for key, secs in pattern:
                    if secs > 0:
                        self.inp.hold(key, secs)
                if not self.inp.mouse_held:
                    self.inp.mouse_down(cx, cy)
        finally:
            self.inp.mouse_up()

    def check_bag_sane(self, bag: float) -> None:
        last = self._last_bag
        self._last_bag = bag
        if last is None:
            return
        if last >= 25 and bag <= 5:
            self.fail("Stopped: bag suddenly emptied in the field (%d%% -> %d%%). "
                            "Your character probably died." % (last, bag))
        if bag < last - 30:
            self.fail("Stopped: bag reading makes no sense (%d%% -> %d%%)" % (last, bag))

    def check_still_in_field(self, img) -> None:
        other = self.senses.wrong_field(img)
        if other:
            self._wrong_field += 1
            if self._wrong_field >= 2:
                self.fail("Stopped: the notifications say I'm gathering in %s, not %s" % (other, self.s.field))
        else:
            self._wrong_field = 0
        if self.senses.in_field(img):
            self._outside_field_checks = 0
            return
        self._outside_field_checks += 1
        if self._outside_field_checks >= 4:
            self.fail("Stopped: no longer in %s (wandered off, or died and respawned?)" % self.s.field)

    # ------------------------------------------------------------------ converting
    def convert(self) -> None:
        img = self.look()
        banner = self.senses.banner(img)
        start_bag = self.bag(img)
        if banner == "collect" and start_bag <= BAG_EMPTY_PCT and not self.dry:
            log.info("nothing to convert (banner says Collect Pollen)")
            self.wait_for_balloon()
            return
        # E is ONLY ever pressed when the banner says "Make Honey" (not the cannon, not anything else)
        if not self.dry and banner != "make_honey":
            raise StopMacro("Stopped: not on my hive pad (the banner doesn't say Make Honey)")
        self.status("Converting bag (%d%%)" % start_bag)
        self.inp.tap("e")  # once - pressing again can toggle converting off
        t0 = self.clock.now()
        started = start_bag <= BAG_EMPTY_PCT
        checks = 0
        while True:
            checks += 1
            if self.dry and checks > 2:
                log.info("[dry run] not waiting for the bag to empty (nothing was really pressed)")
                break
            self.wait(CHECK_EVERY)
            img = self.look()
            self.safety_check(img)
            bag = self.bag(img)
            self.status("Converting bag (%d%%)" % bag)
            if bag <= BAG_EMPTY_PCT:
                self.wait(4)  # let the last bit of pollen finish before looking at the balloon
                break
            if bag < start_bag - 2:
                started = True
            if not started and self.clock.now() - t0 > CONVERT_START_TIMEOUT:
                self.fail("Stopped: converting didn't start after pressing E")
                break
            if self.clock.now() - t0 > CONVERT_MAX:
                self.fail("Stopped: bag took too long to convert")
                break
        self.wait_for_balloon()

    def wait_for_balloon(self) -> None:
        """Always wait for the hive balloon to finish converting before leaving the hive.
        Leaving early is a known duplication glitch, so this is never skipped.  "Done" means
        pollen reads 0 AND the banner says "Collect Pollen..." (or the notifications say the
        hive balloon granted/refreshed the Balloon Blessing), twice in a row.  Balloons on
        screen don't count: neighbours' balloons are always there.  If it takes too long we
        STOP at the hive (we never walk off mid-conversion)."""
        self.status("Converting balloon")
        t0 = self.clock.now()
        done_count = 0
        limit = self.s.balloon_max_wait_min * 60
        checks = 0
        while True:
            checks += 1
            if self.dry and checks > 3:
                log.info("[dry run] not waiting for the balloon (nothing was really pressed)")
                return
            img = self.look()
            self.safety_check(img)
            done_count = done_count + 1 if self.senses.converting_done(img) else 0
            if done_count >= 2:
                log.info("bag and hive balloon converted (%.0f s)", self.clock.now() - t0)
                return
            if self.clock.now() - t0 > limit:
                raise StopMacro("Stopped at the hive: the balloon was still converting after %d minutes. "
                                "Nothing was lost; the macro just won't leave mid-balloon."
                                % self.s.balloon_max_wait_min)
            self.status("Converting balloon (%d s)" % (self.clock.now() - t0))
            self.wait(CHECK_EVERY)
