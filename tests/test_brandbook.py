import json
import tempfile
import unittest
from pathlib import Path



class BrandbookTests(unittest.TestCase):
    def test_generates_pdf_from_brand_json(self):
        try:
            import reportlab
        except ImportError:
            self.skipTest("Optional PDF dependency not installed")
        from reels_maker.brandbook import generate_brandbook
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brand = root / "brands" / "demo"
            brand.mkdir(parents=True)
            (brand / "brand.json").write_text(json.dumps({
                "id": "demo", "name": "Demo Brand", "version": 1,
                "identity": {
                    "palette": {"primary": "#47A013", "background": "#FFFFFF"},
                    "typography": {"primary": "Open Sans", "fallback": "DejaVu Sans"}
                }
            }))
            result = generate_brandbook("demo", root)
            file = Path(result["output"])
            self.assertEqual(result["pages"], 2)
            self.assertTrue(file.read_bytes().startswith(b"%PDF"))
            self.assertGreater(file.stat().st_size, 1000)
            # PDF generation does not require identity.format or safe_areas.
            self.assertNotIn("format", json.loads((brand / "brand.json").read_text())["identity"])


if __name__ == "__main__":
    unittest.main()
