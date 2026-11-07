"""QA must flag invented CTA contact defaults instead of rendering them."""
import unittest

from types import SimpleNamespace

from reels_maker.qa.data import _data_checks


def _built(scene):
    return SimpleNamespace(scene=scene, meta={"component": "cta"}, index=0)


class TestPlaceholderContact(unittest.TestCase):
    def test_verified_copy_is_silent(self):
        scene = {"headline": "Masz pytania?", "phone": "505 012 600",
                 "line_one": "BEZPŁATNA WYCENA", "website": ""}
        self.assertEqual(_data_checks(_built(scene)), [])

    def test_engine_defaults_raise_warning(self):
        scene = {"headline": "SKONTAKUJ SIĘ", "phone": "CONTACT",
                 "line_one": "SPRAWDŹ DOTACJĘ", "website": "example.com"}
        issues = _data_checks(_built(scene))
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "placeholder_contact")
        self.assertEqual(issues[0].severity, "warning")


if __name__ == "__main__":
    unittest.main()
