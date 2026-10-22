"""Project-defined pixels and visual scale must work across all orientations."""
import tempfile
import unittest
from pathlib import Path

from reels_maker.canvas_layout import design_scale, resolve_safe_areas
from reels_maker.cards import draw_card
from reels_maker.ffmpeg import RenderError
from reels_maker.spec import Project


class CanvasLayoutTests(unittest.TestCase):
    def test_explicit_pixels_are_not_scaled(self):
        for width,height in ((1080,1920),(1920,1080),(1080,1080),(512,512)):
            margin, top, bottom = resolve_safe_areas(
                width,height,{"horizontal_pixels":65,"top_pixels":70,"bottom_pixels":85})
            self.assertEqual((margin,top,bottom),(65,70,85))

    def test_defaults_are_based_on_requested_canvas(self):
        for width,height in ((1920,1080),(1080,1920),(1024,1024),(320,568)):
            margin,top,bottom=resolve_safe_areas(width,height,{})
            self.assertAlmostEqual(margin/width,.085,delta=.003)
            self.assertAlmostEqual(top/height,.085,delta=.004)
            self.assertAlmostEqual(bottom/height,.13,delta=.004)

    def test_type_scale_is_rotation_independent(self):
        self.assertEqual(design_scale(1920,1080),design_scale(1080,1920))
        self.assertEqual(design_scale(1080,1080),1)
        self.assertAlmostEqual(design_scale(540,960),.5)

    def test_invalid_pixel_inputs_fail(self):
        for value in (True,-1,5.5,"90",None):
            with self.subTest(value=value), self.assertRaises(RenderError):
                resolve_safe_areas(1920,1080,{"top_pixels":value})
        for setting in ({"horizontal_pixels":10000},{"something":10},
                        {"top_pixels":550},{"bottom_pixels":600}):
            with self.subTest(setting=setting), self.assertRaises(RenderError):
                resolve_safe_areas(1920,1080,setting)

    def test_real_cards_do_not_depend_on_orientation(self):
        with tempfile.TemporaryDirectory() as temp:
            for idx,(w,h) in enumerate(((540,960),(960,540),(540,540))):
                with self.subTest(width=w,height=h):
                    project=Project(name="test",width=w,height=h,fps=25,
                        scenes=[],music=None,output="x.mp4",
                        branding={"safe_areas":{"horizontal_pixels":45,
                              "top_pixels":45,"bottom_pixels":60}})
                    layers=[]
                    path=Path(temp)/f"card-{idx}.png"
                    self.assertTrue(draw_card(project,{"headline":"ENERGIA"},None,path,layers=layers))
                    text_layers=[x for x in layers if x["role"]=="headline"]
                    self.assertEqual(len(text_layers),1)
                    for item in text_layers:
                        self.assertGreaterEqual(item["x"],45)
                        self.assertGreaterEqual(item["y"],45)
                        self.assertLess(item["y"],h-60)

if __name__ == "__main__":
    unittest.main()
