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

    def test_eight_distinct_text_mechanism_families_and_selection(self):
        from reels_maker.design.tokens import resolve_tokens
        from reels_maker.motionkit.presets import (
            apply_entrance, select_text_mechanism, text_mechanism_families,
        )

        families = text_mechanism_families()
        self.assertEqual(len(families), 8)
        presets_seen = set()
        for name, spec in families.items():
            preset = select_text_mechanism(name)
            self.assertEqual(preset, spec["preset"])
            self.assertEqual(select_text_mechanism(str(spec["purpose"])), preset)
            presets_seen.add(preset)
            tokens = resolve_tokens("editorial-premium", width=1080, height=1920)
            node = Node(kind="rect", props={"x": 100, "y": 100, "w": 200, "h": 60})
            apply_entrance(node, preset, 0.0, 0.5, tokens,
                           safe_bounds=(0, 0, 1080, 1920))
            self.assertTrue(node.tracks or node.reveal)
        self.assertEqual(len(presets_seen), 8)

    def test_vector_polyline_trim_and_icon_state_transition(self):
        from reels_maker.components.base import animate_icon_state, animate_progress
        from reels_maker.renderers.canvas import trim_polyline

        pts = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0)]
        self.assertEqual(trim_polyline(pts, 0.0), [])
        half = trim_polyline(pts, 0.5)
        self.assertEqual(half, [(0.0, 0.0), (100.0, 0.0)])
        quarter_to_three = trim_polyline(pts, 0.75, start=0.25)
        self.assertEqual(quarter_to_three[0], (50.0, 0.0))
        self.assertEqual(quarter_to_three[-1], (100.0, 50.0))

        path_node = Node(kind="path", role="trace",
                         props={"points": pts, "progress": 0.0})
        animate_progress(path_node, 0.0, 1.0)
        self.assertAlmostEqual(path_node.sample(0.5).props["progress"], 0.875, places=2)

        icon_a = Node(kind="circle", role="state-a", props={"cx": 50, "cy": 50, "r": 20})
        icon_b = Node(kind="circle", role="state-b", props={"cx": 50, "cy": 50, "r": 20})
        state_group = animate_icon_state(icon_a, icon_b, switch_time=1.0, duration=0.4)
        self.assertAlmostEqual(state_group.sample(0.5).children[0].opacity, 1.0)
        self.assertAlmostEqual(state_group.sample(0.5).children[1].opacity, 0.0)
        self.assertAlmostEqual(state_group.sample(1.5).children[0].opacity, 0.0)
        self.assertAlmostEqual(state_group.sample(1.5).children[1].opacity, 1.0)

    def test_shared_element_continuity_across_scenes(self):
        from types import SimpleNamespace
        from reels_maker.motionkit.choreography import verify_shared_element_continuity

        n1 = Node(kind="rect", props={"x": 100, "y": 200, "w": 80, "h": 40},
                  meta={"stable_row_id": "item-1"})
        n2 = Node(kind="rect", props={"x": 120, "y": 210, "w": 80, "h": 40},
                  meta={"stable_row_id": "item-1"})
        s1 = SimpleNamespace(duration=2.0, at=lambda t: [n1.sample(t)])
        s2 = SimpleNamespace(duration=2.0, at=lambda t: [n2.sample(t)])
        report = verify_shared_element_continuity([s1, s2], max_anchor_jump_px=50.0)
        self.assertTrue(report["ok"])
        self.assertEqual(report["transitions"][0]["shared_ids"], ["item-1"])

        bad = verify_shared_element_continuity([s1, s2], max_anchor_jump_px=5.0)
        self.assertFalse(bad["ok"])

    def test_md304_video_node_md501_parallax_md502_char_accent_md503_path_morph(self):
        import tempfile
        from pathlib import Path
        from PIL import Image
        from reels_maker.components.base import (
            animate_along_path, character_accent_group, parallax_25d_group,
            video_node,
        )
        from reels_maker.layout.engine import Rect
        from reels_maker.renderers.canvas import (
            apply_shape_mask, crop_region, load_video_frame, morph_polyline,
        )
        from reels_maker.textkit.typesetter import FontBook, TextStyle

        with tempfile.TemporaryDirectory() as tmp:
            img_path = Path(tmp) / "frame.png"
            Image.new("RGB", (200, 200), (40, 140, 60)).save(img_path)
            vnode = video_node(
                "clip", str(img_path), Rect(20, 30, 160, 160),
                trim_start=0.2, trim_end=1.8, crop=(0.1, 0.1, 0.9, 0.9),
                mask="circle",
            )
            sampled = vnode.sample(0.5)
            self.assertAlmostEqual(sampled.props["playback_time"], 0.5)
            self.assertEqual(sampled.base_bounds(), (20.0, 30.0, 180.0, 190.0))
            frame = load_video_frame(img_path, 0.5, trim_start=0.2, trim_end=1.8)
            cropped = crop_region(frame, (0.1, 0.1, 0.9, 0.9))
            masked = apply_shape_mask(cropped, "circle")
            self.assertEqual(masked.mode, "RGBA")
            # Corner pixel of circle mask is transparent
            self.assertEqual(masked.getpixel((0, 0))[3], 0)

        bg = Node(kind="rect", props={"x": 0, "y": 0, "w": 100, "h": 100})
        fg = Node(kind="rect", props={"x": 20, "y": 20, "w": 40, "h": 40})
        p25d = parallax_25d_group([(bg, 0.0), (fg, 1.0)], travel_dx=30.0, duration=2.0)
        s_end = p25d.sample(2.0)
        self.assertGreater(s_end.children[1].dx, s_end.children[0].dx)

        fonts = FontBook()
        c_group = character_accent_group(
            "OZE", TextStyle(36, (255, 255, 255), "bold"),
            Rect(50, 50, 300, 80), fonts,
        )
        self.assertEqual(c_group.meta["character_count"], 3)

        mover = Node(kind="circle", props={"cx": 50, "cy": 50, "r": 10})
        animate_along_path(mover, [(0, 0), (40, -20), (80, 0)], onset=0.0, duration=1.0)
        self.assertAlmostEqual(mover.sample(0.5).dx, 40.0, places=2)

        morphed = morph_polyline([(0.0, 0.0), (10.0, 0.0)], [(0.0, 10.0), (10.0, 10.0)], 0.5)
        self.assertEqual(morphed, [(0.0, 5.0), (10.0, 5.0)])


if __name__ == "__main__":
    unittest.main()
