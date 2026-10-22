"""Brand expansion must be identical for validate and render."""
import unittest
from pathlib import Path
from reels_maker.brand import apply_brand
from reels_maker.spec import load_project

ROOT = Path(__file__).resolve().parents[1]


class BrandTests(unittest.TestCase):
    def test_asta_project_expands_brand_scoped_assets(self):
        manifest = ROOT / "brands/asta-energy/projects/asta-rush-demo.json"
        project = load_project(manifest)
        resolved = apply_brand(project, ROOT)
        self.assertIsNone(resolved.brand)
        self.assertTrue(resolved.scenes)
        self.assertTrue(all(s["file"].startswith("brands/asta-energy/") for s in resolved.scenes))
        self.assertEqual(resolved.branding["accent"], "#47A013")
        self.assertEqual(resolved.branding["logo"], "brands/asta-energy/assets/logo.png")

    def test_brand_expansion_is_idempotent(self):
        project = load_project(ROOT / "brands/asta-energy/projects/asta-rush-demo.json")
        once = apply_brand(project, ROOT)
        self.assertEqual(apply_brand(once, ROOT), once)


if __name__ == "__main__":
    unittest.main()
