"""Depth-buffer regression tests (default on; REELS_ISO_DEPTH=0 opts out).

Locks the visibility contract from docs/ISO_PROP_AUTHORING.md §6:
opaque geometry resolves by world depth regardless of call order,
translucent overlays keep painter semantics, and lines/gradients are
inside the same depth model. Guards the frame regression where a
pipe line painted over a panel because line() bypassed the buffer.
"""
import sys
import unittest

sys.path.insert(0, "src")

import numpy as np
from PIL import Image

from reels_maker.iso import projection
from reels_maker.iso.film import focus
from reels_maker.iso.projection import Canvas, DEFAULT_PALETTE

BG = DEFAULT_PALETTE["bg"]


def _canvas():
    k, origin = focus((0.0, 0.15, 0.25), 500)
    return Canvas(BG, k, origin)


def _px(q, world):
    x, y = q.P(world)
    return tuple(int(v) for v in np.asarray(q.im.convert("RGB"))
                 [int(y), int(x)])


def _render(draw, depth):
    projection._USE_DEPTH = depth
    try:
        q = _canvas()
        draw(q)
        return q.im.copy()
    finally:
        projection._USE_DEPTH = False


class DepthOrderTest(unittest.TestCase):
    def test_far_fragment_cannot_cover_near(self):
        # Far red slab drawn AFTER near green slab: painter shows red,
        # depth keeps green.
        def draw(q):
            q.box((-0.2, 0.0, 0.0), (0.2, 0.4, 0.3),
                  (40, 200, 40), (40, 200, 40), (40, 200, 40))
            q.box((-0.2, -0.4, 0.0), (0.2, 0.0, 0.3),
                  (220, 40, 40), (220, 40, 40), (220, 40, 40))
        pan = _render(draw, False)
        dep = _render(draw, True)
        q = _canvas()
        # sample centre of near slab top
        probe = (0.0, 0.2, 0.31)
        x, y = q.P(probe)
        pa = np.asarray(pan)[int(y), int(x)]
        da = np.asarray(dep)[int(y), int(x)]
        self.assertTrue(pa[0] > pa[1], "painter: far slab should win")
        self.assertTrue(da[1] > da[0], "depth: near slab must survive")

    def test_line_behind_opaque_is_culled(self):
        # Bright line inside a box footprint but at lower z: hidden.
        def draw_hidden(q):
            q.box((-0.3, -0.3, 0.0), (0.3, 0.3, 0.5),
                  (60, 60, 90), (60, 60, 90), (60, 60, 90))
            q.line([(-0.2, 0.0, 0.2), (0.2, 0.0, 0.2)], (255, 0, 0), 1.5)
        dep = _render(draw_hidden, True)
        q = _canvas()
        x, y = q.P((0.0, 0.0, 0.5))
        # probe just above the box top face centre where the line pierces
        x2, y2 = q.P((0.0, 0.0, 0.45))
        a = np.asarray(dep)
        # the line at z=0.2 is inside the box (top z=0.5): depth must
        # cull it — pixel keeps box colour, not red
        self.assertFalse(a[int(y2), int(x2), 0] > 200
                         and a[int(y2), int(x2), 1] < 60,
                         "depth: buried line leaked through the box")

    def test_translucent_overlay_always_draws(self):
        def draw(q):
            q.box((-0.3, -0.3, 0.0), (0.3, 0.3, 0.5),
                  (60, 60, 90), (60, 60, 90), (60, 60, 90))
            q.poly([(-0.2, -0.2, 0.6), (0.2, -0.2, 0.6),
                    (0.2, 0.2, 0.6), (-0.2, 0.2, 0.6)],
                   (255, 0, 0, 120))
        dep = _render(draw, True)
        q = _canvas()
        x, y = q.P((0.0, 0.0, 0.6))
        a = np.asarray(dep)[int(y), int(x)]
        # translucent red over blue-ish box: red channel boosted
        self.assertGreater(int(a[0]), 90, "translucent overlay vanished")

    def test_grad_poly_depth_tested(self):
        # Far gradient face drawn after near opaque: depth culls it.
        def draw(q):
            q.poly([(-0.2, 0.0, 0.0), (0.2, 0.0, 0.0),
                    (0.2, 0.4, 0.3), (-0.2, 0.4, 0.3)],
                   (40, 200, 40))
            q.grad_poly([(-0.2, -0.4, 0.0), (0.2, -0.4, 0.0),
                         (0.2, 0.0, 0.3), (-0.2, 0.0, 0.3)],
                        (220, 40, 40), (120, 20, 20))
        dep = _render(draw, True)
        q = _canvas()
        x, y = q.P((0.0, 0.2, 0.31))
        a = np.asarray(dep)[int(y), int(x)]
        self.assertTrue(int(a[1]) > int(a[0]),
                        "depth: far gradient face covered near slab")

    def test_painter_mode_unchanged(self):
        # Sanity: with depth off, later calls still win (fallback path).
        def draw(q):
            q.box((-0.2, 0.0, 0.0), (0.2, 0.4, 0.3),
                  (40, 200, 40), (40, 200, 40), (40, 200, 40))
            q.box((-0.2, -0.4, 0.0), (0.2, 0.0, 0.3),
                  (220, 40, 40), (220, 40, 40), (220, 40, 40))
        pan = _render(draw, False)
        q = _canvas()
        x, y = q.P((0.0, 0.2, 0.31))
        a = np.asarray(pan)[int(y), int(x)]
        self.assertTrue(int(a[0]) > int(a[1]),
                        "painter: later far slab should cover near one")


if __name__ == "__main__":
    unittest.main()
