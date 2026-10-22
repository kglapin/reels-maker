"""Brand isolation, preset inheritance and multi-brand project tests."""
import json
import tempfile
import unittest
from pathlib import Path

from reels_maker.brand import apply_brand, brand_directory
from reels_maker.spec import ProjectError, load_project


class BrandConfigurationTest(unittest.TestCase):
    def test_defaults_and_overrides(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            brand = root / "brands" / "sample-company"
            brand.mkdir(parents=True)
            (brand / "brand.json").write_text(json.dumps({
                "id": "sample-company",
                "branding": {"accent": "#112233", "logo": "assets/logo.png"}
            }))
            manifest = root / "video.json"
            manifest.write_text(json.dumps({
                "brand": "sample-company",
                "name": "intro",
                "branding": {"accent": "#445566"},
                "scenes": [{"file": "media/video/demo.mp4", "duration": 1}],
                "music": {"file": "media/audio/music.mp3"},
            }))
            resolved = apply_brand(load_project(manifest), root)
            self.assertEqual(resolved.branding["accent"], "#445566")
            self.assertEqual(resolved.branding["font_family"], "DejaVu Sans")
            self.assertNotIn("safe_areas", resolved.branding)
            self.assertEqual(resolved.branding["logo"],
                             "brands/sample-company/assets/logo.png")
            self.assertEqual(resolved.scenes[0]["file"],
                             "brands/sample-company/media/video/demo.mp4")
            self.assertEqual(resolved.music["file"],
                             "brands/sample-company/media/audio/music.mp3")
            self.assertIsNone(resolved.brand)
            self.assertEqual(apply_brand(resolved, root), resolved)

    def test_video_safe_areas_are_owned_by_project(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            brand = root / "brands" / "test-brand"
            brand.mkdir(parents=True)
            (brand / "brand.json").write_text(json.dumps({
                "id": "test-brand", "branding": {"accent": "#47A013"},
                "identity": {
                    "typography": {"primary": "Open Sans"},
                }
            }))
            p = root / "test.json"
            p.write_text(json.dumps({"brand": "test-brand",
                 "video": {"width": 1920, "height": 1080, "fps": 30},
                 "branding": {"safe_areas": {"bottom_pixels": 65, "top_pixels": 75}},
                 "scenes": [{"file": "media/demo.mp4", "duration": 1}]}))
            resolved = apply_brand(load_project(p), root)
            self.assertEqual(resolved.branding["font_family"], "Open Sans")
            self.assertEqual(resolved.branding["safe_areas"]["bottom_pixels"], 65)
            self.assertEqual((resolved.width, resolved.height, resolved.fps), (1920, 1080, 30))

    def test_brand_rejects_cross_directory_references(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            b = root / "brands" / "example"
            b.mkdir(parents=True)
            (b / "brand.json").write_text('{"id":"example","branding":{}}')
            manifest = root / "project.json"
            manifest.write_text(json.dumps({
                "brand": "example",
                "scenes": [{"file": "../other-brand/video.mp4", "duration": 1}]
            }))
            with self.assertRaises(ProjectError):
                apply_brand(load_project(manifest), root)

    def test_brand_slug_validation(self):
        with self.assertRaises(ProjectError):
            brand_directory("../secret", Path.cwd())
        with self.assertRaises(ProjectError):
            brand_directory("Brand Name", Path.cwd())

    def test_missing_brand_config_fails_explicitly(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "project.json"
            p.write_text('{"brand":"missing","scenes":[{"file":"clip.mp4","duration":1}]}')
            with self.assertRaisesRegex(ProjectError, "Cannot load brand configuration"):
                apply_brand(load_project(p), Path(d))


if __name__ == "__main__":
    unittest.main()
