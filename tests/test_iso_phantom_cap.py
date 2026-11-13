"""Regression lock for the phantom-cap class (playbook rule 14).

Full-corpus zoom review (158 flags over 230 props, 2026-11-11) showed
~95% of buried-collar / orphan-disc flags read as correct hardware:
collars ARE the joint language (valve bonnets, glands, flanges),
translucent covers show frames by design, coins/buttons stack by
design, propeller discs are effects. Visibility is perceptual
(contrast x isolation x proportion), so G1 (buried collar with
continuation), G1b (foot rim on a confirmed plate) and G3 (orphan
disc) are TRIAGE WARNINGS — the eye + LLM ensemble decide.

What stays an ERROR:
- G1c: a protruding foot rim haloing over the display plinth with
  AIR beneath the overhang (the hay-bale halo). A rim with an
  opaque support top within 0.04 below is a foot on rails/a frame
  (compressor, thermo-head), not a halo.
"""
import sys
import unittest

sys.path.insert(0, "src")
sys.path.insert(0, ".")

from tools.iso_layer_audit import Rec, audit_calls  # noqa: E402
from reels_maker.iso.projection import DEFAULT_PALETTE  # noqa: E402


def _split(q):
    errors, warnings = audit_calls(q, q.calls)
    return ([e for e in errors if e["code"] == "phantom-cap"],
            [e for e in warnings if e["code"] == "phantom-cap"])


def _paint_buried_collar():
    # Tube with a mid collar: cap ellipse buried in the tube's own
    # continuation (manifold/valve house style). Reads as hardware —
    # triage warning, never an error.
    q = Rec(DEFAULT_PALETTE["bg"], 400, (540.0, 760.0))
    q.tube(0.0, 0.0, 0.0, 0.50, 0.10)
    q.box((-0.20, -0.10, 0.0), (0.20, 0.10, 0.50),
          (180, 58, 46), (180, 58, 46), (180, 58, 46))
    q.ground_ellipse(0.0, 0.0, 0.12, 0.12, (140, 65, 50), z=0.25)
    return q


def _paint_rim(supported):
    # Foot rim of a grounded tube over the display plinth.
    q = Rec(DEFAULT_PALETTE["bg"], 400, (540.0, 760.0))
    q.ground_ellipse(0.0, 0.0, 0.55, 0.34, (214, 228, 218), z=-0.125)
    if supported:
        q.box((-0.05, -0.05, -0.05), (0.05, 0.05, 0.008),
              (120, 120, 120), (120, 120, 120), (120, 120, 120))
    q.tube(0.0, 0.0, 0.0, 0.50, 0.10)
    q.ground_ellipse(0.0, 0.0, 0.13, 0.13, (60, 60, 60), z=0.012)
    return q


class PhantomCapTest(unittest.TestCase):
    def test_buried_collar_is_triage_warning(self):
        errs, warns = _split(_paint_buried_collar())
        self.assertEqual(errs, [])
        self.assertEqual(len(warns), 1, warns)

    def test_unsupported_rim_halo_is_error(self):
        # Hay-bale regression: air beneath the overhang.
        errs, _ = _split(_paint_rim(supported=False))
        self.assertEqual(len(errs), 1, errs)

    def test_supported_rim_is_triage_only(self):
        # Compressor regression: foot standing on rails. No ERROR
        # (support rule clears the plinth-halo G1c); the G1b triage
        # warning may remain — rim wider than its pedestal is
        # eye-decided (reads as a foot here).
        errs, warns = _split(_paint_rim(supported=True))
        self.assertEqual(errs, [], errs)
        self.assertTrue(all(e["code"] == "phantom-cap" for e in warns),
                        warns)

    def test_orphan_disc_is_triage_warning(self):
        # Drone propeller: opaque, claimed by nothing, intentional.
        q = Rec(DEFAULT_PALETTE["bg"], 400, (540.0, 760.0))
        q.ground_ellipse(0.0, 0.0, 0.15, 0.15, (240, 240, 240), z=0.30)
        errs, warns = _split(q)
        self.assertEqual(errs, [])
        self.assertEqual(len(warns), 1, warns)

    def test_plinth_stage_is_exempt(self):
        q = Rec(DEFAULT_PALETTE["bg"], 400, (540.0, 760.0))
        q.ground_ellipse(0.0, 0.15, 0.55, 0.34, (214, 228, 218, 200))
        q.box((-0.20, -0.10, 0.0), (0.20, 0.10, 0.50),
              (180, 58, 46), (180, 58, 46), (180, 58, 46))
        errs, warns = _split(q)
        self.assertEqual(errs, [])
        self.assertEqual(warns, [])


if __name__ == "__main__":
    unittest.main()
