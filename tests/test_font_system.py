"""Google-Fonts-grade resolution: weights, fallback flags and verified fetch.

These tests pin the font-supply contract: families resolve
case-insensitively, weights beyond regular/bold work, a missing explicit
family is reported instead of silently swapped, resolved fonts must cover
Polish diacritics, and fetch-fonts only installs hash-verified files.
"""
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from reels_maker.textkit.typesetter import FontBook


def _system_font():
    """A real TTF present on dev machines and CI (matplotlib or system)."""
    candidates = []
    try:
        import matplotlib
        candidates.append(Path(matplotlib.get_data_path()) /
                          "fonts/ttf/DejaVuSans.ttf")
    except ImportError:
        pass
    candidates.append(
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    for path in candidates:
        if path.is_file():
            return path
    return None


SYSTEM_FONT = _system_font()
needs_font = unittest.skipUnless(
    SYSTEM_FONT is not None, "no system DejaVuSans.ttf available")


class FontResolutionTests(unittest.TestCase):
    def _with_home(self, tmp):
        previous = os.environ.get("HOME")
        os.environ["HOME"] = tmp
        self.addCleanup(
            (lambda: os.environ.pop("HOME")) if previous is None else
            (lambda: os.environ.__setitem__("HOME", previous)))

    def _install(self, directory, stem, source=None):
        (directory).mkdir(parents=True, exist_ok=True)
        target = directory / stem
        target.write_bytes((source or SYSTEM_FONT).read_bytes())
        return target

    @needs_font
    def test_weight_beyond_bold_resolves(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._with_home(tmp)
            fonts_dir = Path(tmp) / "Library" / "Fonts"
            self._install(fonts_dir, "ProbeFamily-Medium.ttf")
            self._install(fonts_dir, "ProbeFamily-SemiBold.ttf")
            book = FontBook(family="ProbeFamily")
            self.assertEqual(Path(book.path("medium")).name,
                             "ProbeFamily-Medium.ttf")
            self.assertEqual(Path(book.path("semibold")).name,
                             "ProbeFamily-SemiBold.ttf")

    @needs_font
    def test_family_name_matches_case_insensitively(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._with_home(tmp)
            fonts_dir = Path(tmp) / "Library" / "Fonts"
            self._install(fonts_dir, "probefamily-Regular.ttf")
            book = FontBook(family="ProbeFamily")
            self.assertEqual(Path(book.path("regular")).name,
                             "probefamily-Regular.ttf")

    @needs_font
    def test_missing_explicit_family_flags_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._with_home(tmp)
            book = FontBook(family="Definitely Missing Family")
            try:
                resolved = book.path("regular")
            except RuntimeError:
                self.skipTest("no system fallback font on this host")
            self.assertTrue(Path(resolved).is_file())
            self.assertTrue(book.used_fallback)
            self.assertEqual(book.requested_family,
                             "Definitely Missing Family")

    @needs_font
    def test_unrelated_brand_files_never_shadow_family_miss(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._with_home(tmp)
            other = Path(tmp) / "other"
            other.mkdir()
            (other / "Lato-Bold.ttf").write_bytes(SYSTEM_FONT.read_bytes())
            book = FontBook(family="Montserrat", extra_dirs=[str(other)])
            resolved = Path(book.path("bold"))
            self.assertNotEqual(resolved.name, "Lato-Bold.ttf")
            self.assertTrue(book.used_fallback)

    @needs_font
    def test_layout_engine_is_pinned_to_basic(self):
        # Pillow auto-selects Raqm when the build bundles libraqm, which
        # shifts glyph pixels between machines and breaks exact-pixel
        # golden fixtures; the renderer must not depend on the build.
        from PIL import ImageFont
        book = FontBook()
        self.assertEqual(
            book.get(24).layout_engine, ImageFont.Layout.BASIC)

    def test_strict_missing_family_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._with_home(tmp)
            book = FontBook(family="Definitely Missing Family", strict=True)
            with self.assertRaises(RuntimeError):
                book.path("regular")

    @needs_font
    def test_font_without_polish_glyphs_is_rejected(self):
        from fontTools import subset
        with tempfile.TemporaryDirectory() as tmp:
            self._with_home(tmp)
            ascii_only = Path(tmp) / "AsciiOnly-Regular.ttf"
            options = subset.Options()
            font = subset.load_font(str(SYSTEM_FONT), options)
            subsetter = subset.Subsetter(options)
            subsetter.populate(text="ABCabc012 ")
            subsetter.subset(font)
            font.save(str(ascii_only))
            book = FontBook(family="AsciiOnly", extra_dirs=[tmp])
            with self.assertRaises(RuntimeError) as caught:
                book.path("regular")
            self.assertIn("Polish", str(caught.exception))


class FetchFontsTests(unittest.TestCase):
    def _allowlist(self, directory, source, sha):
        return {"families": {"Probe": {
            "kind": "static",
            "files": {"regular": {
                "url": source.as_uri(), "sha256": sha}}}}}

    @needs_font
    def test_fetch_installs_verified_file(self):
        from reels_maker.google_fonts import fetch_font
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.ttf"
            source.write_bytes(SYSTEM_FONT.read_bytes())
            sha = hashlib.sha256(source.read_bytes()).hexdigest()
            dest = Path(tmp) / "media" / "fonts"
            saved = fetch_font("Probe", dest,
                               allowlist=self._allowlist(tmp, source, sha))
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0].name, "Probe-Regular.ttf")
            self.assertEqual(saved[0].read_bytes(), source.read_bytes())

    @needs_font
    def test_fetch_rejects_hash_mismatch(self):
        from reels_maker.google_fonts import fetch_font
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.ttf"
            source.write_bytes(SYSTEM_FONT.read_bytes())
            dest = Path(tmp) / "media" / "fonts"
            allowlist = self._allowlist(tmp, source, "0" * 64)
            with self.assertRaises(RuntimeError):
                fetch_font("Probe", dest, allowlist=allowlist)
            self.assertFalse(dest.exists() and any(dest.iterdir()))

    def test_fetch_unknown_family_raises(self):
        from reels_maker.google_fonts import fetch_font
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                fetch_font("No Such Family", Path(tmp),
                           allowlist={"families": {}})


class BrandFontsDirTests(unittest.TestCase):
    @needs_font
    def test_font_book_reads_brand_media_fonts(self):
        from reels_maker.studio import _font_book
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            media_fonts = root / "brands" / "probe" / "media" / "fonts"
            media_fonts.mkdir(parents=True)
            (media_fonts / "Probe-Regular.ttf").write_bytes(
                SYSTEM_FONT.read_bytes())
            book = _font_book(root, {"id": "probe",
                                     "identity": {"typography": {}}})
            self.assertIn(str(media_fonts), book.extra_dirs)


if __name__ == "__main__":
    unittest.main()
