"""Declarative project templates must remain syntactically valid."""
import unittest
from pathlib import Path

from reels_maker.spec import load_project

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = (
    "asta-montage.json",
    "asta-rush-demo.json",
    "asta-vamos-beat.json",
    "asta-subsidy-external.json",
)


class ManifestSyntaxTests(unittest.TestCase):
    def test_all_examples_load_without_media(self):
        for name in TEMPLATES:
            with self.subTest(name=name):
                project = load_project(ROOT / "projects" / name)
                self.assertGreater(project.duration, 0)
                self.assertLessEqual(project.duration, 31)
                self.assertTrue(project.output.endswith(".mp4"))
                self.assertGreaterEqual(len(project.scenes), 2)

    def test_vamos_beat_sequence_kept(self):
        p = load_project(ROOT / "projects" / "asta-vamos-beat.json")
        self.assertEqual(len(p.scenes), 22)
        self.assertAlmostEqual(p.duration, 29.7912, places=2)

    def test_subsidy_uses_only_external_footage(self):
        p = load_project(ROOT / "projects" / "asta-subsidy-external.json")
        self.assertEqual(len(p.scenes), 9)
        self.assertTrue(all(x["file"].startswith("engine/assets/commons/")
                            for x in p.scenes))
        self.assertAlmostEqual(p.duration, 29.7, places=2)


if __name__ == "__main__":
    unittest.main()
