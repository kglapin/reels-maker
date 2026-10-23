"""Regression checks for deliberate rotational motion in scene graph.

These tests validate core node animation and transformed bounds, not
automatic creative rotation selection or finished video aesthetics.
"""
import math
import unittest

from reels_maker.core.scene_graph import Node
from reels_maker.motionkit.keyframes import Track


class RotationalTypographyTests(unittest.TestCase):
    def test_rotating_image_settles_without_affecting_source(self):
        image = Node(kind="image", role="photo", props={
            "x": 120, "y": 180, "w": 460, "h": 640
        })
        image.track("rotation", Track.from_pairs(
            [(0.0, -7.0), (0.5, 0.0)]))
        self.assertEqual(image.rotation, 0.0)
        self.assertAlmostEqual(image.sample(0).rotation, -7)
        self.assertAlmostEqual(image.sample(0.5).rotation, 0)
        self.assertEqual(image.rotation, 0.0)

    def test_group_rotation_can_be_independent_of_photo(self):
        photo = Node(kind="image", props={"x": 30, "y": 60, "w": 210, "h": 280})
        title = Node(kind="panel", role="typographic-group",
                     props={"x": 310, "y": 90, "w": 250, "h": 110})
        photo.track("rotation", Track.from_pairs([(0, 6), (.4, 0)]))
        title.track("rotation", Track.from_pairs([(0, -4), (.4, 0)]))
        self.assertGreater(photo.sample(0).rotation, 0)
        self.assertLess(title.sample(0).rotation, 0)
        self.assertEqual(photo.sample(.4).rotation, 0)
        self.assertEqual(title.sample(.4).rotation, 0)

    def test_rotated_bounds_are_larger_than_unrotated(self):
        node = Node(kind="panel", props={"x": 100, "y": 100, "w": 400, "h": 100})
        original = node.world_bounds()
        node.rotation = 30
        rotated = node.bounds()
        self.assertIsNotNone(original)
        self.assertIsNotNone(rotated)
        self.assertGreater(rotated[3] - rotated[1], original[3] - original[1])


if __name__ == "__main__":
    unittest.main()
