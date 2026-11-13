"""Manifest-driven animated image overlays (per-object intra-shot motion).

Overlays place raster layers through the same entrance-track choreography
as text, so objects can slide, pop, wipe and rotate inside one shot.
"""
import unittest

from reels_maker.components.base import SceneContext
from reels_maker.components.scenes import build_scene
from reels_maker.components.scene_support import counter_nodes, overlay_nodes
from reels_maker.design.tokens import resolve_tokens
from reels_maker.textkit.typesetter import FontBook


def context(duration=4.0):
    tokens = resolve_tokens("editorial-premium", width=720, height=1280)
    return SceneContext(720, 1280, 30, duration, tokens,
                        "editorial-premium", FontBook(), scene_index=0)


def item(**overrides):
    base = {"asset": "media/cards/brain_circle.png",
            "x": 0.3, "y": 0.4, "w": 0.4, "h": 0.4}
    base.update(overrides)
    return base


class OverlayNodeTests(unittest.TestCase):
    def test_roles_rects_and_default_entrance(self):
        nodes = overlay_nodes(
            context(), {"overlays": [item(), item(x=0.1, entrance="slide-left")]})
        self.assertEqual(list(nodes), ["overlay-0", "overlay-1"])
        node, entrance = nodes["overlay-0"]
        self.assertEqual(node.kind, "image")
        self.assertEqual(node.props["path"], "media/cards/brain_circle.png")
        self.assertEqual(
            (node.props["x"], node.props["y"],
             node.props["w"], node.props["h"]),
            (0.3 * 720, 0.4 * 1280, 0.4 * 720, 0.4 * 1280))
        self.assertEqual(entrance, "fade-up")
        self.assertEqual(nodes["overlay-1"][1], "slide-left")
        # default anchor is the rect centre
        self.assertEqual(node.anchor, (0.3 * 720 + 0.4 * 720 / 2,
                                     0.4 * 1280 + 0.4 * 1280 / 2))

    def test_custom_anchor_and_rotation(self):
        nodes = overlay_nodes(context(duration=2.0), {"overlays": [item(
            anchor=[0.0, 1.0],
            rotation={"family": "tilt-settle", "angle": -12,
                      "settle_angle": 4, "duration": 1.0})]})
        node, _ = nodes["overlay-0"]
        self.assertEqual(node.anchor, (0.3 * 720, 0.8 * 1280))
        self.assertIn("rotation", node.tracks)
        self.assertAlmostEqual(node.sample(0).rotation, -12)
        self.assertAlmostEqual(node.sample(1.2).rotation, 4)

    def test_absent_overlays_is_empty(self):
        self.assertEqual(overlay_nodes(context(), {}), {})

    def test_reveal_left_draws_from_the_right(self):
        from reels_maker.components.scenes import build_scene
        from reels_maker.motionkit.presets import canonical_preset
        self.assertEqual(canonical_preset("reveal-left"), "reveal-left")
        ctx = context(duration=3.0)
        scene = {"type": "statement", "duration": 3.0, "theme": "light",
                 "photo": "media/cards/paper_light.jpg",
                 "overlays": [item(x=0.6, y=0.3, w=0.2, h=0.2,
                                   entrance="reveal-left")],
                 "cues": {"overlay-0": 0.4}}
        built = build_scene(ctx, scene)
        node = built.elements["overlay-0"]
        self.assertEqual(node.reveal.get("direction"), "left")
        self.assertIn("reveal", node.tracks)
        keys = node.tracks["reveal"].keys
        self.assertAlmostEqual(keys[0].time, 0.4)
        self.assertAlmostEqual(keys[0].value, 0.0)
        self.assertAlmostEqual(keys[-1].value, 1.0)

    def test_travel_overrides_entrance_distance(self):
        from reels_maker.components.scenes import build_scene
        ctx = context(duration=3.0)
        scene = {"type": "statement", "duration": 3.0, "theme": "light",
                 "photo": "media/cards/paper_light.jpg",
                 "overlays": [item(x=0.3, y=0.3, w=0.2, h=0.2,
                                   entrance="slide-left", travel=0.2)],
                 "cues": {"overlay-0": 0.3}}
        built = build_scene(ctx, scene)
        node = built.elements["overlay-0"]
        self.assertAlmostEqual(node.sample(0.3).dx, 0.2 * 720, places=1)
        self.assertAlmostEqual(node.sample(2.9).dx, 0.0, places=3)

    def test_rejects_bad_geometry_preset_and_anchor(self):
        with self.assertRaises(ValueError):
            overlay_nodes(context(), {"overlays": "nope"})
        with self.assertRaises(ValueError):
            overlay_nodes(context(), {"overlays": [item(x=0.8, w=0.4)]})
        with self.assertRaises(ValueError):
            overlay_nodes(context(), {"overlays": [item(entrance="explode")]})
        with self.assertRaises(ValueError):
            overlay_nodes(context(), {"overlays": [item(anchor=[0.5])]})
        with self.assertRaises(ValueError):
            overlay_nodes(context(), {"overlays": [{"x": 0}]})
        with self.assertRaises(ValueError):
            overlay_nodes(context(), {"overlays": [item(w=True)]})


