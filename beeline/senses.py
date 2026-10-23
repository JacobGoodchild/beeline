"""What the macro can 'see', using the calibration.  Each method takes a screenshot."""

from __future__ import annotations

from dataclasses import dataclass

from . import vision
from .config import Calibration


@dataclass
class Seen:
    """One look at the screen, summarised.  Handy for logs and the GUI's Test buttons."""
    bag: float | None = None
    eprompt: bool | None = None
    eprompt_score: float = 0.0
    balloon: str = "unknown"
    saturator: bool = False
    saturator_xy: tuple = (-1.0, -1.0)
    in_field: bool | None = None
    field_score: float = 0.0
    dialog: bool = False


class Senses:
    def __init__(self, cal: Calibration, field_name: str = "Pine Tree Forest") -> None:
        self.cal = cal
        self.field_name = field_name

    def bag_percent(self, img) -> float | None:
        c = self.cal
        if not c.bag_ready():
            return None
        return vision.read_bag_percent(img, tuple(c.bag_left), tuple(c.bag_right),
                                       [tuple(x) for x in c.bag_empty_colours],
                                       tuple(c.bag_fill_colour) if c.bag_fill_colour else None)

    def eprompt(self, img) -> vision.Match | None:
        c = self.cal
        if not c.eprompt_ready():
            return None
        return vision.match_template(img, c.eprompt_img, tuple(c.eprompt_box), margin=30)

    def eprompt_visible(self, img) -> bool:
        m = self.eprompt(img)
        return bool(m and m.found(self.cal.eprompt_threshold))

    def balloon_state(self, img) -> str:
        c = self.cal
        if not c.balloon_ready():
            return "unknown"
        return vision.classify_balloon(img, tuple(c.balloon_box), c.balloon_present_img, c.balloon_gone_img)

    def saturator(self, img) -> vision.Blob | None:
        c = self.cal
        if not c.saturator_ready():
            return None
        return vision.find_colour_blob(img, tuple(c.saturator_colour), c.saturator_tolerance)

    def saturator_visible(self, img) -> bool:
        b = self.saturator(img)
        return bool(b and b.visible(self.cal.saturator_min_count))

    def field_score(self, img) -> float:
        c = self.cal
        if not c.field_ready(self.field_name):
            return 0.0
        x, y, w, h = c.field_box
        hist = vision.colour_histogram(img.crop((x, y, x + w, y + h)))
        return vision.histogram_similarity(hist, c.field_histograms[self.field_name])

    def in_field(self, img) -> bool:
        return self.field_score(img) >= self.cal.field_threshold

    def look(self, img) -> Seen:
        s = Seen()
        s.bag = self.bag_percent(img)
        m = self.eprompt(img)
        if m is not None:
            s.eprompt_score = m.score
            s.eprompt = m.found(self.cal.eprompt_threshold)
        s.balloon = self.balloon_state(img)
        b = self.saturator(img)
        if b is not None:
            s.saturator = b.visible(self.cal.saturator_min_count)
            s.saturator_xy = (b.cx, b.cy)
        if self.cal.field_ready(self.field_name):
            s.field_score = self.field_score(img)
            s.in_field = s.field_score >= self.cal.field_threshold
        s.dialog = vision.looks_like_disconnect_dialog(img)
        return s
