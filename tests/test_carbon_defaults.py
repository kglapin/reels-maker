"""Default policy unit tests and native Studio project integration."""
import copy
import unittest
from reels_maker.design.carbon_defaults import prepare_scenes, sequence_scene, spacing_values, SPACING_PX


class CarbonDefaultPolicyTests(unittest.TestCase):
    def test_normal_studio_scene_defaults_to_productive(self):
        source=[{"id":"a","headline":"TEST","duration":3}]
        old=copy.deepcopy(source)
        result=prepare_scenes(source,{},30)
        self.assertEqual(result[0]["carbon_motion"],{"mode":"productive"})
        self.assertEqual(source,old)
        self.assertNotIn("cues",result[0])

    def test_project_mode_and_explicit_scene_precedence(self):
        source=[{"id":"a"},{"id":"b","carbon_motion":{"mode":"expressive"}}]
        result=prepare_scenes(source,{"carbon_motion":False},30)
        self.assertIsNone(result[0]["carbon_motion"])
        self.assertEqual(result[1]["carbon_motion"]["mode"],"expressive")
        for off in (False,None):
            self.assertIsNone(prepare_scenes([{"carbon_motion":off}],{},30)[0]["carbon_motion"])

    def test_camera_canvas_is_not_implicitly_migrated(self):
        scene={"camera_canvas":{"x":200,"y":300}}
        self.assertIsNone(prepare_scenes([scene],{},30)[0]["carbon_motion"])

    def test_invalid_project_policies_fail(self):
        for value in ("carbon",123,{"mode":"bad"},{"unknown":True}):
            with self.assertRaises(ValueError):
                prepare_scenes([{}],{"carbon_motion":value},30)

    def test_spacing_source_and_video_mapping(self):
        self.assertEqual(len(SPACING_PX),13)
        self.assertEqual(SPACING_PX["spacing-13"],160)
        self.assertEqual(spacing_values(False),{})
        self.assertEqual(spacing_values(True),{"xs":8,"sm":16,"md":32,"lg":48,"xl":64,"xxl":96})
        self.assertEqual(spacing_values({"md":"spacing-06"})["md"],24)
        for bad in (123,{"unknown":"spacing-01"},{"md":"missing"}):
            with self.assertRaises(ValueError): spacing_values(bad)

    def test_sequencing_is_frame_aligned_and_bounded(self):
        scene={"headline":"T","subtitle":"B","kicker":"K","duration":3}
        for fps in (24,30,60):
            result=sequence_scene(scene,True,fps)
            values=list(result["cues"].values())
            self.assertLessEqual(max(values),.5)
            self.assertEqual(values,sorted(values))
            for t in values:self.assertAlmostEqual(t*fps,round(t*fps))
        self.assertNotIn("cues",scene)

    def test_verified_or_authored_cues_are_never_replaced(self):
        scene={"headline":"T","subtitle":"B","duration":4,"cues":{"headline":1.25}}
        self.assertEqual(sequence_scene(scene,True,30),scene)
        result=prepare_scenes([scene],{"carbon_sequence":True},30)
        self.assertEqual(result[0]["cues"],scene["cues"])

    def test_scene_disable_survives_repeated_project_normalization(self):
        source=[{"headline":"T","subtitle":"B","duration":4,"carbon_sequence":False}]
        first=prepare_scenes(source,{"carbon_sequence":True},30)
        second=prepare_scenes(first,{"carbon_sequence":True},30)
        self.assertEqual(first,second)
        self.assertNotIn("cues",second[0])

    def test_native_amount_type_takes_precedence_over_generic_composition(self):
        scene={"type":"amount","composition":"statement","value":42,"duration":3}
        result=sequence_scene(scene,True,30)
        self.assertIn("amount",result["cues"])
        self.assertNotIn("headline",result["cues"])

    def test_sequence_rejects_invalid_or_unrenderable_configuration(self):
        scene={"headline":"T","duration":.01}
        bad=[{"roles":["a","a"]},{"roles":["a","b"],"span":.01},
             {"gap":float("nan")},{"unknown":1}]
        for config in bad:
            with self.assertRaises(ValueError): sequence_scene(scene,config,30)


class CarbonDefaultIntegrationTests(unittest.TestCase):
    def project(self,export=None):
        from pathlib import Path
        from reels_maker.studio_project import StudioProject
        from reels_maker.design.tokens import resolve_tokens
        from reels_maker.textkit.typesetter import FontBook
        root=Path.cwd()
        return StudioProject(path=root/"synthetic-carbon.json",root=root,name="carbon-default",
            width=360,height=640,fps=30,style="editorial-premium",
            scenes=[{"composition":"statement","headline":"CARBON","duration":4}],
            brand=None,brand_data={},audio={},export=export or {},
            tokens=resolve_tokens("editorial-premium",width=360,height=640),
            fonts=FontBook(),asset_manager=None)

    def test_standard_project_build_uses_carbon_without_special_cli(self):
        project=self.project()
        built=project.build()
        self.assertEqual(project.scenes[0]["carbon_motion"]["mode"],"productive")
        self.assertTrue(built[0].meta["carbon_motion"]["applied"])

    def test_disabled_profile_retains_legacy_motion(self):
        project=self.project({"carbon_motion":False})
        self.assertIsNone(project.scenes[0]["carbon_motion"])
        self.assertNotIn("carbon_motion",project.build()[0].meta)

    def test_spacing_preserves_brand_typography_and_safe_area(self):
        base=self.project()
        styled=self.project({"carbon_spacing":True})
        self.assertEqual(base.tokens.palette,styled.tokens.palette)
        self.assertEqual(base.tokens.typography,styled.tokens.typography)
        self.assertEqual(base.tokens.safe,styled.tokens.safe)
        self.assertEqual(styled.tokens.spacing.md,32)
        self.assertEqual(styled.tokens.space("md"),round(32*styled.tokens.scale))


if __name__=="__main__":
    unittest.main()
