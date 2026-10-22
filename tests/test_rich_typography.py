"""Mixed-size words and visual hierarchy independent from brand identity."""
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from reels_maker.cards import draw_card, _font
from reels_maker.spec import Project, ProjectError, load_project
from reels_maker.typography import layout_runs


class RichTextTests(unittest.TestCase):
    def _project(self):
        return Project(name="editorial", width=540, height=960, fps=25,
                       scenes=[], music=None, branding={"accent": "#47A013"},
                       output="out.mp4")

    def test_emphasized_words_get_larger_fonts_and_brand_color(self):
        img = Image.new("RGBA", (540, 960), (0, 0, 0, 0))
        result = layout_runs(ImageDraw.Draw(img), [
            {"text": "Zwiększ ", "scale": 0.75},
            {"text": "ZYSK", "scale": 1.35, "color": "accent"},
            {"text": " z energii", "scale": 0.75, "break_before": True},
        ], lambda size, bold: _font(size, bold),
           35, 480, "#47A013")
        entries = {token: (face, ink) for token, face, ink, _, _, _ in result.parts}
        self.assertGreater(entries["ZYSK"][0].size, entries["Zwiększ"][0].size)
        self.assertEqual(entries["ZYSK"][1], "#47A013")
        self.assertEqual(result.lines, 2)

    def test_mixed_sizes_share_baseline_on_same_line(self):
        draw = ImageDraw.Draw(Image.new("RGBA", (540, 960)))
        layout = layout_runs(draw, [
            {"text": "Więcej ", "scale": .70, "weight": "regular"},
            {"text": "ENERGII", "scale": 1.25, "weight": "bold",
             "color": "accent"}
        ], lambda size, bold: _font(size, bold), 36, 500, "#47A013")
        self.assertEqual(layout.lines, 1)
        self.assertEqual(len({piece[4] for piece in layout.parts}), 1)
        self.assertGreater(layout.parts[-1][1].size,
                           layout.parts[0][1].size)

    def test_backdrop_can_be_explicitly_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._project()
            blank = Path(tmp) / "none.png"
            self.assertTrue(draw_card(p, {
                "headline":"Energia",
                "backdrop":"none"}, None, blank))
            with Image.open(blank) as rendered:
                self.assertEqual(rendered.getpixel((2, rendered.height-2))[3], 0)

    def test_rich_headline_draws_without_motion_and_with_layers(self):
        with tempfile.TemporaryDirectory() as tmp:
            title = {"kicker": "ASTA", "headline": {"runs": [
                {"text": "ZYSK", "scale": 1.3, "color": "accent"},
                {"text": " z energii", "scale": 0.75, "break_before": True}
            ]}, "body": "Fotowoltaika dla firm"}
            folder = Path(tmp)
            file = folder / "still.png"
            self.assertTrue(draw_card(self._project(), title, None, file))
            self.assertGreater(Image.open(file).getbbox()[2], 0)
            layers = []
            self.assertTrue(draw_card(self._project(), title, None,
                                      folder / "layered.png", layers))
            self.assertIn("headline-0", [l["role"] for l in layers])
            self.assertIn("headline-1", [l["role"] for l in layers])
            self.assertTrue(all(Path(l["file"]).is_file() for l in layers))

    def test_rejects_unsafe_or_unreadable_styling(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "project.json"
            for run in (
                {"text": "TEST", "scale": 7},
                {"text": "TEST", "color": "#FF0000"},
                {"text": "TEST", "font": "Comic Sans"},
                {"text": "", "scale": 1},
                {"text": "TEST", "break_before": "yes"},
            ):
                path.write_text(json.dumps({
                    "scenes": [{
                        "file": "source.mp4", "duration": 2,
                        "title": {"headline": {"runs": [run]}}
                    }]
                }))
                with self.assertRaises(ProjectError):
                    load_project(path)

    def test_directional_motion_is_opt_in(self):
        from reels_maker.motion import compose_motion
        layers = [{"file": "a.png", "x": 20, "y": 30, "role": "headline"}]
        for preset in ("rise_soft", "fade_stagger",
                       "slide_left", "slide_right", "editorial_reveal"):
            cfg = {"preset": preset, "duration_frames": 7,
                   "stagger_frames": 0}
            args = compose_motion("scale=540:960", 25, 60,
                                  "bg.png", layers, cfg, 540)
            graph = args[args.index("-filter_complex") + 1]
            self.assertIn("alpha=1", graph)
            if preset in ("slide_left", "slide_right"):
                self.assertIn("overlay=x='20+", graph)
            else:
                self.assertIn("overlay=x='20'", graph)


if __name__ == "__main__":
    unittest.main()
