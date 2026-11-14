"""Creative Engine acceptance suite: LLM JSON -> compiler -> Studio project."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image

from reels_maker.creative import CapabilityRegistry, capabilities, compile_creative_spec
from reels_maker.creative.schema import creative_json_schema
from reels_maker.creative.spec import CreativeSpecError, validate_creative_spec
from reels_maker.creative.edit import CreativeEditError, edit_creative_spec
from reels_maker.creative.quality import audit_creative_spec
from reels_maker.creative.pipeline_core import creative_intent, plan_motion, render_graph

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
        self.assertEqual(cap["schema_version"],2)
        self.assertEqual(cap["creative_spec_version"],1)
        self.assertEqual(cap["modes"]["camera_canvas"]["status"],"implemented")
        self.assertIn("mask-rise",cap["modes"]["camera_canvas"]["typography_motions"])
        self.assertEqual(cap["modes"]["studio"]["scene_controls"],
                         ["split_lines", "cues", "perspective", "graphic_elements"])

    def test_registry_reports_provider_icon_and_feature_status_truthfully(self):
        cap=CapabilityRegistry().describe()
        stock={p["name"]:p for p in cap["providers"]["stock_media"]}
        self.assertEqual(set(stock),{"pexels","unsplash","pixabay",
                                     "wikimedia_commons","openverse"})
        self.assertTrue(all(p["status"] in ("implemented", "partial") for p in stock.values()))
        self.assertEqual(stock["openverse"]["status"], "partial")
        self.assertIn("OPENVERSE_ACCESS_TOKEN", stock["openverse"]["authentication"])
        self.assertEqual(stock["pexels"]["media"],["image","video"])
        self.assertEqual(stock["pixabay"]["media"],["image","video"])
        self.assertEqual(stock["pixabay"]["local_rate_limit"],
                         {"requests":100,"window_seconds":60,"scope":"process"})
        self.assertEqual(stock["pixabay"]["search_cache_ttl_seconds"],86400)
        self.assertEqual(stock["openverse"]["status"],"partial")
        self.assertIn("OPENVERSE_ACCESS_TOKEN",stock["openverse"]["authentication"])
        audio=cap["providers"]["audio"]
        self.assertEqual(audio[0]["status"],"partial")
        self.assertIn("quarantine",audio[0]["workflow"])
        commons_audio = next(item for item in audio if item["name"] == "wikimedia_commons")
        self.assertEqual(commons_audio["status"], "implemented")
        self.assertEqual({p["name"] for p in cap["icon_packs"]},
                         {"lucide","heroicons","tabler","phosphor","material_symbols"})
        self.assertTrue(all(p["license"]["url"] for p in cap["icon_packs"]))
        self.assertTrue(all(p["item_level_rights_review_required"] for p in cap["icon_packs"]))
        self.assertTrue(next(p for p in cap["icon_packs"]
                             if p["name"] == "material_symbols")["material_symbol_variants"])
        flags=cap["feature_flags"]
        self.assertEqual(flags["typed_creative_pipeline_v1"]["status"], "implemented")
        self.assertEqual(flags["stock_video_search"]["status"],"implemented")
        self.assertEqual(flags["vector_line_chart"]["status"], "partial")
        self.assertEqual(flags["data_visualization"]["status"], "partial")
        self.assertTrue(any("Typed LoadedData bridges" in item
                            for item in flags["data_visualization"]["limitations"]))
        self.assertEqual(flags["licensed_asset_download"]["status"],"partial")
        self.assertTrue(any("media-search and media-download" in item
                            for item in flags["licensed_asset_download"]["limitations"]))
        self.assertEqual(flags["semantic_icon_suggestions"]["status"],"implemented")
        self.assertEqual(flags["procedural_sfx_generation"]["status"],"partial")
        procedural = next(item for item in cap["providers"]["audio"]
                          if item["name"] == "reels-maker-procedural")
        self.assertEqual(procedural["status"], "partial")
        self.assertEqual(flags["audio_beat_sync"]["status"],"unsupported")
        self.assertEqual(flags["semantic_photo_sourcing"]["status"],"unsupported")
    def test_validate_creative_spec(self):
        report=validate_creative_spec(self.spec)
        self.assertEqual(report["shot_count"],2)
        self.assertEqual(report["mode"],"camera_canvas")

    def test_graphic_elements_json_schema_matches_bounded_scene_contract(self):
        schema = creative_json_schema()
        shot = schema["properties"]["shots"]["items"]
        elements = shot["properties"]["graphic_elements"]
        self.assertEqual(elements["type"], "array")
        self.assertEqual((elements["minItems"], elements["maxItems"]), (1, 12))
        item = elements["items"]
        self.assertFalse(item["additionalProperties"])
        self.assertEqual(item["required"], ["id", "type"])
        props = item["properties"]
        self.assertEqual(props["type"]["enum"],
                         ["rect", "round", "circle", "ring", "line", "path"])
        self.assertEqual((props["x"]["minimum"], props["x"]["maximum"]), (0, 1))
        self.assertEqual((props["w"]["exclusiveMinimum"], props["w"]["maximum"]), (0, 1))
        self.assertEqual((props["stroke_width"]["minimum"],
                          props["stroke_width"]["maximum"]), (0.001, 0.05))
        points = props["points"]
        self.assertEqual((points["minItems"], points["maxItems"]), (2, 32))
        self.assertEqual(points["items"]["items"]["minimum"], 0)
        self.assertEqual(points["items"]["items"]["maximum"], 1)
        self.assertFalse(props["enter"]["additionalProperties"])
        self.assertFalse(props["draw"]["additionalProperties"])
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

    def test_authored_motion_decisions_survive_pipeline_without_heuristic_rewrite(self):
        self.spec["mode"] = "studio"
        authored = [
            {"id": "opening", "layout": "statement", "typography_motion": "tracking-in",
             "layout_reason": "Open on one deliberate typographic gesture.",
             "entrance_presets": {"body": "none"}},
            {"id": "next", "layout": "split-editorial", "typography_motion": "mask-rise",
             "layout_reason": "Reveal the supporting idea after the opening."},
        ]
        intent = creative_intent(self.spec)
        plan = plan_motion(intent, authored, decision_source="llm")
        graph = render_graph(intent, plan, source_dir=self.root, check_assets=False)
        self.assertEqual(graph.report["decision_source"], "llm")
        self.assertEqual(
            [scene["composition"] for scene in graph.to_renderer_input()["scenes"]],
            ["statement", "split-editorial"],
        )
        self.assertEqual(
            [scene["typography_motion"] for scene in graph.to_renderer_input()["scenes"]],
            ["tracking-in", "mask-rise"],
        )
        self.assertEqual(
            graph.to_renderer_input()["scenes"][0]["entrance_presets"],
            {"body": "none"},
        )

    def test_authored_motion_plan_rejects_unsupported_capability(self):
        self.spec["mode"] = "studio"
        intent = creative_intent(self.spec)
        authored = [
            {"id": shot["id"], "layout": "statement", "typography_motion": "invented-3d"}
            for shot in self.spec["shots"]
        ]
        with self.assertRaises(CreativeSpecError):
            plan_motion(intent, authored, decision_source="llm")

    def test_studio_scene_choreography_camera_and_split_type_survive_compile(self):
        self.spec["mode"] = "studio"
        first = self.spec["shots"][0]
        first.update({
            "composition": "quote",
            "split_lines": ["headline", "body"],
            "cues": {"headline": 0.12, "body": 0.48, "quote-mark": 0.0},
            "perspective": {"mode": "settle", "yaw": -7.0,
                            "pitch": 2.0, "zoom": 1.04,
                            "duration": 1.1, "delay": 0.1},
            "graphic_elements": [{
                "id": "orbit", "type": "ring", "cx": 0.5, "cy": 0.55,
                "r": 0.12, "color": "accent", "stroke_width": 0.005,
                "draw": {"delay": 0.2, "duration": 0.8},
                "enter": {"preset": "fade-up", "delay": 0.1, "duration": 0.4},
            }],
        })
        decisions = [
            {"id": shot["id"], "layout": shot.get("composition", "statement"),
             "typography_motion": "mask-rise"}
            for shot in self.spec["shots"]
        ]
        manifest, _ = compile_creative_spec(
            self.spec, source_dir=self.root, decisions=decisions,
            decision_source="llm")
        scene = manifest["scenes"][0]
        self.assertEqual(scene["split_lines"], ["headline", "body"])
        self.assertEqual(scene["cues"], first["cues"])
        self.assertEqual(scene["perspective"], first["perspective"])
        self.assertEqual(scene["graphic_elements"], first["graphic_elements"])

    def test_graphic_elements_validation_rejects_unsafe_geometry_and_timing(self):
        self.spec["mode"] = "studio"
        valid = {
            "id": "marker", "type": "rect", "x": 0.2, "y": 0.2,
            "w": 0.2, "h": 0.1, "fill": "accent",
        }
        invalid_elements = [
            [valid, {**valid}],
            [{**valid, "fill": "url(https://example.invalid/image.svg)"}],
            [{"id": "edge", "type": "line", "x1": 0.001, "y1": 0.2,
              "x2": 0.8, "y2": 0.7, "color": "ink", "stroke_width": 0.05}],
            [{"id": "late", "type": "path", "points": [[0.2, 0.2], [0.8, 0.8]],
              "color": "ink", "stroke_width": 0.005,
              "draw": {"delay": 2.6, "duration": 0.2}}],
        ]
        for elements in invalid_elements:
            with self.subTest(elements=elements):
                candidate = copy.deepcopy(self.spec)
                candidate["shots"][0]["graphic_elements"] = elements
                with self.assertRaises(CreativeSpecError):
                    validate_creative_spec(candidate)

    def test_scene_program_rejects_stale_cue_and_overlong_camera_path(self):
        self.spec["mode"] = "studio"
        shot = self.spec["shots"][0]
        shot["cues"] = {"visual": 0.3}
        with self.assertRaises(CreativeSpecError):
            validate_creative_spec(self.spec)
        shot.pop("cues")
        shot["perspective"] = {
            "path": [{"t": 0.0}, {"t": 2.8}],
            "duration": 1.0,
        }
        with self.assertRaises(CreativeSpecError):
            validate_creative_spec(self.spec)

    def test_authored_per_element_presets_reject_unsupported_motion(self):
        self.spec["mode"] = "studio"
        authored = [
            {"id": shot["id"], "layout": "statement",
             "typography_motion": "fade-up",
             "entrance_presets": {"body": "teleport"}}
            for shot in self.spec["shots"]
        ]
        with self.assertRaises(CreativeSpecError):
            plan_motion(creative_intent(self.spec), authored, decision_source="llm")

    def test_camera_canvas_rejects_studio_only_per_element_presets(self):
        authored = [
            {"id": shot["id"], "layout": "photo-above",
             "typography_motion": "fade",
             "entrance_presets": {"headline": "none"}}
            for shot in self.spec["shots"]
        ]
        with self.assertRaises(CreativeSpecError):
            plan_motion(creative_intent(self.spec), authored, decision_source="llm")

if __name__=="__main__":
    unittest.main()
