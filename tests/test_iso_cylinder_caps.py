"""Regression lock for buried-cap discipline (see docs/iso-prop-playbook.md
rules 12-13 and visual-plan/PRD.md Polish rounds 2-4).

A ``_cylinder`` whose foot is buried in a plate/flange must pass
``rim=False``; one whose top is buried in the next solid must pass
``top_ring=False``. Otherwise the cap ellipse paints a phantom disc
across the solid it stands in (the hydrant base-disc and barrel-slice
bugs). These tests lock the flag plumbing on the recorder; the layered
look itself stays covered by the pixel gate, the layer audit, blind
reviewers and the LLM ensemble.
"""
import math
import sys
import unittest

sys.path.insert(0, "src")
sys.path.insert(0, ".")

from reels_maker.iso.world import _cylinder  # noqa: E402
from tools.iso_layer_audit import Rec  # noqa: E402
from reels_maker.iso.projection import DEFAULT_PALETTE  # noqa: E402


def _paint(**kw):
    q = Rec(DEFAULT_PALETTE["bg"], 400,
            (540.0, 760.0))
    _cylinder(q, 0.0, 0.15, 0.10, 0.50, 0.10,
              (180, 58, 46), (142, 44, 34), (202, 68, 54), n=8, **kw)
    return q.calls


def _gnds(calls):
    return [c for c in calls if c["op"] == "gnd"]


class CylinderCapTest(unittest.TestCase):
    def test_default_emits_foot_and_collar(self):
        gnds = _gnds(_paint())
        self.assertEqual(len(gnds), 2, [c["pts"][0][2] for c in gnds])

    def test_rim_false_skips_foot_ring(self):
        gnds = _gnds(_paint(rim=False))
        self.assertEqual(len(gnds), 1)
        self.assertAlmostEqual(gnds[0]["pts"][0][2], 0.55, places=6)

    def test_top_ring_false_emits_nothing_up_top(self):
        # Only the foot rim remains; the buried top paints no collar,
        # no cap, no sealing disc (builders seal mouths explicitly FIRST
        # — a disc painted here would cover the surrounding wall).
        gnds = _gnds(_paint(top_ring=False))
        self.assertEqual(len(gnds), 1)
        self.assertAlmostEqual(gnds[0]["pts"][0][2], 0.112, places=6)

    def test_both_false_emits_no_ellipse(self):
        gnds = _gnds(_paint(rim=False, top_ring=False))
        self.assertEqual(gnds, [])

    def test_buried_stack_emits_no_ellipse(self):
        """The hydrant barrel/flange configuration: buried tops and feet
        emit nothing — no raised collars, no foot rings, no sealing
        discs (builders paint mouth seals explicitly FIRST, because a
        disc painted after the walls would cover them as a phantom).
        So no phantom disc can paint across a surrounding wall."""
        q = Rec(DEFAULT_PALETTE["bg"], 400, (540.0, 760.0))
        q.box((-0.16, -0.01, 0.0), (0.16, 0.31, 0.06),
              (142, 44, 34), (142, 44, 34), (142, 44, 34))
        _cylinder(q, 0.0, 0.15, 0.05, 0.12, 0.13,
                  (180, 58, 46), (142, 44, 34), (202, 68, 54),
                  rim=False, top_ring=False, n=8)
        _cylinder(q, 0.0, 0.15, 0.10, 0.55, 0.10,
                  (180, 58, 46), (142, 44, 34), (202, 68, 54),
                  rim=False, top_ring=False, n=8)
        buried = [c for c in q.calls if c["op"] == "gnd"
                  and c["pts"][0][2] > 0.02]
        self.assertEqual(buried, [])


if __name__ == "__main__":
    unittest.main()
