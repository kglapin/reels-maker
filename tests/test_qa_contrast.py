"""QA contrast must retain its settled-frame threshold behavior."""
from __future__ import annotations

from types import SimpleNamespace
import unittest

from PIL import Image

from reels_maker.qa.report import (
    CONTRAST_LARGE, CONTRAST_SMALL, SAFE_AREA_TOLERANCE, _contrast,
)


class ContrastAuditTests(unittest.TestCase):
    def test_rendered_low_contrast_text_uses_the_small_type_threshold(self):
        image = Image.new("RGB", (24, 24), (255, 255, 255))
        element = {
            "role": "caption",
            "bounds": (8, 8, 16, 16),
            "opacity": 1.0,
            "meta": {"color": (230, 230, 230), "size": 16,
                     "weight": "regular"},
        }

        issues = _contrast([element], image, SimpleNamespace(index=0), .5, 30)

        self.assertEqual([issue.code for issue in issues], ["contrast_low"])
        self.assertEqual(CONTRAST_LARGE, 3.0)
        self.assertEqual(CONTRAST_SMALL, 4.5)
        self.assertEqual(SAFE_AREA_TOLERANCE, 1.5)


if __name__ == "__main__":
    unittest.main()
