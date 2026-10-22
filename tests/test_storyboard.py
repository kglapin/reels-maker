"""Storyboard: actual output frames for human QC, timeline-aware sampling."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from reels_maker.ffmpeg import execute
from reels_maker.renderer import render
from reels_maker.spec import load_project
from reels_maker.storyboard import make_storyboard


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg/FFprobe required")
class StoryboardTests(unittest.TestCase):
    def test_motion_strip_samples_three_actual_frames_per_scene(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            execute(["-f", "lavfi", "-i",
                     "color=c=black:s=160x288:r=12:d=3",
                     "-an", "-c:v", "libx264", str(root / "source.mp4")])
            manifest = root / "motion.json"
            manifest.write_text(json.dumps({
                "video": {"width":160,"height":288,"fps":12},
                "scenes": [{
                    "file":"source.mp4","duration":2,
                    "title":{"headline":"ENERGY"},
                    "motion":{"preset":"fade_stagger",
                              "duration_frames":4,"stagger_frames":1}
                }], "output":"renders/motion.mp4"
            }))
            project=load_project(manifest)
            result=render(project,root=root)
            file=root/"qa"/"strip.png"
            report=make_storyboard(project,Path(result["output"]),file,
                                   motion_strip=True)
            self.assertEqual(report["mode"],"motion_strip")
            self.assertEqual([x["phase"] for x in report["samples"]],
                             ["entry","settled","exit"])
            self.assertTrue(all(x["timestamp_seconds"]>=0 for x in report["samples"]))
            with Image.open(file) as picture:
                self.assertGreater(picture.width,500)

    def test_creates_actual_frame_contact_sheet(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, color in (("a", "red"), ("b", "green")):
                execute(["-f", "lavfi", "-i",
                         f"color=c={color}:s=160x288:r=12:d=2",
                         "-an", "-c:v", "libx264", str(root / f"{name}.mp4")])
            manifest = root / "script.json"
            manifest.write_text(json.dumps({
                "video": {"width": 160, "height": 288, "fps": 12},
                "scenes": [{"file": "a.mp4", "duration": 1},
                           {"file": "b.mp4", "duration": 1}],
                "output": "renders/video.mp4"}))
            script = load_project(manifest)
            result = render(script, root=root)
            sheet = root / "qc" / "contact.png"
            qc = make_storyboard(script, Path(result["output"]), sheet, columns=2)
            self.assertEqual(qc["scenes"], 2)
            self.assertTrue(qc["human_review_required"])
            self.assertTrue(sheet.is_file())
            self.assertEqual(len(qc["samples"]), 2)
            with Image.open(sheet) as actual:
                self.assertGreater(actual.width, 200)
                self.assertGreater(actual.height, 300)


if __name__ == "__main__":
    unittest.main()
