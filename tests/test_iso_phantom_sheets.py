"""Regression lock for the phantom-sheet coordinate space (playbook 16).

A scaling bug once cropped the unscaled canvas with scaled
coordinates: every zoom showed background, and the triage evidence
was worthless. This test renders one flagged prop fresh and asserts
the triage bbox center lands on a non-background pixel — i.e. the
sheet crop actually shows the flagged region.
"""
import sys
import unittest

sys.path.insert(0, "src")
sys.path.insert(0, ".")

import tools.iso_layer_audit as A  # noqa: E402
import tools.iso_phantom_sheets as S  # noqa: E402
from reels_maker.iso.projection import DEFAULT_PALETTE  # noqa: E402


def _first_flagged():
    pts = S.painters()
    for label, (_real_fn, audit_fn) in pts.items():
        q = audit_fn()
        _errors, warnings = A.audit_calls(q, q.calls)
        hits = [w for w in warnings if w["code"] == "phantom-cap"]
        if hits:
            return label, q, hits[0]
    raise AssertionError("no phantom triage warnings anywhere on corpus")


class PhantomSheetsTest(unittest.TestCase):
    def test_triage_bbox_lands_on_subject(self):
        label, q_rec, warn = _first_flagged()
        flagged = warn["calls"][1]
        x0, y0, x1, y1 = A._bbox(q_rec, q_rec.calls[flagged])
        real_fn = S.painters()[label][0]
        img = real_fn(dict(DEFAULT_PALETTE)).im.convert("RGB")
        cx, cy = int((x0 + x1) / 2), int((y0 + y1) / 2)
        self.assertTrue(0 <= cx < img.width and 0 <= cy < img.height,
                        f"{label}: bbox center off-canvas")
        bg = tuple(DEFAULT_PALETTE["bg"][:3])
        near = [img.getpixel((max(0, min(img.width - 1, cx + dx)),
                              max(0, min(img.height - 1, cy + dy))))
                for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
        self.assertTrue(any(px != bg for px in near),
                        f"{label} call {flagged}: triage crop shows "
                        "only background — coordinate space broken")


if __name__ == "__main__":
    unittest.main()
