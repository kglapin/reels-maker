"""Stroke tracing for draw-on icon animation."""
import math
import unittest

from reels_maker.icon_strokes import StrokeTraceError, trace_icon


class TraceIconTest(unittest.TestCase):
    def test_lucide_check_traces_single_stroke(self):
        icon = trace_icon("lucide", "check")
        self.assertIsNotNone(icon)
        self.assertEqual(icon.view_box, (0.0, 0.0, 24.0, 24.0))
        self.assertEqual(len(icon.strokes), 1)
        stroke = icon.strokes[0]
        self.assertFalse(stroke.closed)
        self.assertGreaterEqual(len(stroke.points), 3)
        self.assertAlmostEqual(stroke.points[0][0], 20.0)
        self.assertAlmostEqual(stroke.points[-1][0], 4.0)

    def test_sun_circle_and_rays(self):
        icon = trace_icon("lucide", "sun")
        self.assertIsNotNone(icon)
        self.assertGreaterEqual(len(icon.strokes), 9)
        closed = [s for s in icon.strokes if s.closed]
        self.assertTrue(closed, "sun center circle should trace closed")

    def test_droplets_curves_flatten(self):
        icon = trace_icon("lucide", "droplets")
        self.assertIsNotNone(icon)
        long_stroke = max(icon.strokes, key=lambda s: len(s.points))
        self.assertGreater(len(long_stroke.points), 50)

    def test_unknown_icon_raises_or_returns_none(self):
        # Missing icons surface as IconLibraryError from asset(); tracing
        # helpers must not silently fabricate geometry.
        from reels_maker.icon_library import IconLibraryError
        with self.assertRaises(IconLibraryError):
            trace_icon("lucide", "definitely-not-an-icon-xyz")

    def test_trace_error_on_bad_path(self):
        with self.assertRaises(StrokeTraceError):
            from reels_maker.icon_strokes import _trace_path
            _trace_path("M 0 0 X 5", 1.0)


if __name__ == "__main__":
    unittest.main()
