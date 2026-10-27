"""Fail-fast validation of keyframe tracks before frame encoding."""
from __future__ import annotations

import unittest

from reels_maker.core.scene_graph import Node
from reels_maker.motionkit.keyframes import Keyframe, Track


class KeyframeValidationTests(unittest.TestCase):
    def test_rejects_non_finite_vector_components(self):
        for value in ((0.0, float("nan")), (0.0, float("inf")), (True, 1.0)):
            with self.subTest(value=value), self.assertRaisesRegex(
                    ValueError, "tuple values"):
                Keyframe(0.0, value)

    def test_rejects_unknown_easing_and_bad_parameters_at_construction(self):
        with self.assertRaisesRegex(ValueError, "Unknown easing"):
            Keyframe(0.0, 1.0, "surprise")
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            Keyframe(0.0, 1.0, "linear", (("overshoot", 1.05),))
        with self.assertRaisesRegex(ValueError, "overshoot"):
            Keyframe(0.0, 1.0, "back", (("overshoot", 1.5),))
        with self.assertRaisesRegex(ValueError, "finite numbers"):
            Keyframe(0.0, 1.0, "spring", (("damping", float("nan")),))

    def test_track_rejects_shape_mismatch_and_conflicting_duplicate_times(self):
        with self.assertRaisesRegex(ValueError, "matching shapes"):
            Track([Keyframe(0.0, 1.0), Keyframe(1.0, (1.0, 2.0))])
        with self.assertRaisesRegex(ValueError, "same keyframe time"):
            Track([Keyframe(0.0, 1.0), Keyframe(0.0, 2.0)])

    def test_add_validates_atomically_and_accepts_identical_boundary_keys(self):
        track = Track([Keyframe(0.0, (0.0, 0.0))])
        with self.assertRaisesRegex(ValueError, "matching shapes"):
            track.add(1.0, 1.0)
        self.assertEqual(len(track.keys), 1)
        track.add(0.0, (0.0, 0.0))
        self.assertEqual(len(track.keys), 2)
        self.assertEqual(track.value(0.0), (0.0, 0.0))

    def test_non_positive_animated_scale_fails_instead_of_collapsing_to_a_pixel(self):
        node = Node(kind="rect", props={"x": 0, "y": 0, "w": 10, "h": 10})
        node.track("scale", Track([Keyframe(0.0, 1.0), Keyframe(1.0, 0.0)]))
        with self.assertRaisesRegex(ValueError, "scale must remain"):
            node.sample(1.0)
        with self.assertRaisesRegex(ValueError, "scale must be positive"):
            Node(kind="rect", scale=0).local_to_parent_transform()

    def test_node_rejects_empty_tracks_before_render(self):
        node = Node(kind="rect")
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            node.track("opacity", Track())


if __name__ == "__main__":
    unittest.main()
