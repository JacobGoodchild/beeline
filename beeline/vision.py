"""Screen reading: simple colour checks and small template matches on screenshots of
the hidden screen.  Pure Pillow, no OCR, no AI, nothing that touches the game.

All functions take a PIL RGB screenshot (the whole hidden screen) plus calibration data.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageChops, ImageFilter, ImageStat


def colour_distance(a, b) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def mean_colour(img: Image.Image) -> tuple:
    s = ImageStat.Stat(img.convert("RGB"))
    return tuple(int(round(v)) for v in s.mean[:3])


def _band_colour(img: Image.Image, x: int, y: int, half: int = 1) -> tuple:
    """Median colour of a tiny square around (x, y) so one stray pixel doesn't matter."""
    w, h = img.size
    box = (max(0, x - half), max(0, y - half), min(w, x + half + 1), min(h, y + half + 1))
    s = ImageStat.Stat(img.crop(box))
    return tuple(int(v) for v in s.median[:3])


# ---------------------------------------------------------------------------
# Bag (pollen) meter
# ---------------------------------------------------------------------------

def bag_sample_points(left: tuple, right: tuple, n: int = 60) -> list:
    (x0, y0), (x1, y1) = left, right
    return [(int(round(x0 + (x1 - x0) * i / (n - 1))), int(round(y0 + (y1 - y0) * i / (n - 1))))
            for i in range(n)]


def sample_bag_colours(img: Image.Image, left: tuple, right: tuple, n: int = 60) -> list:
    return [_band_colour(img, x, y) for (x, y) in bag_sample_points(left, right, n)]


def read_bag_percent(img: Image.Image, left: tuple, right: tuple, empty_colours: list,
                     fill_colour: tuple | None = None, threshold: float = 60.0) -> float:
    """How full the bag bar is, 0-100.

    empty_colours: the colours along the bar captured when the bag was EMPTY.
    fill_colour:   optional colour of the filled part (captured when the bag was full).
    A point counts as filled if it is closer to fill_colour than to its empty colour
    (or, with no fill colour, if it differs from the empty colour by > threshold).
    The answer is the furthest point from the left where at least 80% of points so
    far are filled - so a few pixels hidden by text don't throw the reading off.
    """
    n = len(empty_colours)
    if n < 2:
        raise ValueError("bag meter not calibrated")
    cols = sample_bag_colours(img, left, right, n)
    filled = []
    for c, e in zip(cols, empty_colours):
        if fill_colour is not None:
            filled.append(colour_distance(c, fill_colour) + 10 < colour_distance(c, e))
        else:
            filled.append(colour_distance(c, e) > threshold)
    best = 0
    count = 0
    for i, f in enumerate(filled):
        count += 1 if f else 0
        if f and count >= 0.8 * (i + 1):
            best = i + 1
    return 100.0 * best / n


# ---------------------------------------------------------------------------
# Template matching (E-prompt, etc.)
# ---------------------------------------------------------------------------

@dataclass
class Match:
    score: float  # 0..1, 1 = identical
    x: int        # top-left of the best match, screen pixels
    y: int

    def found(self, threshold: float) -> bool:
        return self.score >= threshold


