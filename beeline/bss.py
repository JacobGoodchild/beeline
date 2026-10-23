"""Reading the REAL Bee Swarm screen (layout learned from Jacob's screenshots).

Everything here only LOOKS at screenshots of the game area.  Positions are fractions of
the game area (never fixed pixels), so it works at any window size.  Defaults come from
the screenshots in screenshots/; calibration on Jacob's PC can fine-tune them.

Signals:
  * pollen numbers "current/capacity" by OCR (Tesseract), cross-checked with the bar fill
  * the banner under the bars: "Make Honey" / "Fire the Red Cannon" /
    "To Make Honey, Collect Pollen From Flower Fields"
  * the notification feed (bottom right): "(from Pine Tree Forest)", balloon messages
  * the ground: blue + white flowers on green = a blue field
  * the Supreme Saturator: a solid, very saturated cyan patch of the right size
"""

from __future__ import annotations

import io
import re
import shutil
import subprocess
from dataclasses import dataclass

from PIL import Image, ImageChops, ImageOps

# Fractions (x0, y0, x1, y1) of the GAME AREA (the Sober window without its title bar).
LAYOUT = {
    "pollen_text": (0.527, 0.020, 0.634, 0.052),
    "pollen_bar": (0.5275, 0.630, 0.046),      # x0, x1, y of a row through the bar below the text
    "banner": (0.45, 0.052, 0.80, 0.108),       # the words next to the E box
    "banner_wide": (0.30, 0.052, 0.80, 0.108),  # "To Make Honey, Collect Pollen..." may be wider
    "ebox": (0.419, 0.052, 0.451, 0.108),
    "feed": (0.80, 0.82, 1.0, 0.995),
    "ground": (0.20, 0.55, 0.80, 0.88),
    "world": (0.15, 0.13, 0.95, 0.86),          # where the Saturator can be (not the UI)
    "hive_name": (0.40, 0.10, 0.62, 0.17),      # "Popcat989" on the hive sign (when visible)
}

# Areas the mouse must never click (fractions of the game area), from the screenshots.
NO_CLICK = {
    "top-left Roblox buttons, buffs and menu icons": (0.0, 0.0, 0.16, 0.16),
    "top-centre Honey/Pollen bars and banner": (0.36, 0.0, 0.64, 0.13),
    "top-right ? button": (0.94, 0.08, 0.99, 0.15),
    "bottom hotbar and ability icons": (0.37, 0.88, 0.68, 1.0),
    "bottom-right notification feed": (0.83, 0.86, 1.0, 1.0),
    "bottom-left lock button": (0.0, 0.95, 0.03, 1.0),
}

# Desktop screenshots (like the ones in screenshots/) include Sober's title bar and the
# Mint taskbar.  The hidden screen doesn't.  These fractions crop a desktop screenshot.
DESKTOP_GAME_TOP = 28 / 1125
DESKTOP_GAME_BOTTOM = 1088 / 1125


def crop_desktop_screenshot(img: Image.Image) -> Image.Image:
    W, H = img.size
    return img.crop((0, int(H * DESKTOP_GAME_TOP), W, int(H * DESKTOP_GAME_BOTTOM)))


def region(img: Image.Image, box) -> Image.Image:
    W, H = img.size
    x0, y0, x1, y1 = box
    return img.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))


# ---------------------------------------------------------------------------
# OCR (Tesseract, a separate program: sudo apt install tesseract-ocr)
# ---------------------------------------------------------------------------

def ocr_available() -> bool:
    return shutil.which("tesseract") is not None


def tesseract(img: Image.Image, psm: int = 7, whitelist: str | None = None) -> str:
    if not ocr_available():
        return ""
    args = ["tesseract", "stdin", "stdout", "--psm", str(psm)]
    if whitelist:
        args += ["-c", "tessedit_char_whitelist=" + whitelist]
    buf = io.BytesIO()
    img.save(buf, "PNG")
    try:
        r = subprocess.run(args, input=buf.getvalue(), capture_output=True, timeout=10)
    except Exception:
        return ""
    return r.stdout.decode("utf-8", "replace").strip()


def _scaled_grey(img: Image.Image, target_h: int = 90) -> Image.Image:
    g = img.convert("L")
    s = max(1.0, target_h / max(1, g.height))
    return g.resize((max(1, int(g.width * s)), max(1, int(g.height * s))), Image.LANCZOS)


