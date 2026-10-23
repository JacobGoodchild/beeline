"""What the macro can 'see'.  Built on bss.Reader (the real Bee Swarm layout, defaults
from Jacob's screenshots) plus optional fine-tuning from calibration.

Each method takes a screenshot.  Results for the same screenshot are cached, because
the main loop asks several questions about one look and OCR takes a moment.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import bss, vision
from .config import Calibration


@dataclass
class Seen:
    """One look at the screen, summarised (for logs, dry runs and the Test buttons)."""
    bag: float | None = None
    bag_source: str = ""
    pollen_text: str = ""
    banner: str = ""
    feed_field: str | None = None
    converting_done: bool = False
    saturator: bool = False
    saturator_xy: tuple = (-1.0, -1.0)
    ground_blue_field: bool = False
    in_field: bool = False
    in_field_reason: str = ""
    balloon: str = "unknown"
    dialog: bool = False


class Senses:
    def __init__(self, cal: Calibration, field_name: str = "Pine Tree Forest",
                 reader: bss.Reader | None = None) -> None:
        self.cal = cal
        self.field_name = field_name
        self.reader = reader or bss.Reader(layout=getattr(cal, "layout", None) or None)
        if getattr(cal, "saturator_hue", None):
            self.reader.sat_hue = tuple(cal.saturator_hue)
        self._img = None
        self._cache: dict = {}

    def ocr_ready(self) -> bool:
        return self.reader.use_ocr

    def _cached(self, img, key, fn):
        if img is not self._img:
            self._img = img
            self._cache = {}
        if key not in self._cache:
            self._cache[key] = fn()
        return self._cache[key]

    # -- bag ---------------------------------------------------------------------
    def bag(self, img) -> bss.Bag:
        return self._cached(img, "bag", lambda: self.reader.bag(img))

    def bag_percent(self, img) -> float | None:
        return self.bag(img).percent

    # -- hive ---------------------------------------------------------------------
    def banner(self, img) -> str:
        return self._cached(img, "banner", lambda: self.reader.banner(img))

    def eprompt_visible(self, img) -> bool:
        """True only when the banner says "Make Honey" (NOT the cannon or anything else)."""
        return self.banner(img) == "make_honey"

    def at_hive(self, img) -> bool:
        """On the hive pad: "Make Honey", or "Collect Pollen..." when there's nothing to convert."""
        return self.banner(img) in ("make_honey", "collect")

    def feed(self, img) -> str:
        return self._cached(img, "feed", lambda: self.reader.feed(img))

    def balloon_state(self, img) -> str:
        """Optional extra signal: the calibrated spot in front of MY pad only."""
        c = self.cal
        if not c.balloon_ready():
            return "unknown"
        return vision.classify_balloon(img, tuple(c.balloon_box), c.balloon_present_img, c.balloon_gone_img)

    def converting_done(self, img) -> bool:
        done = bss.converting_done(self.bag(img), self.banner(img), self.feed(img))
        if done and self.balloon_state(img) == "present":
            return False   # my own balloon is still there (only if Jacob calibrated that spot)
        return done

    # -- field ---------------------------------------------------------------------
    def saturator(self, img) -> bss.Blob:
        return self._cached(img, "sat", lambda: self.reader.saturator(img))

    def saturator_visible(self, img) -> bool:
        return self.saturator(img).visible()

    def in_field(self, img) -> bool:
        """Arrival check: the ground looks like a blue field and the notifications don't
        name a different field."""
        if not self.reader.ground_is_blue_field(img):
            return False
        return not self.wrong_field(img)

    def wrong_field(self, img) -> str | None:
        named = bss.feed_field(self.feed(img))
        return named if (named and named != self.field_name) else None

    def field_confirmed(self, img) -> tuple:
        return bss.in_field_check(self.reader, img, self.field_name, self.bag(img), self.feed(img))

    def look(self, img) -> Seen:
        s = Seen()
        b = self.bag(img)
        s.bag, s.bag_source = b.percent, b.source
        if b.current is not None:
            s.pollen_text = "{:,}/{:,}".format(b.current, b.capacity)
        s.banner = self.banner(img)
        s.feed_field = bss.feed_field(self.feed(img))
        s.converting_done = self.converting_done(img)
        blob = self.saturator(img)
        s.saturator, s.saturator_xy = blob.visible(), (blob.cx, blob.cy)
        s.ground_blue_field = self.reader.ground_is_blue_field(img)
        s.in_field, s.in_field_reason = self.field_confirmed(img)
        s.balloon = self.balloon_state(img)
        s.dialog = vision.looks_like_disconnect_dialog(img)
        return s
