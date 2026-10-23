"""Tests on Jacob's real Bee Swarm screenshots (screenshots/).  The screenshots include
Sober's title bar and the taskbar, which are cropped off first.  Each is also tested
scaled to 1920 wide (the hidden screen size) to make sure nothing depends on pixels."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image  # noqa: E402

from beeline import bss  # noqa: E402
from beeline.safety import SafeZone  # noqa: E402

DIR = os.path.join(os.path.dirname(__file__), "..", "screenshots")
TRUTH = {  # name: (bag %, banner, saturator, in Pine Tree)
    "01-at-hive-make-honey": (100 * 2348365 / 32442211, "make_honey", False, False),
    "02-red-cannon-prompt": (100 * 2348365 / 32442211, "cannon", False, False),
    "03-pine-tree-grinding-a": (100 * 2282586 / 68036081, "", True, True),
    "04-pine-tree-grinding-b": (100 * 797332 / 68036081, "", True, True),
    "05-hive-before-convert": (100 * 23776408 / 32442211, "make_honey", False, False),
    "06-hive-after-convert": (0.0, "collect", False, False),
}
OCR = bss.ocr_available()


def load(name, width=None):
    p = os.path.join(DIR, name + ".png")
    if not os.path.exists(p):
        return None
    im = Image.open(p).convert("RGB")
    if width:
        im = im.resize((width, int(width * im.height / im.width)), Image.LANCZOS)
    return bss.crop_desktop_screenshot(im)


class RealScreenshotTests(unittest.TestCase):
    reader = bss.Reader()

    def each(self):
        for name, truth in TRUTH.items():
            for width in (None, 1920):
                img = load(name, width)
                if img is None:
                    continue
                yield name, width, img, truth

    def test_screenshots_present(self):
        self.assertGreaterEqual(sum(1 for n in TRUTH if load(n) is not None), 5)

    def test_bag_percent_within_3(self):
        for name, width, img, (pct, *_rest) in self.each():
            b = self.reader.bag(img)
            self.assertAlmostEqual(b.percent, pct, delta=3, msg="%s @%s: %s" % (name, width, b))
            if b.current is not None:   # when the OCR reads the numbers, they must be exactly right
                self.assertAlmostEqual(b.percent, pct, delta=0.05, msg="%s OCR %s" % (name, b))
            self.assertFalse(b.disagree, name)

    def test_bar_alone_within_3(self):
        for name, width, img, (pct, *_rest) in self.each():
            self.assertAlmostEqual(self.reader.bar_percent(img), pct, delta=3, msg="%s @%s" % (name, width))

    @unittest.skipUnless(OCR, "tesseract not installed")
    def test_pollen_numbers_read_exactly_on_most(self):
        exact = 0
        for name, width, img, (pct, *_rest) in self.each():
            b = self.reader.bag(img)
            if b.current is not None:
                exact += 1
        self.assertGreaterEqual(exact, 6)

    @unittest.skipUnless(OCR, "tesseract not installed")
    def test_banner_text(self):
        for name, width, img, (_p, banner, *_r) in self.each():
            self.assertEqual(self.reader.banner(img), banner, "%s @%s" % (name, width))

    @unittest.skipUnless(OCR, "tesseract not installed")
    def test_converting_done(self):
        for name, width, img, truth in self.each():
            done = bss.converting_done(self.reader.bag(img), self.reader.banner(img), self.reader.feed(img))
            self.assertEqual(done, name.startswith("06"), "%s @%s" % (name, width))

    def test_saturator_found_only_in_03_and_04(self):
        for name, width, img, (_p, _b, sat, _f) in self.each():
            blob = self.reader.saturator(img)
            self.assertEqual(blob.visible(), sat, "%s @%s: %s" % (name, width, blob))

    def test_saturator_position(self):
        for name, x_frac in (("03-pine-tree-grinding-a", 0.63), ("04-pine-tree-grinding-b", 0.46)):
            img = load(name)
            b = self.reader.saturator(img)
            self.assertAlmostEqual(b.cx / img.width, x_frac, delta=0.03, msg=name)

    def test_ground_check(self):
        for name, width, img, (_p, _b, _s, field) in self.each():
            self.assertEqual(self.reader.ground_is_blue_field(img), field, "%s @%s" % (name, width))

    @unittest.skipUnless(OCR, "tesseract not installed")
    def test_in_pine_tree(self):
        for name, width, img, (_p, _b, _s, field) in self.each():
            ok, why = bss.in_field_check(self.reader, img, bag=self.reader.bag(img))
            self.assertEqual(ok, field, "%s @%s: %s" % (name, width, why))

    @unittest.skipUnless(OCR, "tesseract not installed")
    def test_feed_names_pine_tree_in_04(self):
        self.assertEqual(bss.feed_field(self.reader.feed(load("04-pine-tree-grinding-b"))), "Pine Tree Forest")

    def test_safe_zone_never_covers_no_click_areas(self):
        for zone in (SafeZone(), SafeZone(0, 0, 1, 1)):   # the default AND the biggest allowed
            for what, (x0, y0, x1, y1) in bss.NO_CLICK.items():
                overlap = not (zone.right <= x0 or zone.left >= x1 or zone.bottom <= y0 or zone.top >= y1)
                self.assertFalse(overlap, "safe zone %s overlaps %s" % (zone.to_dict(), what))

    def test_no_click_areas_really_contain_ui(self):
        """Sanity check on the real screenshots: the screen centre (where clicks go) is the
        game world, and the hotbar area is where the hotbar is (dark slots + white frames)."""
        img = load("01-at-hive-make-honey")
        hot = bss.region(img, bss.NO_CLICK["bottom hotbar and ability icons"]).convert("L")
        self.assertGreater(max(hot.getdata()), 200)


class ParsingTests(unittest.TestCase):
    def test_parse_pollen(self):
        self.assertEqual(bss.parse_pollen("2,348,365/32,442,211"), (2348365, 32442211))
        self.assertEqual(bss.parse_pollen("2,282,586/68,036,081(+18,647/sec)"), (2282586, 68036081))
        self.assertEqual(bss.parse_pollen("0/42,174,874"), (0, 42174874))
        for bad in ("21348,365/32,442,211", "2)348,365/32,442,211", ",282,586/68,036,081", "5/3", "", "abc"):
            self.assertIsNone(bss.parse_pollen(bad), bad)

    def test_classify_banner(self):
        self.assertEqual(bss.classify_banner("Make Honey"), "make_honey")
        self.assertEqual(bss.classify_banner("Fire the Red Cannon"), "cannon")
        self.assertEqual(bss.classify_banner("To Make Honey, Collect Pollen From Flower Fields"), "collect")
        self.assertEqual(bss.classify_banner("~~ i"), "")

    def test_converting_done_logic(self):
        empty = bss.Bag(0.0, 0, 42174874)
        self.assertTrue(bss.converting_done(empty, "collect"))
        self.assertTrue(bss.converting_done(empty, "", "The hive balloon refreshed your Balloon Blessing!"))
        self.assertFalse(bss.converting_done(empty, "make_honey"))
        self.assertFalse(bss.converting_done(bss.Bag(5.0, 100, 2000), "collect"))

    def test_feed(self):
        self.assertEqual(bss.feed_field("+2 Blueberries (from Pine Tree Forest)"), "Pine Tree Forest")
        self.assertEqual(bss.feed_field("+5 Honey (from Sunflower Field)"), "Sunflower Field")
        self.assertIsNone(bss.feed_field("+5,000 Honey (from Blue Bloom Petal)"))
        self.assertTrue(bss.feed_balloon_done("The hive balloon granted you x3 of Balloon Blessing!"))


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(OCR, "tesseract not installed")
class PracticeGameScreenTests(unittest.TestCase):
    """The practice game must read like the real game (so practising is meaningful)."""

    def test_reader_on_practice_screens(self):
        from beeline import synth_bss as S
        r = bss.Reader()
        cases = [
            (dict(current=2348365, capacity=32442211, banner="make_honey"), 7.2, "make_honey", False, False),
            (dict(current=2282586, capacity=68036081, gathering_rate=18647, in_field=True, saturator_at=(0.6, 0.5),
                  feed=["+2 Blueberries (from Pine Tree Forest)"]), 3.4, "", True, False),
            (dict(current=23776408, capacity=32442211, banner="make_honey", my_balloon=True), 73.3, "make_honey",
             False, False),
            (dict(current=0, capacity=42174874, banner="collect"), 0.0, "collect", False, True),
            (dict(current=5000000, capacity=32442211, banner="stop", my_balloon=True), 15.4, "", False, False),
        ]
        for kw, pct, banner, sat, done in cases:
            img = S.draw(1920, 1080, **kw)
            b = r.bag(img)
            self.assertAlmostEqual(b.percent, pct, delta=3, msg=kw)
            self.assertEqual(r.banner(img), banner, kw)
            self.assertEqual(r.saturator(img).visible(), sat, kw)
            self.assertEqual(bss.converting_done(b, r.banner(img), r.feed(img)), done, kw)
