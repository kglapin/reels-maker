import json
import tempfile
import unittest
from pathlib import Path



class BrandbookTests(unittest.TestCase):
    def test_embeds_authentic_logo_when_brand_declares_one(self):
        try:
            import reportlab
        except ImportError:
            self.skipTest("Optional PDF dependency not installed")
        from PIL import Image
        from reels_maker.brandbook import generate_brandbook

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "brands" / "sample"
            (folder / "assets").mkdir(parents=True)
            logo_file = folder / "assets" / "logo.png"
            Image.new("RGBA", (420, 95), (245, 245, 247, 255)).save(logo_file)
            (folder / "brand.json").write_text(json.dumps({
                "id": "sample", "name": "Sample",
                "branding": {"logo": "assets/logo.png"},
                "identity": {
                    "palette": {"primary": "#47A013"},
                    "logo": {"preview_background": "#14221A"}
                }
            }))
            result = generate_brandbook("sample", root)
            pdf = Path(result["output"]).read_bytes()
            self.assertTrue(result["logo_included"])
            self.assertIn(b"/Subtype /Image", pdf)

    def test_missing_configured_logo_is_an_error(self):
        try:
            import reportlab
        except ImportError:
            self.skipTest("Optional PDF dependency not installed")
        from reels_maker.brandbook import generate_brandbook
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brand = root / "brands" / "sample"
            brand.mkdir(parents=True)
            (brand / "brand.json").write_text(json.dumps({
                "id": "sample",
                "branding": {"logo": "assets/nonexistent.png"}
            }))
            with self.assertRaisesRegex(ValueError, "Brand logo is missing"):
                generate_brandbook("sample", root)

    def test_asta_brandbook_embeds_real_repo_logo(self):
        try:
            import reportlab
        except ImportError:
            self.skipTest("Optional PDF dependency not installed")
        from reels_maker.brandbook import generate_brandbook
        root = Path(__file__).resolve().parents[1]
        logo = root / "brands" / "asta-energy" / "assets" / "logo.png"
        if not logo.is_file():
            self.skipTest("ASTA brand asset excluded from checkout")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "asta-brandbook.pdf"
            result = generate_brandbook("asta-energy", root, output)
            data = output.read_bytes()
            self.assertTrue(result["logo_included"])
            self.assertEqual(result["pages"], 2)
            self.assertGreaterEqual(data.count(b"/Subtype /Image"), 1)
            self.assertTrue(data.startswith(b"%PDF"))

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
