"""Draws fake Bee Swarm-like screenshots.  Used by the tests and the fake game so the
whole macro can be checked without Roblox.  The layout matches what fakegame.py draws.
"""

from __future__ import annotations

from PIL import Image, ImageDraw

W, H = 1280, 720

BAG_LEFT = (522, 38)
BAG_RIGHT = (758, 38)
BAG_BOX = (520, 26, 760, 42)
BAG_EMPTY = (55, 55, 60)
BAG_FILL = (250, 196, 40)

EPROMPT_BOX = (590, 80, 100, 44)
BALLOON_BOX = (880, 170, 160, 160)
FIELD_BOX = (440, 470, 400, 140)
SATURATOR_COLOUR = (20, 200, 255)


def draw_scene(bag: float = 0.0, eprompt: bool = False, balloon: bool = False,
               in_field: bool = False, saturator_at: tuple | None = None,
               dialog: bool = False, tick: int = 0) -> Image.Image:
    img = Image.new("RGB", (W, H), (110, 160, 90))  # grass
    d = ImageDraw.Draw(img)
    # sky
    d.rectangle((0, 0, W, 200), fill=(140, 190, 235))
    if in_field:
        # Pine Tree Forest: blue + white flowers on the ground
        for gy in range(220, H, 20):
            for gx in range(0, W, 20):
                col = (70, 110, 230) if (gx // 20 + gy // 20 + tick) % 3 else (235, 235, 245)
                d.rectangle((gx, gy, gx + 19, gy + 19), fill=col)
    else:
        # hive area: wooden hives and dirt path
        d.rectangle((0, 220, W, H), fill=(150, 120, 80))
        for i in range(6):
            d.rectangle((150 + i * 170, 120, 270 + i * 170, 330), fill=(200, 160, 60), outline=(90, 60, 20))
    # a few bees buzzing about (they move every tick, so the screen is never frozen)
    for i in range(6):
        bx = 320 + ((tick * 37 + i * 97) % 520)
        by = 232 + ((tick * 23 + i * 41) % 60)
        d.ellipse((bx, by, bx + 16, by + 12), fill=(250, 210, 30))
    # the player (always in the middle)
    d.ellipse((620, 380, 660, 440), fill=(240, 200, 150))
    if saturator_at is not None:
        sx, sy = saturator_at
        d.rectangle((sx - 6, sy, sx + 6, sy + 60), fill=(230, 190, 40))  # golden pipe
        d.ellipse((sx - 26, sy - 26, sx + 26, sy + 26), fill=SATURATOR_COLOUR)  # neon blue bear head
    if balloon:
        x, y, w, h = BALLOON_BOX
        d.ellipse((x + 20, y + 10, x + w - 20, y + h - 30), fill=(60, 140, 255), outline=(255, 255, 255))
        d.line((x + w // 2, y + h - 30, x + w // 2, y + h), fill=(255, 255, 255), width=2)
    # --- UI on top ---
    # inventory side panel on the left
    d.rectangle((0, 120, 200, 640), fill=(45, 45, 50))
    for i in range(6):
        d.rectangle((15, 140 + i * 80, 185, 200 + i * 80), fill=(80, 80, 90))
    # hotbar at the bottom
    for i in range(7):
        d.rectangle((390 + i * 72, 650, 450 + i * 72, 710), fill=(30, 30, 30), outline=(220, 220, 220))
    # top bar
    d.rectangle((0, 0, W, 20), fill=(20, 20, 20))
    # bag meter
    x0, y0, x1, y1 = BAG_BOX
    d.rectangle(BAG_BOX, fill=BAG_EMPTY)
    fill_to = x0 + int((x1 - x0) * max(0.0, min(1.0, bag / 100.0)))
    if fill_to > x0:
        d.rectangle((x0, y0, fill_to, y1), fill=BAG_FILL)
    d.text((610, 27), "%d / 100" % int(bag), fill=(255, 255, 255))  # text over the bar
    if eprompt:
        x, y, w, h = EPROMPT_BOX
        d.rounded_rectangle((x, y, x + w, y + h), radius=8, fill=(250, 250, 250), outline=(0, 0, 0), width=2)
        d.rectangle((x + 10, y + 8, x + 38, y + 36), fill=(30, 30, 30))
        d.text((x + 20, y + 15), "E", fill=(255, 255, 255))
        d.text((x + 46, y + 15), "Honey", fill=(0, 0, 0))
    if dialog:
        # Roblox disconnect box over a dimmed screen
        dim = Image.new("RGB", (W, H), (0, 0, 0))
        img = Image.blend(img, dim, 0.6)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((400, 240, 880, 480), radius=10, fill=(57, 59, 61))
        d.text((560, 280), "Disconnected", fill=(255, 255, 255))
        d.text((470, 330), "You were kicked for being idle 20 minutes", fill=(255, 255, 255))
        d.rectangle((560, 410, 720, 450), fill=(255, 255, 255))
    return img
