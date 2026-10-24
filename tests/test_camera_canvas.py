"""Regression checks for optional shared-canvas camera mode."""
import tempfile
import unittest
import math
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
from reels_maker.renderers.camera_canvas import (
    CameraCanvasRenderer, camera_viewport_to_world, validate_camera_canvas,
)
from reels_maker.core.transforms import Point, Space

class CameraCanvasTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=str(Path(self.tmp.name)/"photo.png")
        Image.new("RGB",(500,600),(65,118,166)).save(self.path)
        self.scenes=[
            {"photo":self.path,"headline":"FIRST","subtitle":"Caption A",
             "camera_canvas":{"x":550,"y":590,"angle":-13,"layout":"photo-above"}},
            {"photo":self.path,"headline":"NEXT","subtitle":"Caption B",
             "camera_canvas":{"x":1300,"y":740,"angle":74,"layout":"photo-left",
                              "move_duration":.8,"reveal_delay":.15}},
        ]
    def tearDown(self):
        self.tmp.cleanup()
    def project(self):
        return SimpleNamespace(width=360,height=640,scenes=self.scenes)
    def test_validate_rejects_partial_opt_in(self):
        with self.assertRaises(ValueError):
            validate_camera_canvas([self.scenes[0],{}])
    def test_validate_rejects_nonfinite_rotation(self):
        self.scenes[1]["camera_canvas"]["angle"]=float("nan")
        with self.assertRaises(ValueError):
            validate_camera_canvas(self.scenes)
    def test_irregular_camera_interpolates_between_stops(self):
        renderer=CameraCanvasRenderer(self.project())
        a=renderer.camera(1,0)
        b=renderer.camera(1,.8)
        self.assertEqual(a,renderer.stops[0])
        self.assertEqual(b,renderer.stops[1])
        self.assertEqual(round(b[2]-a[2]),87)
    def test_render_dimensions_and_delayed_typography(self):
        renderer=CameraCanvasRenderer(self.project())
        frame=renderer.render(SimpleNamespace(index=1),0)
        final=renderer.render(SimpleNamespace(index=1),1.5)
        self.assertEqual(frame.size,(360,640))
        self.assertEqual(final.size,(360,640))
        self.assertNotEqual(frame.tobytes(),final.tobytes())
    def test_existing_stages_preserve_images(self):
        renderer=CameraCanvasRenderer(self.project())
        self.assertEqual(len(renderer.stages),3)
        self.assertEqual(renderer.stages[0].size,renderer.stages[1].size)

    def test_camera_sampling_uses_shared_viewport_to_world_affine(self):
        transform = camera_viewport_to_world(550, 590, -13, 1.2, 360, 640)
        self.assertEqual((transform.source, transform.target),
                         (Space.VIEWPORT, Space.WORLD))
        center = transform.apply(Point(180, 320))
        self.assertAlmostEqual(center.x, 550)
        self.assertAlmostEqual(center.y, 590)
        cosine, sine = math.cos(math.radians(-13)), math.sin(math.radians(-13))
        self.assertAlmostEqual(transform.a, 1.2 * cosine)
        self.assertAlmostEqual(transform.b, 1.2 * sine)
        self.assertAlmostEqual(transform.c, -1.2 * sine)
        self.assertAlmostEqual(transform.d, 1.2 * cosine)
        self.assertAlmostEqual(transform.e, 550 - 1.2*cosine*180 + 1.2*sine*320)
        self.assertAlmostEqual(transform.f, 590 - 1.2*sine*180 - 1.2*cosine*320)

if __name__=="__main__":
    unittest.main()
