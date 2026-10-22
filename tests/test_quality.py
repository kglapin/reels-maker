"""Creative linting is transparent and tunable; does not depend on FFmpeg."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from reels_maker.quality import review_project
from reels_maker.spec import Project


def project(scenes):
    return Project(name="example", width=540, height=960, fps=25,
                   scenes=scenes, music=None, branding={}, output="a.mp4")


class QualityGateTests(unittest.TestCase):
    def test_clean_short_scene_passes(self):
        report = review_project(project([{
            "file": "a.mp4", "duration": 3.0,
            "title": {"headline": "Energia dla firm"}
        }]))
        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["human_review_required"])

    def test_warns_on_overload_without_rewriting_story(self):
        rich = {"runs": [
            {"text": "Bardzo ", "color": "accent", "scale": 1.4},
            {"text": "DUŻO ", "color": "accent", "scale": 1.35},
            {"text": "SŁÓW ", "color": "accent", "scale": 1.4}
        ]}
        scenes = [{"file": "a.mp4", "duration": 1.2,
                   "title": {"headline": rich,
                             "body": "Dodatkowe bardzo długie wyjaśnienie"},
                   "motion": {"preset": "rise_soft",
                              "duration_frames": 8, "stagger_frames": 3}}]
        report = review_project(project(scenes))
        codes = {item["code"] for item in report["warnings"]}
        self.assertIn("too_many_hero_words", codes)
        self.assertIn("reading_speed", codes)
        self.assertEqual(report["status"], "review")

    def test_transition_density_is_flagged(self):
        scenes = [{"file": "a.mp4", "duration": 2}]
        for _ in range(4):
            scenes.append({"file": "a.mp4", "duration": 2,
                           "transition_in": {"type": "dissolve", "frames": 4}})
        codes = {x["code"] for x in review_project(project(scenes))["warnings"]}
        self.assertIn("transition_density", codes)
        self.assertIn("repeated_transition", codes)

    def test_strict_cli_gives_structured_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "test.json"
            manifest.write_text(json.dumps({
                "scenes": [{"file": "a.mp4", "duration": 0.7,
                            "title": {"headline": "Bardzo długi nagłówek testowy"}}]
            }))
            proc = subprocess.run([sys.executable, "-m", "reels_maker",
                 "validate", str(manifest), "--syntax-only",
                 "--strict-quality", "--json"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)
            self.assertEqual(json.loads(proc.stderr)["error"]["type"],
                             "QualityReviewRequired")


if __name__ == "__main__":
    unittest.main()
