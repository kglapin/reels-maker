"""Deterministic motion/editing guards wired into the QA report."""
from __future__ import annotations

from types import SimpleNamespace
import unittest

from reels_maker.core.scene_graph import Node
from reels_maker.motionkit.keyframes import Keyframe, Track
from reels_maker.qa.motion import audit_motion


def _built(nodes, *, duration=2.0, index=0, entries=None, recipe="spotlight",
           scene=None):
    choreography = SimpleNamespace(entries=entries or {})
    layout = SimpleNamespace(recipe=recipe)
    return SimpleNamespace(
        nodes=nodes, duration=duration, index=index,
        choreography=choreography, layout=layout,
        scene=scene or {})


def _rect(role="headline", **tracks):
    node = Node(kind="rect", role=role,
                props={"x": 10, "y": 10, "w": 50, "h": 20})
    for name, pairs in tracks.items():
        node.track(name, Track.from_pairs(pairs))
    return node


class MotionAuditTests(unittest.TestCase):
    def test_low_final_opacity_is_flagged(self):
        node = _rect(opacity=[(0.0, 0.0), (0.4, 1.0), (1.8, 0.92)])
        built = _built([node])
        codes = [issue.code for issue in audit_motion([built], SimpleNamespace(scenes=[]))]
        self.assertIn("low_final_opacity", codes)

    def test_full_opacity_settle_is_clean(self):
        node = _rect(opacity=[(0.0, 0.0), (0.4, 1.0)])
        built = _built([node])
        codes = [issue.code for issue in audit_motion([built], SimpleNamespace(scenes=[]))]
        self.assertNotIn("low_final_opacity", codes)

    def test_blink_cycle_is_flagged(self):
        # Linear keys make a true 5 Hz triangle wave; eased keys would be
        # smoothed below the detector's reversal threshold.
        opacity = Track([
            Keyframe(t, 1.0 if int(t * 5) % 2 == 0 else 0.0, "linear")
            for t in [i * 0.1 for i in range(21)]])
        node = _rect()
        node.track("opacity", opacity)
        built = _built([node], duration=2.0)
        codes = [issue.code for issue in audit_motion([built], SimpleNamespace(scenes=[]))]
        self.assertIn("blink_cycle", codes)

    def test_flutter_track_is_flagged(self):
        dx = [(t, 50 * (1 if int(t * 12) % 2 == 0 else -1))
              for t in [i * 0.05 for i in range(41)]]
        node = _rect(dx=dx)
        built = _built([node], duration=2.0)
        codes = [issue.code for issue in audit_motion([built], SimpleNamespace(scenes=[]))]
        self.assertIn("motion_flutter", codes)

    def test_static_tail_is_flagged(self):
        node = _rect(opacity=[(0.0, 0.0), (0.3, 1.0)])
        built = _built([node], duration=6.0)
        codes = [issue.code for issue in audit_motion([built], SimpleNamespace(scenes=[]))]
        self.assertIn("static_tail", codes)

    def test_media_node_exempts_static_tail(self):
        video = Node(kind="video", role="footage",
                     props={"path": "x.mp4", "x": 0, "y": 0,
                            "w": 10, "h": 10})
        built = _built([video], duration=6.0)
        codes = [issue.code for issue in audit_motion([built], SimpleNamespace(scenes=[]))]
        self.assertNotIn("static_tail", codes)

    def test_entrance_crowding_is_flagged(self):
        entries = {f"role{i}": SimpleNamespace(onset=0.05 * i)
                   for i in range(7)}
        built = _built([_rect()], entries=entries)
        codes = [issue.code for issue in audit_motion([built], SimpleNamespace(scenes=[]))]
        self.assertIn("entrance_crowding", codes)

    def test_repeated_adjacent_scene_is_flagged(self):
        scene = {"kicker": "Oferta", "headline": {"runs": [
            {"text": "To samo"}]}}
        first = _built([_rect()], index=0, recipe="spotlight", scene=scene)
        second = _built([_rect()], index=1, recipe="spotlight", scene=scene)
        third = _built([_rect()], index=2, recipe="cta",
                       scene={"headline": "Inne"})
        codes = [issue.code for issue in
                 audit_motion([first, second, third], SimpleNamespace(scenes=[]))]
        self.assertEqual(codes.count("repeated_adjacent_scene"), 1)

    def test_transition_monotony_is_flagged(self):
        scenes = [{"transition_in": {"type": "pixel-dissolve"}}
                  for _ in range(4)]
        project = SimpleNamespace(scenes=scenes)
        codes = [issue.code for issue in audit_motion([], project)]
        self.assertIn("transition_monotony", codes)

    def test_clean_scene_produces_no_motion_issues(self):
        node = _rect(opacity=[(0.0, 0.0), (0.3, 1.0)],
                     dx=[(0.0, 0.0), (0.3, -20.0)])
        built = _built([node], duration=1.5)
        issues = audit_motion([built], SimpleNamespace(scenes=[]))
        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
