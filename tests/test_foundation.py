"""Offline unit tests (no FFmpeg binaries or downloadable media required)."""
import json
import tempfile
import unittest
from pathlib import Path

from reels_maker.paths import AssetError, resolve_asset
from reels_maker.spec import ProjectError, load_project


class FoundationTest(unittest.TestCase):
    def test_resolves_unicode_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "chodzież.mp4"
            path.write_bytes(b"mock")
            self.assertEqual(resolve_asset("chodziez\u0307.mp4", root), path)

    def test_prevents_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(AssetError):
                resolve_asset("../outside.mp4", Path(tmp))

    def test_detects_unpulled_lfs_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "clip.webm"
            p.write_text("version https://git-lfs.github.com/spec/v1\n"
                         "oid sha256:abc\nsize 999\n")
            with self.assertRaisesRegex(AssetError, "Git LFS"):
                resolve_asset(p.name, Path(tmp))

    def test_validates_and_sums_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sample.json"
            p.write_text(json.dumps({"scenes": [
                {"file": "a.mp4", "start": 2, "duration": 1.5},
                {"file": "b.mp4", "duration": 2.5}
            ]}))
            item = load_project(p)
            self.assertEqual(item.duration, 4.0)
            self.assertEqual((item.width, item.height), (1080, 1920))

    def test_rejects_negative_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            p.write_text('{"scenes":[{"file":"a.mp4","duration":-1}]}')
            with self.assertRaises(ProjectError):
                load_project(p)


if __name__ == "__main__":
    unittest.main()
