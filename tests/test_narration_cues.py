"""Frame-accurate voiceover cues: schema, QA timeline and decoded MP4 pixels."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from reels_maker.ffmpeg import RenderError, execute
from reels_maker.motion_timing import (
    build_cue_schedule, scripted_text_roles)
from reels_maker.quality import review_project
from reels_maker.spec import Project, ProjectError, load_project
from reels_maker.storyboard import _sample_frames


def make_project(scene, fps=25):
    return Project(
        name="cue", width=320, height=568, fps=fps,
        scenes=[scene], music=None, branding={}, output="out.mp4")


class CueUnitTests(unittest.TestCase):
    def test_narration_seconds_quantize_to_output_frames(self):
        title = {"headline": {"runs": [
            {"text": "Zwiększ "},
            {"text": "ZYSK", "color": "accent"}
        ]}, "body": "Magazyny energii"}
        self.assertEqual(scripted_text_roles(title), [
            ("headline-0", "Zwiększ "),
            ("headline-1", "ZYSK"),
            ("body", "Magazyny energii")])
        cfg = {"preset": "rise_soft",
               "duration_frames": 6, "stagger_frames": 2,
               "cue_seconds": {
                   "headline-0": .42,
                   "headline-1": 1.04,
                   "body": 1.60,
               }}
        schedule = build_cue_schedule(
            cfg, ["logo", "accent"] + [role for role, _ in
                scripted_text_roles(title)], 25, 75)
        self.assertEqual(schedule.starts["headline-0"], 10)
        self.assertEqual(schedule.starts["headline-1"], 26)
        self.assertEqual(schedule.starts["body"], 40)
        self.assertEqual(schedule.starts["logo"], 0)
        self.assertEqual(schedule.last_settled_frame, 46)

    def test_legacy_stagger_is_preserved(self):
        s = build_cue_schedule(
            {"duration_frames": 6, "stagger_frames": 3},
            ["logo", "accent", "kicker", "headline", "body"],
            fps=25, scene_frames=75)
        self.assertEqual(
            s.starts, {"logo": 0, "accent": 0, "kicker": 0,
                       "headline": 3, "body": 6})

    def test_invalid_automatic_or_ambiguous_cues_are_rejected(self):
        for patch in (
            {"cue_seconds": {"headline": -1}},
            {"cue_seconds": {"headline": True}},
            {"cue_seconds": {"headline": float("nan")}},
            {"cue_seconds": {"headline": float("inf")}},
            {"cue_seconds": {"headline": "1.0"}},
            {"cue_frames": {"headline": 4.0}},
            {"cue_frames": {"headline": True}},
            {"cue_frames": {"missing-3": 5}},
            {"cue_seconds": {"headline": 1.05},
             "cue_frames": {"headline": 26}},
            {"cue_frames": {"headline": 48}},
        ):
            with self.subTest(cfg=patch), self.assertRaises(ValueError):
                build_cue_schedule(
                    {"duration_frames": 6, "stagger_frames": 1, **patch},
                    ["logo", "accent", "headline"], 25, 60)

    def test_manifest_rejects_invalid_cue_before_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "story.json"
            for cues in (
                {"cue_seconds": {"headline-5": .6}},
                {"cue_seconds": {"headline": 9.4}},
                {"cue_frames": {"headline": -2}},
                {"cue_frames": {"headline": 10},
                 "cue_seconds": {"headline": 1}},
            ):
                path.write_text(json.dumps({
                    "video": {"width": 320, "height": 568, "fps": 25},
                    "scenes": [{
                        "file": "source.mp4",
                        "duration": 2.4,
                        "title": {"headline": "Energia"},
                        "motion": {
                            "preset": "fade_stagger",
                            "duration_frames": 6,
                            **cues
                        }
                    }]
                }))
                with self.subTest(cues=cues), self.assertRaises(ProjectError):
                    load_project(path)

    def test_quality_measures_each_phrase_after_its_cue(self):
        scene = {
            "file": "source.mp4", "duration": 2.5,
            "title": {
                "headline": {"runs": [
                    {"text": "WIĘCEJ "}, {"text": "ENERGII"}
                ]},
                "body": "Bardzo długi podpis, który trudno przeczytać"
            },
            "motion": {
                "preset": "rise_soft", "duration_frames": 6,
                "cue_frames": {"headline-0": 4,
                               "headline-1": 12, "body": 35}
            }
        }
        result = review_project(make_project(scene))
        self.assertIn("reading_speed",
            [w["code"] for w in result["warnings"]])
        self.assertNotIn("invalid_motion_timing",
            [w["code"] for w in result["warnings"]])

    def test_outgoing_transition_consumes_reading_window(self):
        first = {
            "file": "a.mp4", "duration": 2.0,
            "title": {"headline": "Energia"},
            "motion": {"preset": "fade_stagger",
                       "duration_frames": 6,
                       "cue_frames": {"headline": 29}}
        }
        second = {
            "file": "b.mp4", "duration": 2,
            "transition_in": {"type": "dissolve", "frames": 7}
        }
        project = Project(name="test", width=320, height=568, fps=25,
                          scenes=[first, second], music=None, branding={},
                          output="x.mp4")
        warnings = review_project(project)["warnings"]
        self.assertIn("no_reading_hold", [w["code"] for w in warnings])

    def test_storyboard_settled_sample_follows_delayed_headline(self):
        scene = {
            "duration": 3.0,
            "title": {"headline": "Energia"},
            "motion": {"preset": "fade_stagger",
                       "duration_frames": 6,
                       "cue_frames": {"headline": 48}}
        }
        samples = _sample_frames(
            scene, 25, 0, 75, 0, 5, motion_strip=True)
        positions = dict(samples)
        self.assertLess(positions["entry"], 48)
        self.assertGreater(positions["settled"], 54)
        self.assertLess(positions["settled"], 70)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg and FFprobe are required")
class NarrationCueVideoTests(unittest.TestCase):
    def test_delayed_text_is_not_visible_before_the_cue(self):
        from PIL import Image
        from reels_maker.renderer import render
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            execute([
                "-f", "lavfi", "-i",
                "color=c=black:s=320x568:r=25:d=3",
                "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                str(root / "black.mp4")
            ])
            path = root / "script.json"
            path.write_text(json.dumps({
                "video": {"width": 320, "height": 568, "fps": 25},
                "scenes": [{
                    "file": "black.mp4", "duration": 2.4,
                    "title": {"headline": "ENERGY", "backdrop": "none"},
                    "motion": {
                        "preset": "fade_stagger",
                        "duration_frames": 6,
                        "cue_seconds": {"headline": 1.0}
                    }
                }],
                "output": "renders/cued.mp4"
            }))
            project = load_project(path)
            encoded = render(project, root=root)
            self.assertEqual(encoded["export_quality"]["frames_actual"], 60)
            frames = []
            for moment in (.3, 1.4):
                still = root / f"frame-{moment}.png"
                execute([
                    "-ss", str(moment), "-i", encoded["output"],
                    "-frames:v", "1", str(still)
                ])
                with Image.open(still) as image:
                    picture = image.convert("RGB")
                    bright = sum(1 for r, g, b in picture.getdata()
                                 if min(r, g, b) >= 200)
                    frames.append(bright)
            # Neutral background/green accent never register as bright white;
            # the readable headline should appear only after the chosen cue.
            self.assertEqual(frames[0], 0)
            self.assertGreater(frames[1], 30)
            warm = render(project, root=root)
            self.assertEqual(warm["scenes_encoded"], 0)


if __name__ == "__main__":
    unittest.main()
