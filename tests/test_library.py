"""MD-05 acceptance: asset library with mandatory license metadata."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from reels_maker.library import LibraryError, check_library


def _brand(base: Path) -> dict:
    """Build a minimal valid library manifest plus a real asset on disk."""
    assets = base / "media" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1640, 1640), (20, 40, 20)).save(assets / "panel.png")
    return {
        "schema_version": 1,
        "entries": [{
            "id": "panel-hero",
            "kind": "product",
            "file": "media/assets/panel.png",
            "source": "https://example.org/source",
            "license": "CC0 1.0",
            "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
            "resolution": [1640, 1640],
            "topics": ["pv", "installation"],
            "editorial_state": "reviewed",
            "review": {"by": "owner", "date": "2026-10-23"},
        }],
    }


class AssetLibraryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, entries=None, **overrides) -> Path:
        manifest = _brand(self.base)
        if entries is not None:
            manifest["entries"] = entries
        manifest.update(overrides)
        path = self.base / "media" / "asset-library.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def test_valid_manifest_passes_with_counts(self):
        report = check_library(self._write())
        self.assertTrue(report["ok"])
        self.assertEqual(report["entries"], 1)
        self.assertEqual(report["reviewed"], 1)
        self.assertEqual(report["quarantine"], 0)

    def test_missing_field_is_a_named_error(self):
        path = self._write()
        raw = json.loads(path.read_text(encoding="utf-8"))
        del raw["entries"][0]["license"]
        path.write_text(json.dumps(raw), encoding="utf-8")
        with self.assertRaises(LibraryError) as ctx:
            check_library(path)
        self.assertIn("license", str(ctx.exception))
        self.assertIn("does not invent", str(ctx.exception))

    def test_unreviewed_state_must_be_declared_quarantine(self):
        path = self._write()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["entries"][0]["editorial_state"] = "unknown"
        path.write_text(json.dumps(raw), encoding="utf-8")
        with self.assertRaises(LibraryError) as ctx:
            check_library(path)
        self.assertIn("quarantine", str(ctx.exception))

    def test_review_record_is_mandatory(self):
        path = self._write()
        raw = json.loads(path.read_text(encoding="utf-8"))
        del raw["entries"][0]["review"]
        path.write_text(json.dumps(raw), encoding="utf-8")
        with self.assertRaises(LibraryError) as ctx:
            check_library(path)
        self.assertIn("review", str(ctx.exception))
        self.assertIn("required", str(ctx.exception))

    def test_duplicate_shot_is_rejected(self):
        entries = _brand(self.base)["entries"]
        duplicate = dict(entries[0], id="panel-alt")
        path = self._write(entries + [duplicate])
        with self.assertRaises(LibraryError) as ctx:
            check_library(path)
        self.assertIn("duplicate", str(ctx.exception))

    def test_lottie_kind_is_rejected_until_supported(self):
        path = self._write()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["entries"][0]["kind"] = "lottie"
        path.write_text(json.dumps(raw), encoding="utf-8")
        with self.assertRaises(LibraryError) as ctx:
            check_library(path)
        self.assertIn("not implemented", str(ctx.exception))

    def test_missing_file_on_disk_fails(self):
        path = self._write()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["entries"][0]["file"] = "media/assets/missing.png"
        path.write_text(json.dumps(raw), encoding="utf-8")
        with self.assertRaises(LibraryError) as ctx:
            check_library(path)
        self.assertIn("does not exist", str(ctx.exception))

    def test_quarantine_and_low_resolution_warn_without_error(self):
        entries = _brand(self.base)["entries"]
        Image.new("RGB", (640, 480), (5, 5, 5)).save(
            self.base / "media" / "assets" / "stamp.png")
        quarantined = dict(entries[0], id="stamp", kind="icon",
                           file="media/assets/stamp.png",
                           resolution=[640, 480],
                           editorial_state="quarantine")
        report = check_library(self._write(entries + [quarantined]))
        self.assertTrue(report["ok"])
        self.assertEqual(report["quarantine"], 1)
        self.assertTrue(any("quarantined" in w for w in report["warnings"]))
        self.assertTrue(any("720px" in w for w in report["warnings"]))


if __name__ == "__main__":
    unittest.main()
