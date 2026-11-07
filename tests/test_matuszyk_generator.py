"""Unit tests for tools/generate_matuszyk_reels.py helpers.

Fail-closed copy contract: short whole sentences, no ellipsis, facts only
when parsed from the source description.
"""
import importlib.util
import unittest

from pathlib import Path

GEN = Path(__file__).resolve().parent.parent / \
    "tools/generate_matuszyk_reels.py"
_spec = importlib.util.spec_from_file_location("matuszyk_gen", GEN)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


class TestFirstSentence(unittest.TestCase):
    def test_short_sentence_kept_whole(self):
        self.assertEqual(gen.first_sentence("Krótki opis. Dalszy ciąg."),
                         "Krótki opis.")

    def test_long_sentence_dropped_not_cut(self):
        sent = gen.first_sentence(
            "To bardzo długie zdanie wprowadzające, które na pewno "
            "przekracza osiemdziesiąt znaków i dlatego musi zniknąć.")
        self.assertEqual(sent, "")
        self.assertNotIn("…", sent)

    def test_empty(self):
        self.assertEqual(gen.first_sentence(""), "")


class TestParseFacts(unittest.TestCase):
    def test_open_cell_thickness_and_area(self):
        tech, thick, area = gen.parse_facts(
            "Ocieplenie pianą otwartokomórkową o grubości 15 cm, "
            "powierzchnia 200 m2.")
        self.assertEqual(tech, "OTWARTOKOMÓRKOWA")
        self.assertEqual(thick, "15 cm")
        self.assertEqual(area, "200 m²")

    def test_closed_cell(self):
        tech, _, _ = gen.parse_facts("pianka zamknietokomorkowa 10cm")
        self.assertEqual(tech, "ZAMKNIĘTOKOMÓRKOWA")

    def test_hydro_without_thickness(self):
        tech, thick, area = gen.parse_facts("hydroizolacja dachu")
        self.assertIsNone(tech)
        self.assertIsNone(thick)
        self.assertIsNone(area)

    def test_nothing_found(self):
        self.assertEqual(gen.parse_facts("ogólny remont bez danych"),
                         (None, None, None))


class TestBuildManifest(unittest.TestCase):
    def _realization(self, **kw):
        r = {
            "id": "1", "slug": "x",
            "title": "Izolacja poddasza w Kaliszu",
            "location": "Kalisz",
            "description": "Krótki opis.",
            "local_folder": "imports/photos/realizacje/1-x",
            "local_images": [f"img{i}.jpg" for i in range(5)],
        }
        r.update(kw)
        return r

    def test_no_ellipsis_no_invented_cta(self):
        _, manifest = gen.build_manifest(self._realization(
            description=("To bardzo długie zdanie wprowadzające, które "
                         "na pewno przekracza osiemdziesiąt znaków "
                         "i dlatego musi zostać pominięte.")))
        blob = str(manifest["scenes"])
        self.assertNotIn("…", blob)
        self.assertNotIn("Skontaktuj", blob)
        self.assertNotIn("example.com", blob)

    def test_cta_has_no_location(self):
        _, manifest = gen.build_manifest(self._realization())
        cta = manifest["scenes"][-1]
        self.assertNotIn("Kalisz", str(cta))

    def test_hook_headline_uses_title(self):
        _, manifest = gen.build_manifest(self._realization())
        hook = manifest["scenes"][0]
        self.assertIn("IZOLACJA", hook["headline"])


if __name__ == "__main__":
    unittest.main()