class OverlayChoreographyTests(unittest.TestCase):
    def test_overlays_animate_through_scene_choreography(self):
        ctx = context(duration=4.0)
        scene = {"type": "statement", "duration": 4.0, "theme": "light",
                 "photo": "media/cards/paper_light.jpg",
                 "overlays": [
                     item(x=0.09, y=0.3, w=0.3, h=0.5, entrance="slide-left"),
                     item(x=0.61, y=0.3, w=0.3, h=0.5, entrance="slide-right"),
                     item(x=0.35, y=0.45, w=0.3, h=0.3,
                          entrance="pop-settle"),
                 ],
                 "cues": {"overlay-0": 0.2, "overlay-1": 0.2,
                          "overlay-2": 1.2}}
        built = build_scene(ctx, scene)
        for role in ("overlay-0", "overlay-1", "overlay-2"):
            self.assertIn(role, built.elements)
        left = built.elements["overlay-0"]
        right = built.elements["overlay-1"]
        brain = built.elements["overlay-2"]
        # slide entrances start offset and settle centred
        self.assertNotAlmostEqual(left.sample(0.2).dx, 0.0)
        self.assertAlmostEqual(left.sample(3.9).dx, 0.0, places=3)
        self.assertNotAlmostEqual(right.sample(0.2).dx, 0.0)
        # pop entrance starts small and transparent, settles opaque
        early = brain.sample(1.2)
        self.assertLess(early.scale, 1.0)
        self.assertLess(early.opacity, 1.0)
        settled = brain.sample(3.9)
        self.assertAlmostEqual(settled.scale, 1.0, places=3)
        self.assertAlmostEqual(settled.opacity, 1.0, places=3)
        # manifest cues land on the choreography plan
        self.assertAlmostEqual(
            built.choreography.entries["overlay-2"].onset, 1.2)

    def test_scale_from_overrides_pop_start_scale(self):
        from reels_maker.components.scenes import build_scene
        ctx = context(duration=3.0)
        scene = {"type": "statement", "duration": 3.0, "theme": "light",
                 "photo": "media/cards/paper_light.jpg",
                 "overlays": [item(x=0.3, y=0.3, w=0.2, h=0.2,
                                   entrance="pop-settle", scale_from=0.55)],
                 "cues": {"overlay-0": 0.3}}
        built = build_scene(ctx, scene)
        node = built.elements["overlay-0"]
        self.assertAlmostEqual(node.sample(0.3).scale, 0.55, places=2)
        self.assertAlmostEqual(node.sample(2.9).scale, 1.0, places=3)

    def test_easing_override_applies(self):
        from reels_maker.components.scenes import build_scene
        ctx = context(duration=3.0)
        scene = {"type": "statement", "duration": 3.0, "theme": "light",
                 "photo": "media/cards/paper_light.jpg",
                 "overlays": [item(x=0.3, y=0.3, w=0.2, h=0.2,
                                   entrance="slide-left", easing="out-expo")],
                 "cues": {"overlay-0": 0.3}}
        built = build_scene(ctx, scene)
        node = built.elements["overlay-0"]
        self.assertEqual(node.tracks["dx"].keys[0].easing, "out-expo")
        with self.assertRaises(ValueError):
            overlay_nodes(context(), {"overlays": [item(easing="warp")]})
        from reels_maker.motionkit.presets import apply_entrance
        from reels_maker.core.scene_graph import Node
        with self.assertRaises(ValueError):
            apply_entrance(Node(kind="image", role="x"),
                           "slide-left", 0.0, 0.5, context().tokens,
                           easing="warp")

    def test_rejects_bad_scale_from(self):
        with self.assertRaises(ValueError):
            overlay_nodes(context(), {"overlays": [item(scale_from=0.01)]})
        with self.assertRaises(ValueError):
            overlay_nodes(context(), {"overlays": [item(scale_from="big")]})
        from reels_maker.motionkit.presets import apply_entrance
        from reels_maker.core.scene_graph import Node
        with self.assertRaises(ValueError):
            apply_entrance(Node(kind="image", role="x"),
                           "pop-settle", 0.0, 0.5, context().tokens,
                           scale_from=float("nan"))

    def test_unknown_cue_role_warns_without_crash(self):
        ctx = context()
        scene = {"type": "statement", "duration": 2.0, "theme": "light",
                 "photo": "media/cards/paper_light.jpg",
                 "overlays": [item()],
                 "cues": {"overlay-9": 0.5}}
        built = build_scene(ctx, scene)
        codes = [w["code"] for w in built.choreography.warnings]
        self.assertIn("cue_without_element", codes)


