"""Tests for the prop-showcase film: gallery props as clip worlds.

A manifest scene with ``film: prop`` + ``prop: <module>.<name>``
paints that registry prop (same painters the gallery gate verifies)
instead of a topic world. Unknown labels fail fast, never silent.
"""
import unittest

from reels_maker.iso.film import (
    _prop_window,
    _resolve_prop,
    render_iso_frame,
)
from reels_maker.iso.projection import DEFAULT_PALETTE


def _frame(prop, t=1.0, w=270, h=480):
    spec = {"t0": 0.0, "snow": 0, "logo": None, "font": None,
            "film": "prop", "prop": prop,
            "copy": {"title": "T", "body": ["B"]}}
    return render_iso_frame(spec, w, h, t)


def _nonbg(im):
    bg = tuple(DEFAULT_PALETTE["bg"][:3])
    px = im.convert("RGB").load()
    return sum(1 for x in range(0, im.width, 7)
               for y in range(0, im.height, 7)
               if px[x, y] != bg)


class PropFilmTest(unittest.TestCase):
    def test_registry_resolves(self):
        spec = _resolve_prop("props_heat_a.manifold")
        self.assertTrue(callable(spec["fn"]))

    def test_unknown_label_fails_fast(self):
        for bad in ("props_heat_a.nope", "nosuchmod.x", "no-dot",
                    None, ""):
            with self.subTest(label=bad):
                with self.assertRaises(ValueError):
                    _resolve_prop(bad)

    def test_window_paints_subject(self):
        im, _ = _prop_window("props_heat_a.manifold", 1.0,
                             dict(DEFAULT_PALETTE))
        self.assertEqual(im.size, (920, 750))
        self.assertGreater(_nonbg(im), 500)

    def test_frame_matches_clip_format(self):
        im = _frame("props_heat_a.manifold")
        self.assertEqual(im.size, (270, 480))
        self.assertGreater(_nonbg(im), 50)

    def test_push_in_moves_pixels(self):
        a = _frame("props_heat_a.manifold", t=0.5)
        b = _frame("props_heat_a.manifold", t=4.0)
        from PIL import ImageChops
        self.assertIsNotNone(
            ImageChops.difference(a.convert("RGB"),
                                  b.convert("RGB")).getbbox(),
            "showcase holds must breathe, never freeze")

    def test_photo_scene_paints_photo(self):
        import tempfile as _t
        from PIL import Image as _I
        with _t.NamedTemporaryFile(suffix=".png", delete=False) as fh:
            _I.new("RGB", (100, 100), (200, 30, 30)).save(fh.name)
            path = fh.name
        from reels_maker.iso.film import _photo_bg, _full_frame
        from reels_maker.iso.projection import DEFAULT_PALETTE
        photo = _photo_bg(path, dict(DEFAULT_PALETTE))
        self.assertIsNotNone(photo)
        self.assertEqual(photo.size, (1080, 1920))
        im, _, _ = _full_frame(5.0, dict(DEFAULT_PALETTE), None, None,
                               None, 0, "prop", path, "props_heat_a.manifold")
        self.assertEqual(im.size, (1080, 1920))

    def test_camera_moves(self):
        from reels_maker.iso.film import _prop_window
        from reels_maker.iso.projection import DEFAULT_PALETTE
        base, _ = _prop_window("props_heat_a.manifold", 4.0,
                                  dict(DEFAULT_PALETTE))
        for move in ("push", "pull", "pan-left", "pan-right", "still"):
            with self.subTest(move=move):
                im, _ = _prop_window(
                    "props_heat_a.manifold", 4.0, dict(DEFAULT_PALETTE),
                    {"move": move, "amount": 0.08})
                self.assertEqual(im.size, (920, 750))
        with self.assertRaises(ValueError):
            _prop_window("props_heat_a.manifold", 1.0,
                         dict(DEFAULT_PALETTE), {"move": "orbit"})
        self.assertIsNotNone(base)

    def test_photo_zoom_moves_pixels(self):
        import tempfile as _t
        from PIL import Image as _I, ImageChops as _C
        with _t.NamedTemporaryFile(suffix=".png",
                                    delete=False) as fh:
            _I.new("RGB", (200, 200), (30, 120, 60)).save(fh.name)
            path = fh.name
        from reels_maker.iso.film import _photo_bg, _duotone, E
        from reels_maker.iso.projection import DEFAULT_PALETTE
        P = dict(DEFAULT_PALETTE)
        a = _duotone(_photo_bg(path, P), P, 0.85)
        b = _duotone(_photo_bg(path, P), P, 0.1)
        self.assertIsNotNone(_C.difference(a, b).getbbox(),
                             "duotone strength is visible")
        self.assertEqual(E(0), 0.0)

    def test_photo_focus_anchors_crop(self):
        import tempfile as _t
        from PIL import Image as _I, ImageChops as _C
        with _t.NamedTemporaryFile(suffix=".png",
                                    delete=False) as fh:
            base = _I.new("RGB", (200, 400), (20, 20, 20))
            from PIL import ImageDraw as _D
            _D.Draw(base).rectangle([0, 0, 80, 400], fill=(230, 30, 30))
            base.save(fh.name)
            path = fh.name
        from reels_maker.iso.film import _full_frame
        from reels_maker.iso.projection import DEFAULT_PALETTE
        kw = dict(film="prop", photo_path=path, prop=None)
        a, _, _ = _full_frame(4.0, dict(DEFAULT_PALETTE), None, None,
                              None, 0, zoom={"focus": [0.1, 0.5],
                                              "amount": 0.5}, **kw)
        b, _, _ = _full_frame(4.0, dict(DEFAULT_PALETTE), None, None,
                              None, 0, zoom={"focus": [0.9, 0.5],
                                              "amount": 0.5}, **kw)
        self.assertIsNotNone(_C.difference(a, b).getbbox(),
                             "focus steers the crop")

    def test_ensemble_paints_sidekicks(self):
        from reels_maker.iso.film import _prop_window
        from reels_maker.iso.projection import DEFAULT_PALETTE
        solo, _ = _prop_window("props_storage2.battery-rack", 4.0,
                                  dict(DEFAULT_PALETTE))
        duo, _ = _prop_window(
            ["props_storage2.battery-rack",
             {"label": "props_storage2.bms-box", "dx": 0.55, "dy": 0.0}],
            4.0, dict(DEFAULT_PALETTE))
        self.assertEqual(duo.size, (920, 750))
        import numpy as _np
        n_solo = int((_np.asarray(solo.convert("RGB")) !=
                      _np.asarray(DEFAULT_PALETTE["bg"][:3])).any(axis=-1).sum())
        n_duo = int((_np.asarray(duo.convert("RGB")) !=
                     _np.asarray(DEFAULT_PALETTE["bg"][:3])).any(axis=-1).sum())
        self.assertGreater(n_duo, n_solo, "sidekick adds pixels")
        with self.assertRaises(ValueError):
            _prop_window(["props_storage2.battery-rack", "no.such"],
                         1.0, dict(DEFAULT_PALETTE))

    def test_spin_turns_world(self):
        from reels_maker.iso.film import _prop_window, _full_frame, E
        from reels_maker.iso.projection import DEFAULT_PALETTE
        from PIL import ImageChops
        a, _ = _prop_window("props_heat_a.manifold", 4.0,
                              dict(DEFAULT_PALETTE),
                              {"move": "still", "spin": 0.0})
        b, _ = _prop_window("props_heat_a.manifold", 4.0,
                            dict(DEFAULT_PALETTE),
                            {"move": "still", "spin": 0.3})
        self.assertIsNotNone(
            ImageChops.difference(a.convert("RGB"),
                                  b.convert("RGB")).getbbox(),
            "spin visibly turns the world")
        self.assertEqual(E(0), 0.0)

    def test_title_size_override(self):
        spec = {"t0": 0.0, "snow": 0, "logo": None, "font": None,
                "film": "prop", "prop": "props_heat_a.manifold",
                "title_size": 70,
                "copy": {"title": "ROZDZIELACZ",
                         "body": ["Mosiezna belka"]}}
        from reels_maker.iso.film import render_iso_frame, _full_frame
        from PIL import ImageChops
        a = render_iso_frame(dict(spec, title_size=None), 270, 480, 2.0)
        b = render_iso_frame(spec, 270, 480, 2.0)
        self.assertIsNotNone(
            ImageChops.difference(a.convert("RGB"),
                                  b.convert("RGB")).getbbox(),
            "bigger headline changes pixels")
        with self.assertRaises(ValueError):
            _full_frame(1.0, dict(DEFAULT_PALETTE), None, None, None,
                        0, "prop", None, "props_heat_a.manifold", None,
                        {"move": "orbit"})

    def test_zoom_out_reveals(self):
        # Zoom-out opens tight and reveals; zoom-in does the reverse.
        import tempfile as _t
        from PIL import Image as _I
        from reels_maker.iso.film import _full_frame
        from reels_maker.iso.projection import DEFAULT_PALETTE
        from PIL import ImageChops
        with _t.NamedTemporaryFile(suffix=".png",
                                    delete=False) as fh:
            _I.new("RGB", (400, 200), (30, 120, 60)).save(fh.name)
            im = _I.open(fh.name)
            from PIL import ImageDraw as _D
            _D.Draw(im).rectangle([150, 80, 190, 120], fill=(200, 40, 40))
            _D.Draw(im).rectangle([230, 80, 270, 120], fill=(40, 40, 200))
            im.save(fh.name)
            path = fh.name
        kw = dict(film="prop", prop=None, photo_path=path)
        a, _, _ = _full_frame(1.0, dict(DEFAULT_PALETTE), None, None,
                              None, 0, zoom={"amount": 0.5, "dir": "in",
                                              "time": 8}, **kw)
        b, _, _ = _full_frame(1.0, dict(DEFAULT_PALETTE), None, None,
                              None, 0, zoom={"amount": 0.5, "dir": "out",
                                              "time": 8}, **kw)
        self.assertIsNotNone(
            ImageChops.difference(a.convert("RGB"),
                                  b.convert("RGB")).getbbox(),
            "zoom direction changes framing")
        with self.assertRaises(ValueError):
            _full_frame(1.0, dict(DEFAULT_PALETTE), None, None, None,
                        0, zoom={"dir": "sideways"}, **kw)

    def test_light_card(self):
        from reels_maker.iso.film import _contact_card
        from reels_maker.iso.projection import DEFAULT_PALETTE
        im, _, _ = _contact_card(
            104.0, dict(DEFAULT_PALETTE), None, None, None, 0, "prop",
            {"title": "ZAMÓW", "body": ["67 350 90 90",
                                        "kontakt@asta-energy.pl"]})
        self.assertEqual(im.size, (1080, 1920))
        px = im.convert("RGB").load()
        self.assertGreater(sum(1 for x in range(400, 680, 20)
                               for y in range(700, 950, 20)
                               if sum(px[x, y]) > 600), 20,
                          "white card panel present")

    def test_boxg_shades_down(self):
        from reels_maker.iso.projection import Canvas, DEFAULT_PALETTE
        from reels_maker.iso.film import focus
        k, origin = focus((0.0, 0.15, 0.3), 400)
        q = Canvas(DEFAULT_PALETTE["bg"], k, origin)
        q.boxg((-0.2, -0.1, 0.0), (0.2, 0.1, 0.4), (150, 160, 150))
        import numpy as _np
        im = q.im.convert("RGB")
        a = _np.asarray(im, dtype=float)
        top = a[500:560, 800:900, :].mean()
        bot = a[700:760, 800:900, :].mean()
        self.assertGreater(top, bot, "top face lighter than bottom")

    def test_ao_cap_and_effect(self):
        from reels_maker.iso.projection import Canvas, DEFAULT_PALETTE
        from PIL import ImageChops
        q = Canvas(DEFAULT_PALETTE["bg"], 400, (540.0, 760.0))
        q.box((-0.2, -0.2, 0.0), (0.2, 0.2, 0.4), (150, 160, 150),
              (150, 160, 150), (150, 160, 150))
        before = q.im.copy()
        q.ao(0.0, 0.0, 0.5, 0.2)
        self.assertIsNotNone(ImageChops.difference(before, q.im).getbbox(),
                             "ao darkens the ground")
        with self.assertRaises(ValueError):
            q.ao(0.0, 0.0, 0.5, 0.9)

    def test_body_line_side(self):
        spec = {"t0": 0.0, "snow": 0, "logo": None, "font": None,
                "film": "prop", "prop": "props_heat_a.manifold",
                "copy": {"title": "T",
                         "body": [{"text": "L", "from": "left"},
                                  {"text": "X", "from": "up"}]}}
        with self.assertRaises(ValueError):
            render_iso_frame(spec, 270, 480, 1.0)

    def test_card_uses_override_copy(self):
        from reels_maker.iso.film import _contact_card
        from reels_maker.iso.projection import DEFAULT_PALETTE
        im, _, _ = _contact_card(104.5, dict(DEFAULT_PALETTE), None,
                                 None, None, 0, "prop",
                                 {"title": "ZAMÓW",
                                  "body": ["67 350 90 90",
                                           "kontakt@asta-energy.pl"]})
        self.assertEqual(im.size, (1080, 1920))
        px = im.convert("RGB")
        white = sum(1 for x in range(200, 880, 8)
                    for y in range(700, 990, 8)
                    if sum(px.getpixel((x, y))) > 660)
        self.assertGreater(white, 200, "white rounded card present")
        dark = sum(1 for x in range(300, 780, 6)
                   for y in range(740, 860, 6)
                   if sum(px.getpixel((x, y))) < 200)
        self.assertGreater(dark, 100, "dark number on the card")

    def test_empty_override_keeps_house_card(self):
        # Existing films pass empty card copies: an empty override
        # must render byte-identical to no override (house card kept).
        from PIL import ImageChops
        from reels_maker.iso.film import _contact_card
        from reels_maker.iso.projection import DEFAULT_PALETTE
        a, _, _ = _contact_card(100.5, dict(DEFAULT_PALETTE), None,
                                None, None, 0, "taktowanie",
                                {"title": "", "body": []})
        b, _, _ = _contact_card(100.5, dict(DEFAULT_PALETTE), None,
                                None, None, 0, "taktowanie", None)
        self.assertIsNone(
            ImageChops.difference(a.convert("RGB"),
                                  b.convert("RGB")).getbbox())


if __name__ == "__main__":
    unittest.main()
