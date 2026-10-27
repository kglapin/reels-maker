"""Regression coverage for the reusable Pillow motion-design studio."""
from __future__ import annotations

import copy
import contextlib
import io
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from PIL import Image, ImageChops

from reels_maker.audiokit.cues import load_transcript, plan_cues
from reels_maker.components.base import SceneContext
from reels_maker.components.scenes import build_scene
from reels_maker.components.title_overlay import build_title_overlay
from reels_maker.core.scene_graph import Node, collect_qa_elements
from reels_maker.design.color import contrast_ratio, ensure_contrast
from reels_maker.design.tokens import resolve_tokens
from reels_maker.ffmpeg import RenderError
from reels_maker.qa.report import _audio_report, audit
from reels_maker.renderers.scene import RenderOptions, SceneRenderer
from reels_maker.renderers.studio import probe_output, render_studio
from reels_maker.spec import Project
from reels_maker.studio import StudioError, load_kinetic_studio, load_studio
from reels_maker.textkit.typesetter import FontBook, Run
from media_fixtures import has_real_media

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "brands/asta-energy/projects/asta-motion-system-demo.json"
_DEMO_MEDIA_AVAILABLE = has_real_media(
    ROOT / "brands/asta-energy/media/stock/agrivoltaics_heggelbach_05.webm")


