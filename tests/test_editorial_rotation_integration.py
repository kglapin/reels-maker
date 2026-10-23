import unittest
from reels_maker.core.scene_graph import Node
from reels_maker.motionkit.editorial_rotation import (
    apply_editorial_rotations, editorial_media_nodes, rotation_track)


class EditorialRotationIntegrationTests(unittest.TestCase):
    def test_rotation_families_have_distinct_trajectories(self):
        tilt=rotation_track({"family":"tilt-settle","angle":-7,"duration":.5},2,role="photo")
        hold=rotation_track({"family":"diagonal-hold","angle":7,"start":.7,"duration":.5},2,role="photo")
        transition=rotation_track({"family":"rotation-to-layout","angle":6,"duration":.5},2,role="headline")
        self.assertAlmostEqual(tilt.value(0),-7)
        self.assertAlmostEqual(tilt.value(.5),0)
        self.assertAlmostEqual(hold.value(0),7)
        self.assertAlmostEqual(transition.value(0),0)
        self.assertAlmostEqual(transition.value(.55),6)

    def test_opposite_rotations_of_photo_and_type(self):
        photo=editorial_media_nodes({"editorial_media":[
            {"asset":"fixture.jpg","x":.08,"y":.1,"w":.8,"h":.6,
             "rotation":{"family":"counter-rotation","angle":-6}}]},540,960,2)[0]
        title=Node(kind="text",role="headline",props={"x":80,"y":750,"w":400,"h":80})
        warnings=apply_editorial_rotations({"headline":title},{
            "headline":{"family":"counter-rotation","angle":5}},2)
        self.assertEqual(warnings,[])
        self.assertLess(photo.sample(0).rotation,0)
        self.assertGreater(title.sample(0).rotation,0)
        self.assertAlmostEqual(photo.sample(1).rotation,0)
        self.assertAlmostEqual(title.sample(1).rotation,0)

    def test_rotating_media_remains_inside_source_geometry(self):
        nodes=editorial_media_nodes({"editorial_media":[
            {"asset":"fixture.jpg","x":.1,"y":.1,"w":.72,"h":.55,
             "rotation":{"angle":6}}]},540,960,2)
        node=nodes[0]
        self.assertEqual(node.kind,"image")
        self.assertEqual(node.props["w"],.72*540)
        self.assertGreater(node.sample(0).rotation,0)

    def test_invalid_rotation_and_media_rejected(self):
        with self.assertRaises(ValueError):
            rotation_track({"angle":90},2,role="photo")
        with self.assertRaises(ValueError):
            editorial_media_nodes({"editorial_media":[
                {"asset":"fixture.jpg","x":.8,"y":.2,"w":.4,"h":.4}]},540,960,2)
        with self.assertRaises(ValueError):
            editorial_media_nodes({"editorial_media":[
                {"asset":"fixture.jpg","x":0,"y":0,"w":1,"h":1,
                 "rotation":{"duration":0}}]},540,960,2)

    def test_missing_typography_role_warns_without_crash(self):
        result=apply_editorial_rotations({},{"headline":{"angle":7}},2)
        self.assertEqual(result[0]["code"],"rotation_missing_role")


if __name__=="__main__":
    unittest.main()