def match_template(img: Image.Image, template: Image.Image, box: tuple, margin: int = 40,
                   scale: int = 2) -> Match:
    """Find `template` near `box` (x, y, w, h: where it was captured), searching
    `margin` pixels around it.  Returns the best score (1 = perfect)."""
    x, y, w, h = box
    W, H = img.size
    sx0, sy0 = max(0, x - margin), max(0, y - margin)
    sx1, sy1 = min(W, x + w + margin), min(H, y + h + margin)
    region = img.crop((sx0, sy0, sx1, sy1)).convert("RGB")
    tw, th = template.size
    if region.size[0] < tw or region.size[1] < th:
        return Match(0.0, x, y)
    s = max(1, scale)
    reg_s = region.resize((max(1, region.size[0] // s), max(1, region.size[1] // s)), Image.BILINEAR)
    tpl_s = template.convert("RGB").resize((max(1, tw // s), max(1, th // s)), Image.BILINEAR)
    tws, ths = tpl_s.size
    best = Match(0.0, x, y)
    rw, rh = reg_s.size
    for oy in range(0, rh - ths + 1):
        for ox in range(0, rw - tws + 1):
            diff = ImageChops.difference(reg_s.crop((ox, oy, ox + tws, oy + ths)), tpl_s)
            m = sum(ImageStat.Stat(diff).mean[:3]) / 3.0
            score = 1.0 - m / 255.0
            if score > best.score:
                best = Match(score, sx0 + ox * s, sy0 + oy * s)
    return best


# ---------------------------------------------------------------------------
# Region comparison (balloon present / gone)
# ---------------------------------------------------------------------------

def region_difference(a: Image.Image, b: Image.Image, size: tuple = (32, 32)) -> float:
    """Average colour difference 0..255 between two images after blurring and shrinking
    them (so bees flying past don't matter much)."""
    a2 = a.convert("RGB").resize(size, Image.BILINEAR).filter(ImageFilter.BoxBlur(1))
    b2 = b.convert("RGB").resize(size, Image.BILINEAR).filter(ImageFilter.BoxBlur(1))
    return sum(ImageStat.Stat(ImageChops.difference(a2, b2)).mean[:3]) / 3.0


def classify_balloon(img: Image.Image, box: tuple, present: Image.Image | None,
                     gone: Image.Image | None, margin: float = 6.0) -> str:
    """Return "present", "gone" or "unknown" for the hive balloon region."""
    x, y, w, h = box
    region = img.crop((x, y, x + w, y + h))
    if present is None and gone is None:
        return "unknown"
    dp = region_difference(region, present) if present is not None else None
    dg = region_difference(region, gone) if gone is not None else None
    if dp is not None and dg is not None:
        if dg + margin < dp:
            return "gone"
        if dp + margin < dg:
            return "present"
        return "unknown"
    if dp is not None:
        return "present" if dp < 20 else ("gone" if dp > 40 else "unknown")
    return "gone" if dg < 20 else ("present" if dg > 40 else "unknown")


# ---------------------------------------------------------------------------
# Colour blobs (Supreme Saturator)
# ---------------------------------------------------------------------------

def dominant_bright_colour(img: Image.Image) -> tuple:
    """The average of the most saturated, bright pixels in a sample (for the neon-blue
    Saturator head).  Used when Jacob captures the Saturator sample."""
    small = img.convert("RGB").resize((max(1, img.size[0] // 2), max(1, img.size[1] // 2)))
    px = list(small.getdata())

    def vividness(p):
        mx, mn = max(p), min(p)
        return (mx - mn) + mx * 0.3
    px.sort(key=vividness, reverse=True)
    top = px[:max(1, len(px) // 10)]
    return tuple(int(sum(p[i] for p in top) / len(top)) for i in range(3))


@dataclass
class Blob:
    count: int        # matching pixels (in the shrunken image)
    cx: float         # centre, screen pixels
    cy: float

    def visible(self, min_count: int) -> bool:
        return self.count >= min_count


def find_colour_blob(img: Image.Image, colour: tuple, tolerance: float = 45.0,
                     scale: int = 4, area: tuple | None = None) -> Blob:
    """Find pixels close to `colour`.  `area` (x0, y0, x1, y1) limits where to look, so the
    side panel / hotbar / top bar are ignored."""
    W, H = img.size
    if area is None:
        area = (int(W * 0.2), int(H * 0.12), int(W * 0.95), int(H * 0.82))
    x0, y0, x1, y1 = area
    crop = img.crop(area).convert("RGB")
    small = crop.resize((max(1, crop.size[0] // scale), max(1, crop.size[1] // scale)), Image.NEAREST)
    sw = small.size[0]
    n = 0
    sx = sy = 0.0
    tr, tg, tb = colour
    tol2 = tolerance * tolerance
    for i, (r, g, b) in enumerate(small.getdata()):
        if (r - tr) ** 2 + (g - tg) ** 2 + (b - tb) ** 2 <= tol2:
            n += 1
            sx += i % sw
            sy += i // sw
    if n == 0:
        return Blob(0, -1.0, -1.0)
    return Blob(n, x0 + (sx / n + 0.5) * scale, y0 + (sy / n + 0.5) * scale)


# ---------------------------------------------------------------------------
# Field ground check ("am I standing in Pine Tree Forest?")
# ---------------------------------------------------------------------------

def colour_histogram(img: Image.Image, levels: int = 4) -> list:
    """A coarse colour fingerprint: fraction of pixels in each of levels^3 colour bins."""
    small = img.convert("RGB").resize((48, 32), Image.BILINEAR)
    step = 256 // levels
    bins = [0] * (levels ** 3)
    px = list(small.getdata())
    for (r, g, b) in px:
        bins[(r // step) * levels * levels + (g // step) * levels + (b // step)] += 1
    total = float(len(px))
    return [v / total for v in bins]


def histogram_similarity(h1: list, h2: list) -> float:
    """1.0 = same colours, 0.0 = nothing in common."""
    return sum(min(a, b) for a, b in zip(h1, h2))


# ---------------------------------------------------------------------------
# Whole-screen checks
# ---------------------------------------------------------------------------

def thumbnail(img: Image.Image) -> Image.Image:
    return img.convert("L").resize((128, 72), Image.BILINEAR)


def frame_change(a: Image.Image, b: Image.Image) -> float:
    """How much two screenshots differ, 0..255 (tiny numbers = the screen is frozen)."""
    return ImageStat.Stat(ImageChops.difference(thumbnail(a), thumbnail(b))).mean[0]


def looks_like_disconnect_dialog(img: Image.Image) -> bool:
    """Roblox's 'Disconnected' / 'kicked for being idle' box: a big flat dark-grey panel
    in the middle of a dimmed screen.  Deliberately strict; the frozen-screen check is
    the main safety net and this just catches it sooner."""
    W, H = img.size
    centre = img.crop((int(W * 0.36), int(H * 0.40), int(W * 0.64), int(H * 0.58))).convert("RGB")
    small = centre.resize((40, 20), Image.NEAREST)
    px = list(small.getdata())
    med = tuple(int(v) for v in ImageStat.Stat(small).median[:3])
    if not (25 <= max(med) <= 95 and max(med) - min(med) <= 12):
        return False  # the panel colour must be a flat dark grey
    same = sum(1 for p in px if colour_distance(p, med) <= 14)
    if same < 0.65 * len(px):  # allow up to 35% for the white text on it
        return False
    # And the edges of the screen are dimmed (dark) behind it.
    edge = img.crop((0, int(H * 0.2), int(W * 0.15), int(H * 0.8))).convert("L")
    return ImageStat.Stat(edge).mean[0] < 70
