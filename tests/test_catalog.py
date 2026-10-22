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
