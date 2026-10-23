"""Regression tests for packaged SVG icon providers and graph rendering."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

try:  # pragma: no cover - environment probe (system cairo needed by cairosvg)
    import cairocffi  # noqa: F401
    _CAIRO = True
except (ImportError, OSError):
    _CAIRO = False

from reels_maker.icon_library import (
    IconLibraryError, _validated, asset, raster,
)
from reels_maker.components.scenes import _external_icon
from reels_maker.core.scene_graph import Node

SVG = b'''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"
 viewBox="0 0 24 24" fill="none" stroke="currentColor"
 stroke-width="2"><circle cx="12" cy="12" r="9" /></svg>'''


class IconLibraryTests(unittest.TestCase):
    def test_normalize_and_reject_path_traversal(self):
        for bad in ("../../etc/passwd", "camelCase", "spaces bad", "x.svg",
                    "", "foo/bar"):
            with self.subTest(bad=bad):
                with self.assertRaises(IconLibraryError):
                    asset("lucide", bad, offline=True)
        with self.assertRaises(IconLibraryError):
            asset("unknown", "home", offline=True)
        with self.assertRaises(IconLibraryError):
            asset("lucide", "home", style="solid", offline=True)

    def test_reject_unsafe_svg(self):
        malicious = [
            b'<!DOCTYPE svg [<!ENTITY x SYSTEM "file:///etc/passwd">]><svg/>',
            b'<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>',
            b'<svg xmlns="http://www.w3.org/2000/svg"><image href="http://x"/></svg>',
            b'<svg xmlns="http://www.w3.org/2000/svg" onload="bad()" />',
        ]
        for item in malicious:
            with self.subTest(item=item[:25]):
                with self.assertRaises(IconLibraryError):
                    _validated(item)

    @unittest.skipUnless(_CAIRO, "system cairo is not available (cairosvg)")
    def test_cache_and_recolour(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "lucide" / "0.468.0" / "outline" / "sun.svg"
            path.parent.mkdir(parents=True)
            path.write_bytes(SVG)
            actual = asset("lucide", "sun", cache_dir=root, offline=True)
            self.assertEqual(actual, path)
            icon = raster("lucide", "sun", 72, "#FF6600",
                          cache_dir=root, offline=True)
            self.assertEqual(icon.size, (72, 72))
            self.assertEqual(icon.mode, "RGBA")
            self.assertIsNotNone(icon.getbbox())
            self.assertGreater(sum(1 for pixel in icon.getdata()
                                   if pixel[0] > pixel[2] and pixel[3]), 0)

    def test_graph_bounds_and_sample(self):
        node = Node(kind="icon", role="graphic",
                    props={"x": 20, "y": 30, "w": 90, "h": 90})
        self.assertEqual(node.base_bounds(), (20, 30, 110, 120))
        self.assertEqual(node.sample(0).base_bounds(), (20, 30, 110, 120))

    def test_opt_in_and_backwards_compatibility(self):
        self.assertIsNone(_external_icon({}, "sun", 40, 40, 20, (255, 0, 0)))
        node = _external_icon(
            {"icon_library": "heroicons",
             "icon_names": {"sun": "bolt"}, "icon_style": "solid"},
            "sun", 80, 100, 48, (255, 0, 0))
        self.assertEqual(node.kind, "icon")
        self.assertEqual(node.props["library"], "heroicons")
        self.assertEqual(node.props["name"], "bolt")
        self.assertEqual(node.props["style"], "solid")
        self.assertEqual(node.base_bounds(), (56, 76, 104, 124))


if __name__ == "__main__":
    unittest.main()
