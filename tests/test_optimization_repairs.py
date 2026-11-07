"""Regression tests for the comprehensive optimization/repair pass."""
from __future__ import annotations

import unittest

from PIL import Image

from reels_maker.cli_parser import build_parser
from reels_maker.colormatrix import color_filter
from reels_maker.core.scene_graph import Node
from reels_maker.motionkit.easing import (
    ease, easing_extrema_progress, spring_physics,
)
from reels_maker.motionkit.keyframes import Keyframe, Track
from reels_maker.motionkit.presets import apply_entrance
from reels_maker.design.tokens import resolve_tokens
from reels_maker.renderers.studio import encoder_options
from reels_maker.renderers.transition_engine import transition_frame


class CubicBezierEasingTests(unittest.TestCase):
    def test_cubic_bezier_usable_in_keyframes(self):
        track = Track([
            Keyframe(0.0, 0.0, "cubic-bezier",
                     (("x1", 0.2), ("y1", 1.4), ("x2", 0.3), ("y2", 1.0))),
            Keyframe(1.0, 10.0, "cubic-bezier",
                     (("x1", 0.2), ("y1", 1.4), ("x2", 0.3), ("y2", 1.0))),
        ])
        self.assertEqual(track.value(0.0), 0.0)
        self.assertEqual(track.value(1.0), 10.0)
        # y > 1 is legal CSS overshoot, so mid-flight exceeds the target.
        self.assertGreater(track.value(0.55), 10.0)

    def test_cubic_bezier_rejects_missing_or_bad_params(self):
        with self.assertRaises(ValueError):
            Keyframe(0.0, 1.0, "cubic-bezier", (("x1", 0.2),))
        with self.assertRaises(ValueError):
            ease("cubic-bezier", 0.5, x1=1.5, y1=0.0, x2=0.0, y2=1.0)


class SpringPhysicsTests(unittest.TestCase):
    def test_endpoints_and_underdamped_overshoot(self):
        self.assertEqual(spring_physics(0.0), 0.0)
        self.assertEqual(spring_physics(1.0), 1.0)
        self.assertGreater(spring_physics(0.45), 1.0)

    def test_spring_physics_usable_in_keyframes_and_has_extrema(self):
        track = Track([
            Keyframe(0.0, 0.0, "spring-physics",
                     (("omega", 11.0), ("zeta", 0.3))),
            Keyframe(1.0, 1.0, "spring-physics",
                     (("omega", 11.0), ("zeta", 0.3))),
        ])
        self.assertGreater(track.value(0.45), 1.0)
        self.assertTrue(easing_extrema_progress(
            "spring-physics", omega=11.0, zeta=0.3))


class NonUniformScaleTests(unittest.TestCase):
    def test_scale_xy_track_squashes_node(self):
        node = Node(kind="rect", props={"x": 0, "y": 0, "w": 100, "h": 50})
        node.track("scale_xy", Track([
            Keyframe(0.0, (1.0, 1.0)), Keyframe(1.0, (1.2, 0.8))]))
        sampled = node.sample(1.0)
        self.assertEqual(sampled.effective_scale(), (1.2, 0.8))
        box = sampled.world_bounds()
        self.assertAlmostEqual(box[2] - box[0], 120.0, places=5)
        self.assertAlmostEqual(box[3] - box[1], 40.0, places=5)

    def test_anticipate_pop_preset_dips_vertically(self):
        node = Node(kind="rect", props={"x": 10, "y": 10, "w": 40, "h": 40})
        apply_entrance(node, "anticipate-pop", 0.0, 0.6,
                       resolve_tokens("editorial-premium"))
        sampled = node.sample(0.18)
        self.assertLess(sampled.effective_scale()[1], 1.0)
        self.assertEqual(node.sample(0.6).effective_scale(), (1.0, 1.0))


class TransitionEasingTests(unittest.TestCase):
    def test_per_effect_easing_changes_mid_frame(self):
        a = Image.new("RGB", (32, 32), (200, 0, 0))
        b = Image.new("RGB", (32, 32), (0, 0, 200))
        smooth = transition_frame(a, b, 0.4, effect="diagonal-wipe")
        linear = transition_frame(a, b, 0.4, effect="diagonal-wipe",
                                  easing="linear")
        self.assertNotEqual(smooth.tobytes(), linear.tobytes())

    def test_unknown_easing_rejected(self):
        a = Image.new("RGB", (16, 16), (0, 0, 0))
        with self.assertRaises(ValueError):
            transition_frame(a, a, 0.5, easing="nope")


class EncoderAndCliTests(unittest.TestCase):
    def test_hw_encoder_uses_quality_bitrate_not_crf_preset(self):
        hw = encoder_options("h264_videotoolbox", crf=20, preset="medium",
                             threads=2)
        self.assertIn("h264_videotoolbox", hw)
        self.assertNotIn("-crf", hw)
        self.assertNotIn("-preset", hw)
        cpu = encoder_options("libx264", crf=20, preset="medium", threads=2)
        self.assertIn("-crf", cpu)
        self.assertEqual(cpu[cpu.index("-threads") + 1], "2")

    def test_studio_render_defaults_to_parallel_jobs(self):
        args = build_parser().parse_args(["studio-render", "x.json"])
        self.assertGreaterEqual(args.jobs, 2)


