"""MD-10 acceptance: a scaffolded brand is directly usable by the studio."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from reels_maker.design.color import parse_hex
from reels_maker.brand import init_brand
from reels_maker.library import LibraryError
from reels_maker.spec import ProjectError
from reels_maker.studio import load_studio


SCENE = {
    "name": "scaffold-check",
    "brand": "fresh-brand",
    "video": {"width": 1080, "height": 1920, "fps": 30},
    "scenes": [{"type": "statement", "duration": 1.2,
                "headline": "SZKIELET MARKI"}],
}


class BrandInitTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _init(self, root=None, **kwargs) -> dict:
        return init_brand("fresh-brand", name="Fresh Brand",
                          accent="#2057C9", root=root or self.root,
                          **kwargs)

    def test_scaffold_files_and_neutral_palette(self):
        report = self._init()
        directory = self.root / "brands" / "fresh-brand"
        self.assertEqual(report["brand"], "fresh-brand")
        for relative in ("brand.json", "BRAND.md", "projects", "licensing",
                         "media/footage", "media/assets"):
            self.assertTrue((directory / relative).exists(), relative)
        config = json.loads((directory / "brand.json").read_text("utf-8"))
        self.assertEqual(config["identity"]["palette"]["primary"], "#2057C9")
        self.assertTrue(any("laceholder" in warning
                            for warning in report["warnings"]))

    def test_existing_brand_never_overwritten_silently(self):
        self._init()
        with self.assertRaises(ProjectError) as ctx:
            self._init()
        self.assertIn("--force", str(ctx.exception))

    def test_scaffold_is_immediately_usable_by_the_studio(self):
        self._init()
        projects = self.root / "brands" / "fresh-brand" / "projects"
        projects.mkdir(parents=True, exist_ok=True)
        manifest = projects / "scaffold-check.json"
        manifest.write_text(json.dumps(SCENE), encoding="utf-8")
        project = load_studio(manifest, root=self.root)
        self.assertEqual(parse_hex("#2057C9"),
                         project.tokens.palette.accent)
        self.assertEqual(project.brand, "fresh-brand")

    def test_scaffold_treats_rights_documentation_as_mandatory(self):
        from reels_maker.library import check_library
        self._init()
        library = self.root / "brands" / "fresh-brand" / "media" / \
            "asset-library.json"
        self.assertFalse(library.is_file(),
                         "scaffold ships no media and no library manifest")
        with self.assertRaises((LibraryError, OSError)):
            check_library(library)


if __name__ == "__main__":
    unittest.main()
