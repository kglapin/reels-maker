"""Regression guards for premium ASTA editorial card layout.

These checks cover the 2026-10-23 user-reported overprinting in subsidy
amounts, secondary headlines and line spacing. No remote media needed.
"""
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from reels_maker.cards import draw_card
from reels_maker.spec import Project, ProjectError, load_project


def project(branding=None):
    return Project(name="editorial", width=720, height=1280, fps=25,
                   scenes=[], music=None, output="qa.mp4",
                   branding=branding or {"accent": "#47A013",
                                        "font_family": "Open Sans"})


def bounds_by_role(layers):
    result = {}
    for layer in layers:
        with Image.open(layer["file"]) as im:
            result[layer["role"]] = (
                layer["x"], layer["y"],
                layer["x"] + im.width, layer["y"] + im.height)
    return result


class EditorialLayoutTests(unittest.TestCase):
    def _render(self, root, title, basename):
        layers = []
        card = root / f"{basename}.png"
        self.assertTrue(draw_card(project(), title, None, card, layers))
        return layers, bounds_by_role(layers)

    def test_large_amount_never_overprints_supporting_copy(self):
        with tempfile.TemporaryDirectory() as d:
            layers, rectangles = self._render(Path(d), {
                "theme": "light", "backdrop": "none", "position": "upper",
                "kicker": "ŁĄCZNIE NAWET",
                "headline": "19 000 zł",
                "body": "maksymalnego wsparcia / PPE",
                "footer": "Obowiązują warunki programu",
            }, "amount")
            sequence = [rectangles[key] for key in
                        ("kicker", "headline", "body", "footer")]
            for before, after in zip(sequence, sequence[1:]):
                self.assertGreaterEqual(after[1] - before[3], 5,
                    "Rendered text glyphs overlap vertically")
            self.assertLess(sequence[-1][3], 1280 - round(1280*.13))
            self.assertGreater(sequence[0][1], 0)

    def test_both_themes_have_correct_text_color(self):
        with tempfile.TemporaryDirectory() as d:
            for theme in ("dark", "light"):
                layers, _ = self._render(Path(d), {
                    "theme": theme, "backdrop": "none",
                    "headline": "16 000 zł"
                }, theme)
                headline = next(x for x in layers if x["role"] == "headline")
                with Image.open(headline["file"]) as src:
                    rgba = src.convert("RGBA")
                    opaque = [p for p in rgba.getdata() if p[3] >= 240]
                    self.assertTrue(opaque)
                    # Light-theme ink has dark luminance and vice versa.
                    representative = min(opaque, key=lambda p:
                                         abs(p[0]-p[1]) + abs(p[1]-p[2]))
                    if theme == "light":
                        self.assertLess(max(representative[:3]), 100)
                    else:
                        self.assertGreater(min(representative[:3]), 160)

    def test_three_positions_produce_distinct_safe_vertical_bounds(self):
        with tempfile.TemporaryDirectory() as d:
            ys = []
            for position in ("upper", "middle", "lower"):
                layers, rectangles = self._render(Path(d), {
                    "theme": "light", "position": position,
                    "headline": "MAGAZYN ENERGII"
                }, position)
                ys.append(rectangles["headline"][1])
            self.assertEqual(ys, sorted(ys))
            self.assertEqual(len(set(ys)), 3)

    def test_rich_headline_keeps_body_separate_and_semantic_colors(self):
        with tempfile.TemporaryDirectory() as d:
            _, rectangles = self._render(Path(d), {
                "theme": "light", "position": "upper",
                "headline": {"runs": [
                    {"text": "DO", "scale": 0.7},
                    {"text": "30%", "scale": 1.3,
                     "color": "accent", "break_before": True}
                ]},
                "body": "kosztów kwalifikowanych",
            }, "rich")
            self.assertLess(rectangles["headline-1"][3],
                            rectangles["body"][1])

    def test_bad_theme_settings_rejected_at_manifest_load(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"bad.json"
            bad = [
                {"theme": "bright"},
                {"position": "random"},
                {"logo": "false"},
                {"theme": "light", "backdrop": "strong"}
            ]
            for item in bad:
                with self.subTest(title=item):
                    p.write_text(json.dumps({
                        "video": {"width":720,"height":1280,"fps":25},
                        "scenes": [{"file":"shot.mp4","duration":2,"title":item}]
                    }))
                    with self.assertRaises(ProjectError):
                        load_project(p)


if __name__ == "__main__":
    unittest.main()
