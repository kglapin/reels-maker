"""Cue sheets expose exact visual and narration timing to editors."""
import json
import tempfile
import unittest
from pathlib import Path

from reels_maker.cue_sheet import make_cue_sheet
from reels_maker.spec import Project
from reels_maker.cli import main


class CueSheetTests(unittest.TestCase):
    def test_xfade_shifts_global_word_cues(self):
        project = Project(
            name="test", width=320, height=568, fps=25,
            scenes=[
                {"file": "a.mp4", "duration": 2,
                 "title": {"headline": "HELLO"},
                 "motion": {"preset": "fade_stagger",
                            "duration_frames": 6,
                            "cue_frames": {"headline": 25}}},
                {"file": "b.mp4", "duration": 2,
                 "transition_in": {"type": "dissolve", "frames": 5},
                 "title": {"headline": "ENERGY"},
                 "motion": {"preset": "fade_stagger",
                            "duration_frames": 6,
                            "cue_frames": {"headline": 10}}}
            ],
            music=None, branding={}, output="test.mp4",
            voiceover={"file": "narrator.wav", "offset_seconds": .2})
        report = make_cue_sheet(project)
        self.assertEqual(report["total_frames"], 95)
        self.assertEqual(report["scenes"][1]["start_frame"], 45)
        self.assertEqual(report["scenes"][1]["cues"][0]["timeline_frame"], 55)
        self.assertAlmostEqual(report["scenes"][1]["cues"][0]["timeline_seconds"], 2.2)
        self.assertEqual(report["voiceover"]["timeline_offset_seconds"], .2)
        self.assertEqual(report["warnings"], [])
        self.assertTrue(report["manual_audio_review_required"])

    def test_flags_a_word_revealed_under_incoming_transition(self):
        p = Project(name="warn", width=320, height=568, fps=25,
            scenes=[
                {"file": "a.mp4", "duration": 2},
                {"file": "b.mp4", "duration": 2,
                 "transition_in": {"type": "dissolve", "frames": 5},
                 "title": {"headline": "CUT"},
                 "motion": {"preset": "fade_stagger",
                            "duration_frames": 6,
                            "cue_frames": {"headline": 0}}}
            ], music=None, branding={}, output="warn.mp4")
        report = make_cue_sheet(p)
        self.assertIn("cue_begins_inside_crossfade",
                      [w["code"] for w in report["warnings"]])

    def test_cli_prints_report_without_media_assets(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as temp:
            manifest = Path(temp) / "project.json"
            manifest.write_text(json.dumps({
                "video": {"width": 320, "height": 568, "fps": 25},
                "scenes": [{
                    "file": "unavailable.mp4", "duration": 3,
                    "title": {"headline": "PROJEKT"},
                    "motion": {"preset": "rise_soft",
                               "cue_seconds": {"headline": 1.1}}
                }]
            }))
            report_file = Path(temp) / "report.json"
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                status = main(["cue-sheet", str(manifest),
                               "--output", str(report_file), "--json"])
            self.assertEqual(status, 0)
            self.assertTrue(report_file.exists())
            response = json.loads(out.getvalue())
            self.assertEqual(response["scenes"][0]["cues"][0]["local_frame"], 28)
            self.assertTrue(response["ok"])


if __name__ == "__main__":
    unittest.main()