class OverlayDynamicsTests(unittest.TestCase):
    """path / appear / press / ripple / exit overlay extensions."""

    def scene(self, overlays, duration=4.0, **extra):
        base = {"type": "statement", "duration": duration, "theme": "light",
                "photo": "media/cards/paper_light.jpg", "overlays": overlays}
        base.update(extra)
        return base

    def test_path_moves_overlay_absolutely(self):
        built = build_scene(context(), self.scene([item(
            entrance="none",
            path=[{"t": 1.0, "x": 0.3, "y": 0.4},
                  {"t": 2.0, "x": 0.5, "y": 0.5}])]))
        node = built.elements["overlay-0"]
        # before the first key the overlay holds the first path position
        self.assertAlmostEqual(node.sample(0.0).dx, 0.0, places=3)
        mid = node.sample(1.5)
        self.assertGreater(mid.dx, 0.0)
        self.assertGreater(mid.dy, 0.0)
        end = node.sample(3.9)
        self.assertAlmostEqual(end.dx, (0.5 - 0.3) * 720, places=1)
        self.assertAlmostEqual(end.dy, (0.5 - 0.4) * 1280, places=1)

    def test_path_rejects_translating_entrance(self):
        with self.assertRaises(ValueError):
            build_scene(context(), self.scene([item(
                entrance="slide-left",
                path=[{"t": 0.5, "x": 0.3, "y": 0.4}])]))

    def test_path_rejects_bad_times_and_offscreen(self):
        with self.assertRaises(ValueError):
            build_scene(context(), self.scene([item(entrance="none", path=[
                {"t": 2.0, "x": 0.3, "y": 0.4},
                {"t": 1.0, "x": 0.4, "y": 0.4}])]))
        with self.assertRaises(ValueError):
            build_scene(context(), self.scene([item(
                entrance="none",
                path=[{"t": 0.5, "x": 0.7, "y": 0.4}])]))

    def test_appear_hides_overlay_until_onset(self):
        built = build_scene(context(), self.scene([item(
            entrance="none", appear={"at": 1.5, "duration": 0.5})]))
        node = built.elements["overlay-0"]
        self.assertEqual(node.sample(0.5).opacity, 0.0)
        self.assertEqual(node.sample(1.5).opacity, 0.0)
        self.assertGreater(node.sample(2.0).opacity, 0.5)
        self.assertAlmostEqual(node.sample(3.9).opacity, 1.0, places=3)

    def test_press_dips_scale_then_recovers(self):
        built = build_scene(context(), self.scene([item(
            entrance="none", press={"at": 2.0, "depth": 0.08,
                                   "duration": 0.2})]))
        node = built.elements["overlay-0"]
        self.assertAlmostEqual(node.sample(1.9).scale, 1.0, places=3)
        dipped = node.sample(2.09)
        self.assertLess(dipped.scale, 0.95)
        self.assertAlmostEqual(node.sample(2.5).scale, 1.0, places=2)

    def test_burn_exit_adds_progress_track_and_seed(self):
        built = build_scene(context(), self.scene([item(
            entrance="none",
            exit={"style": "burn", "at": 2.5, "duration": 1.0,
                  "seed": 3})]))
        node = built.elements["overlay-0"]
        self.assertIn("prop.burn_progress", node.tracks)
        self.assertEqual(node.sample(2.0).props.get("burn_progress"), 0.0)
        self.assertAlmostEqual(node.sample(3.0).props["burn_progress"],
                               0.5, places=2)
        self.assertIn("burn_seed", node.meta)
        self.assertEqual(node.sample(3.9).opacity, 0.0)

    def test_tear_exit_adds_progress_track_and_seed(self):
        built = build_scene(context(), self.scene([item(
            entrance="none",
            exit={"style": "tear", "at": 2.0, "duration": 0.8,
                  "seed": 5})]))
        node = built.elements["overlay-0"]
        self.assertIn("prop.tear_progress", node.tracks)
        self.assertNotIn("prop.burn_progress", node.tracks)
        self.assertEqual(node.sample(1.9).props.get("tear_progress"), 0.0)
        self.assertGreater(node.sample(2.5).props["tear_progress"], 0.0)
        self.assertAlmostEqual(node.sample(2.8).props["tear_progress"],
                               1.0, places=3)
        self.assertLess(node.sample(3.9).opacity, 0.01)

    def test_tear_rejects_bad_seed(self):
        with self.assertRaises(ValueError):
            build_scene(context(), self.scene([item(
                exit={"style": "tear", "seed": "x"})]))

    def test_fade_exit_uses_opacity_track(self):
        built = build_scene(context(), self.scene([item(
            entrance="none",
            exit={"style": "fade", "at": 3.0, "duration": 0.8})]))
        node = built.elements["overlay-0"]
        self.assertNotIn("prop.burn_progress", node.tracks)
        self.assertLess(node.sample(3.9).opacity, 0.2)

    def test_ripple_adds_ring_sibling(self):
        built = build_scene(context(), self.scene([item(
            entrance="none",
            ripple={"at": 2.0, "cx": 0.5, "cy": 0.5, "radius": 0.2,
                    "duration": 0.6, "color": "#47A013"})]))
        ripple = built.elements.get("overlay-0-ripple")
        self.assertIsNone(ripple)  # sibling node, not an element
        rings = [n for n in built.nodes if n.role == "overlay-0-ripple"]
        self.assertEqual(len(rings), 1)
        ring = rings[0]
        self.assertEqual(ring.kind, "ring")
        self.assertIn("prop.r", ring.tracks)
        early = ring.sample(1.9)
        late = ring.sample(2.5)
        self.assertEqual(early.opacity, 0.0)
        self.assertGreater(late.props["r"], early.props["r"])
        self.assertEqual(late.sample(3.9).opacity, 0.0)

    def test_dynamics_validation_errors(self):
        with self.assertRaises(ValueError):
            build_scene(context(), self.scene([item(exit={"style": "explode"})]))
        with self.assertRaises(ValueError):
            build_scene(context(), self.scene([item(
                exit={"style": "burn", "at": 3.9, "duration": 0.6})]))
        with self.assertRaises(ValueError):
            build_scene(context(), self.scene([item(
                ripple={"at": 3.9, "cx": 0.5, "cy": 0.5, "radius": 0.2,
                        "duration": 0.6})]))
        with self.assertRaises(ValueError):
            build_scene(context(), self.scene([item(press="hard")]))


