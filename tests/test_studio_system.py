"""Regression coverage for the reusable Pillow motion-design studio."""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from reels_maker.audiokit.cues import load_transcript, plan_cues
from reels_maker.components.base import SceneContext
from reels_maker.components.scenes import build_scene
from reels_maker.core.scene_graph import collect_qa_elements
from reels_maker.design.color import contrast_ratio, ensure_contrast
from reels_maker.design.tokens import resolve_tokens
from reels_maker.ffmpeg import RenderError
from reels_maker.qa.report import _audio_report, audit
from reels_maker.renderers.scene import RenderOptions, SceneRenderer
from reels_maker.renderers.studio import probe_output, render_studio
from reels_maker.studio import StudioError, load_studio
from reels_maker.textkit.typesetter import FontBook, Run

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "brands/asta-energy/projects/asta-motion-system-demo.json"


class StudioDesignTests(unittest.TestCase):
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

    def test_demo_builds_all_scene_compositions_and_qa_passes(self):
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
        self.assertTrue(report["ok"], report["issues"])
        self.assertEqual(report["summary"]["errors"], 0)

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


if __name__ == "__main__":
    unittest.main()
