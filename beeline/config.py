"""Settings and calibration, saved as small files in the Beeline folder.

Nothing personal is stored except the hive slot.  No passwords, no cookies, ever.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field, fields

from PIL import Image

from . import vision
from .safety import SafeZone, is_main_desktop

log = logging.getLogger("beeline.config")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# Where settings, calibration, routes and logs live (the Beeline folder; tests point it elsewhere).
DATA = os.environ.get("BEELINE_DATA") or ROOT
SETTINGS_FILE = os.path.join(DATA, "settings.json")
CALIBRATION_DIR = os.path.join(DATA, "calibration")
ROUTES_DIR = os.path.join(DATA, "routes")
LOGS_DIR = os.path.join(DATA, "logs")

FIELDS = ["Pine Tree Forest"]  # more can be added later
SCREEN_SIZE = (1280, 720)       # the hidden screen is always this size


@dataclass
class Settings:
    field: str = "Pine Tree Forest"
    run_hours: int = 1
    run_minutes: int = 0
    convert_percent: int = 95
    convert_balloon: bool = True
    balloon_max_wait_min: float = 10.0
    loop_size: str = "small"          # "small" or "medium"
    hive_slot: int = 1
    dry_run: bool = True              # safe default: the first run shows what it WOULD press
    allow_sprinkler_retry: bool = False
    max_trip_minutes: float = 15.0    # backstop: walk home after this long gathering even if bag reads low
    drift_compensation: bool = True
    zoom_out_at_start: bool = True    # hold O for 2 s at the start so the view matches calibration
    display: str = ":5"
    screen_mode: str = "xephyr"       # "xephyr" (visible window) or "xvfb" (fully hidden)
    xephyr_glamor: bool = False       # use the graphics card inside Xephyr (faster, may not work everywhere)
    stuck_screen_seconds: float = 60.0
    route_slack: float = 1.5          # stop if arrival isn't confirmed within route time x this (+10 s)

    def run_seconds(self) -> float:
        return max(0, int(self.run_hours)) * 3600 + max(0, int(self.run_minutes)) * 60

    def validate(self) -> None:
        self.convert_percent = max(10, min(100, int(self.convert_percent)))
        self.hive_slot = max(1, min(6, int(self.hive_slot)))
        if self.loop_size not in ("small", "medium"):
            self.loop_size = "small"
        if self.field not in FIELDS:
            self.field = FIELDS[0]
        if self.screen_mode not in ("xephyr", "xvfb"):
            self.screen_mode = "xephyr"
        if is_main_desktop(self.display):
            self.display = ":5"
        self.balloon_max_wait_min = max(1.0, min(30.0, float(self.balloon_max_wait_min)))
        self.max_trip_minutes = max(2.0, min(60.0, float(self.max_trip_minutes)))
        self.stuck_screen_seconds = max(20.0, min(300.0, float(self.stuck_screen_seconds)))
        self.route_slack = max(1.1, min(3.0, float(self.route_slack)))

    @classmethod
    def load(cls, path: str = SETTINGS_FILE) -> "Settings":
        s = cls()
        try:
            with open(path) as f:
                data = json.load(f)
            names = {f.name for f in fields(cls)}
            for k, v in data.items():
                if k in names:
                    setattr(s, k, v)
        except FileNotFoundError:
            pass
        except Exception:
            log.exception("settings file unreadable; using defaults")
        s.validate()
        return s

    def save(self, path: str = SETTINGS_FILE) -> None:
        self.validate()
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)


def _img_path(d: str, name: str) -> str:
    return os.path.join(d, name + ".png")


@dataclass
class Calibration:
    """Everything the macro learned about Jacob's screen during Setup."""

    bag_left: list | None = None            # [x, y]
    bag_right: list | None = None
    bag_empty_colours: list | None = None   # colours along the bar when EMPTY
    bag_fill_colour: list | None = None     # colour of the filled part (optional)

    eprompt_box: list | None = None         # [x, y, w, h]
    eprompt_threshold: float = 0.88

    balloon_box: list | None = None
    saturator_colour: list | None = None
    saturator_extra_colours: list = field(default_factory=list)  # e.g. a night-time sample
    saturator_min_count: int = 6
    saturator_tolerance: float = 40.0

    field_box: list | None = None
    field_histograms: dict = field(default_factory=dict)  # field name -> list of histograms (day, night...)
    field_threshold: float = 0.55

    safe_zone: dict = field(default_factory=lambda: SafeZone().to_dict())

    # images (not saved in the JSON, saved next to it as PNGs)
    eprompt_img: Image.Image | None = None
    balloon_present_img: Image.Image | None = None
    balloon_gone_img: Image.Image | None = None

    IMAGE_FIELDS = ("eprompt_img", "balloon_present_img", "balloon_gone_img")

    # -- what's done -------------------------------------------------------------
    def bag_ready(self) -> bool:
        return bool(self.bag_left and self.bag_right and self.bag_empty_colours)

    def eprompt_ready(self) -> bool:
        return bool(self.eprompt_box) and self.eprompt_img is not None

    def balloon_ready(self) -> bool:
        return bool(self.balloon_box) and (self.balloon_present_img is not None
                                           or self.balloon_gone_img is not None)

    def saturator_ready(self) -> bool:
        return bool(self.saturator_colour)

    def field_ready(self, field_name: str) -> bool:
        return bool(self.field_box) and bool(self.field_samples(field_name))

    def zone(self) -> SafeZone:
        return SafeZone.from_dict(self.safe_zone)

    def missing(self, field_name: str, convert_balloon: bool) -> list:
        out = []
        if not self.bag_ready():
            out.append("bag meter")
        if not self.eprompt_ready():
            out.append("E-prompt")
        if not self.saturator_ready():
            out.append("Saturator sample")
        if not self.field_ready(field_name):
            out.append("field ground sample")
        if convert_balloon and not self.balloon_ready():
            out.append("hive balloon samples")
        return out

    # -- capture helpers (called from the Setup tab) --------------------------
    def capture_bag(self, img: Image.Image, left, right, which: str = "empty") -> None:
        self.bag_left, self.bag_right = [int(left[0]), int(left[1])], [int(right[0]), int(right[1])]
        cols = vision.sample_bag_colours(img, tuple(self.bag_left), tuple(self.bag_right))
        if which == "empty":
            self.bag_empty_colours = [list(c) for c in cols]
        else:
            # full bag: average colour of the bar is the fill colour
            n = len(cols)
            self.bag_fill_colour = [int(sum(c[i] for c in cols) / n) for i in range(3)]

    def capture_eprompt(self, img: Image.Image, box) -> None:
        x, y, w, h = [int(v) for v in box]
        self.eprompt_box = [x, y, w, h]
        self.eprompt_img = img.crop((x, y, x + w, y + h)).copy()

    def capture_balloon(self, img: Image.Image, box, present: bool) -> None:
        x, y, w, h = [int(v) for v in box]
        self.balloon_box = [x, y, w, h]
        crop = img.crop((x, y, x + w, y + h)).copy()
        if present:
            self.balloon_present_img = crop
        else:
            self.balloon_gone_img = crop

    def capture_saturator(self, img: Image.Image, box, add: bool = False) -> None:
        """add=True keeps the existing sample and adds this one (e.g. at night)."""
        x, y, w, h = [int(v) for v in box]
        crop = img.crop((x, y, x + w, y + h))
        colour = list(vision.dominant_bright_colour(crop))
        blob = vision.find_colour_blob(img, tuple(colour), self.saturator_tolerance)
        count = max(4, int(blob.count * 0.25))
        if add and self.saturator_colour:
            self.saturator_extra_colours.append(colour)
            self.saturator_min_count = min(self.saturator_min_count, count)
        else:
            self.saturator_colour = colour
            self.saturator_extra_colours = []
            self.saturator_min_count = count

    def saturator_colours(self) -> list:
        return ([self.saturator_colour] if self.saturator_colour else []) + list(self.saturator_extra_colours)

    def field_samples(self, field_name: str) -> list:
        v = self.field_histograms.get(field_name) or []
        if v and not isinstance(v[0], list):  # older single-sample format
            v = [v]
        return v

    def capture_field(self, img: Image.Image, box, field_name: str, add: bool = False) -> None:
        """add=True keeps earlier samples (e.g. add a night-time one)."""
        x, y, w, h = [int(v) for v in box]
        self.field_box = [x, y, w, h]
        hist = vision.colour_histogram(img.crop((x, y, x + w, y + h)))
        samples = self.field_samples(field_name) if add else []
        self.field_histograms[field_name] = samples + [hist]

    def set_safe_zone(self, left, top, right, bottom) -> None:
        self.safe_zone = SafeZone(left, top, right, bottom).to_dict()

    # -- save / load ---------------------------------------------------------------
    def save(self, d: str = CALIBRATION_DIR) -> None:
        os.makedirs(d, exist_ok=True)
        data = {}
        for f in fields(self):
            if f.name in self.IMAGE_FIELDS:
                img = getattr(self, f.name)
                if img is not None:
                    img.save(_img_path(d, f.name))
                continue
            data[f.name] = getattr(self, f.name)
        with open(os.path.join(d, "calibration.json"), "w") as fh:
            json.dump(data, fh, indent=1)

    @classmethod
    def load(cls, d: str = CALIBRATION_DIR) -> "Calibration":
        c = cls()
        try:
            with open(os.path.join(d, "calibration.json")) as fh:
                data = json.load(fh)
            names = {f.name for f in fields(cls)}
            for k, v in data.items():
                if k in names and k not in cls.IMAGE_FIELDS:
                    setattr(c, k, v)
        except FileNotFoundError:
            return c
        except Exception:
            log.exception("calibration file unreadable")
        for name in cls.IMAGE_FIELDS:
            p = _img_path(d, name)
            if os.path.exists(p):
                with Image.open(p) as im:
                    setattr(c, name, im.convert("RGB").copy())
        c.safe_zone = SafeZone.from_dict(c.safe_zone).to_dict()  # never trust the file
        return c
