"""Unit tests for the iso prop auto-critique (synthetic fixtures only)."""
import unittest

from PIL import Image, ImageDraw

from tools.iso_prop_critique import autoreframe, critique

PLATE = None

BG = (18, 42, 28)


def _canvas():
    return Image.new("RGB", (384, 320), BG)


def _plate():
    return _canvas()


class PropCritiqueTests(unittest.TestCase):
    def test_clean_prop_passes(self):
        im = _canvas()
        ImageDraw.Draw(im).rectangle([140, 100, 244, 260], fill=(200, 210, 200))
        report = critique(im, _plate())
        self.assertTrue(report["ok"], report["issues"])

    def test_detached_part_is_floater(self):
        im = _canvas()
        draw = ImageDraw.Draw(im)
        draw.rectangle([140, 120, 244, 260], fill=(200, 210, 200))
        draw.rectangle([40, 40, 70, 70], fill=(200, 210, 200))
        report = critique(im, _plate())
        self.assertFalse(report["ok"])
        codes = [i["code"] for i in report["issues"]]
        self.assertIn("floater", codes)

    def test_ground_touching_part_is_no_floater(self):
        im = _canvas()
        draw = ImageDraw.Draw(im)
        draw.rectangle([140, 60, 244, 200], fill=(200, 210, 200))
        draw.rectangle([40, 290, 90, 319], fill=(150, 170, 150))
        report = critique(im, _plate())
        codes = [i["code"] for i in report["issues"]]
        self.assertNotIn("floater", codes)

    def test_top_crop_fails(self):
        im = _canvas()
        ImageDraw.Draw(im).rectangle([140, 0, 244, 200], fill=(200, 210, 200))
        report = critique(im, _plate())
        self.assertFalse(report["ok"])
        by_code = {i["code"]: i for i in report["issues"]}
        self.assertIn("cropped", by_code)
        self.assertIn("top", by_code["cropped"]["detail"]["edges"])

    def test_tiny_prop_fails_framing(self):
        im = _canvas()
        ImageDraw.Draw(im).rectangle([180, 140, 204, 164], fill=(200, 210, 200))
        report = critique(im, _plate())
        self.assertFalse(report["ok"])
        self.assertIn("framing", [i["code"] for i in report["issues"]])

    def test_thin_tall_prop_warns_only(self):
        im = _canvas()
        ImageDraw.Draw(im).rectangle([188, 10, 196, 310], fill=(200, 210, 200))
        report = critique(im, _plate())
        self.assertTrue(report["ok"])
        self.assertIn("thin-subject", [i["code"] for i in report["issues"]])

    def test_autoreframe_fixes_tiny_prop(self):
        def paint(k, origin):
            im = _canvas()
            s = max(6, int(k))
            ImageDraw.Draw(im).rectangle(
                [192 - s, 160 - s, 192 + s, 160 + s], fill=(200, 210, 200))
            return im

        _image, corrections, report = autoreframe(
            paint, _plate(), k=20.0, origin=(0.0, 0.0), size=(384, 320))
        self.assertTrue(corrections)
        self.assertTrue(report["ok"], report["issues"])


if __name__ == "__main__":
    unittest.main()
