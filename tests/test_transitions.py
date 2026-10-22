"""Test subtle, deterministic transition presets."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from reels_maker.ffmpeg import execute, probe
from reels_maker.renderer import render
from reels_maker.spec import ProjectError, load_project
from reels_maker.transitions import transition_plan, timeline_frames


class ManifestTests(unittest.TestCase):
    def test_rejects_invalid_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a.json"
            for effect in ({"type": "spinzoom", "frames": 3},
                           {"type": "dissolve", "frames": 100},
                           {"type": "dissolve", "frames": 2.5}):
                p.write_text(json.dumps({
                    "scenes": [{"file": "a.mp4", "duration": 1},
                               {"file": "b.mp4", "duration": 1,
                                "transition_in": effect}]}))
                with self.assertRaises(ProjectError):
                    load_project(p)

    def test_timeline_accounts_for_overlap(self):
        from reels_maker.spec import Project
        p = Project(name="a", width=256, height=448, fps=25,
                    scenes=[{"duration": 1},
                            {"duration": 1, "transition_in":
                                {"type": "dissolve", "frames": 5}},
                            {"duration": 1}], music=None, branding={}, output="a.mp4")
        steps = transition_plan(p, [25, 25, 25])
        self.assertEqual([s["type"] for s in steps], ["dissolve", "cut"])
        self.assertEqual(timeline_frames([25, 25, 25], steps), 70)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg required")
class RenderTests(unittest.TestCase):
    def test_mixed_cut_and_dissolve_and_scene_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for label, color in (("a", "red"), ("b", "blue"), ("c", "green")):
                execute(["-f", "lavfi", "-i",
                         f"color=c={color}:s=256x448:r=12:d=2",
                         "-c:v", "libx264", "-pix_fmt", "yuv420p",
                         str(root / f"{label}.mp4")])
            manifest = root / "video.json"
            manifest.write_text(json.dumps({
                "video": {"width": 256, "height": 448, "fps": 12},
                "scenes": [
                    {"file": "a.mp4", "duration": 1},
                    {"file": "b.mp4", "duration": 1,
                     "transition_in": {"type": "dissolve", "frames": 3}},
                    {"file": "c.mp4", "duration": 1}],
                "output": "render/test.mp4"
            }))
            project = load_project(manifest)
            result = render(project, root=root)
            self.assertEqual(result["assembly_mode"], "xfade")
            self.assertEqual(result["transition_overlaps_frames"], 3)
            self.assertAlmostEqual(result["duration_actual"], 2.75, delta=.13)
            self.assertEqual(result["scenes_encoded"], 3)
            video = next(s for s in probe(Path(result["output"]))["streams"]
                         if s["codec_type"] == "video")
            self.assertEqual(int(video["nb_frames"]), 33)
            again = render(project, root=root)
            self.assertEqual(again["scenes_encoded"], 0)
            self.assertEqual(again["cache_hits"], 3)


if __name__ == "__main__":
    unittest.main()
