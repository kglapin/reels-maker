"""Tests for the taktowanie iso film: dispatch, copy, card, cameras."""
import unittest

from reels_maker.iso.film import (
    TAKT_CARD,
    cyc,
    frame_at,
    render_iso_frame,
    tstate,
    world_cam_takt,
)
from reels_maker.iso.projection import Canvas, DEFAULT_PALETTE


def _frame(film, t0, w=270, h=480, copy=None):
    spec = {"t0": t0, "snow": 0, "logo": None, "font": None,
            "film": film, "copy": copy}
    return render_iso_frame(spec, w, h, 1.0)


class TaktFilmTest(unittest.TestCase):
    def test_zones_render_without_crash(self):
        for t0 in (0.0, 7.0, 15.0, 22.0, 30.0, 37.0, 44.0, 45.0, 52.0,
                   59.0, 60.0, 67.0, 74.0, 75.0, 82.0, 89.0, 90.0, 95.0,
                   100.0, 104.0):
            with self.subTest(t0=t0):
                im = _frame("taktowanie", t0)
                self.assertEqual(im.size, (270, 480))

    def test_cyc_square_wave(self):
        self.assertEqual(cyc(10.0), 0.0)
        self.assertEqual(cyc(31.0), 1.0)
        self.assertEqual(cyc(36.0), 0.0)
        self.assertEqual(cyc(50.0), 0.0)

    def test_state_mild(self):
        st = tstate(20.0, dict(DEFAULT_PALETTE))
        self.assertEqual(st["frost"], 0.0)
        self.assertGreater(st["speed"], 0.0)
        st = tstate(50.0, dict(DEFAULT_PALETTE))
        self.assertEqual(st["speed"], 0.0)

    def test_copy_override_titles_frames(self):
        im = _frame("taktowanie", 0.0,
                    copy={"title": "WERDYKT TESTU", "body": ["linia pierwsza"]})
        self.assertEqual(im.size, (270, 480))

    def test_photo_scene_keeps_copy_layout(self):
        photo = ("imports/photos/blog-taktowanie/"
                 "taktowanie-pompy-ciepla-hero.jpg")
        im, boxes = frame_at(2.0, dict(DEFAULT_PALETTE), None, None, None,
                             snow=0, film="taktowanie",
                             copy_override={"title": "FOTO TEST",
                                            "body": ["linia"]},
                             scene_time=2.0, photo_path=photo)
        texts = [b[0] for b in boxes]
        self.assertIn("FOTO TEST", texts)
        plain, _ = frame_at(2.0, dict(DEFAULT_PALETTE), None, None, None,
                            snow=0, film="taktowanie",
                            copy_override={"title": "FOTO TEST",
                                           "body": ["linia"]},
                            scene_time=2.0, photo_path=None)
        self.assertNotEqual(list(im.getdata()), list(plain.getdata()))

    def test_missing_photo_falls_back_to_world(self):
        im, boxes = frame_at(2.0, dict(DEFAULT_PALETTE), None, None, None,
                             snow=0, film="taktowanie",
                             copy_override={"title": "FOTO TEST",
                                            "body": ["linia"]},
                             scene_time=2.0,
                             photo_path="imports/photos/nie-ma.jpg")
        self.assertIn("FOTO TEST", [b[0] for b in boxes])

    def test_minimalist_card(self):
        im, boxes = frame_at(104.0, dict(DEFAULT_PALETTE), None, None,
                             None, snow=0, film="taktowanie",
                             copy_override=None, scene_time=4.0)
        texts = [b[0] for b in boxes]
        self.assertIn("67 350 90 90", texts)
        self.assertFalse(any("Pn–pt" in t for t in texts))
        self.assertFalse(any("Ilustracja poglądowa" in t for t in texts))

    def test_card_uses_takt_beats(self):
        im, boxes = frame_at(100.5, dict(DEFAULT_PALETTE), None, None,
                             None, snow=0, film="taktowanie",
                             copy_override=None, scene_time=1.0)
        self.assertEqual(im.size, (1080, 1920))
        texts = [b[0] for b in boxes]
        self.assertIn(TAKT_CARD[0][1], texts)

    def test_zone_framing_inside_canvas(self):
        # (film time, extreme world points) per scenario zone, checked at
        # zone middle AND zone end (cameras move: push, pull, pan); every
        # point must project inside the 1840x1500 canvas with margin,
        # otherwise the gallery-style crop complaints return in motion.
        zones = [
            ([7.0, 14.5], [(-3.92, -3.52, 0.0), (-0.18, 0.22, 0.0),
                           (-2.05, -1.65, 3.55), (0.32, -1.6, 1.05)]),
            ([22.0, 29.5], [(0.08, -2.25, 0.0), (0.56, -1.0, 0.0),
                            (0.08, -2.25, 1.0), (0.56, -1.0, 1.0)]),
            ([37.0, 44.5], [(5.6, 0.1, 0.0), (6.4, 0.9, 0.0),
                            (5.6, 0.1, 0.75), (6.4, 0.9, 0.75)]),
            ([52.0, 59.5], [(4.3, 3.7, -0.1), (7.7, 3.7, -0.1),
                            (4.3, 6.6, -0.1), (7.7, 6.6, -0.1),
                            (4.3, 3.7, 2.1), (7.7, 3.7, 2.1),
                            (4.3, 6.6, 2.1), (7.7, 6.6, 2.1)]),
            ([67.0, 74.5], [(5.3, -3.2, 0.0), (6.7, -2.9, 0.0),
                            (5.3, -3.2, 1.75), (6.7, -2.9, 1.75)]),
            ([82.0, 89.5], [(-1.2, 4.8, 0.0), (1.6, 6.0, 0.0),
                            (-1.2, 4.8, 1.6), (1.6, 6.0, 1.6)]),
            ([95.0, 99.5], [(-3.92, -3.52, 0.0), (-0.18, 0.22, 0.0),
                            (-2.05, -1.65, 3.55)]),
        ]
        for times, pts in zones:
            for u in times:
                with self.subTest(u=u):
                    q = Canvas(dict(DEFAULT_PALETTE)["bg"],
                               *world_cam_takt(u))
                    for p in pts:
                        x, y = q._raw(p)
                        self.assertGreaterEqual(x, 80, f"{p} left")
                        self.assertLessEqual(x, 1840 - 80, f"{p} right")
                        self.assertGreaterEqual(y, 80, f"{p} top")
                        self.assertLessEqual(y, 1500 - 80, f"{p} bottom")


if __name__ == "__main__":
    unittest.main()