_NUM = r"(\d{1,3}(?:,\d{3})*)"
_POLLEN_START_RE = re.compile(_NUM + r"/" + _NUM + r"(?!\d)")


def parse_pollen(text: str):
    """'2,348,365/32,442,211' -> (2348365, 32442211).  Strict: the commas must group
    properly, so a misread like '21348,365' is rejected rather than guessed."""
    t = text.replace(" ", "").replace(".", ",")
    # The numbers must start the text: a stray mark inside the first number (e.g. "2)348,365")
    # must not turn it into a different, smaller number.
    m = _POLLEN_START_RE.match(t)
    if m:
        cur, cap = int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))
        if cap > 0 and cur <= cap:
            return cur, cap
    return None


def classify_banner(text: str) -> str:
    t = " ".join(text.lower().split())
    if "collect" in t or "flower field" in t or "pollen from" in t:
        return "collect"          # nothing left to convert
    if "cannon" in t:
        return "cannon"
    if "make honey" in t or "make hone" in t or "ake honey" in t:
        return "make_honey"
    return ""


def feed_field(text: str) -> str | None:
    """The field named in the notification feed, e.g. '(from Pine Tree Forest)'."""
    t = " ".join(text.lower().split())
    if "pine tree" in t:
        return "Pine Tree Forest"
    m = re.search(r"from ([a-z ]+?) field", t)
    if m:
        return m.group(1).strip().title() + " Field"
    return None


def feed_balloon_done(text: str) -> bool:
    t = " ".join(text.lower().split())
    return "balloon" in t and ("refreshed" in t or "granted" in t or "blessing" in t)


# ---------------------------------------------------------------------------
# The reader
# ---------------------------------------------------------------------------

@dataclass
class Bag:
    percent: float | None          # 0-100, or None if it couldn't be read
    current: int | None = None
    capacity: int | None = None
    bar_percent: float | None = None
    source: str = ""               # "ocr", "bar", "ocr+bar"
    disagree: bool = False         # OCR and the bar fill disagree a lot (something's wrong)
    gathering: bool = False        # "(+N/sec)" rate text shown = pollen is coming in


@dataclass
class Blob:
    count: int
    cx: float
    cy: float
    w: int = 0
    h: int = 0
    fill: float = 0.0

    def visible(self, min_count: int = 1) -> bool:
        return self.count >= min_count


TOP_CENTRE_KEYS = ("pollen_text", "banner", "banner_wide", "ebox", "hive_name")


def scaled_layout(base: dict, ui_scale: float) -> dict:
    """Roblox may draw its interface a bit bigger or smaller relative to the window than in
    Jacob's screenshots.  Scale the read areas: the bars/banner grow from the top centre,
    the notification feed from the bottom-right corner."""
    k = float(ui_scale)
    out = dict(base)
    if abs(k - 1.0) < 1e-6:
        return out
    for key in TOP_CENTRE_KEYS:
        x0, y0, x1, y1 = base[key]
        out[key] = (0.5 + (x0 - 0.5) * k, y0 * k, 0.5 + (x1 - 0.5) * k, y1 * k)
    x0, x1, y = base["pollen_bar"]
    out["pollen_bar"] = (0.5 + (x0 - 0.5) * k, 0.5 + (x1 - 0.5) * k, y * k)
    x0, y0, x1, y1 = base["feed"]
    out["feed"] = (1 - (1 - x0) * k, 1 - (1 - y0) * k, 1.0, 1.0)
    return out


