"""Distinct title layers, deterministic stagger animation and render validation."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from reels_maker.ffmpeg import RenderError, execute, probe
from reels_maker.spec import Project, ProjectError, load_project
from reels_maker.cards import draw_card
from reels_maker.motion import compose_motion
from reels_maker.renderer import render


class MotionUnitTests(unittest.TestCase):
    def test_layers_are_isolated_and_cropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Project(name="test", width=256, height=448, fps=25,
                        scenes=[], music=None, branding={},
                        output="video.mp4")
            folder = Path(tmp)
            layers = []
            result = draw_card(p, {
                "kicker": "ASTA", "headline": "Energia",
                "body": "Dla firm", "footer": "Kontakt"
            }, None, folder / "background.png", layers=layers)
            self.assertTrue(result)
            self.assertEqual([part["role"] for part in layers],
                             ["accent", "kicker", "headline", "body", "footer"])
            from PIL import Image
            for layer in layers:
                image = Image.open(layer["file"])
                self.assertLess(image.width, p.width)
                self.assertLess(image.height, p.height)
                self.assertGreater(image.getbbox()[2], 0)

    def test_motion_parameters_are_validated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            for config in (
                {"preset": "bounce"},
                {"preset": "editorial_reveal", "duration_frames": -2},
                {"preset": "editorial_reveal", "stagger_frames": 30},
                {"preset": "editorial_reveal", "distance_px": 200},
                {"preset": "fade_stagger", "distance_px": 5},
            ):
                path.write_text(json.dumps({
                    "video": {"fps": 25},
                    "scenes": [{"file": "unused.mp4", "duration": 2,
                                "motion": config}]
                }))
                with self.assertRaises(ProjectError):
                    load_project(path)

    def test_entrance_must_fit_shot(self):
        with self.assertRaises(RenderError):
            compose_motion("scale=256:448", 25, 5, "bg.png", [
                {"file": "layer.png", "x": 2, "y": 5}
            ], {"preset": "editorial_reveal", "duration_frames": 7,
                "stagger_frames": 2}, 256)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg and FFprobe required")
class MotionRenderTests(unittest.TestCase):
    def test_motion_render_and_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            execute(["-f", "lavfi", "-i",
                     "color=c=navy:s=256x448:r=25:d=2",
                     "-an", "-c:v", "libx264",
                     str(root / "source.mp4")])
            manifest = root / "project.json"
            manifest.write_text(json.dumps({
                "video": {"width": 256, "height": 448, "fps": 25},
                "scenes": [{
                    "file": "source.mp4", "duration": 1.6,
                    "title": {"kicker": "ASTA", "headline": "Energia",
                              "body": "Dla firm"},
                    "motion": {"preset": "editorial_reveal",
                               "duration_frames": 6,
                               "stagger_frames": 2, "distance_px": 20}
                }],
                "output": "output/reveal.mp4"
            }))
            p = load_project(manifest)
            cold = render(p, root=root)
            self.assertEqual(cold["scenes_encoded"], 1)
            self.assertAlmostEqual(cold["duration_actual"], 1.6, delta=0.08)
            video = next(s for s in probe(Path(cold["output"]))["streams"]
                         if s["codec_type"] == "video")
            self.assertEqual(int(video["nb_frames"]), 40)
            warm = render(p, root=root)
            self.assertEqual(warm["cache_hits"], 1)
            self.assertEqual(warm["scenes_encoded"], 0)


if __name__ == "__main__":
    unittest.main()