class StudioDesignTests(unittest.TestCase):
    def test_gravity_words_interleaves_icons_as_reproducible_bouncing_beats(self):
        width, height, fps = 720, 1280, 30
        tokens = resolve_tokens("editorial-premium", width=width, height=height)
        context = SceneContext(width, height, fps, 6.0, tokens,
                               "editorial-premium", FontBook(), seed=42)
        scene = {
            "type": "gravity_words", "duration": 6.0,
            "headline": "one two three four five six",
            "word_drop": {
                "start": .2, "stagger": .5, "duration": .9,
                "distance_units": 120, "restitution": .48,
                "pan_duration": .1,
                "icons": {
                    "count": 2, "library": "lucide",
                    "names": ["sparkles", "heart"],
                    "color": "#FFFFFF",
                },
            },
        }

        first = build_scene(context, scene).elements["headline"].children
        second = build_scene(context, scene).elements["headline"].children
        self.assertEqual(len(first), 8)
        self.assertEqual([node.role for node in first],
                         [node.role for node in second])
        icons = [node for node in first if node.kind == "icon"]
        self.assertEqual([node.props["name"] for node in icons],
                         [node.props["name"] for node in second
                          if node.kind == "icon"])
        self.assertEqual([node.props["color"] for node in icons],
                         ["#FFFFFF", "#FFFFFF"])

        onsets = [node.tracks["opacity"].keys[1].time for node in first]
        self.assertEqual(onsets, [round(.2 + index * .5, 6)
                                  for index in range(len(first))])
        reference = first[0].tracks["dy"]
        reference_onset = reference.start
        reference_motion = [(key.time - reference_onset, key.value)
                            for key in reference.keys]
        for node in icons:
            track = node.tracks["dy"]
            onset = track.start
            actual_motion = [(key.time - onset, key.value)
                             for key in track.keys]
            self.assertEqual([value for _time, value in actual_motion],
                             [value for _time, value in reference_motion])
            for (actual_time, _), (expected_time, _) in zip(
                    actual_motion, reference_motion):
                self.assertAlmostEqual(actual_time, expected_time)
            self.assertAlmostEqual(node.sample(onset).dx, 0.0)
            self.assertAlmostEqual(node.sample(onset).dy, -80.0, delta=1.0)

    def test_animated_node_opacity_is_applied_once_to_isolated_layer(self):
        width = height = 24
        tokens = resolve_tokens("editorial-premium", width=width, height=height)
        renderer = SceneRenderer(width, height, tokens, FontBook(),
                                 options=RenderOptions(supersample=1))
        node = Node(kind="rect", role="half-opacity",
                    props={"x": 4, "y": 4, "w": 12, "h": 12,
                           "fill": "#FFFFFF"}, opacity=.5)
        target = Image.new("RGBA", (width, height), "black")
        renderer._draw_node(target, node)
        pixel = target.getpixel((8, 8))
        self.assertTrue(126 <= pixel[0] <= 129, pixel)

    def test_semantic_text_mechanism_family_resolves_to_supported_preset(self):
        tokens = resolve_tokens("editorial-premium", width=360, height=640)
        context = SceneContext(360, 640, 30, 3.0, tokens,
                               "editorial-premium", FontBook())
        built = build_scene(context, {
            "type": "statement", "duration": 3.0,
            "headline": "MECHANISM FAMILY",
            "typography_motion": "vertical-drift",
        })
        self.assertEqual(built.choreography.entries["headline"].preset,
                         "fade-up")

    def test_build_rejects_a_timeline_from_another_project(self):
        from dataclasses import replace

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "project.json"
            manifest.write_text(json.dumps({
                "name": "timeline-check",
                "video": {"width": 360, "height": 640, "fps": 20},
                "scenes": [
                    {"type": "statement", "duration": 1.0,
                     "headline": "ONE SCENE"},
                ],
            }), encoding="utf-8")
            project = load_studio(manifest, root=root)
            timeline = project.timeline()
            with self.assertRaisesRegex(ValueError, "FPS"):
                project.build(replace(timeline, fps=24))
            with self.assertRaisesRegex(ValueError, "scene count"):
                project.build(replace(timeline, scenes=()))

    def test_contrast_adjustment_moves_toward_the_backdrop_opposite(self):
        deep_green = (20, 44, 30)
        accessible = ensure_contrast((71, 160, 19), deep_green, 4.5)
        self.assertGreaterEqual(contrast_ratio(accessible, deep_green), 4.5)

    def test_negative_rich_word_inverts_only_its_bold_glyphs(self):
        width, height, fps = 720, 1280, 30
        tokens = resolve_tokens("editorial-premium", width=width, height=height)
        fonts = FontBook()
        context = SceneContext(width, height, fps, 2.5, tokens,
                               "editorial-premium", fonts, scene_index=0)
        scene = {
            "type": "statement", "duration": 2.5, "decor": False,
            "background": {"kind": "solid", "color": "#345678"},
            "headline": {"runs": [{
                "text": "INVERT", "scale": 1.08, "weight": "bold",
                "color": "white", "effect": "negative",
            }]},
        }
        built = build_scene(context, scene)
        block = built.elements["headline"].props["block"]
        self.assertEqual(block.lines[0].words[0].effect, "negative")
        renderer = SceneRenderer(width, height, tokens, fonts,
                                 options=RenderOptions(supersample=1))
        frame = renderer.render(built, 2.0)
        bounds = built.elements["headline"].meta["bounds"]
        x0, y0, x1, y1 = (round(value) for value in bounds)
        colours = frame.crop((x0, y0, x1, y1)).getcolors(500_000) or []
        self.assertIn((203, 169, 135), {colour for _count, colour in colours})

    def test_negative_rich_word_rejects_light_or_multiword_runs(self):
        with self.assertRaisesRegex(ValueError, "one word"):
            Run("TWO WORDS", scale=1.2, weight="bold", effect="negative")
        with self.assertRaisesRegex(ValueError, "one word"):
            Run("WORD", scale=1.2, weight="regular", effect="negative")

    def test_word_cues_are_exact_and_subtitles_do_not_invent_intra_cue_times(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            word_file = base / "words.json"
            word_file.write_text(json.dumps({"words": [
                {"text": "Energia", "start": 1.2, "end": 1.5},
                {"text": "dla", "start": 1.51, "end": 1.65},
                {"text": "firm", "start": 1.66, "end": 2.0},
            ]}), encoding="utf-8")
            words = load_transcript(word_file)
            plan = plan_cues([{"cue_phrases": {"headline": "dla firm"}}], words)
            self.assertEqual(plan.scenes[0]["headline"], 1.51)
            segment_file = base / "segments.json"
            segment_file.write_text(json.dumps({"segments": [
                {"text": "Energia dla firm", "start": 1, "end": 2}
            ]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "word-level"):
                load_transcript(segment_file)
            subtitle_file = base / "subtitles.srt"
            subtitle_file.write_text(
                "1\n00:00:01,000 --> 00:00:02,000\nEnergia dla firm\n",
                encoding="utf-8")
            subtitle_words = load_transcript(subtitle_file)
            self.assertEqual({word.start for word in subtitle_words}, {1.0})
            self.assertEqual({word.end for word in subtitle_words}, {2.0})

    def test_manifest_cannot_escape_its_brand_root(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project = base / "brands/asta-energy/projects/demo.json"
            project.parent.mkdir(parents=True)
            outside = base / "secret.mp4"
            outside.write_bytes(b"not-media")
            project.write_text(json.dumps({
                "brand": "asta-energy", "video": {"width": 720,
                "height": 1280, "fps": 30},
                "scenes": [{"type": "spotlight", "duration": 1,
                            "photo": "../../../secret.mp4"}],
            }), encoding="utf-8")
            with self.assertRaisesRegex(StudioError, "escapes brand scope"):
                load_studio(project, root=base)

    def test_video_layer_path_is_brand_scoped_and_participates_in_asset_qa(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            brand = root / "brands" / "demo"
            projects = brand / "projects"
            media = brand / "media" / "stock"
            projects.mkdir(parents=True)
            media.mkdir(parents=True)
            clip = media / "generated-demo.mp4"
            clip.write_bytes(b"synthetic-test-placeholder")
            manifest = projects / "demo.json"
            data = {
                "name": "video-layer-check",
                "video": {"width": 360, "height": 640, "fps": 20},
                "scenes": [{
                    "type": "statement", "duration": 1.0,
                    "headline": "VIDEO LAYER",
                    "video_layer": {"path": "media/stock/generated-demo.mp4"},
                }],
            }
            manifest.write_text(json.dumps(data), encoding="utf-8")
            project = load_studio(manifest, root=root)
            built = project.build()
            node = next(node for node in built[0].nodes[0].flatten()
                        if node.kind == "video")
            self.assertEqual(Path(node.props["path"]), clip.resolve())
            report = audit(project, built, project.timeline(), samples_per_scene=2)
            self.assertIn("asset_unreviewed",
                          {issue["code"] for issue in report["issues"]})

            data["scenes"][0]["video_layer"]["path"] = "../../outside.mp4"
            manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(StudioError, "escapes brand scope"):
                load_studio(manifest, root=root)

    def test_studio_qa_includes_camera_canvas_path_violations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "camera.json"
            (root / "photo-a.png").write_bytes(b"not-decoded-by-camera-qa")
            (root / "photo-b.png").write_bytes(b"not-decoded-by-camera-qa")
            manifest.write_text(json.dumps({
                "name": "camera-qa",
                "video": {"width": 720, "height": 1280, "fps": 30},
                "scenes": [
                    {"type": "statement", "duration": 3.0,
                     "headline": "FIRST",
                     "photo": str(root / "photo-a.png"),
                     "camera_canvas": {"x": 600, "y": 620, "angle": 0}},
                    {"type": "statement", "duration": 3.0,
                     "headline": "SECOND",
                     "photo": str(root / "photo-b.png"),
                     "camera_canvas": {"x": 1600, "y": 620, "angle": 90}},
                ],
            }), encoding="utf-8")
            # Camera Canvas QA needs geometry, not decodable photo bytes.
            project = load_studio(manifest, root=root)
            built = project.build()
            report = audit(project, built, project.timeline(), samples_per_scene=2)
            codes = {issue["code"] for issue in report["issues"]}
            self.assertIn("excessive_camera_rotation", codes)
            self.assertFalse(report["ok"])

    def test_three_brand_profiles_keep_palette_and_style_isolated(self):
        brands = (
            ("energy", "#47A013", "editorial-premium"),
            ("technology", "#2864DC", "product-cinematic"),
            ("services", "#A24670", "social-native"),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resolved = []
            for slug, accent, style in brands:
                brand_root = root / "brands" / slug
                projects = brand_root / "projects"
                projects.mkdir(parents=True)
                (brand_root / "brand.json").write_text(json.dumps({
                    "id": slug,
                    "branding": {"accent": accent},
                    "identity": {"palette": {
                        "primary": accent, "background": "#111820",
                        "text": "#FFFFFF", "neutral": "#233040"}},
                }), encoding="utf-8")
                manifest = projects / "demo.json"
                manifest.write_text(json.dumps({
                    "brand": slug, "style": style,
                    "video": {"width": 360, "height": 640, "fps": 20},
                    "scenes": [{"type": "statement", "duration": 2,
                                "headline": f"{slug.upper()}", "decor": False}],
                }), encoding="utf-8")
                project = load_studio(manifest, root=root, profile="preview")
                built = project.build()
                resolved.append((project.brand, project.style,
                                 project.tokens.palette.as_hex()["accent"],
                                 built[0].meta["headline"]))
            self.assertEqual([item[0] for item in resolved],
                             [item[0] for item in brands])
            self.assertEqual([item[1] for item in resolved],
                             [item[2] for item in brands])
            self.assertEqual([item[2] for item in resolved],
                             [item[1] for item in brands])

    @unittest.skipUnless(_DEMO_MEDIA_AVAILABLE,
                         "Studio demo source video is LFS-backed and unavailable in offline CI")
    def test_demo_builds_all_scene_compositions_and_qa_reports_animated_geometry_blocks(self):
        project = load_studio(DEMO, root=ROOT, profile="review")
        timeline = project.timeline()
        scenes = project.build(timeline)
        self.assertEqual(project.tokens.palette.as_hex()["surface"], "#F7F7F2")
        self.assertEqual(len(scenes), 13)
        self.assertEqual(len({scene.layout.recipe for scene in scenes}), 12)
        self.assertEqual(scenes[-1].elements["logo"].kind, "image")
        comparison_elements = [
            element for node in scenes[7].at(2.0)
            for element in collect_qa_elements(node)]
        label_paths = {element["path"] for element in comparison_elements
                       if element["role"] == "label"}
        self.assertIn("column-0/label", label_paths)
        self.assertIn("column-1/label", label_paths)
        renderer = SceneRenderer(
            project.width, project.height, project.tokens, project.fonts,
            options=RenderOptions(supersample=1))
        report = audit(project, scenes, timeline, renderer=renderer, strict=True)
        self.assertFalse(report["ok"])
        self.assertGreater(report["summary"]["errors"], 0)
        self.assertTrue({"text_ink_safe_area", "safe_area_violation", "element_collision"}
                        & {issue["code"] for issue in report["issues"]})
        self.assertIn("negative_text_review",
                      {issue["code"] for issue in report["issues"]})

    @unittest.skipUnless(_DEMO_MEDIA_AVAILABLE,
                         "Studio demo source video is LFS-backed and unavailable in offline CI")
    def test_qa_detects_collision_and_safe_area_regressions(self):
        project = load_studio(DEMO, root=ROOT, profile="review")
        timeline = project.timeline()
        built = project.build(timeline)
        scene = built[0]
        scene.elements["body"].meta["bounds"] = scene.elements["headline"].meta["bounds"]
        report = audit(project, built, timeline, samples_per_scene=4)
        self.assertIn("element_collision",
                      {issue["code"] for issue in report["issues"]})

        built = project.build(timeline)
        built[0].elements["body"].props["x"] = -10
        report = audit(project, built, timeline, samples_per_scene=4)
        # 9:16 scenes are checked against the stricter platform content zone.
        self.assertIn("reels_content_safe_zone",
                      {issue["code"] for issue in report["issues"]})

    def test_demo_layouts_report_geometry_blocks_in_three_aspects(self):
        source = json.loads(DEMO.read_text(encoding="utf-8"))
        source.pop("export", None)
        for scene in source["scenes"]:
            scene.pop("photo", None)
            scene.pop("photo_time", None)
        for label, (width, height) in (
                ("portrait", (1080, 1920)),
                ("square", (1080, 1080)),
                ("landscape", (1920, 1080))):
            with self.subTest(aspect=label), tempfile.TemporaryDirectory() as directory:
                data = copy.deepcopy(source)
                data["video"] = {"width": width, "height": height, "fps": 30}
                manifest = Path(directory) / f"{label}.json"
                manifest.write_text(json.dumps(data, ensure_ascii=False),
                                    encoding="utf-8")
                project = load_studio(manifest, root=ROOT)
                timeline = project.timeline()
                built = project.build(timeline)
                report = audit(project, built, timeline, samples_per_scene=4)
                self.assertFalse(report["ok"], report["issues"])
                self.assertGreater(report["summary"]["errors"], 0)
                self.assertTrue({"text_ink_safe_area", "safe_area_violation", "element_collision"}
                                & {issue["code"] for issue in report["issues"]})

    def test_audio_report_keeps_resolved_track_path_and_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audio = root / "music.wav"
            audio.write_bytes(b"placeholder")
            manifest = root / "audio.json"
            manifest.write_text(json.dumps({
                "name": "audio report", "video": {"width": 360,
                "height": 640, "fps": 20},
                "audio": {"music": {"file": str(audio), "volume": .2}},
                "scenes": [{"type": "statement", "duration": 1,
                            "headline": "ENERGIA"}],
            }), encoding="utf-8")
            project = load_studio(manifest, root=ROOT, profile="preview")
            report = _audio_report(project, project.timeline())
            self.assertEqual(report["music"]["path"], str(audio.resolve()))

    def test_legacy_kinetic_manifest_adapts_to_shared_scene_graph(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            manifest = base / "legacy-kinetic.json"
            manifest.write_text(json.dumps({
                "name": "legacy compatibility",
                "identity": {"name": "Example", "accent": "#336699"},
                "video": {"width": 360, "height": 640, "fps": 20},
                "scenes": [{"type": "amount", "duration": 1.5,
                            "value": 16000, "kicker": "DOTACJA",
                            "subtitle": "PRZYKŁADOWA DANA",
                            "visual": "none"}],
            }), encoding="utf-8")
            project, default_output = load_kinetic_studio(manifest, root=ROOT)
            self.assertIsNone(default_output)
            self.assertEqual(project.style, "kinetic-advertising")
            self.assertEqual(project.tokens.palette.as_hex()["accent"], "#336699")
            self.assertEqual(project.build()[0].meta["value"], 16000)

    def test_legacy_kinetic_cli_backend_remains_the_default(self):
        from reels_maker.cli import main
        stdout = io.StringIO()
        with patch("reels_maker.kinetic_video.render_kinetic",
                   return_value={"ok": True}) as legacy_render:
            with contextlib.redirect_stdout(stdout):
                code = main(["kinetic-render", "old-project.json", "--json"])
        self.assertEqual(code, 0)
        legacy_render.assert_called_once()
        self.assertEqual(json.loads(stdout.getvalue())["status"], "ok")


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg and FFprobe are required for export integration")
class StudioRenderIntegrationTests(unittest.TestCase):
    def test_small_project_renders_a_probeable_real_mp4(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            manifest = base / "tiny.json"
            manifest.write_text(json.dumps({
                "name": "studio-smoke", "video": {"width": 360,
                "height": 640, "fps": 20},
                "scenes": [
                    {"type": "statement", "duration": 1.0,
                     "headline": "ENERGIA", "subtitle": "DLA FIRM"},
                    {"type": "amount", "duration": 1.0, "visual": "none",
                     "value": 16000, "subtitle": "PRZYKŁADOWE DANE"},
                ],
            }), encoding="utf-8")
            project = load_studio(manifest, root=ROOT, profile="preview")
            output = base / "studio-smoke.mp4"
            result = render_studio(project, output=output, profile="preview",
                                   supersample=1)
            self.assertTrue(result["ok"])
            self.assertGreater(output.stat().st_size, 1000)
            metadata = probe_output(output)
            self.assertEqual((metadata["width"], metadata["height"]), (360, 640))
            self.assertAlmostEqual(metadata["duration"], 2.0, delta=.1)
            self.assertEqual(metadata["codec"], "h264")

    def test_synthetic_music_is_mixed_as_aac_without_changing_video(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            music = base / "tone.wav"
            subprocess.run([
                shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=1.5",
                "-ac", "2", "-ar", "48000", str(music),
            ], check=True, capture_output=True)
            manifest = base / "with-audio.json"
            manifest.write_text(json.dumps({
                "name": "studio-audio-smoke", "video": {"width": 360,
                "height": 640, "fps": 20},
                "audio": {
                    "music": {"file": str(music), "volume": .1,
                              "fade_out": .2, "ducking": "off"},
                    "sfx": [{"file": str(music), "time": .25,
                             "gain_db": -24}],
                },
                "scenes": [{"type": "statement", "duration": 1.0,
                            "headline": "ENERGIA"}],
            }), encoding="utf-8")
            project = load_studio(manifest, root=ROOT, profile="preview")
            output = base / "studio-audio-smoke.mp4"
            result = render_studio(project, output=output, profile="preview",
                                   supersample=1)
            metadata = probe_output(output)
            self.assertTrue(result["audio"]["music"])
            self.assertEqual(result["audio"]["sfx"], 1)
            self.assertEqual(metadata["audio_codec"], "aac")

    def test_failed_export_preserves_the_previous_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            manifest = base / "invalid-crf.json"
            manifest.write_text(json.dumps({
                "name": "atomic-smoke", "video": {"width": 360,
                "height": 640, "fps": 20},
                "export": {"codec": "not_a_real_codec"},
                "scenes": [{"type": "statement", "duration": 1.0,
                            "headline": "ENERGIA"}],
            }), encoding="utf-8")
            project = load_studio(manifest, root=ROOT, profile="preview")
            output = base / "keep.mp4"
            previous = b"previous-valid-delivery-placeholder"
            output.write_bytes(previous)
            with self.assertRaises(RenderError):
                render_studio(project, output=output, profile="preview",
                              supersample=1)
            self.assertEqual(output.read_bytes(), previous)
            self.assertEqual(list(base.glob(".reels-studio-*")), [])

    def test_kinetic_cli_can_opt_into_shared_studio_engine(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            manifest = base / "legacy-kinetic.json"
            output = base / "kinetic-studio.mp4"
            manifest.write_text(json.dumps({
                "name": "kinetic adapter smoke",
                "video": {"width": 360, "height": 640, "fps": 20},
                "scenes": [{"type": "amount", "duration": 1.5,
                            "value": 16000, "visual": "none"}],
            }), encoding="utf-8")
            completed = subprocess.run([
                str(ROOT / ".venv/bin/reels-maker"), "kinetic-render",
                str(manifest), "--root", str(ROOT), "--output", str(output),
                "--engine", "studio", "--json",
            ], text=True, capture_output=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["engine"], "studio")
            self.assertEqual(probe_output(output)["codec"], "h264")

    def test_classic_video_render_can_opt_into_studio_title_overlays(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source.mp4"
            music = base / "tone.wav"
            subprocess.run([
                shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i",
                "color=c=0x335577:s=320x240:r=20:d=2",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
            ], check=True, capture_output=True)
            subprocess.run([
                shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "sine=frequency=330:duration=2",
                "-ac", "2", "-ar", "48000", str(music),
            ], check=True, capture_output=True)
            manifest = base / "classic.json"
            manifest.write_text(json.dumps({
                "name": "shared-overlay-smoke",
                "video": {"width": 360, "height": 640, "fps": 20},
                "music": {"file": "tone.wav", "volume": .1,
                          "fade_out": .2, "ducking": "off"},
                "scenes": [{
                    "file": "source.mp4", "start": 0, "duration": 1.8,
                    "framing": "crop",
                    "motion": {"preset": "rise_soft", "duration_frames": 4,
                               "stagger_frames": 2, "distance_px": 12,
                               "cue_seconds": {"headline": .15, "body": .42}},
                    "title": {"theme": "dark", "backdrop": "soft",
                              "logo": False, "kicker": "ASTA ENERGY",
                              "headline": "WSPÓLNY SILNIK",
                              "body": "Tekst na ruchomym obrazie"},
                }],
            }), encoding="utf-8")
            output = base / "classic-studio-title.mp4"
            completed = subprocess.run([
                str(ROOT / ".venv/bin/reels-maker"), "render", str(manifest),
                "--root", str(base), "--output", str(output), "--jobs", "1",
                "--no-cache", "--title-engine", "studio", "--json",
            ], text=True, capture_output=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["title_engine"], "studio")
            metadata = probe_output(output)
            self.assertEqual((metadata["width"], metadata["height"]), (360, 640))
            self.assertEqual(metadata["frames"], 36)
            self.assertEqual(metadata["audio_codec"], "aac")
            first, last = base / "first.png", base / "last.png"
            for timestamp, frame in ((.15, first), (1.55, last)):
                subprocess.run([
                    shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error",
                    "-ss", str(timestamp), "-i", str(output),
                    "-frames:v", "1", str(frame),
                ], check=True, capture_output=True)
            with Image.open(first) as first_frame, Image.open(last) as last_frame:
                difference = ImageChops.difference(
                    first_frame.convert("RGB"), last_frame.convert("RGB"))
                self.assertIsNotNone(difference.getbbox())

    def test_classic_title_engine_choice_invalidates_cached_scene(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source.mp4"
            subprocess.run([
                shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "color=c=0x335577:s=320x240:r=20:d=1.5",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
            ], check=True, capture_output=True)
            manifest = base / "classic-cache.json"
            manifest.write_text(json.dumps({
                "name": "title-engine-cache",
                "video": {"width": 360, "height": 640, "fps": 20},
                "scenes": [{"file": "source.mp4", "duration": 1.2,
                            "title": {"theme": "dark", "logo": False,
                                      "headline": "CACHE TEST"}}],
            }), encoding="utf-8")
            cache = base / "shared-cache"
            executable = str(ROOT / ".venv/bin/reels-maker")
            outputs = []
            for engine in ("legacy", "studio", "studio"):
                output = base / f"{engine}-{len(outputs)}.mp4"
                command = [executable, "render", str(manifest), "--root",
                           str(base), "--output", str(output), "--cache-dir",
                           str(cache), "--jobs", "1", "--json"]
                if engine != "legacy":
                    command += ["--title-engine", engine]
                completed = subprocess.run(command, text=True,
                                           capture_output=True, check=False)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                outputs.append(json.loads(completed.stdout))
            self.assertEqual(outputs[0]["cache_misses"], 1)
            self.assertEqual(outputs[1]["cache_misses"], 1)
            self.assertEqual(outputs[2]["cache_hits"], 1)

    def test_classic_audio_mix_matches_across_title_engines(self):
        """Same manifest, both title engines: identical, valid audio output."""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source.mp4"
            music = base / "tone.wav"
            subprocess.run([
                shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i",
                "color=c=0x335577:s=320x240:r=20:d=2",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
            ], check=True, capture_output=True)
            subprocess.run([
                shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "sine=frequency=330:duration=2",
                "-ac", "2", "-ar", "48000", str(music),
            ], check=True, capture_output=True)
            manifest = base / "audio-parity.json"
            manifest.write_text(json.dumps({
                "name": "audio-parity-across-engines",
                "video": {"width": 360, "height": 640, "fps": 20},
                "music": {"file": "tone.wav", "volume": .4,
                          "fade_out": .4, "ducking": "off"},
                "scenes": [{
                    "file": "source.mp4", "start": 0, "duration": 1.8,
                    "framing": "crop",
                    "title": {"theme": "dark", "backdrop": "soft",
                              "logo": False, "headline": "PARITY"},
                }],
            }), encoding="utf-8")
            executable = str(ROOT / ".venv/bin/reels-maker")
            outputs = []
            for engine in ("legacy", "studio"):
                output = base / f"audio-parity-{engine}.mp4"
                command = [executable, "render", str(manifest), "--root",
                           str(base), "--output", str(output), "--jobs", "1",
                           "--no-cache", "--json"]
                if engine != "legacy":
                    command += ["--title-engine", engine]
                completed = subprocess.run(command, text=True,
                                           capture_output=True, check=False)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                outputs.append(output)
            legacy_meta, studio_meta = (probe_output(path)
                                        for path in outputs)
            self.assertEqual(legacy_meta["audio_codec"], "aac")
            self.assertEqual(studio_meta["audio_codec"], "aac")
            self.assertLessEqual(
                abs(float(legacy_meta["duration"])
                    - float(studio_meta["duration"])), .05)
            loudness = {}
            for engine, path in (("legacy", outputs[0]),
                                 ("studio", outputs[1])):
                probe = subprocess.run([
                    shutil.which("ffmpeg"), "-hide_banner", "-i", str(path),
                    "-map", "0:a:0", "-af", "volumedetect", "-f", "null", "-",
                ], text=True, capture_output=True, check=True)
                match = re.search(r"mean_volume:\s*(-?[\d.]+) dB",
                                  probe.stderr)
                self.assertIsNotNone(match, probe.stderr)
                loudness[engine] = float(match.group(1))
            self.assertLessEqual(abs(loudness["legacy"]
                                     - loudness["studio"]), .4)

    def test_brand_tokens_drive_studio_title_overlay_visuals(self):
        """Classic-title bridge consumes branding accent, not a fixed palette."""
        scene = {"duration": 2.0,
                 "title": {"theme": "dark", "backdrop": "soft",
                           "headline": "TOKENS", "accent_rule": True}}
        fills = []
        for accent in ("#47A013", "#2864DC"):
            project = Project(
                "brand-isolation", 360, 640, 20, [dict(scene)], None,
                {"accent": accent,
                 "motion_style": "editorial-premium"}, "isolation.mp4")
            built = build_title_overlay(
                project, scene, index=0, duration=2.0, logo=None)
            fills.append((
                built.elements["accent-rule"].props["fill"],
                built.context.tokens.palette.as_hex()["accent"]))
        self.assertNotEqual(fills[0][0], fills[1][0])
        self.assertNotEqual(fills[0][1], fills[1][1])
        self.assertEqual(fills[0][1], fills[0][0]
                         if isinstance(fills[0][0], str) else fills[0][1])

    def test_studio_title_route_reports_cold_warm_cache_benchmark(self):
        """Second studio render must reuse cached scene parts and be faster."""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source.mp4"
            subprocess.run([
                shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i",
                "color=c=0x506070:s=640x360:r=20:d=3",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
            ], check=True, capture_output=True)
            manifest = base / "bench.json"
            manifest.write_text(json.dumps({
                "name": "studio-cache-bench",
                "video": {"width": 360, "height": 640, "fps": 20},
                "scenes": [{
                    "file": "source.mp4", "start": 0, "duration": 2.6,
                    "framing": "crop",
                    "title": {"theme": "dark", "backdrop": "strong",
                              "logo": False, "kicker": "BENCH",
                              "headline": "COLD TO WARM"},
                }],
            }), encoding="utf-8")
            cache = base / "cache"
            executable = str(ROOT / ".venv/bin/reels-maker")
            timings = []
            for attempt, expect in ((0, "cold"), (1, "warm")):
                output = base / f"bench-{expect}.mp4"
                completed = subprocess.run([
                    executable, "render", str(manifest), "--root", str(base),
                    "--output", str(output), "--cache-dir", str(cache),
                    "--jobs", "1", "--title-engine", "studio", "--json",
                ], text=True, capture_output=True, check=False)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                result = json.loads(completed.stdout)
                timings.append(result["timings_seconds"]["scene_encoding"])
                self.assertEqual(result["cache_hits"],
                                 1 if expect == "warm" else 0)
                self.assertEqual(probe_output(output)["frames"], 52)
            self.assertLess(timings[1], timings[0])
            self.assertLess(timings[1], 1.0)


if __name__ == "__main__":
    unittest.main()
