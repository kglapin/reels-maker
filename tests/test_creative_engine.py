"""Creative Engine acceptance suite: LLM JSON -> compiler -> Studio project."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image

from reels_maker.creative import capabilities, compile_creative_spec
from reels_maker.creative.spec import CreativeSpecError, validate_creative_spec
from reels_maker.creative.edit import CreativeEditError, edit_creative_spec
from reels_maker.creative.quality import audit_creative_spec

class CreativeEngineTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.root=Path(self.folder.name)
        (self.root/"assets").mkdir()
        for i in range(2):
            Image.new("RGB",(850,1000), (40+50*i,90,140)).save(
                self.root/"assets"/f"shot{i+1}.png")
        self.spec={
            "creative_schema_version":1,
            "name":"test-creative-engine",
            "mode":"camera_canvas",
            "style":"editorial-premium",
            "video":{"width":360,"height":640,"fps":24},
            "shots":[
                {"id":"opening","intent":"opening","headline":"FRAMES MOVE",
                 "subtitle":"Designed with purpose","asset":"assets/shot1.png",
                 "duration":2.7},
                {"id":"next","intent":"reveal","headline":"NEW ANGLE",
                 "subtitle":"Camera moves first","asset":"assets/shot2.png",
                 "duration":3.1},
            ],
        }
    def tearDown(self):
        self.folder.cleanup()
    def test_registry_never_advertises_unimplemented_motion(self):
        cap=capabilities()
        self.assertEqual(cap["creative_spec_version"],1)
        self.assertEqual(cap["modes"]["camera_canvas"]["status"],"implemented")
        self.assertIn("mask-rise",cap["modes"]["camera_canvas"]["typography_motions"])
    def test_validate_creative_spec(self):
        report=validate_creative_spec(self.spec)
        self.assertEqual(report["shot_count"],2)
        self.assertEqual(report["mode"],"camera_canvas")
    def test_reject_unknown_animation(self):
        self.spec["shots"][0]["typography"]={"family":"magical-3d"}
        with self.assertRaises(CreativeSpecError):
            validate_creative_spec(self.spec)
    def test_reject_unknown_root_field(self):
        self.spec["random_effect"]=42
        with self.assertRaises(CreativeSpecError):
            validate_creative_spec(self.spec)
    def test_reject_partial_asset(self):
        self.spec["shots"][1].pop("asset")
        with self.assertRaises(CreativeSpecError):
            validate_creative_spec(self.spec)
    def test_reject_path_traversal(self):
        self.spec["shots"][1]["asset"]="../../etc/passwd"
        with self.assertRaises(CreativeSpecError):
            compile_creative_spec(self.spec,source_dir=self.root)
    def test_reject_missing_real_media(self):
        self.spec["shots"][1]["asset"]="assets/missing.png"
        with self.assertRaises(CreativeSpecError):
            compile_creative_spec(self.spec,source_dir=self.root)
    def test_compilation_preserves_assets(self):
        manifest,report=compile_creative_spec(self.spec,source_dir=self.root)
        self.assertEqual(len(manifest["scenes"]),2)
        self.assertIn("camera_canvas",manifest["scenes"][0])
        self.assertTrue(Path(manifest["scenes"][0]["photo"]).is_file())
        self.assertNotEqual(manifest["scenes"][0]["camera_canvas"]["angle"],
                            manifest["scenes"][1]["camera_canvas"]["angle"])
        self.assertTrue(report["ok"])
    def test_deterministic_compile(self):
        a,_=compile_creative_spec(self.spec,source_dir=self.root)
        b,_=compile_creative_spec(self.spec,source_dir=self.root)
        self.assertEqual(json.dumps(a,sort_keys=True),json.dumps(b,sort_keys=True))
    def test_quality_reading_hold(self):
        self.spec["shots"][1]["duration"]=1
        manifest,_=compile_creative_spec(self.spec,source_dir=self.root)
        report=audit_creative_spec(self.spec,manifest)
        self.assertFalse(report["ok"])
        self.assertIn("insufficient_reading_hold",[v["code"] for v in report["issues"]])
    def test_quality_standard_clip(self):
        manifest,_=compile_creative_spec(self.spec,source_dir=self.root)
        report=audit_creative_spec(self.spec,manifest)
        self.assertTrue(report["ok"],report)
    def test_intent_driven_motion_family_variety(self):
        _,report=compile_creative_spec(self.spec,source_dir=self.root)
        effects=[x["typography_motion"] for x in report["decisions"]]
        self.assertEqual(len(set(effects)),2)
    def test_camera_override_and_layout(self):
        self.spec["shots"][1]["camera"]={"x":1300,"y":1550,"angle":113,"zoom":1.13}
        self.spec["shots"][1]["layout"]="diagonal"
        manifest,_=compile_creative_spec(self.spec,source_dir=self.root)
        camera=manifest["scenes"][1]["camera_canvas"]
        self.assertEqual(camera["angle"],113)
        self.assertEqual(camera["layout"],"diagonal")
    def test_atomic_edit_by_scene_id(self):
        original=copy.deepcopy(self.spec)
        edited,report=edit_creative_spec(self.spec,[
            {"op":"replace","path":"/shots/@next/headline","value":"A NEW WORLD"},
            {"op":"add","path":"/shots/@next/camera","value":{"angle":116}}
        ])
        self.assertEqual(edited["shots"][1]["headline"],"A NEW WORLD")
        self.assertEqual(self.spec,original)
        self.assertEqual(len(report["applied"]),2)
    def test_invalid_edit_does_not_mutate(self):
        original=copy.deepcopy(self.spec)
        with self.assertRaises(CreativeEditError):
            edit_creative_spec(self.spec,[{"op":"replace","path":"/shots/@next/duration","value":-3}])
        self.assertEqual(self.spec,original)
    def test_protect_renderer_paths_from_edit(self):
        with self.assertRaises(CreativeEditError):
            edit_creative_spec(self.spec,[{"op":"add","path":"/__import__/os","value":"bad"}])
    def test_studio_variant_compiles_explicit_animation(self):
        self.spec["mode"]="studio"
        self.spec["shots"][0]["typography"]={"family":"mask-rise"}
        manifest,_=compile_creative_spec(self.spec,source_dir=self.root)
        self.assertNotIn("camera_canvas",manifest["scenes"][0])
        self.assertEqual(manifest["scenes"][0]["typography_motion"],"mask-rise")
    def test_studio_rejects_camera_settings(self):
        self.spec["mode"]="studio"
        self.spec["shots"][0]["camera"]={"angle":15}
        with self.assertRaises(CreativeSpecError):
            validate_creative_spec(self.spec)

if __name__=="__main__":
    unittest.main()
