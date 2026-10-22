import json
import tempfile
import unittest
from pathlib import Path

from reels_maker.brandbook import generate_brandbook


class BrandbookTests(unittest.TestCase):
    def test_generates_pdf_from_brand_json(self):
        try:
            import reportlab
        except ImportError:
            self.skipTest("Optional PDF dependency not installed")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brand = root / "brands" / "demo"
            brand.mkdir(parents=True)
            (brand / "brand.json").write_text(json.dumps({
                "id": "demo", "name": "Demo Brand", "version": 1,
                "identity": {
                    "palette": {"primary": "#47A013", "background": "#FFFFFF"},
                    "typography": {"primary": "Open Sans", "fallback": "DejaVu Sans"},
                    "safe_areas": {"top_pixels": 190, "bottom_pixels": 290,
                                   "horizontal_pixels": 88},
                    "format": {"default_width": 1080, "default_height": 1920,
                               "default_fps": 25}
                }
            }))
            result = generate_brandbook("demo", root)
            file = Path(result["output"])
            self.assertEqual(result["pages"], 1)
            self.assertTrue(file.read_bytes().startswith(b"%PDF"))
            self.assertGreater(file.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
