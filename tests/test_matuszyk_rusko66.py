"""Owner-approved invariants for the Matuszyk & Radajak Rusko test reel.

Guards the fixes from the human phone-review round: logo on the hook and
the end card, explicit CTA copy (no invented defaults), a readable end-card
hold and quiet transition whooshes.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "brands" / "matuszyk-radajak" / "projects" / "rusko-66-test.json"


def _load():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@unittest.skipUnless(MANIFEST.is_file(),
                     "client fixture not committed")
class RuskoReelTest(unittest.TestCase):
    def test_logo_on_hook_and_end_card(self):
        data = _load()
        hook = next(s for s in data["scenes"] if s["id"] == "hook")
        media = hook.get("editorial_media") or []
        self.assertTrue(
            any(str(item.get("asset", "")).endswith("logo-badge-white.png")
                for item in media),
            "hook scene must carry the logo badge overlay",
        )
        cta = next(s for s in data["scenes"] if s["id"] == "cta")
        media = cta.get("editorial_media") or []
        badge = [str(item.get("asset", "")) for item in media]
        self.assertTrue(
            any(path.endswith("logo-badge-white.png") for path in badge),
            "end card must render the big logo badge, not the raw dark logo",
        )
        self.assertNotIn("MATUSZYK & RADAJAK", str(cta.get("headline", "")))

    def test_cta_copy_is_explicit(self):
        data = _load()
        cta = next(s for s in data["scenes"] if s["id"] == "cta")
        self.assertEqual(cta.get("composition"), "cta")
        self.assertEqual(cta.get("headline"), "Masz pytania?")
        self.assertEqual(cta.get("phone"), "505 012 600")
        self.assertEqual(cta.get("line_one"), "BEZPŁATNA WYCENA")
        self.assertEqual(cta.get("line_two"), "")
        self.assertNotIn("KALISZ", json.dumps(cta, ensure_ascii=False))
        for forbidden in ("CONTACT", "example.com", "SPRAWD"):
            self.assertNotIn(forbidden, json.dumps(cta, ensure_ascii=False))

    def test_end_card_hold_and_total_runtime(self):
        data = _load()
        cta = next(s for s in data["scenes"] if s["id"] == "cta")
        self.assertGreaterEqual(cta.get("duration", 0), 7.0)
        total = sum(s.get("duration", 0) for s in data["scenes"])
        self.assertGreaterEqual(total, 20.0)

    def test_transition_whooshes_are_quiet(self):
        data = _load()
        sfx = (data.get("audio") or {}).get("sfx") or []
        self.assertEqual(len(sfx), 4)
        cuts = [2.2, 6.2, 10.2, 14.2]
        for track, cut in zip(sfx, cuts):
            self.assertAlmostEqual(track.get("time", -1), cut, places=1)
            self.assertLessEqual(track.get("gain_db", 0), -10.0)


if __name__ == "__main__":
    unittest.main()
