"""MD-04 acceptance: restrained, hold-preserving exit choreography."""
from __future__ import annotations

import unittest

from reels_maker.core.scene_graph import Node
from reels_maker.design.tokens import resolve_tokens
from reels_maker.motionkit.choreography import (
    ElementSpec, ExitTiming, plan_choreography)
from reels_maker.motionkit.presets import apply_exit
from reels_maker.qa.report import audit
from reels_maker.studio import load_studio
from reels_maker.textkit.typesetter import FontBook

import studio_golden
from media_fixtures import has_real_media

ROOT = None  # imported helpers use absolute demo path


def _tokens(style: str = "editorial-premium"):
    return resolve_tokens(style, width=720, height=1280)


class ExitPlanningTests(unittest.TestCase):
    def test_short_scenes_never_gain_an_exit(self):
        tokens = _tokens()
        specs = [ElementSpec("headline", 10, kind="display"),
                 ElementSpec("kicker", 6, kind="support")]
        plan = plan_choreography(specs, style="editorial-premium",
                                 scene_index=0, scene_duration=1.2,
                                 tokens=tokens)
        self.assertEqual(plan.exits, {},
                         "A 1.2s scene cannot host both reading hold "
                         "and a fade-out")

    def test_long_scenes_get_quiet_exit_after_full_hold(self):
        tokens = _tokens()
        specs = [ElementSpec("headline", 10, kind="display")]
        plan = plan_choreography(specs, style="editorial-premium",
                                 scene_index=0, scene_duration=3.0,
                                 tokens=tokens)
        self.assertIn("headline", plan.exits)
        exits = plan.exits["headline"]
        entry = plan.entries["headline"]
        self.assertEqual(exits.duration, tokens.motion.exit)
        self.assertEqual(exits.onset, round(3.0 - exits.duration, 4))
        self.assertGreaterEqual(exits.onset - entry.settle, tokens.motion.hold)
        self.assertFalse(exits.onset > 3.0)

    def test_decor_elements_are_exempt_from_exits(self):
        tokens = _tokens()
        specs = [ElementSpec("accent-rule", 1, kind="decor")]
        plan = plan_choreography(specs, style="editorial-premium",
                                 scene_index=0, scene_duration=4.0,
                                 tokens=tokens)
        self.assertNotIn("accent-rule", plan.exits)


class ExitApplicationTests(unittest.TestCase):
    def test_static_node_fades_to_zero_at_scene_end(self):
        tokens = _tokens()
        node = Node(kind="text", role="headline", props={})
        apply_exit(node, 2.1, .28, tokens)
        self.assertEqual(float(node.tracks["opacity"].value(1.9)), 1.0)
        self.assertEqual(float(node.tracks["opacity"].value(2.38)), 0.0)
        self.assertNotIn("dy", node.tracks)
        self.assertNotIn("scale", node.tracks)
        self.assertEqual(node.meta["exit_onset"], 2.1)

    def test_animated_node_extends_only_existing_axes(self):
        tokens = _tokens()
        node = Node(kind="text", role="body", props={})
        spec = [ElementSpec("body", 5, kind="support")]
        plan = plan_choreography(spec, style="editorial-premium",
                                 scene_index=0, scene_duration=3.0,
                                 tokens=tokens)
        from reels_maker.motionkit.presets import apply_entrance
        entry = plan.entries["body"]
        apply_entrance(node, entry.preset, entry.onset, entry.duration,
                       tokens, seed=3)
        axes_before = set(node.tracks)
        self.assertIn("opacity", axes_before)
        apply_exit(node, plan.exits["body"].onset,
                   plan.exits["body"].duration, tokens)
        self.assertEqual(set(node.tracks), axes_before,
                         "exit never introduces a new motion axis")
        # Opacity is 1 at settle and 0 at the end of the exit.
        self.assertEqual(float(node.tracks["opacity"].value(entry.settle)),
                         1.0)
        self.assertEqual(float(node.tracks["opacity"].value(3.0)), 0.0)


class ExitPipelineBehaviourTests(unittest.TestCase):
    @unittest.skipUnless(has_real_media(
        studio_golden.ROOT / "brands/asta-energy/media/stock/agrivoltaics_heggelbach_05.webm"),
        "Studio demo source video is LFS-backed and unavailable in offline CI")
    def test_demo_qa_surfaces_geometry_blocks_with_exits_active(self):
        project = load_studio(studio_golden.DEMO, root=studio_golden.ROOT,
                              profile="preview")
        timeline = project.timeline()
        built = project.build(timeline)
        report = audit(project, built, timeline, samples_per_scene=4)
        self.assertFalse(report["ok"], report["issues"])
        self.assertTrue({"text_ink_safe_area", "safe_area_violation", "element_collision"}
                        & {issue["code"] for issue in report["issues"]})
        with_exits = [scene for scene in built if scene.choreography.exits]
        self.assertTrue(with_exits, "expected some demo scenes to host exits")

    @unittest.skipUnless(has_real_media(
        studio_golden.ROOT / "brands/asta-energy/media/stock/agrivoltaics_heggelbach_05.webm"),
        "Studio demo source video is LFS-backed and unavailable in offline CI")
    def test_exit_renders_quieter_at_tail_than_mid_scene(self):
        _, built, renderer = studio_golden.build_demo()
        scene = next(item for item in built if item.choreography.exits)
        exit_onset = next(iter(scene.choreography.exits.values())).onset
        mid = renderer.render(scene, scene.duration * .5)
        tail = renderer.render(scene, scene.duration - .02)
        difference = None
        from PIL import ImageChops
        difference = ImageChops.difference(mid, tail)
        self.assertIsNotNone(difference.getbbox())
