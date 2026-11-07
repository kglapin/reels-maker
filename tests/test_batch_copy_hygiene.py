"""Batch manifest copy hygiene: no truncated subtitles on title cards.

A hook subtitle is either a complete first sentence from the verified
realization description or absent entirely. Mid-sentence cuts with an
ellipsis read as broken copy and must never ship (human phone-review
finding, 2026-11-06).
"""
import glob
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUTO = ROOT / "brands/matuszyk-radajak/projects/auto"


def _manifests():
    return sorted(glob.glob(str(AUTO / "*.json")))


class BatchCopyHygieneTest(unittest.TestCase):
    def test_hooks_have_no_truncated_subtitles(self):
        files = _manifests()
        if len(files) < 100:
            self.skipTest("batch manifests are not committed; "
                          "run locally against the client workspace")
        for path in files:
            with self.subTest(manifest=Path(path).name):
                data = json.loads(Path(path).read_text(encoding="utf-8"))
                hook = next(s for s in data["scenes"] if s["id"] == "hook")
                sub = hook.get("subtitle", "")
                self.assertNotIn("…", sub)
                self.assertLessEqual(len(sub), 80)

    def test_hooks_use_only_verified_fields(self):
        for path in _manifests():
            with self.subTest(manifest=Path(path).name):
                data = json.loads(Path(path).read_text(encoding="utf-8"))
                hook = next(s for s in data["scenes"] if s["id"] == "hook")
                self.assertTrue(hook.get("headline"))
                self.assertTrue(hook.get("photo", "").startswith(
                    "imports/photos/realizacje/"))

    def test_middle_slides_carry_only_verified_facts(self):
        allowed_kickers = {"TECHNOLOGIA", "GRUBOŚĆ", "POWIERZCHNIA"}
        fact_headline = re.compile(
            r"^(PIANA PUR|WEŁNA CELULOZOWA|ZAMKNIĘTOKOMÓRKOWA|"
            r"OTWARTOKOMÓRKOWA|.+ (cm|m²))$")
        for path in _manifests():
            with self.subTest(manifest=Path(path).name):
                data = json.loads(Path(path).read_text(encoding="utf-8"))
                for scene in data["scenes"]:
                    if scene.get("id", "").startswith("foto-"):
                        self.assertNotIn("…", json.dumps(
                            scene, ensure_ascii=False))
                        kicker = scene.get("kicker", "")
                        headline = scene.get("headline", "")
                        if kicker in allowed_kickers:
                            self.assertTrue(headline,
                                            "fact slides need their number")
                        if headline:
                            # A fact headline is verified; its label kicker
                            # may have been dropped by the contrast fallback.
                            self.assertTrue(
                                kicker in allowed_kickers or kicker == "",
                                "unexpected kicker on a fact slide")
                            self.assertRegex(headline, fact_headline)


if __name__ == "__main__":
    unittest.main()
