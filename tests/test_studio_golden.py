"""MD-08 regression coverage: studio golden frames, transitions, profiles."""
from __future__ import annotations

import unittest
from pathlib import Path

from PIL import Image, ImageChops

import studio_golden
from reels_maker.qa.report import audit
from reels_maker.studio import load_studio
from media_fixtures import has_real_media

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "brands/asta-energy/projects/asta-motion-system-demo.json"
_MEDIA_AVAILABLE = has_real_media(
    ROOT / "brands/asta-energy/media/stock/agrivoltaics_heggelbach_05.webm")


@unittest.skipUnless(_MEDIA_AVAILABLE,
                     "Studio golden rendering requires LFS media unavailable in offline CI")
class StudioGoldenFrameTests(unittest.TestCase):
    def test_every_golden_strip_matches_the_current_engine(self):
        diffs = studio_golden.collect(write=False)
        self.assertEqual(diffs, [])

    def test_comparator_detects_a_single_pixel_mutation(self):
        _, built, renderer = studio_golden.build_demo()
        strip = studio_golden.scene_strip(built, renderer, 0)
        fixture = (studio_golden.FIXTURES / "scene-00-strip.png")
        self.assertTrue(fixture.is_file(), "golden fixture not captured yet")
        with Image.open(fixture) as image:
            golden = image.convert("RGB").copy()
        mutated = golden.copy()
        mutated.putpixel((mutated.width // 2, mutated.height // 2),
                         (255 - mutated.getpixel(
                             (mutated.width // 2, mutated.height // 2))[0],
                          40, 40))
        self.assertTrue(ImageChops.difference(
            strip, golden).getbbox() is None,
            "engine output drifted from its own fresh strip")
        self.assertIsNotNone(ImageChops.difference(strip, mutated).getbbox())
        self.assertIsNotNone(ImageChops.difference(golden, mutated).getbbox())

    def test_consecutive_transitions_never_repeat_the_same_style(self):
        project, built, _ = studio_golden.build_demo()
        previous = None
        for scene in built:
            transition = scene.meta["transition_in"]
            if previous is not None:
                self.assertNotEqual(
                    transition, previous,
                    "style-targeted audience reads repeated identical cuts "
                    "as template motion (reference-board grammar #9)")
            previous = transition
            self.assertIsInstance(scene.meta["transition_duration"], float)

    def test_demo_audit_reports_animated_safe_area_blocks_at_preview_profile(self):
        with self.subTest(profile="preview"):
            project = load_studio(DEMO, root=ROOT, profile="preview")
            timeline = project.timeline()
            built = project.build(timeline)
            report = audit(project, built, timeline, samples_per_scene=4)
            self.assertFalse(report["ok"], report["issues"])
            self.assertTrue({"text_ink_safe_area", "safe_area_violation", "element_collision"}
                            & {issue["code"] for issue in report["issues"]})


if __name__ == "__main__":
    unittest.main()