def counter_item(**overrides):
    base = {"x": 0.2, "y": 0.6, "w": 0.6, "h": 0.08, "value": 1248,
            "format": {"suffix": " zł", "decimals": 0},
            "color": "#8F2415",
            "count": {"at": 1.0, "duration": 1.0, "from": 180,
                      "easing": "out-cubic"}}
    base.update(overrides)
    return base


class CounterNodeTests(unittest.TestCase):
    def test_count_animates_value_and_fades_in(self):
        nodes = counter_nodes(context(), {"counters": [counter_item()]})
        self.assertEqual(len(nodes), 1)
        node = nodes[0]
        self.assertEqual(node.kind, "number")
        self.assertEqual(node.sample(0.5).opacity, 0.0)
        self.assertEqual(node.sample(1.0).props["value"], 180.0)
        mid = node.sample(1.5)
        self.assertGreater(mid.props["value"], 180.0)
        self.assertLess(mid.props["value"], 1248.0)
        end = node.sample(2.5)
        self.assertAlmostEqual(end.props["value"], 1248.0, places=3)
        self.assertAlmostEqual(end.opacity, 1.0, places=3)

    def test_burn_exit_removes_counter_with_surface(self):
        nodes = counter_nodes(context(), {"counters": [counter_item(
            exit={"style": "burn", "at": 2.0, "duration": 0.8,
                  "seed": 3})]})
        node = nodes[0]
        self.assertIn("prop.burn_progress", node.tracks)
        self.assertEqual(node.sample(1.9).props.get("burn_progress"), 0.0)
        self.assertAlmostEqual(node.sample(2.8).props["burn_progress"],
                               1.0, places=3)
        self.assertLess(node.sample(3.9).opacity, 0.01)

    def test_counter_rotation_and_exit_styles(self):
        nodes = counter_nodes(context(), {"counters": [counter_item(
            rotation=-2.4,
            exit={"style": "tear", "at": 2.0, "duration": 0.8})]})
        node = nodes[0]
        self.assertAlmostEqual(node.rotation, -2.4)
        self.assertIn("prop.tear_progress", node.tracks)
        with self.assertRaises(ValueError):
            counter_nodes(context(), {"counters": [counter_item(
                rotation=90)]})

    def test_counter_validation_errors(self):
        ctx = context()
        with self.assertRaises(ValueError):
            counter_nodes(ctx, {"counters": {"x": 0.1}})
        with self.assertRaises(ValueError):
            counter_nodes(ctx, {"counters": [counter_item(value="high")]})
        with self.assertRaises(ValueError):
            counter_nodes(ctx, {"counters": [counter_item(
                count={"at": 1.0, "duration": 3.5, "from": 0})]})
        with self.assertRaises(ValueError):
            counter_nodes(ctx, {"counters": [counter_item(
                exit={"style": "explode"})]})
        with self.assertRaises(ValueError):
            counter_nodes(ctx, {"counters": [counter_item(
                exit="fade")]} )


if __name__ == "__main__":
    unittest.main()