class StoryboardExtremaTests(unittest.TestCase):
    def test_peak_times_come_from_overshoot_tracks(self):
        from types import SimpleNamespace
        from reels_maker.storyboard import _extrema_local_times
        node = Node(kind="rect", props={"x": 0, "y": 0, "w": 10, "h": 10})
        node.track("scale", Track([
            Keyframe(0.2, 0.88, "back"), Keyframe(1.2, 1.0, "back")]))
        scene = SimpleNamespace(nodes=[node])
        peaks = _extrema_local_times(scene, 3.0)
        self.assertTrue(peaks)
        self.assertTrue(all(0.2 < p < 1.2 for p in peaks))


class ArgparseJsonErrorTests(unittest.TestCase):
    def test_bad_flag_with_json_request_emits_json_error(self):
        import io
        import sys
        from contextlib import redirect_stderr
        from unittest.mock import patch
        stderr = io.StringIO()
        with patch.object(sys, "argv", ["reels-maker", "render", "--json",
                                        "--nope"]), \
                redirect_stderr(stderr), \
                self.assertRaises(SystemExit) as caught:
            build_parser().parse_args(["render", "--json", "--nope"])
        self.assertEqual(caught.exception.code, 2)
        payload = __import__("json").loads(stderr.getvalue())
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["schema_version"], 1)


class TypographyDivergenceTests(unittest.TestCase):
    def test_profile_divergences_are_reported(self):
        from reels_maker.design.typography_policy import (
            typography_profile_divergences)
        divergences = typography_profile_divergences()
        self.assertTrue(divergences)
        self.assertTrue(all(
            d["suggested_px"] != d["rendered_px"] for d in divergences))


class ColorFilterTests(unittest.TestCase):
    def test_color_filter_is_real_ffmpeg_filter_not_copy(self):
        self.assertIn("eq=", color_filter("warm"))
        self.assertIn("colortemperature", color_filter("warm"))
        self.assertIn("eq=", color_filter("sdr"))
        self.assertIn("lut3d", color_filter("custom", lut_path="grade.cube"))
        with self.assertRaises(ValueError):
            color_filter("unknown-grade")


def _studio_manifest(path, codec=None):
    import json
    export = {"profile": "preview"}
    if codec:
        export["codec"] = codec
    path.write_text(json.dumps({
        "name": "opt-repairs",
        "video": {"width": 360, "height": 640, "fps": 20},
        "scenes": [
            {"type": "statement", "duration": 1.0, "headline": "SZYBCIEJ"},
            {"type": "cta", "duration": .9, "headline": "KONTAKT",
             "phone": "+00 000 000 000", "line_one": "TAG",
             "website": "example.org"},
        ],
        "export": export,
    }), encoding="utf-8")


@unittest.skipUnless(__import__("shutil").which("ffmpeg"),
                     "FFmpeg required")
class StudioIntegrationTests(unittest.TestCase):
    def test_hardware_encoder_render_is_valid(self):
        import shutil
        import subprocess
        import tempfile
        from pathlib import Path
        from reels_maker.renderers.studio import probe_output, render_studio
        from reels_maker.studio import load_studio
        ffmpeg = shutil.which("ffmpeg")
        try:
            encoders = subprocess.run(
                [ffmpeg, "-hide_banner", "-encoders"],
                capture_output=True, text=True, timeout=30).stdout or ""
        except (OSError, TypeError, subprocess.SubprocessError):
            encoders = ""
        if "h264_videotoolbox" not in encoders:
            self.skipTest("h264_videotoolbox is macOS-only")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            manifest = base / "hw.json"
            _studio_manifest(manifest, codec="h264_videotoolbox")
            result = render_studio(load_studio(manifest, root=base),
                                   output=base / "hw.mp4", cache=False,
                                   supersample=1, jobs=2)
            self.assertEqual(result["status"], "ok")
            self.assertGreater(probe_output(base / "hw.mp4")["frames"], 0)

    def test_studio_storyboard_single_pass_motion_strip(self):
        import tempfile
        from pathlib import Path
        from reels_maker.renderers.studio import render_studio
        from reels_maker.storyboard import make_studio_storyboard
        from reels_maker.studio import load_studio
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            manifest = base / "board.json"
            _studio_manifest(manifest)
            project = load_studio(manifest, root=base)
            result = render_studio(project, output=base / "board.mp4",
                                   cache=False, supersample=1, jobs=1)
            sheet = base / "board.png"
            report = make_studio_storyboard(
                project, Path(result["output"]), sheet, motion_strip=True)
            self.assertTrue(sheet.is_file())
            phases = {sample["phase"] for sample in report["samples"]}
            self.assertTrue({"entry", "settled", "exit"} <= phases)


if __name__ == "__main__":
    unittest.main()
