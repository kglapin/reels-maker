"""End-to-end tests render tiny synthetic clips to exercise FFmpeg and scene cache."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from reels_maker.ffmpeg import execute, probe
from reels_maker.renderer import render, _frame_counts
from reels_maker.spec import load_project
from reels_maker.cli import main


class FrameTimingTests(unittest.TestCase):
    def test_fractional_scene_durations_have_no_accumulated_drift(self):
        from reels_maker.spec import Project
        project = Project(
            name="beat", width=256, height=448, fps=25,
            scenes=[{"file": "unused.mp4", "duration": 1.2771}] * 22,
            music=None, branding={}, output="output/timing.mp4",
        )
        frames = _frame_counts(project)
        self.assertEqual(sum(frames), round(project.duration * project.fps))
        self.assertLess(abs(sum(frames) / project.fps - project.duration), 1 / project.fps)

    def test_too_short_scene_is_rejected(self):
        from reels_maker.spec import Project
        from reels_maker.ffmpeg import RenderError
        project = Project(
            name="invalid", width=256, height=448, fps=25,
            scenes=[{"file": "unused.mp4", "duration": 0.001}],
            music=None, branding={}, output="output/invalid.mp4",
        )
        with self.assertRaises(RenderError):
            _frame_counts(project)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg and FFprobe required")
class RenderIntegrationTests(unittest.TestCase):
    def test_render_validate_and_cache_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, color in (("clip_a.mp4", "blue"), ("clip_b.mp4", "green")):
                execute(["-f", "lavfi", "-i",
                         f"color=c={color}:s=256x448:r=12:d=2.5",
                         "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                         str(root / name)])
            execute(["-f", "lavfi", "-i", "sine=frequency=440:duration=4",
                     "-c:a", "pcm_s16le", str(root / "music.wav")])
            manifest = root / "project.json"
            manifest.write_text(json.dumps({
                "name": "smoke",
                "video": {"width": 256, "height": 448, "fps": 12},
                "scenes": [
                    {"file": "clip_a.mp4", "duration": 1, "title": {
                        "kicker": "ASTA", "headline": "Energia", "body": "Prosty test"}},
                    {"file": "clip_b.mp4", "start": 0.5, "duration": 1,
                     "framing": "pad"}
                ],
                "music": {"file": "music.wav", "volume": 0.3, "fade_out": 0.3},
                "output": "output/test.mp4"
            }), encoding="utf-8")
            self.assertEqual(main(["validate", str(manifest), "--root",
                                   str(root), "--json"]), 0)
            project = load_project(manifest)
            result_1 = render(project, root=root)
            self.assertEqual(result_1["scenes_encoded"], 2)
            self.assertEqual(result_1["cache_hits"], 0)
            self.assertGreater(result_1["size_bytes"], 500)
            metadata = probe(root / "output/test.mp4")
            self.assertTrue(any(s["codec_type"] == "audio" for s in metadata["streams"]))
            self.assertAlmostEqual(result_1["duration_actual"], 2.0, delta=0.25)
            result_2 = render(project, root=root)
            self.assertEqual(result_2["scenes_encoded"], 0)
            self.assertEqual(result_2["cache_hits"], 2)
            self.assertEqual(result_2["cache_hit_rate"], 1.0)
            self.assertGreaterEqual(result_2["timings_seconds"]["total"], 0)
            self.assertTrue(Path(result_2["output"]).is_file())

    def test_silent_render_and_no_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            execute(["-f", "lavfi", "-i", "color=c=black:s=256x448:r=12:d=2",
                     "-an", "-c:v", "libx264", str(root / "clip.mp4")])
            manifest = root / "silent.json"
            manifest.write_text(json.dumps({
                "video": {"width": 256, "height": 448, "fps": 12},
                "scenes": [{"file": "clip.mp4", "duration": 1}],
                "output": "output/silent.mp4"
            }))
            result = render(load_project(manifest), root=root, cache=False)
            self.assertEqual(result["scenes_encoded"], 1)
            self.assertEqual(result["cache_hits"], 0)
            self.assertEqual(len([s for s in probe(Path(result["output"]))["streams"]
                                  if s["codec_type"] == "audio"]), 0)


if __name__ == "__main__":
    unittest.main()
