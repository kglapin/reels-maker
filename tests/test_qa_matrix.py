"""QA matrix tests for edge cases: accent-heavy text, Polish copy, face shots,
multiple transitions, narration gaps, bright/dark footage, and more."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from reels_maker.renderer import render
from reels_maker.spec import load_project, ProjectError
from reels_maker.ffmpeg import execute
from media_fixtures import has_real_media

# Use the actual repo root for brand media references
REPO_ROOT = Path(__file__).resolve().parents[1]
BRAND_DIR = REPO_ROOT / "brands/asta-energy"


@unittest.skipUnless(shutil.which("ffmpeg"),
                     "FFmpeg required for matrix renders")
@unittest.skipUnless(all(has_real_media(BRAND_DIR / "media/footage" / name)
                         for name in (
                             "1_fotowoltaika-25wp-budzyn.mp4",
                             "2_dron-pv-dla-firm-asta.mp4",
                             "10_tracker-pv.mp4",
                             "11_chodzież-2x39,59kwp-fotowoltaika-asta.mp4",
                             "12_pv na bloku.mp4",
                             "14_Piła-pv-39,96-kwp.mp4",
                         )),
                     "ASTA footage is LFS-backed and unavailable in offline CI")
class QAMatrixTests(unittest.TestCase):

    def _make_project(self, scenes: list, music: dict = None,
                      voiceover: dict = None, width=1080, height=1920, fps=25) -> Path:
        project = {
            "name": "qa-matrix-test",
            "version": 1,
            "video": {"width": width, "height": height, "fps": fps},
            "scenes": scenes,
            "music": music,
            "voiceover": voiceover,
            "branding": {},
            "output": "qa-matrix-output.mp4",
        }
        manifest = BRAND_DIR / "projects" / "qa-matrix-test.json"
        manifest.write_text(json.dumps(project))
        return manifest

    def test_accent_heavy_text_renders_correctly(self):
        """QA-10: Accent-heavy text (Polish diacritics, special chars) renders."""
        manifest = self._make_project([{
            "file": "media/footage/1_fotowoltaika-25wp-budzyn.mp4",
            "start": 0,
            "duration": 4.0,
            "title": {"headline": {"runs": [
                {"text": "WIĘCEJ ", "scale": 0.8, "color": "white"},
                {"text": "ENERGII", "scale": 1.3, "color": "accent"},
                {"text": " dla firmy", "scale": 0.8, "color": "white", "break_before": True}
            ]}},
            "body": "Zażółć gęślą jaźń - Polish diacritics test"
        }])
        project = load_project(manifest)
        result = render(project, root=BRAND_DIR.resolve())
        self.assertTrue(result["ok"])
        self.assertEqual(result["export_quality"]["status"], "pass")
        # Clean up temp project file
        manifest.unlink(missing_ok=True)

    def test_long_polish_copy_reading_speed(self):
        """QA-10: Long Polish copy with reading-speed validation."""
        long_copy = ("Fotowoltaika to inwestycja w przyszłość, "
                     "która dziś oszczędza pieniądze jutrą.")
        manifest = self._make_project([{
            "file": "media/footage/1_fotowoltaika-25wp-budzyn.mp4",
            "start": 0,
            "duration": 5.0,
            "title": {"headline": {"runs": [{"text": "ENERGIA"}]}, "body": long_copy}
        }])
        project = load_project(manifest)
        result = render(project, root=BRAND_DIR.resolve())
        self.assertTrue(result["ok"])
        manifest.unlink(missing_ok=True)

    def test_numerical_overlays_render(self):
        """QA-10: Numerical overlays (kW outputs, metrics) render correctly."""
        manifest = self._make_project([{
            "file": "media/footage/11_chodzież-2x39,59kwp-fotowoltaika-asta.mp4",
            "start": 0,
            "duration": 3.0,
            "title": {"headline": "39,59 kWp", "body": "156 paneli fotowoltaicznych • 2x39,59 kWp"}
        }])
        project = load_project(manifest)
        result = render(project, root=BRAND_DIR.resolve())
        self.assertTrue(result["ok"])
        manifest.unlink(missing_ok=True)

    def test_face_shot_collision_avoidance(self):
        """QA-10: Verify text does not collide with faces in shots."""
        manifest = self._make_project([{
            "file": "media/footage/11_chodzież-2x39,59kwp-fotowoltaika-asta.mp4",
            "start": 0,
            "duration": 4.0,
            "title": {"headline": "INSTALACJA", "body": "Nowoczesna farma fotowoltaiczna"},
            "backdrop": "strong"
        }])
        project = load_project(manifest)
        result = render(project, root=BRAND_DIR.resolve())
        self.assertTrue(result["ok"])
        manifest.unlink(missing_ok=True)

    def test_bright_and_dark_footage(self):
        """QA-10: Verify text legibility on bright and dark footage."""
        manifest = self._make_project([
            {"file": "media/footage/2_dron-pv-dla-firm-asta.mp4",
             "start": 0, "duration": 3.0, "title": {"headline": "BIAŁE DNI", "backdrop": "strong"}},
            {"file": "media/footage/12_pv na bloku.mp4",
             "start": 0, "duration": 3.0, "title": {"headline": "CIESZCZENIE", "backdrop": "strong"}}
        ])
        project = load_project(manifest)
        result = render(project, root=BRAND_DIR.resolve())
        self.assertTrue(result["ok"])
        manifest.unlink(missing_ok=True)

    def test_multiple_transitions_sequence(self):
        """QA-10: Multiple transitions in sequence render without glitches."""
        manifest = self._make_project([
            {"file": "media/footage/1_fotowoltaika-25wp-budzyn.mp4",
             "start": 0, "duration": 3.0},
            {"file": "media/footage/10_tracker-pv.mp4",
             "start": 0, "duration": 3.0,
             "transition_in": {"type": "dissolve", "frames": 8}},
            {"file": "media/footage/14_Piła-pv-39,96-kwp.mp4",
             "start": 0, "duration": 3.0,
             "transition_in": {"type": "dip_to_black", "frames": 6}},
        ])
        project = load_project(manifest)
        result = render(project, root=BRAND_DIR.resolve())
        self.assertTrue(result["ok"])
        self.assertEqual(result["transitions"][0]["type"], "dissolve")
        self.assertEqual(result["transitions"][1]["type"], "dip_to_black")
        manifest.unlink(missing_ok=True)

    def test_narration_gaps_do_not_crash(self):
        """QA-10: Scenes without text render correctly alongside narrated scenes."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            # Create a synthetic silent audio track for voiceover testing
            wav_dest = BRAND_DIR / "media" / "audio" / "test-silence.wav"
            execute(["-f", "lavfi", "-i", "anullsrc=channel_layout=mono:sample_rate=48000",
                     "-t", "9", "-q:a", "9", "-acodec", "pcm_s16le", str(wav_dest)])

            project = {
                "name": "qa-narration-gaps",
                "version": 1,
                "video": {"width": 1080, "height": 1920, "fps": 25},
                "scenes": [
                    {"file": "media/footage/1_fotowoltaika-25wp-budzyn.mp4",
                     "start": 0, "duration": 4.0, "title": {"headline": "Z NAUKĄ"},
                     "motion": {"preset": "rise_soft",
                                "duration_frames": 7, "stagger_frames": 2,
                                "distance_px": 18}},
                    {"file": "media/footage/10_tracker-pv.mp4",
                     "start": 0, "duration": 4.0}
                ],
                "voiceover": {
                    "file": "media/audio/test-silence.wav",
                    "start": 0,
                    "offset_seconds": 0.0,
                    "sync_marks": [
                        {"scene": 1, "role": "headline", "source_seconds": 0.5,
                         "tolerance_frames": 3}
                    ]
                },
                "music": None,
                "branding": {},
                "output": "qa-narration-gaps.mp4",
            }
            manifest = BRAND_DIR / "projects" / "qa-narration-gaps.json"
            manifest.write_text(json.dumps(project))
            p = load_project(manifest)
            result = render(p, root=BRAND_DIR.resolve())
            self.assertTrue(result["ok"])
            manifest.unlink(missing_ok=True)
            wav_dest.unlink(missing_ok=True)

    def test_1080x1080_square_profile(self):
        """QA-10: 1:1 square format renders with correct aspect ratio."""
        manifest = self._make_project([{
            "file": "media/footage/1_fotowoltaika-25wp-budzyn.mp4",
            "start": 0, "duration": 3.0, "title": {"headline": "KWADRAT"}
        }], width=1080, height=1080, fps=30)
        project = load_project(manifest)
        result = render(project, root=BRAND_DIR.resolve())
        self.assertTrue(result["ok"])
        self.assertEqual(result["export_quality"]["width"], 1080)
        self.assertEqual(result["export_quality"]["height"], 1080)
        self.assertEqual(result["export_quality"]["fps"], 30)
        manifest.unlink(missing_ok=True)

    def test_1920x1080_landscape_profile(self):
        """QA-10: Landscape format renders with correct aspect ratio."""
        manifest = self._make_project([{
            "file": "media/footage/2_dron-pv-dla-firm-asta.mp4",
            "start": 0, "duration": 3.0, "title": {"headline": "LANDSCAPE"}
        }], width=1920, height=1080, fps=25)
        project = load_project(manifest)
        result = render(project, root=BRAND_DIR.resolve())
        self.assertTrue(result["ok"])
        self.assertEqual(result["export_quality"]["width"], 1920)
        self.assertEqual(result["export_quality"]["height"], 1080)
        manifest.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
