import unittest
from reels_maker.core.scene_graph import Node
from reels_maker.motionkit.editorial_rotation import (
    rotation_track, apply_editorial_rotations, editorial_media_nodes)

class EditorialRotationTests(unittest.TestCase):
    def test_photo_tilt_settle(self):
        track = rotation_track({"family":"tilt-settle","angle":-7,
                               "duration":.6}, 2.0, role="photo")
        self.assertAlmostEqual(track.value(0),-7)
        self.assertAlmostEqual(track.value(.8),0)

    def test_counter_rotation_independent(self):
        photo=Node(kind="image",props={"x":10,"y":20,"w":200,"h":300})
        title=Node(kind="text",props={"x":20,"y":40,"w":200,"h":80})
        warnings=apply_editorial_rotations({"headline":title,"photo":photo},{
            "headline":{"family":"counter-rotation","angle":5},
            "photo":{"family":"counter-rotation","angle":-7},
        },2.0)
        self.assertFalse(warnings)
        self.assertGreater(title.sample(0).rotation,0)
        self.assertLess(photo.sample(0).rotation,0)

    def test_diagonal_hold(self):
        track=rotation_track({"family":"diagonal-hold","angle":-5,
                              "start":1,"duration":.8,"settle_angle":-5},3,role="photo")
        self.assertAlmostEqual(track.value(.7),-5)
        self.assertAlmostEqual(track.value(2),-5)

    def test_frame_geometry_and_rotated_bounds(self):
        scene={"editorial_media":[{"asset":"/tmp/source.png",
            "x":.12,"y":.24,"w":.74,"h":.42,
            "rotation":{"family":"tilt-settle","angle":9}}]}
        nodes=editorial_media_nodes(scene,540,960,2.0)
        self.assertEqual(len(nodes),1)
        n=nodes[0]
        self.assertAlmostEqual(n.props["x"],64.8)
        before=n.sample(0).world_bounds()
        after=n.sample(.9).world_bounds()
        self.assertNotEqual(before,after)

    def test_invalid_angles_and_overflow_rejected(self):
        with self.assertRaises(ValueError):
            rotation_track({"angle":float("nan")},2,role="photo")
        with self.assertRaises(ValueError):
            editorial_media_nodes({"editorial_media":[{
                "asset":"x.png","x":.8,"w":.5}]},540,960,2)

    def test_warning_for_missing_role(self):
        self.assertEqual(
            apply_editorial_rotations({},{"headline":{"angle":3}},2)[0]["code"],
            "rotation_missing_role")

    def test_rotation_to_layout(self):
        t=rotation_track({"family":"rotation-to-layout",
                          "angle":-9,"settle_angle":0},2,role="photo")
        self.assertEqual(t.value(0),0)
        self.assertAlmostEqual(t.value(2),-9)

if __name__=="__main__":
    unittest.main()
