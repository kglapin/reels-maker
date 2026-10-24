"""Regression tests for packaged SVG icon providers and graph rendering."""
import tempfile
import unittest
import hashlib
from types import SimpleNamespace
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from reels_maker import icon_library

try:  # pragma: no cover - environment probe (system cairo needed by cairosvg)
    icon_library._homebrew_cairo_fallback()
    import cairocffi  # noqa: F401
    _CAIRO = True
except (ImportError, OSError):
    _CAIRO = False

from reels_maker.icon_library import (
    IconLibraryError, VERSIONS, _validated, asset, provenance, raster,
    suggest_icons,
)
from reels_maker.components.scenes import _external_icon, _extra_icons
from reels_maker.core.scene_graph import Node
from reels_maker.renderers.studio import _icon_provenance

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

    def test_rejects_excessive_svg_path_complexity(self):
        paths = b'<path d="M0 0"/>' * 257
        source = b'<svg xmlns="http://www.w3.org/2000/svg">' + paths + b'</svg>'
        with self.assertRaisesRegex(IconLibraryError, "path safety limit"):
            _validated(source)

    def test_pinned_tabler_phosphor_and_material_symbol_sources(self):
        with tempfile.TemporaryDirectory() as root:
            with patch("reels_maker.icon_library.urllib.request.urlopen",
                       side_effect=lambda *args, **kwargs: BytesIO(SVG)) as fetch:
                tabler = asset("tabler", "home", cache_dir=root)
                phosphor = asset("phosphor", "house", style="bold", cache_dir=root)
                material = asset(
                    "material_symbols", "web/home", style="outlined",
                    weight=500, fill=True, grade=200, optical_size=24,
                    cache_dir=root)
            urls = [call.args[0].full_url for call in fetch.call_args_list]
            self.assertIn("tabler-icons/v3.49.0/icons/outline/home.svg", urls[0])
            self.assertIn("phosphor-icons/core/v2.0.8/assets/bold/house-bold.svg", urls[1])
            self.assertIn(
                "material-design-icons/10ecc14790612ca8fd164e3f4ffe9c16fc50d5b7/"
                "symbols/web/home/materialsymbolsoutlined/home_wght500grad200fill1_24px.svg",
                urls[2])
            self.assertTrue(tabler.is_file() and phosphor.is_file() and material.is_file())

    def test_material_symbol_names_variants_are_strict(self):
        with self.assertRaisesRegex(IconLibraryError, "web/<lowercase_symbol_name>"):
            asset("material_symbols", "../../etc/passwd", style="outlined", offline=True)
        with self.assertRaisesRegex(IconLibraryError, "weight must be"):
            asset("material_symbols", "web/home", style="outlined", weight=450, offline=True)
        with self.assertRaisesRegex(IconLibraryError, "fill must be a boolean"):
            asset("material_symbols", "web/home", style="outlined", fill="false", offline=True)

    def test_brand_logo_symbols_are_blocked_without_item_clearance(self):
        for library, name, style in (
            ("tabler", "brand-facebook", "outline"),
            ("phosphor", "facebook-logo", "regular"),
            ("material_symbols", "web/company_logo", "outlined"),
        ):
            with self.subTest(library=library, name=name):
                with self.assertRaisesRegex(IconLibraryError, "item-level license/trademark"):
                    asset(library, name, style=style, offline=True)

    def test_icon_director_is_deterministic_bounded_and_nonhallucinatory(self):
        suggestions = suggest_icons("photovoltaic", libraries=("lucide", "tabler", "material_symbols"))
        self.assertEqual(len(suggestions), 3)
        self.assertTrue(all(item["role"] == "sun" and item["rights_status"] == "unknown"
                            and item["license"]["url"] for item in suggestions))
        material = suggest_icons("battery storage", libraries=("material_symbols",))[0]
        self.assertEqual((material["name"], material["style"]),
                         ("web/battery_charging_full", "outlined"))
        self.assertEqual(suggest_icons("invented-glyph"), [])
        with self.assertRaisesRegex(IconLibraryError, "limit"):
            suggest_icons("sun", limit=4)

    def test_icon_provenance_records_pin_license_source_and_hash(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "tabler" / "v3.49.0" / "outline" / "home.svg"
            path.parent.mkdir(parents=True)
            path.write_bytes(SVG)
            result = provenance("tabler", "home", cache_dir=root, offline=True)
            self.assertEqual(result["version"], "v3.49.0")
            self.assertEqual(result["license"]["id"], "MIT")
            self.assertIn("tabler-icons/v3.49.0", result["source_url"])
            self.assertEqual(result["sha256"], hashlib.sha256(SVG).hexdigest())
            self.assertEqual(result["rights_status"], "unknown")

    def test_studio_export_provenance_deduplicates_selected_icon_assets(self):
        props = {"library": "tabler", "name": "home", "style": "outline",
                 "weight": 400, "fill": False, "grade": 0, "optical_size": 24}
        nodes = [Node(kind="icon", role="home-a", props=props),
                 Node(kind="icon", role="home-b", props=dict(props)),
                 Node(kind="icon", role="check", props={**props, "name": "check"})]
        scene = SimpleNamespace(nodes=nodes)

        def record(library, name, **options):
            return {"provider": library, "asset_id": name, "style": options["style"],
                    "source_url": f"https://icons.example/{name}", "sha256": "abc",
                    "license": {"id": "MIT", "url": "license"}}

        with patch("reels_maker.icon_library.provenance", side_effect=record):
            result = _icon_provenance([scene])
        self.assertEqual([item["asset_id"] for item in result], ["check", "home"])

    def test_icon_assets_support_safe_static_and_authored_rotation(self):
        context = SimpleNamespace(width=1080, height=1920, duration=2.0)
        static = _extra_icons(context, {"icon_assets": [{
            "library": "tabler", "name": "home", "x": .5, "y": .5,
            "size": .1, "color": "#227744", "rotation": -12,
        }]}, {})[0]
        self.assertEqual(static.rotation, -12)
        self.assertGreater(static.world_bounds()[2] - static.world_bounds()[0],
                           static.base_bounds()[2] - static.base_bounds()[0])
        animated = _extra_icons(context, {"icon_assets": [{
            "library": "material_symbols", "name": "web/home", "x": .5, "y": .5,
            "size": .1, "color": "#227744",
            "rotation_motion": {"family": "tilt-settle", "angle": -8,
                                "duration": .5, "reason": "arrival"},
        }]}, {})[0]
        self.assertIn("rotation", animated.tracks)
        self.assertAlmostEqual(animated.sample(.5).rotation, 0, delta=.01)
        with self.assertRaisesRegex(ValueError, "between -35 and 35"):
            _extra_icons(context, {"icon_assets": [{
                "library": "tabler", "name": "home", "x": .5, "y": .5,
                "size": .1, "color": "#227744", "rotation": 90,
            }]}, {})

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

    @unittest.skipUnless(_CAIRO, "system cairo is not available (cairosvg)")
    def test_fillless_material_svg_inherits_requested_colour(self):
        # Material Symbols paths carry no fill attribute; the inherited colour
        # must not fall back to the default black fill.
        filled = (b'<svg xmlns="http://www.w3.org/2000/svg" height="24" '
                  b'viewBox="0 -960 960 960" width="24"><path d="M480-320'
                  b'q-66 0-113-47t-47-113q0-66 47-113t113-47q66 0 113 47t47 '
                  b'113q0 66-47 113t-113 47Z"/></svg>')
        with tempfile.TemporaryDirectory() as root:
            path = (Path(root) / "material_symbols"
                    / VERSIONS["material_symbols"] / "outlined"
                    / "web--sunny-f0-g0-o24.svg")
            path.parent.mkdir(parents=True)
            path.write_bytes(filled)
            icon = raster("material_symbols", "web/sunny", 72, "#123456",
                          cache_dir=root, offline=True)
            coloured = [pixel for pixel in icon.getdata() if pixel[3] > 0]
            self.assertTrue(coloured)
            strongest = max(coloured, key=lambda pixel: pixel[3])
            self.assertEqual(strongest[:3], (0x12, 0x34, 0x56))

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
        material = _external_icon(
            {"icon_library": "material_symbols", "icon_fill": True,
             "icon_weight": 500, "icon_grade": 200},
            "battery", 80, 100, 48, (255, 0, 0))
        self.assertEqual(material.props["name"], "web/battery_charging_full")
        self.assertEqual(material.props["style"], "outlined")
        self.assertEqual((material.props["weight"], material.props["fill"],
                          material.props["grade"]), (500, True, 200))


if __name__ == "__main__":
    unittest.main()
