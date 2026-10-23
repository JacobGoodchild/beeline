"""`python3 beeline.py --check picture.png [more.png ...]`

Prints everything Beeline reads from screenshots of the game, so readings can be
checked (and sent to Claude) without running the macro.  Works on screenshots of the
hidden screen and on normal desktop screenshots of the Sober window (title bar and
taskbar are trimmed off automatically)."""

from __future__ import annotations

import sys

from PIL import Image, ImageStat

from . import bss
from .config import Calibration
from .senses import Senses


def looks_like_desktop_screenshot(img: Image.Image) -> bool:
    W, H = img.size
    top = ImageStat.Stat(img.crop((0, 0, W, max(1, int(H * 0.015)))).convert("L")).mean[0]
    bottom = ImageStat.Stat(img.crop((0, int(H * 0.975), W, H)).convert("L")).mean[0]
    return top > 200 and bottom < 80   # light Sober title bar + dark Mint taskbar


def check(path: str) -> str:
    img = Image.open(path).convert("RGB")
    trimmed = looks_like_desktop_screenshot(img)
    if trimmed:
        img = bss.crop_desktop_screenshot(img)
    senses = Senses(Calibration.load())
    s = senses.look(img)
    lines = [
        "%s  (%dx%d%s)" % (path, img.width, img.height, ", title bar/taskbar trimmed" if trimmed else ""),
        "  bag:              %s  [%s]%s" % ("?" if s.bag is None else "%.1f%%" % s.bag, s.bag_source,
                                            ("  numbers " + s.pollen_text) if s.pollen_text else ""),
        "  banner:           %s" % (s.banner or "nothing readable"),
        "  converting done:  %s" % ("YES" if s.converting_done else "no"),
        "  Saturator:        %s" % ("SEEN at %.0f%% across, %.0f%% down" % (
            100 * s.saturator_xy[0] / img.width, 100 * s.saturator_xy[1] / img.height) if s.saturator else "not seen"),
        "  in the field:     %s (%s)" % ("YES" if s.in_field else "no", s.in_field_reason),
        "  feed names:       %s" % (s.feed_field or "-"),
        "  disconnect box:   %s" % ("YES" if s.dialog else "no"),
    ]
    if not bss.ocr_available():
        lines.append("  NOTE: Tesseract isn't installed, so text wasn't read (sudo apt install tesseract-ocr)")
    return "\n".join(lines)


def main(paths) -> None:
    if not paths:
        print(__doc__)
        return
    for p in paths:
        try:
            print(check(p))
        except Exception as e:
            print("%s: couldn't check it (%s)" % (p, e))


if __name__ == "__main__":
    main(sys.argv[1:])
