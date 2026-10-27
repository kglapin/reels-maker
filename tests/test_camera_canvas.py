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
    def test_lazy_stage_matches_full_cumulative_composition(self):
        renderer=CameraCanvasRenderer(self.project())
        self.assertEqual(renderer._active_stage_index,-1)
        for index in range(len(renderer.scenes)):
            expected=renderer._base_world.copy()
            for previous in range(index):
                renderer._paste(expected,renderer.local_typography[previous],
                                renderer.stops[previous])
            actual=renderer._stage_for(index)
            self.assertEqual(expected.size,actual.size)
            self.assertEqual(expected.tobytes(),actual.tobytes())
            # Only one cumulative world is retained, regardless of shot count.
            self.assertIs(actual,renderer._active_stage)
            self.assertEqual(index,renderer._active_stage_index)

        # The pre-refactor renderer selected this materialized stage before
        # camera sampling. Verify that the lazy path reaches identical pixels.
        frame_time=0.0
        old_stage=renderer._base_world.copy()
        renderer._paste(old_stage,renderer.local_typography[0],
                        renderer.stops[0])
        expected=renderer._frame(old_stage,renderer.camera(1,frame_time)).convert("RGB")
        actual=renderer.render(SimpleNamespace(index=1),frame_time)
        self.assertEqual(expected.tobytes(),actual.tobytes())

    def test_lazy_stages_can_seek_back_without_pixel_drift(self):
        renderer=CameraCanvasRenderer(self.project())
        final=renderer._stage_for(1).copy()
        first=renderer._stage_for(0)
        self.assertEqual(renderer._base_world.tobytes(),first.tobytes())
        self.assertEqual(final.tobytes(),renderer._stage_for(1).tobytes())

    def test_stage_storage_does_not_grow_with_shot_count(self):
        scenes=[]
        for index in range(8):
            scenes.append({
                "photo": self.path, "headline": f"SHOT {index}",
                "camera_canvas": {"x": 550 + index * 300, "y": 590,
                                  "layout": "photo-above"},
            })
        renderer=CameraCanvasRenderer(
            SimpleNamespace(width=360,height=640,scenes=scenes))
        for index in range(len(scenes)):
            renderer._stage_for(index)
            self.assertEqual(renderer._active_stage_index,index)
            self.assertIsNotNone(renderer._active_stage)
            self.assertFalse(hasattr(renderer,"stages"))

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
