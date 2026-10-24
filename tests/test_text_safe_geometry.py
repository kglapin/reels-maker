import unittest
from dataclasses import replace

from reels_maker.core.transforms import Affine2D
from reels_maker.textkit.safe_geometry import SafePolygon, check_text_block
from reels_maker.textkit.typesetter import FontBook, Run, TextStyle, typeset, typeset_runs


REGULAR = "/System/Library/Fonts/Supplemental/Arial.ttf"
BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def rectangle(left, top, right, bottom, name="rect"):
    return SafePolygon(((left, top), (right, top), (right, bottom), (left, bottom)), name)


class SafeGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # These are installed local system fonts; no downloaded or project media.
        cls.fonts = FontBook(regular=REGULAR, bold=BOLD)
        cls.style = TextStyle(36, weight="regular", tracking=1.25, line_height=1.2)

    def test_measures_polish_word_ink_on_baseline_with_tracking_and_runs(self):
        block = typeset_runs((Run("Łódź", weight="regular"),
                              Run("energię", scale=1.1, weight="bold")),
                             self.style, 700, self.fonts)
        report = check_text_block(block, self.fonts, (rectangle(-20, -100, 900, 150),))
        self.assertTrue(report.safe)
        self.assertEqual([word.text for word in report.words], ["Łódź", "energię"])
        self.assertNotEqual(report.words[0].bounds, report.words[1].bounds)
        self.assertGreater(report.words[0].bounds.bottom, 0)
        self.assertEqual(report.words[1].line_index, 0)

    def test_transform_is_applied_to_word_bbox(self):
        block = typeset("Zażółć", self.style, 500, self.fonts)
        identity = check_text_block(block, self.fonts, (rectangle(-20, -80, 600, 100),))
        shifted = check_text_block(
            block, self.fonts, (rectangle(90, 10, 700, 200),),
            transform=Affine2D(e=100, f=100))
        self.assertEqual(shifted.words[0].bounds.left, identity.words[0].bounds.left + 100)
        self.assertEqual(shifted.words[0].bounds.top, identity.words[0].bounds.top + 100)
        self.assertTrue(shifted.safe)

    def test_deterministic_safe_area_and_mask_failures_are_per_word(self):
        block = typeset("Energia dla domu", self.style, 600, self.fonts)
        report = check_text_block(
            block, self.fonts, (rectangle(-2, -100, 180, 100, "platform"),),
            mask_polygons=(rectangle(-2, -100, 70, 100, "visible-mask"),))
        self.assertEqual([failure.text for failure in report.failures], ["dla", "domu"])
        self.assertEqual([failure.text for failure in report.mask_boundary_failures],
                         ["Energia", "dla", "domu"])
        self.assertEqual([failure.reason for failure in report.mask_boundary_failures],
                         ["ink-bounds-cross-mask-boundary"] * 3)
        again = check_text_block(
            block, self.fonts, (rectangle(-2, -100, 180, 100, "platform"),),
            mask_polygons=(rectangle(-2, -100, 70, 100, "visible-mask"),))
        self.assertEqual(report, again)

    def test_whole_bbox_must_fit_concave_polygon_not_only_its_corners(self):
        block = typeset("energia", self.style, 400, self.fonts)
        # U-shaped polygon: bbox corners can sit in the two arms while its top
        # edge crosses the excluded notch.
        notch = SafePolygon(((0, 0), (200, 0), (200, 100), (130, 100),
                             (130, 30), (70, 30), (70, 100), (0, 100)), "notch")
        report = check_text_block(block, self.fonts, (notch,))
        self.assertFalse(report.safe)

    def test_rejects_bad_polygons_truncation_and_unsafe_transform(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            SafePolygon(((0, 0), (float("inf"), 0), (0, 1)))
        with self.assertRaisesRegex(ValueError, "simple"):
            SafePolygon(((0, 0), (4, 4), (0, 4), (4, 0)))
        block = typeset("bezpieczeństwo", self.style, 500, self.fonts)
        with self.assertRaisesRegex(ValueError, "truncated"):
            check_text_block(replace(block, truncated=True), self.fonts,
                             (rectangle(-10, -100, 600, 100),))
        with self.assertRaisesRegex(ValueError, "singular"):
            check_text_block(block, self.fonts, (rectangle(-10, -100, 600, 100),),
                             transform=Affine2D(a=1, d=0))

    def test_empty_text_placements_fail_closed(self):
        block = typeset("   ", self.style, 500, self.fonts)
        with self.assertRaisesRegex(ValueError, "no measurable"):
            check_text_block(block, self.fonts, (rectangle(0, 0, 500, 200),))


if __name__ == "__main__":
    unittest.main()
