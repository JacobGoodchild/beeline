"""Draws a pretend Bee Swarm screen that looks like Jacob's real screenshots: Honey and
Pollen bars with numbers, the E box + blue banner, notification feed, hotbar, menu icons,
blue/white flower field with pine trees, hives with neighbours' balloons, and a neon-cyan
Saturator with a gold top.  Everything is placed by proportions (any size works) using
the same layout as bss.LAYOUT, so the real screen reader is exercised by the practice game.
"""

from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

from . import bss

FONT_PATHS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
_font_cache: dict = {}


def font(px: int):
    px = max(6, int(px))
    if px not in _font_cache:
        f = None
        for p in FONT_PATHS:
            if os.path.exists(p):
                f = ImageFont.truetype(p, px)
                break
        if f is None:
            try:
                f = ImageFont.load_default(size=px)
            except TypeError:
                f = ImageFont.load_default()
        _font_cache[px] = f
    return _font_cache[px]


def fmt(n: int) -> str:
    return "{:,}".format(int(n))


SATURATOR_CYAN = (0, 217, 253)


def draw(W: int = 1920, H: int = 1080, *, current: int = 0, capacity: int = 32442211,
         honey: int = 7705462943, gathering_rate: int = 0, banner: str = "", in_field: bool = False,
         my_balloon: bool = False, saturator_at: tuple | None = None, feed: list | None = None,
         dialog: bool = False, tick: int = 0) -> Image.Image:
    """banner: "make_honey", "cannon", "collect", "stop" or "".  saturator_at: fractions (fx, fy)."""
    img = Image.new("RGB", (W, H), (120, 180, 230))
    d = ImageDraw.Draw(img)
    horizon = int(H * 0.38)
    if in_field:
        d.rectangle((0, horizon, W, H), fill=(60, 150, 70))
        cell = max(6, W // 64)
        for gy in range(horizon + cell, H, cell):
            for gx in range((gy // cell) % 2 * cell // 2, W, cell):
                k = (gx // cell * 7 + gy // cell * 3 + tick) % 7
                if k in (0, 1, 2):
                    d.ellipse((gx, gy, gx + cell * 0.6, gy + cell * 0.6), fill=(40, 70, 225))      # blue flowers
                elif k == 3:
                    d.ellipse((gx, gy, gx + cell * 0.6, gy + cell * 0.6), fill=(240, 240, 245))   # white flowers
        for tx in (0.33, 0.70):   # dark pine trees
            x = int(W * tx)
            d.polygon([(x, int(H * 0.08)), (x - W * 0.07, int(H * 0.42)), (x + W * 0.07, int(H * 0.42))],
                      fill=(30, 85, 45))
        d.rectangle((int(W * 0.40), int(H * 0.10), int(W * 0.62), int(H * 0.36)), fill=(80, 80, 85))  # rock wall
    else:
        d.rectangle((0, horizon, W, H), fill=(50, 160, 70))
        for i in range(5):   # hives in a row (mine is the middle one)
            x = int(W * (0.06 + i * 0.2))
            d.rectangle((x, int(H * 0.15), x + int(W * 0.13), int(H * 0.50)), fill=(220, 175, 40),
                        outline=(120, 90, 20), width=3)
            d.ellipse((x - W * 0.01, int(H * 0.48), x + W * 0.14, int(H * 0.60)), fill=(240, 240, 235))
        # neighbours' balloons (always there) - dark blue, NOT cyan
        for (bx, by, r) in ((0.21, 0.40, 0.065), (0.79, 0.50, 0.045)):
            d.ellipse((W * (bx - r), H * by - W * r, W * (bx + r), H * by + W * r), fill=(45, 70, 190))
        if my_balloon:
            d.ellipse((W * 0.50, H * 0.50, W * 0.56, H * 0.61), fill=(45, 75, 200))
    # bees buzzing (screen always changes a bit)
    for i in range(8):
        bx = int(W * (0.3 + ((tick * 37 + i * 97) % 400) / 1000))
        by = int(H * (0.45 + ((tick * 23 + i * 41) % 120) / 1000))
        d.ellipse((bx, by, bx + W * 0.008, by + W * 0.006), fill=(250, 210, 30))
    # the player in the middle
    d.ellipse((W * 0.485, H * 0.50, W * 0.515, H * 0.60), fill=(110, 75, 40))
    if saturator_at is not None:
        sx, sy = W * saturator_at[0], H * saturator_at[1]
        w, h = W * 0.022, H * 0.07
        d.rounded_rectangle((sx - w, sy - h / 2, sx + w, sy + h / 2), radius=int(w / 3), fill=SATURATOR_CYAN)
        d.ellipse((sx - w * 0.5, sy - h / 2 - w * 0.9, sx + w * 0.5, sy - h / 2 + w * 0.1), fill=(225, 190, 50))
    # ---------------- UI ----------------
    # top-left Roblox buttons + menu icons
    for i in range(4):
        d.rounded_rectangle((W * (0.006 + i * 0.022), H * 0.01, W * (0.024 + i * 0.022), H * 0.05),
                            radius=6, fill=(30, 30, 35))
    for i in range(6):
        d.ellipse((W * (0.006 + i * 0.026), H * 0.10, W * (0.024 + i * 0.026), H * 0.14), fill=(235, 235, 235))
    # top-right "?"
    d.ellipse((W * 0.952, H * 0.10, W * 0.970, H * 0.135), fill=(220, 40, 40))
    # Honey bar
    f = font(H * 0.0125)
    d.rounded_rectangle((W * 0.363, H * 0.018, W * 0.496, H * 0.056), radius=6, fill=(235, 230, 215))
    d.text((W * 0.367, H * 0.026), "Honey", fill=(40, 40, 40), font=f)
    d.rectangle((W * 0.39, H * 0.022, W * 0.49, H * 0.052), fill=(100, 98, 92))
    d.text((W * 0.393, H * 0.024), fmt(honey), fill=(245, 225, 120), font=font(H * 0.016))
    # Pollen bar
    d.rounded_rectangle((W * 0.500, H * 0.018, W * 0.634, H * 0.056), radius=6, fill=(235, 230, 215))
    d.text((W * 0.503, H * 0.026), "Pollen", fill=(40, 40, 40), font=f)
    bx0, bx1 = W * 0.5265, W * 0.631
    d.rectangle((bx0, H * 0.022, bx1, H * 0.052), fill=(105, 104, 100))
    frac = max(0.0, min(1.0, current / float(capacity))) if capacity else 0.0
    if frac > 0:
        col = (66, 250, 136) if frac < 0.5 else (153, 133, 81)
        d.rectangle((bx0, H * 0.022, bx0 + (bx1 - bx0) * frac, H * 0.052), fill=col)
    text = "%s/%s" % (fmt(current), fmt(capacity))
    if gathering_rate:
        text += " (+%s/sec)" % fmt(gathering_rate)
    d.text((W * 0.5295, H * 0.0285), text, fill=(255, 255, 255), font=font(H * 0.0115))
    # E box + banner
    texts = {"make_honey": "Make Honey", "cannon": "Fire the Red Cannon",
             "collect": "To Make Honey, Collect Pollen From Flower Fields", "stop": "Stop Making Honey"}
    if banner in ("make_honey", "cannon", "stop"):
        d.rectangle((W * 0.419, H * 0.055, W * 0.450, H * 0.106), fill=(240, 240, 240), outline=(60, 60, 60))
        d.text((W * 0.428, H * 0.060), "E", fill=(60, 60, 60), font=font(H * 0.036))
        tw = d.textlength(texts[banner], font=font(H * 0.030))
        d.rectangle((W * 0.452, H * 0.058, W * 0.460 + tw, H * 0.104), fill=(50, 110, 220))
        d.text((W * 0.456, H * 0.062), texts[banner], fill=(255, 255, 255), font=font(H * 0.030))
    elif banner == "collect":
        tw = d.textlength(texts[banner], font=font(H * 0.022))
        d.rectangle((W * 0.452, H * 0.062, W * 0.458 + tw, H * 0.100), fill=(50, 110, 220))
        d.text((W * 0.455, H * 0.066), texts[banner], fill=(255, 255, 255), font=font(H * 0.022))
    # hotbar + ability icons
    for i in range(7):
        x = W * (0.383 + i * 0.035)
        d.rounded_rectangle((x, H * 0.905, x + W * 0.030, H * 0.97), radius=6, fill=(225, 225, 225),
                            outline=(250, 250, 250), width=2)
    for i in range(8):
        d.ellipse((W * (0.385 + i * 0.018), H * 0.86, W * (0.399 + i * 0.018), H * 0.888), fill=(120, 140, 40))
    # notification feed
    lines = list(feed or [])[-3:]
    for i, line in enumerate(reversed(lines)):
        y = H * (0.965 - i * 0.03)
        d.rectangle((W * 0.835, y - H * 0.012, W * 0.995, y + H * 0.013), fill=(40, 90, 200))
        d.text((W * 0.84, y - H * 0.010), line, fill=(255, 255, 255), font=font(H * 0.016))
    if dialog:
        dim = Image.new("RGB", (W, H), (0, 0, 0))
        img = Image.blend(img, dim, 0.6)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((W * 0.31, H * 0.33, W * 0.69, H * 0.67), radius=10, fill=(57, 59, 61))
        d.text((W * 0.44, H * 0.38), "Disconnected", fill=(255, 255, 255), font=font(H * 0.03))
        d.text((W * 0.35, H * 0.45), "You were kicked for being idle 20 minutes", fill=(255, 255, 255),
               font=font(H * 0.022))
    return img


assert bss.LAYOUT  # same layout family
