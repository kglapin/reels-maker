"""CLI contract checks for Pi/OpenCode and rendering smoke tests."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from reels_maker.cli import main
from reels_maker.spec import load_project
from reels_maker.renderer import render


class CLIContractTest(unittest.TestCase):
    def test_validate_syntax_from_any_workdir(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest = Path(folder) / "project.json"
            manifest.write_text(json.dumps({
                "name": "check", "scenes": [{"file": "missing.mp4", "duration": 1}]
            }))
            proc = subprocess.run([sys.executable, "-m", "reels_maker",
                                   "validate", str(manifest), "--syntax-only", "--json"],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = json.loads(proc.stdout)
            self.assertEqual(result["schema_version"], 1)
            self.assertEqual(result["status"], "ok")
            self.assertFalse(result["media_checked"])

    def test_failure_has_machine_readable_stderr(self):
        proc = subprocess.run([sys.executable, "-m", "reels_maker",
                               "validate", "does-not-exist.json", "--json"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(json.loads(proc.stderr)["status"], "error")
        self.assertEqual(proc.stdout, "")


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg/FFprobe not available")
class TinyRenderTest(unittest.TestCase):
    def test_two_runs_reuse_video_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            clip = root / "input.mp4"
            subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                            "-f", "lavfi", "-i", "testsrc2=size=144x256:rate=12",
                            "-t", "3", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                            str(clip)], check=True)
            project_path = root / "test.json"
            project_path.write_text(json.dumps({
                "name": "integration", "video": {"width": 144, "height": 256, "fps": 12},
                "scenes": [
                    {"file": "input.mp4", "start": 0, "duration": 1},
                    {"file": "input.mp4", "start": 1, "duration": 1, "framing": "pad"}
                ], "output": "output/out.mp4"
            }))
            project = load_project(project_path)
            first = render(project, root=root)
            second = render(project, root=root)
            self.assertEqual(first["cache_misses"], 2)
            self.assertEqual(second["cache_hits"], 2)
            self.assertAlmostEqual(second["duration"], 2, delta=0.15)
            self.assertTrue(Path(second["output"]).exists())


    def test_branded_scene_audio_and_pad(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            Image.new("RGBA", (100, 35), (60, 150, 40, 255)).save(root / "logo.png")
            subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                            "-f", "lavfi", "-i", "testsrc2=size=360x640:rate=15",
                            "-t", "3", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                            str(root / "source.mp4")], check=True)
            subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                            "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
                            str(root / "music.wav")], check=True)
            manifest = root / "audio.json"
            manifest.write_text(json.dumps({
                "name": "branding-and-audio",
                "video": {"width": 360, "height": 640, "fps": 15},
                "branding": {"logo": "logo.png", "accent": "#47A013"},
                "scenes": [
                    {"file": "source.mp4", "start": 0, "duration": 0.6,
                     "title": {"kicker": "ASTA", "headline": "Energy"}},
                    {"file": "source.mp4", "start": 1, "duration": 0.6,
                     "framing": "pad"}
                ],
                "music": {"file": "music.wav", "start": 0.1, "volume": 0.7,
                          "fade_out": 0.3},
                "output": "output/audio-demo.mp4"
            }))
            first = render(load_project(manifest), root=root)
            second = render(load_project(manifest), root=root)
            self.assertTrue(first["audio"])
            self.assertEqual(second["cache_hits"], 2)
            self.assertAlmostEqual(second["duration"], 1.2, delta=0.18)


if __name__ == "__main__":
    unittest.main()
