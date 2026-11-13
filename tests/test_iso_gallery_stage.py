"""No elliptical stage bases under ISO props (owner rule 2026-11-12).

The gallery plate and the film prop window must not paint any
``ground_ellipse`` slab: bases read as decoration and keep getting
flagged. Tool PARTS that happen to be discs (grinder disc, chimney
flue, insulator collars, wheels) are not bases and stay.
"""
import unittest

from reels_maker.iso import film as _film
from reels_maker.iso import props_storage2
from reels_maker.iso.projection import DEFAULT_PALETTE, Canvas

import tools.iso_gallery2 as _gallery


def _bg():
    return tuple(DEFAULT_PALETTE["bg"][:3])


class NoEllipseStageTest(unittest.TestCase):
    def test_gallery_plate_is_pure_bg(self):
        spec = props_storage2.PROPS["bms-box"]
        plate = _gallery.paint_prop(spec, False, dict(DEFAULT_PALETTE))
        bad = [px for px in plate.convert("RGB").getdata() if px != _bg()]
        self.assertEqual(bad, [], "plate has no slab pixels")

    def test_gallery_render_still_has_prop_ink(self):
        spec = props_storage2.PROPS["bms-box"]
        plate = _gallery.paint_prop(spec, False, dict(DEFAULT_PALETTE))
        render = _gallery.paint_prop(spec, True, dict(DEFAULT_PALETTE))
        diff = sum(1 for a, b in zip(plate.convert("RGB").getdata(),
                                    render.convert("RGB").getdata())
                   if a != b)
        self.assertGreater(diff, 1000, "prop still paints")

    def _window_ellipses(self, stage):
        calls = []
        orig = Canvas.ground_ellipse

        def spy(self, *args, **kwargs):
            calls.append((args, kwargs))
            return orig(self, *args, **kwargs)

        Canvas.ground_ellipse = spy
        try:
            _film._prop_window("props_storage2.bms-box", 50.0,
                               dict(DEFAULT_PALETTE), stage=stage)
        finally:
            Canvas.ground_ellipse = orig
        return calls

    def test_prop_window_plinth_draws_no_ellipse(self):
        self.assertEqual(self._window_ellipses("plinth"), [],
                         "no ellipse slab in clip prop scenes")

    def test_prop_window_slab_draws_no_ellipse(self):
        self.assertEqual(self._window_ellipses("slab"), [],
                         "slab stage is the full-bleed box, never ellipse")
