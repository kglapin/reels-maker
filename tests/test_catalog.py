"""Asset catalog tests without media codecs or network dependencies."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reels_maker.catalog import catalog
from reels_maker.ffmpeg import RenderError
from reels_maker.cli import main


class CatalogTests(unittest.TestCase):
    def test_catalog_skips_outputs_and_detects_lfs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "one.mp4").write_bytes(b"not a real video, enumeration only")
            (root / "music.mp3").write_bytes(b"music")
            (root / "engine" / "assets" / "commons").mkdir(parents=True)
            (root / "engine" / "assets" / "commons" / "stock.webm").write_text(
                "version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 4321\n")
            (root / "output").mkdir()
            (root / "output" / "render.mp4").write_bytes(b"skip this")
            result = catalog(root)
            paths = {item["file"]: item for item in result["items"]}
            self.assertEqual(len(paths), 3)
            self.assertNotIn("output/render.mp4", paths)
            self.assertFalse(paths["engine/assets/commons/stock.webm"]["available"])
            self.assertEqual(paths["music.mp3"]["kind"], "audio")
            self.assertTrue(paths["one.mp4"]["available"])

    def test_cli_brand_catalog_is_brand_scoped(self):
        import contextlib
        import io
        import json
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            brand = root / "brands" / "example"
            (brand / "media").mkdir(parents=True)
            (brand / "media" / "clip.mp4").write_bytes(b"x")
            other = root / "brands" / "other"
            (other / "media").mkdir(parents=True)
            (other / "media" / "private.mp4").write_bytes(b"x")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["catalog", "--root", str(root),
                             "--brand", "example", "--json"])
            self.assertEqual(code, 0)
            response = json.loads(output.getvalue())
            self.assertEqual(response["brand"], "example")
            self.assertEqual([x["file"] for x in response["items"]],
                             ["media/clip.mp4"])

    def test_catalog_surfaces_visual_provenance_to_agents(self):
        import contextlib
        import io
        import json
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / "brands" / "example" / "media"
            folder.mkdir(parents=True)
            (folder / "old.mp4").write_bytes(b"already branded reel")
            (folder / "new.mp4").write_bytes(b"clean master")
            (folder / "unknown.mp4").write_bytes(b"not yet reviewed")
            (folder / "asset-reviews.json").write_text(json.dumps({
                "schema_version": 1,
                "assets": {
                    "media/old.mp4": {
                        "type": "finished_promo",
                        "burned_in": ["logo", "captions"]},
                    "media/new.mp4": {
                        "type": "clean_source",
                        "burned_in": []}
                }
            }))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["catalog", "--root", str(root),
                             "--brand", "example", "--json"])
            self.assertEqual(code, 0)
            items = {item["file"]: item
                     for item in json.loads(output.getvalue())["items"]}
            self.assertEqual(items["media/old.mp4"]["editorial_state"],
                             "finished_promo")
            self.assertFalse(items["media/old.mp4"]["overlay_ready"])
            self.assertEqual(items["media/new.mp4"]["editorial_state"],
                             "clean_source")
            self.assertTrue(items["media/new.mp4"]["overlay_ready"])
            self.assertIsNone(items["media/unknown.mp4"]["overlay_ready"])

    def test_listing_does_not_invoke_ffprobe_by_default(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "clip.mp4").write_bytes(b"placeholder")
            with patch("reels_maker.catalog.probe", side_effect=AssertionError("unexpected probe")):
                result = catalog(Path(temp))
            self.assertEqual(result["count"], 1)

    def test_bad_root_rejected(self):
        with self.assertRaises(RenderError):
            catalog(Path("/this/path/is/not/a/media/root"))

    def test_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            for n in range(3):
                (Path(temp) / f"{n}.mp4").write_bytes(b"x")
            result = catalog(Path(temp), limit=2)
            self.assertEqual(result["count"], 2)
            self.assertTrue(result["truncated"])


if __name__ == "__main__":
    unittest.main()
