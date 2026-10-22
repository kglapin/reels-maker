"""Verify editor-provided spoken-word marks against visual cue frames.

No speech recognition is claimed: marks come from trusted, manually
verified timestamps in the original narration source WAV.
"""
import contextlib
import io
import json
import math
import shutil
import tempfile
import unittest
from pathlib import Path

from reels_maker.cue_sheet import make_cue_sheet
from reels_maker.cli import main
from reels_maker.media import preflight
from reels_maker.quality import review_project
from reels_maker.spec import ProjectError, load_project
from reels_maker.ffmpeg import RenderError, execute


def example(marker=2.18):
    return {
        "name": "sync-audit",
        "video": {"width": 160, "height": 288, "fps": 25},
        "scenes": [
            {"file": "shot-a.mp4", "duration": 2.0},
            {"file": "shot-b.mp4", "duration": 2.0,
             "transition_in": {"type": "dissolve", "frames": 5},
             "title": {"headline": {"runs": [
                 {"text": "Więcej "}, {"text": "ENERGII", "color": "accent"}
             ]}},
             "motion": {"preset": "fade_stagger",
                        "duration_frames": 6,
                        "cue_frames": {"headline-1": 7}}}
        ],
        "voiceover": {
            "file": "narrator.wav", "start": .2,
            "offset_seconds": .1, "volume": 1.0,
            "sync_marks": [{"scene": 2, "role": "headline-1",
                            "source_seconds": marker, "tolerance_frames": 2}]
        },
        "output": "renders/sync-test.mp4"
    }


class ManualSyncTests(unittest.TestCase):
    def load(self, data, folder):
        path = Path(folder) / "script.json"
        path.write_text(json.dumps(data))
        return load_project(path)

    def test_absolute_word_timing_accounts_for_audio_trim_and_xfade(self):
        with tempfile.TemporaryDirectory() as folder:
            p = self.load(example(), folder)
            sheet = make_cue_sheet(p)
            self.assertEqual(sheet["total_frames"], 95)
            self.assertEqual(len(sheet["sync_marks"]), 1)
            mark = sheet["sync_marks"][0]
            self.assertEqual(mark["scene"], 2)
            self.assertEqual(mark["visual_frame"], 52)
            self.assertEqual(mark["narration_frame"], 52)
            self.assertEqual(mark["delta_frames"], 0)
            self.assertEqual(mark["status"], "pass")
            self.assertFalse(any(
                w["code"] == "narration_cue_drift" for w in sheet["warnings"]))
            q = review_project(p)
            self.assertNotIn("narration_cue_drift",
                             [w["code"] for w in q["warnings"]])

    def test_strict_quality_fails_for_speech_misalignment(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest = Path(folder) / "script.json"
            manifest.write_text(json.dumps(example(2.66)))
            p = load_project(manifest)
            sheet = make_cue_sheet(p)
            mark = sheet["sync_marks"][0]
            self.assertEqual(mark["status"], "drift")
            self.assertLess(mark["delta_frames"], -2)
            codes = [w["code"] for w in review_project(p)["warnings"]]
            self.assertIn("narration_cue_drift", codes)
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                status = main(["validate", str(manifest),
                               "--syntax-only", "--strict-quality", "--json"])
            self.assertEqual(status, 2)
            payload = json.loads(err.getvalue())
            self.assertEqual(payload["error"]["type"], "QualityReviewRequired")
            self.assertIn(
                "narration_cue_drift",
                [w["code"] for w in payload["quality"]["warnings"]])

    def test_invalid_editor_markers_cannot_silently_pass(self):
        bad = [
            {"scene": 0, "role": "headline-1", "source_seconds": 2.18},
            {"scene": 3, "role": "headline-1", "source_seconds": 2.18},
            {"scene": 2, "role": "headline-100", "source_seconds": 2.18},
            {"scene": 1, "role": "headline-1", "source_seconds": 2.18},
            {"scene": 2, "role": "headline-1", "source_seconds": .1},
            {"scene": 2, "role": "headline-1", "source_seconds": float("nan")},
            {"scene": 2, "role": "headline-1", "source_seconds": float("inf")},
            {"scene": 2, "role": "headline-1", "source_seconds": 2.18,
             "tolerance_frames": 7},
            {"scene": 2, "role": "headline-1", "source_seconds": 2.18,
             "tolerance_frames": -1},
        ]
        with tempfile.TemporaryDirectory() as folder:
            for item in bad:
                with self.subTest(item=item):
                    config = example()
                    config["voiceover"]["sync_marks"] = [item]
                    with self.assertRaises(ProjectError):
                        self.load(config, folder)

    def test_duplicate_words_and_static_cues_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            config = example()
            config["voiceover"]["sync_marks"] *= 2
            with self.assertRaisesRegex(ProjectError, "Duplicate sync mark"):
                self.load(config, folder)
            config = example()
            config["scenes"][1].pop("motion")
            with self.assertRaisesRegex(ProjectError, "require animated text"):
                self.load(config, folder)

    def test_nonfinite_duration_and_music_cannot_escape_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            config = example()
            for bad in (float("nan"), float("inf")):
                x = json.loads(json.dumps(config))
                x["scenes"][0]["duration"] = bad
                with self.assertRaises(ProjectError):
                    self.load(x, folder)
                x = json.loads(json.dumps(config))
                x["music"] = {"file": "music.wav", "volume": bad}
                with self.assertRaises(ProjectError):
                    self.load(x, folder)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg/FFprobe required")
class MarkerMediaPreflightTests(unittest.TestCase):
    def test_audited_markers_must_fit_original_voice_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            execute(["-f", "lavfi", "-i",
                     "color=c=black:s=160x288:r=25:d=3",
                     "-an", "-c:v", "libx264", str(root / "shot-a.mp4")])
            execute(["-f", "lavfi", "-i",
                     "color=c=blue:s=160x288:r=25:d=3",
                     "-an", "-c:v", "libx264", str(root / "shot-b.mp4")])
            execute(["-f", "lavfi", "-i",
                     "sine=frequency=560:duration=1:sample_rate=48000",
                     "-c:a", "pcm_s16le", str(root / "narrator.wav")])
            p = self.load_config(example(), root)
            with self.assertRaisesRegex(
                    RenderError, "past the end of the source recording"):
                preflight(p, root)

    @staticmethod
    def load_config(data, root):
        path = root / "script.json"
        path.write_text(json.dumps(data))
        return load_project(path)


if __name__ == "__main__":
    unittest.main()