class Reader:
    def __init__(self, layout: dict | None = None, use_ocr: bool = True, ui_scale: float = 1.0) -> None:
        self.layout = scaled_layout(LAYOUT, max(0.6, min(1.8, float(ui_scale or 1.0))))
        if layout:   # exact fine-tuning (e.g. the clicked bar ends) wins over the scale
            self.layout.update({k: tuple(v) for k, v in layout.items()})
        self.use_ocr = use_ocr and ocr_available()
        # Saturator colour test (PIL HSV units 0-255).  From the screenshots: hue ~189 deg,
        # saturation ~1.0, value ~1.0.  Pale tool rings and the swirl are less saturated.
        self.sat_hue = (182, 198)
        self.sat_min_s = 0.80
        self.sat_min_v = 0.70

    # -- OCR hooks (tests replace ocr_text to avoid running Tesseract thousands of times) --
    def ocr_text(self, img: Image.Image, kind: str) -> str:
        if not self.use_ocr:
            return ""
        if kind == "pollen":
            crop = region(img, self.layout["pollen_text"])
            outs = []
            for h, mode in ((90, "white"), (90, "thr"), (60, "thr"), (120, "thr"), (90, "grey")):
                g = _scaled_grey(crop, h)
                if mode == "white":
                    # keep only pixels that are white in ALL colours: the bright green fill
                    # (which looks light grey in black-and-white) is dropped
                    c = crop.convert("RGB").resize(g.size, Image.LANCZOS)
                    r_, g_, b_ = c.split()
                    m = ImageChops.darker(ImageChops.darker(r_, g_), b_)
                    g = m.point(lambda p: 0 if p > 165 else 255)
                elif mode == "thr":  # keep only the light digits
                    g = g.point(lambda p: 0 if p > 170 else 255)
                outs.append(tesseract(g, 7, "0123456789,/()+sec"))
                if parse_pollen(outs[-1]):
                    text = outs[-1]
                    if mode == "white" and "+" not in text and "sec" not in text:
                        # the "(+N/sec)" rate text isn't pure white: one more pass to catch it
                        g2 = _scaled_grey(crop, 90).point(lambda p: 0 if p > 170 else 255)
                        text += " || " + tesseract(g2, 7, "0123456789,/()+sec")
                    return text
            return " || ".join(outs)
        if kind == "banner":
            outs = []
            for box in ("banner", "banner_wide"):
                g = _scaled_grey(region(img, self.layout[box]), 110)
                for variant in (ImageOps.invert(g), g):
                    outs.append(tesseract(variant, 7))
                    if classify_banner(outs[-1]):
                        return outs[-1]
            return " || ".join(outs)
        if kind == "feed":
            g = _scaled_grey(region(img, self.layout["feed"]), 260)
            return tesseract(ImageOps.invert(g), 6)
        if kind == "hive_name":
            g = _scaled_grey(region(img, self.layout["hive_name"]), 110)
            return tesseract(g, 7)
        return ""

    # -- bag -----------------------------------------------------------------
    def bar_percent(self, img: Image.Image) -> float:
        """Fill of the pollen bar: a column counts as filled if it's colourful or bright
        (the empty part is a see-through grey).  Fill colour changes with fullness, so no
        fixed colour is used."""
        W, H = img.size
        x0, x1, y = self.layout["pollen_bar"]
        n = 80
        row = img.convert("RGB").crop((int(x0 * W), max(0, int(y * H) - 1),
                                       int(x1 * W), int(y * H) + 2)).resize((n, 1), Image.BILINEAR)
        filled = []
        for (r, g, b) in row.getdata():
            mx, mn = max(r, g, b), min(r, g, b)
            sat = (mx - mn) / mx if mx else 0
            filled.append(sat >= 0.28 or mx >= 140)
        best = count = 0
        for i, f in enumerate(filled):
            count += 1 if f else 0
            if f and count >= 0.85 * (i + 1):
                best = i + 1
        return 100.0 * best / n

    def bag(self, img: Image.Image) -> Bag:
        bar = self.bar_percent(img)
        text = self.ocr_text(img, "pollen")
        parsed = parse_pollen(text) if text else None
        gathering = "+" in text or "sec" in text
        if parsed:
            cur, cap = parsed
            pct = 100.0 * cur / cap
            gap = abs(pct - bar)
            if gap > 4:
                # OCR can drop a leading group ("348,365" for "2,348,365") and still look
                # valid, so when the two disagree the bar wins.  A huge gap = something's wrong.
                return Bag(bar, None, cap, bar, "bar (ocr disagreed: %.1f%%)" % pct, gap > 20, gathering)
            return Bag(pct, cur, cap, bar, "ocr+bar", False, gathering)
        return Bag(bar, None, None, bar, "bar", False, gathering)

    # -- banner / feed ----------------------------------------------------------
    def banner(self, img: Image.Image) -> str:
        return classify_banner(self.ocr_text(img, "banner"))

    def feed(self, img: Image.Image) -> str:
        return self.ocr_text(img, "feed")

    def at_my_hive_name(self, img: Image.Image, name: str = "Popcat989") -> bool | None:
        """Extra check: is Jacob's name readable on the hive sign?  None = can't tell."""
        t = self.ocr_text(img, "hive_name").lower().replace(" ", "")
        if not t:
            return None
        return name.lower() in t or name.lower()[:6] in t

    # -- field ground ------------------------------------------------------------
    def ground_scores(self, img: Image.Image) -> tuple:
        r = region(img, self.layout["ground"]).convert("RGB").resize((240, 100)).convert("HSV")
        px = list(r.getdata())
        n = float(len(px))
        blue = sum(1 for h, s, v in px if 145 <= h <= 167 and s > 110 and v > 120) / n
        green = sum(1 for h, s, v in px if 64 <= h <= 106 and s > 80 and v > 80) / n
        return blue, green

    def ground_is_blue_field(self, img: Image.Image) -> bool:
        blue, green = self.ground_scores(img)
        return blue >= 0.07 and green >= 0.15

    # -- Saturator ---------------------------------------------------------------
    def saturator(self, img: Image.Image, work_w: int = 400) -> Blob:
        """Biggest solid patch of the Saturator's neon cyan, if it has a believable size
        and shape.  Returns Blob(0, ...) if there's none."""
        W, H = img.size
        wx0, wy0, wx1, wy1 = self.layout["world"]
        crop = region(img, self.layout["world"]).convert("RGB")
        sw = work_w
        sh = max(1, int(crop.height * sw / max(1, crop.width)))
        small = crop.resize((sw, sh), Image.BILINEAR).convert("HSV")
        h0, h1 = self.sat_hue[0] * 255 / 360, self.sat_hue[1] * 255 / 360
        smin, vmin = self.sat_min_s * 255, self.sat_min_v * 255
        hits = set(i for i, (h, s, v) in enumerate(small.getdata()) if h0 <= h <= h1 and s >= smin and v >= vmin)
        best = None
        seen = set()
        for start in hits:
            if start in seen:
                continue
            seen.add(start)
            comp, stack = [start], [start]
            while stack:
                i = stack.pop()
                x, y = i % sw, i // sw
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        j = ny * sw + nx
                        if 0 <= nx < sw and 0 <= ny < sh and j in hits and j not in seen:
                            seen.add(j)
                            comp.append(j)
                            stack.append(j)
            if best is None or len(comp) > len(best):
                best = comp
        if not best:
            return Blob(0, -1, -1)
        xs = [i % sw for i in best]
        ys = [i // sw for i in best]
        bw, bh = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
        fill = len(best) / float(bw * bh)
        area = sw * sh
        n = len(best)
        # believable: 0.03% .. 4% of the view, solid-ish, not a thin ring or a line
        if not (0.0003 * area <= n <= 0.04 * area and fill >= 0.3 and 0.3 <= bw / float(bh) <= 3.5):
            return Blob(0, -1, -1)
        cx = (wx0 + (sum(xs) / n + 0.5) / sw * (wx1 - wx0)) * W
        cy = (wy0 + (sum(ys) / n + 0.5) / sh * (wy1 - wy0)) * H
        return Blob(n, cx, cy, bw, bh, round(fill, 2))


def converting_done(bag: Bag, banner: str, feed_text: str = "") -> bool:
    """Bag AND hive balloon finished: pollen reads 0 and the banner has changed to
    "To Make Honey, Collect Pollen From Flower Fields" (or the feed says the hive balloon
    granted/refreshed the Balloon Blessing).  Balloons on screen are NOT used: neighbours'
    balloons are always visible."""
    empty = (bag.current == 0) if bag.current is not None else (bag.percent is not None and bag.percent <= 1.0)
    return empty and (banner == "collect" or feed_balloon_done(feed_text))


def in_field_check(reader: "Reader", img, field_name: str = "Pine Tree Forest", bag: Bag | None = None,
                   feed_text: str | None = None) -> tuple:
    """(in_field, reason).  Ground must look like a blue field, plus at least one of:
    the feed names this field, pollen is coming in, or the Saturator is in view.
    If the feed names a DIFFERENT field, it's False."""
    if not reader.ground_is_blue_field(img):
        return False, "ground doesn't look like a blue field"
    text = reader.feed(img) if feed_text is None else feed_text
    named = feed_field(text)
    if named and named != field_name:
        return False, "the notifications say %s" % named
    if named == field_name:
        return True, "notifications say %s" % field_name
    if bag is not None and bag.gathering:
        return True, "blue field + pollen coming in"
    if reader.saturator(img).visible():
        return True, "blue field + Saturator in view"
    return False, "blue field, but nothing confirms it's %s yet" % field_name
