import math
import unittest

from reels_maker.core.transforms import (
    Affine2D, Bounds, CameraSpace, LocalSpace, ParentSpace, Point, Space,
    TransformHierarchy, TransformNode, Viewport, ViewportSpace, WorldSpace,
    world_bounds_to_viewport, world_to_viewport,
)


class TransformTests(unittest.TestCase):
    def test_composition_and_inverse_round_trip(self):
        local_to_parent = Affine2D(2, 0, 0, 3, 10, -4, Space.LOCAL, Space.PARENT)
        parent_to_world = Affine2D(0, 1, -1, 0, 5, 7, Space.PARENT, Space.WORLD)
        local_to_world = local_to_parent.then(parent_to_world)
        point = Point[LocalSpace](2.5, -3)
        restored = local_to_world.inverse().apply(local_to_world.apply(point))
        self.assertAlmostEqual(restored.x, point.x)
        self.assertAlmostEqual(restored.y, point.y)

    def test_nested_hierarchy(self):
        graph = TransformHierarchy()
        graph.add(TransformNode("root", Affine2D(1, 0, 0, 1, 10, 20,
                                                   Space.LOCAL, Space.WORLD)))
        graph.add(TransformNode("group", Affine2D(2, 0, 0, 2, 3, 4,
                                                    Space.LOCAL, Space.PARENT), "root"))
        graph.add(TransformNode("shape", Affine2D(1, 0, 0, 1, -1, 5,
                                                    Space.LOCAL, Space.PARENT), "group"))
        mapped = graph.world_transform("shape").apply(Point[LocalSpace](1, 1))
        self.assertEqual((mapped.x, mapped.y), (13, 36))

    def test_reparent_cycle_and_depth_fail_closed(self):
        graph = TransformHierarchy(max_depth=2)
        graph.add(TransformNode("root", Affine2D(target=Space.WORLD)))
        graph.add(TransformNode("child", Affine2D(target=Space.PARENT), "root"))
        with self.assertRaisesRegex(ValueError, "depth limit"):
            graph.add(TransformNode("grandchild", Affine2D(target=Space.PARENT), "child"))
        with self.assertRaisesRegex(ValueError, "Cyclic"):
            graph.reparent("root", "child")
        self.assertIsNone(graph._nodes["root"].parent_id)

    def test_camera_viewport_points_bounds_and_edges(self):
        camera = Affine2D(1, 0, 0, 1, -10, -20, Space.WORLD, Space.CAMERA)
        viewport = Viewport(100, 80, scale_x=2, scale_y=2, offset_x=5, offset_y=7)
        self.assertEqual(world_to_viewport(Point[WorldSpace](10, 20), camera, viewport),
                         Point[ViewportSpace](5, 7))
        mapped = world_bounds_to_viewport(Bounds[WorldSpace](10, 20, 20, 30), camera, viewport)
        self.assertEqual(mapped, Bounds[ViewportSpace](5, 7, 25, 27))
        self.assertTrue(0 <= mapped.left <= viewport.width)
        self.assertTrue(0 <= mapped.bottom <= viewport.height)

    def test_invalid_values_spaces_and_dimensions(self):
        with self.assertRaises(ValueError):
            Point(math.inf, 0)
        with self.assertRaises(ValueError):
            Affine2D(e=math.nan)
        with self.assertRaisesRegex(ValueError, "Singular"):
            Affine2D(1, 2, 2, 4).inverse()
        with self.assertRaisesRegex(ValueError, "ordered"):
            Bounds(2, 0, 1, 1)
        with self.assertRaisesRegex(ValueError, "positive"):
            Viewport(0, 20)
        with self.assertRaisesRegex(ValueError, "non-zero"):
            Viewport(20, 20, scale_x=0)
        with self.assertRaisesRegex(ValueError, "Cannot compose"):
            Affine2D(source=Space.LOCAL, target=Space.PARENT).then(
                Affine2D(source=Space.WORLD, target=Space.CAMERA))
        with self.assertRaisesRegex(ValueError, "world -> camera"):
            world_to_viewport(Point(0, 0), Affine2D(), Viewport(20, 20))


if __name__ == "__main__":
    unittest.main()
