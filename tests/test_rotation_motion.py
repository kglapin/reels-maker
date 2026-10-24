"""Regression checks for deliberate rotational motion in scene graph.

These tests validate core node animation and transformed bounds, not
automatic creative rotation selection or finished video aesthetics.
"""
import math
import unittest

from reels_maker.core.scene_graph import (
    Node, build_transform_hierarchy, collect_qa_elements,
)
from reels_maker.core.transforms import Bounds, LocalSpace, Point, Space
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
        rotated = node.world_bounds()
        self.assertIsNotNone(original)
        self.assertIsNotNone(rotated)
        self.assertGreater(rotated[3] - rotated[1], original[3] - original[1])

    def test_node_bounds_use_shared_affine_transform_contract(self):
        node = Node(kind="panel", props={"x": 10, "y": 20, "w": 80, "h": 40},
                    dx=7, dy=-3, scale=1.5, rotation=30, anchor=(10, 20))
        expected = node.local_to_parent_transform().map_bounds(
            Bounds(10, 20, 90, 60))
        self.assertEqual(node.world_bounds(),
                         (expected.left, expected.top, expected.right, expected.bottom))
        transform = node.local_to_parent_transform()
        self.assertEqual((transform.source, transform.target),
                         (Space.LOCAL, Space.PARENT))
        restored = transform.inverse().apply(transform.apply(Point(13, 29)))
        self.assertAlmostEqual(restored.x, 13)
        self.assertAlmostEqual(restored.y, 29)

    def test_nested_scene_tree_qa_bounds_use_shared_hierarchy(self):
        leaf = Node(kind="text", role="headline",
                    props={"x": 90, "y": 80, "w": 120, "h": 30},
                    qa_class="text", meta={"bounds": (96, 84, 196, 104)})
        group = Node(kind="group", role="card",
                     props={"x": 50, "y": 40, "w": 220, "h": 150},
                     scale=1.1, rotation=-12, dx=5, children=[leaf])
        hierarchy, node_ids = build_transform_hierarchy(group)
        expected = hierarchy.world_transform(node_ids[(0,)]).map_bounds(
            Bounds[LocalSpace](96, 84, 196, 104))
        actual = collect_qa_elements(group)[0]["bounds"]
        self.assertEqual(actual, tuple(round(value, 2) for value in (
            expected.left, expected.top, expected.right, expected.bottom)))

    def test_studio_hierarchy_adapter_rejects_cycles_and_depth_overflow(self):
        cyclic = Node(kind="group", role="cycle")
        cyclic.children.append(cyclic)
        with self.assertRaisesRegex(ValueError, "Cyclic Node"):
            build_transform_hierarchy(cyclic)
        root = Node(kind="group", role="root")
        child = Node(kind="group", role="child")
        root.children.append(child)
        child.children.append(Node(kind="rect", role="leaf",
                                   props={"x": 0, "y": 0, "w": 1, "h": 1}))
        with self.assertRaisesRegex(ValueError, "depth limit"):
            build_transform_hierarchy(root, max_depth=2)


if __name__ == "__main__":
    unittest.main()
