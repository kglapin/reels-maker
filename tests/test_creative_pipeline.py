"""Focused contract tests for the additive typed creative stages."""
import unittest

from reels_maker.creative import (
    CreativeSpecError, compile_creative_spec, creative_intent, plan_motion,
    render_graph,
)


def spec(name="pipeline-contract"):
    return {
        "creative_schema_version": 1,
        "name": name,
        "mode": "studio",
        "shots": [
            {"id": "open", "intent": "opening", "headline": "A clear start",
             "duration": 2.5, "layout": "statement"},
            {"id": "close", "intent": "finale", "headline": "A clear finish",
             "duration": 3.0, "layout": "stack-center"},
        ],
    }


class CreativePipelineTests(unittest.TestCase):
    def test_intent_rejects_missing_and_ambiguous_data(self):
        invalid = spec()
        invalid["shots"][0].pop("headline")
        with self.assertRaises(CreativeSpecError):
            creative_intent(invalid)
        invalid = spec()
        invalid["shots"][0]["camera"] = {"angle": 10}
        with self.assertRaises(CreativeSpecError):
            creative_intent(invalid)

    def test_stages_are_deterministic_and_snapshot_inputs(self):
        source = spec()
        intent = creative_intent(source)
        source["shots"][0]["headline"] = "mutated"
        self.assertEqual(intent.spec["shots"][0]["headline"], "A clear start")

        first_plan = plan_motion(intent)
        second_plan = plan_motion(intent)
        self.assertEqual(first_plan, second_plan)
        first = render_graph(intent, first_plan, check_assets=False)
        second = render_graph(intent, second_plan, check_assets=False)
        self.assertEqual(first, second)
        self.assertEqual([node.start for node in first.scenes], [0.0, 2.5])
        self.assertEqual(first.backend, "studio_manifest_v1")

    def test_graph_renderer_input_has_exact_v1_compiler_parity(self):
        source = spec()
        intent = creative_intent(source)
        graph = render_graph(intent, plan_motion(intent), check_assets=False)
        manifest, report = compile_creative_spec(source, check_assets=False)
        self.assertEqual(graph.to_renderer_input(), manifest)
        self.assertEqual(graph.report, report)

    def test_motion_plan_cannot_be_reused_for_another_intent(self):
        first = creative_intent(spec())
        plan = plan_motion(first)
        other = creative_intent(spec("different"))
        with self.assertRaises(CreativeSpecError):
            render_graph(other, plan, check_assets=False)

    def test_camera_canvas_remains_explicit_existing_backend(self):
        source = spec()
        source["mode"] = "camera_canvas"
        for shot in source["shots"]:
            shot["asset"] = "assets/local-photo.jpg"
            shot["layout"] = "auto"
        intent = creative_intent(source)
        graph = render_graph(intent, plan_motion(intent), check_assets=False)
        self.assertEqual(graph.backend, "camera_canvas_manifest_v1")
        self.assertTrue(all("camera_canvas" in node.payload for node in graph.scenes))

    def test_explicit_line_chart_data_compiles_through_typed_pipeline(self):
        source = spec()
        shot = source["shots"][0]
        shot["layout"] = "line-chart"
        shot["chart"] = {
            "points": [{"label": "2026-01-01", "value": 15},
                       {"label": "2026-01-03", "value": 42}],
            "x_axis_type": "date", "x_axis_label": "Day",
            "y_axis_label": "Energy (kWh)", "y_domain": [0, 50],
        }
        intent = creative_intent(source)
        graph = render_graph(intent, plan_motion(intent), check_assets=False)
        scene = graph.to_renderer_input()["scenes"][0]
        self.assertEqual(scene["composition"], "line-chart")
        self.assertEqual(scene["points"], shot["chart"]["points"])
        self.assertEqual(scene["y_domain"], [0, 50])

    def test_line_chart_data_is_rejected_when_semantics_are_incomplete(self):
        source = spec()
        source["shots"][0]["layout"] = "line-chart"
        source["shots"][0]["chart"] = {
            "points": [{"label":"2026-02-01","value":1},
                       {"label":"2026-01-01","value":2}],
            "x_axis_type":"date", "x_axis_label":"Period",
            "y_axis_label":"Output (kWh)", "y_domain":[0,3],
        }
        with self.assertRaisesRegex(CreativeSpecError, "strictly increasing"):
            creative_intent(source)
        source["shots"][0]["chart"]["points"].reverse()
        del source["shots"][0]["chart"]["y_domain"]
        with self.assertRaisesRegex(CreativeSpecError, "y_domain"):
            creative_intent(source)

    def test_f5_director_revisions_and_f6_contracts(self):
        import copy
        import tempfile
        from pathlib import Path
        from PIL import Image
        from reels_maker.audiokit.cues import plan_audio_dramaturgy, plan_beat_cue_mix
        from reels_maker.components.base import SceneContext
        from reels_maker.components.scenes import build_scene
        from reels_maker.creative.director import (
            PreferenceLibrary, generate_and_select_storyboard,
            match_reference_rhythm, rank_video_sources,
        )
        from reels_maker.creative.edit import apply_natural_language_revision
        from reels_maker.creative.pipeline import (
            build_review_portal_bundle, composite_depth_layers,
            execute_render_farm_batch, plan_render_farm_batch,
            render_3d_product_frame, validate_3d_product_scene,
            validate_depth_composite, write_review_portal_html,
            write_scene_graph_inspector_html,
        )
        from reels_maker.design.tokens import resolve_tokens
        from reels_maker.studio import StudioProject
        from reels_maker.textkit.typesetter import FontBook

        # MD-505, MD-506, MD-507, MD-508 (with real rendered contact sheets), MD-509, MD-510
        rhythm = match_reference_rhythm([3.2, 2.7, 3.5])
        self.assertTrue(rhythm["has_pacing_contrast"])
        ranked = rank_video_sources([
            {"id": "promo", "editorial_state": "finished_promo", "duration": 5.0, "width": 1080, "height": 1920},
            {"id": "clean-hd", "editorial_state": "clean_source", "duration": 5.0, "width": 1080, "height": 1920, "fps": 30},
        ])
        self.assertEqual([r["id"] for r in ranked], ["clean-hd"])

        dram = plan_audio_dramaturgy([2.5, 2.5, 2.5, 2.5, 2.5])
        self.assertFalse(dram["over_synchronized"])
        mix_plan = plan_beat_cue_mix([3.0, 3.0], bpm=120.0, voiceover_segments=[(0.5, 2.5)])
        self.assertTrue(mix_plan["buses"]["music"]["sidechain_ducked"])

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sb = generate_and_select_storyboard(spec(), output_dir=str(root / "storyboards"))
            self.assertEqual(len(sb["candidates"]), 3)
            for cand in sb["candidates"]:
                self.assertEqual(cand["rendered_frames_measured"], 2)
                self.assertGreater(cand["pixel_contrast_score"], 0.0)
                self.assertTrue(Path(cand["contact_sheet"]).is_file())

            # MD-601: real 3D mesh perspective + 3-point lighting renderer
            obj_file = root / "cube.obj"
            obj_file.write_text(
                "v -0.6 -0.8 -0.4\nv 0.6 -0.8 -0.4\nv 0.6 0.8 -0.4\nv -0.6 0.8 -0.4\n"
                "v -0.6 -0.8 0.4\nv 0.6 -0.8 0.4\nv 0.6 0.8 0.4\nv -0.6 0.8 0.4\n"
                "f 5 6 7 8\nf 2 1 4 3\nf 6 2 3 7\nf 1 5 8 4\n",
                encoding="utf-8",
            )
            spec_3d = {
                "mesh_path": str(obj_file),
                "camera": {"focal_length_mm": 50.0, "turntable_deg_per_s": 45.0},
                "lighting": {"key_light": {}, "fill_light": {}, "rim_light": {}},
            }
            f3d_0 = render_3d_product_frame(spec_3d, 200, 200, time=0.0)
            f3d_1 = render_3d_product_frame(spec_3d, 200, 200, time=0.8)
            self.assertIsNotNone(f3d_0.getbbox())
            self.assertNotEqual(f3d_0.tobytes(), f3d_1.tobytes())

            # MD-602: real depth-map compositor
            fg = Image.new("RGBA", (120, 120), (40, 200, 80, 255))
            bg = Image.new("RGBA", (120, 120), (20, 30, 50, 255))
            dmap = Image.new("L", (120, 120), 220)
            badge = Image.new("RGBA", (30, 30), (255, 200, 0, 255))
            comp_depth = composite_depth_layers(fg, bg, dmap, tracked_badge=badge)
            self.assertEqual(comp_depth.size, (120, 120))

            # MD-603 & MD-604: interactive HTML5/SVG apps
            tokens = resolve_tokens("editorial-premium", width=360, height=640)
            fonts = FontBook()
            ctx = SceneContext(360, 640, 15, 1.5, tokens, "editorial-premium", fonts)
            built_3d = build_scene(ctx, {"type": "product_3d", "duration": 1.5, "headline": "INWERTER 3D", "product_3d": spec_3d})
            html_ins = write_scene_graph_inspector_html([built_3d], root / "inspector.html")
            self.assertIn("motion-viewport", Path(html_ins["output_html"]).read_text(encoding="utf-8"))

            portal = build_review_portal_bundle(
                "asta-demo",
                renders={"v1": "renders/v1.mp4", "v2": "renders/v2.mp4"},
                comments=[{"shot": 1, "timecode_s": 1.2, "text": "Approved", "resolved": True}],
                release_version="2.0.0-rc1",
            )
            html_rev = write_review_portal_html(portal, root / "portal.html")
            self.assertIn("ab-slider", Path(html_rev["output_html"]).read_text(encoding="utf-8"))

            # MD-605: execute_render_farm_batch with shared segment cache
            p1 = StudioProject(
                path=root / "j1.json", root=root, name="job-1",
                width=360, height=640, fps=15, style="editorial-premium",
                scenes=[{"headline": "WSPÓLNY KADR", "duration": 1.2}],
                brand="asta", brand_data={}, audio={},
                export={"codec": "libx264", "crf": 26, "preset": "ultrafast"},
                tokens=tokens, fonts=fonts, asset_manager=None,
            )
            p2 = StudioProject(
                path=root / "j2.json", root=root, name="job-2",
                width=360, height=640, fps=15, style="editorial-premium",
                scenes=[{"headline": "WSPÓLNY KADR", "duration": 1.2}],
                brand="asta", brand_data={}, audio={},
                export={"codec": "libx264", "crf": 26, "preset": "ultrafast"},
                tokens=tokens, fonts=fonts, asset_manager=None,
            )
            batch_res = execute_render_farm_batch([p1, p2], root / "farm", budget_usd=2.0)
            self.assertTrue(batch_res["ok"])
            self.assertEqual(batch_res["completed_jobs"][1]["cache_hits"], 1)

        prefs = PreferenceLibrary()
        with self.assertRaisesRegex(ValueError, "unlicensed"):
            prefs.record(
                reference_id="ref-1", intent="opening", preferred_layout="statement",
                preferred_motion="mask-rise", reviewer="op", license_name="",
                rights_authorized=False,
            )
        prefs.record(
            reference_id="ref-1", intent="opening", preferred_layout="statement",
            preferred_motion="mask-rise", reviewer="op", license_name="CC0-1.0",
            rights_authorized=True,
        )
        self.assertEqual(prefs.recommend("opening")["preferred_layout"], "statement")

        revised, rev_rep = apply_natural_language_revision(
            spec(), "set duration of shot open to 3.4s"
        )
        self.assertEqual(revised["shots"][0]["duration"], 3.4)
        self.assertEqual(rev_rep["cache_preserved_shot_ids"], ["close"])
        self.assertEqual(rev_rep["cache_invalidated_shot_ids"], ["open"])

        with self.assertRaisesRegex(ValueError, "planar"):
            validate_3d_product_scene({"simulated_planar_rotation": True})
        ok_depth = validate_depth_composite({
            "depth_model": "depth-anything-v2-Metric-Indoor",
            "depth_map_sha256": "a" * 64,
            "occlusion_mask": "masks/fg.png",
        })
        self.assertTrue(ok_depth["ok"])


if __name__ == "__main__":
    unittest.main()
