"""Craft policy contracts; rendering quality still needs independent review."""
import copy
import unittest
from reels_maker.creative.professional_direction import (
    calibration_report, plan_issues, recipe_catalog, refine_plan, select_recipe,
)


def source(shots=None, mode="studio"):
    return {"creative_schema_version": 1, "name": "craft-contract", "mode": mode,
            "shots": shots or [{"id": "open", "headline": "CZYTELNY PRZEKAZ", "duration": 4.0}]}


def baseline(spec):
    return [{"id": shot["id"], "layout": "stack-center",
             "typography_motion": "pop-settle"} for shot in spec["shots"]]


class ProfessionalDirectionTests(unittest.TestCase):
    def test_catalog_is_traceable_and_not_self_approved(self):
        catalog = recipe_catalog()
        self.assertEqual(len(catalog["recipes"]), 6)
        for recipe in catalog["recipes"]:
            self.assertEqual(recipe["status"], "experimental")
            self.assertIsNone(recipe["visual_approval"])
            self.assertTrue(all(url.startswith("https://") for url in recipe["source_urls"]))
        catalog["recipes"][0]["invariants"].clear()
        self.assertTrue(recipe_catalog()["recipes"][0]["invariants"])

    def test_auto_photo_and_no_asset_invention(self):
        spec = source([{"id": "photo", "headline": "REALIZACJA", "asset": "a.png"}])
        plan = refine_plan(spec, baseline(spec))
        self.assertEqual(plan[0]["layout"], "split-editorial")
        self.assertNotIn("photo", plan[0]["scene_defaults"])

    def test_coherence_replaces_automatic_effect_rotation(self):
        spec = source([{"id": str(i), "headline": "PRZEKAZ", "intent": "cta"} for i in range(3)])
        plan = refine_plan(spec, baseline(spec))
        self.assertEqual({p["typography_motion"] for p in plan}, {"fade-up"})

    def test_explicit_motion_and_layout_are_preserved(self):
        spec = source([{"id": "a", "headline": "AKCENT", "layout": "full-bleed-type",
                        "typography": {"family": "tracking-in"}}])
        plan = refine_plan(spec, [{"id": "a", "layout": "full-bleed-type",
                                   "typography_motion": "tracking-in"}])
        self.assertEqual(plan[0]["layout"], "full-bleed-type")
        self.assertEqual(plan[0]["typography_motion"], "tracking-in")

    def test_auto_layout_does_not_hide_explicit_composition(self):
        spec = source([{"id": "a", "headline": "TEST", "layout": "auto", "composition": "statement"}])
        self.assertEqual(refine_plan(spec, baseline(spec))[0]["layout"], "statement")

    def test_number_does_not_imply_currency(self):
        self.assertEqual(select_recipe({"value": 42}), "editorial-statement")
        self.assertEqual(select_recipe({"value": 42, "layout": "amount"}), "metric-proof")

    def test_camera_canvas_is_unchanged(self):
        spec = source(mode="camera_canvas")
        self.assertEqual(refine_plan(spec, baseline(spec)), baseline(spec))

    def test_deterministic_without_input_mutation(self):
        spec = source()
        old = copy.deepcopy(spec)
        plan = baseline(spec)
        self.assertEqual(refine_plan(spec, plan), refine_plan(spec, plan))
        self.assertEqual(spec, old)
        self.assertNotIn("craft", plan[0])

    def test_short_hold_is_reported_not_fixed_by_shrinking_type(self):
        spec = source([{"id": "a", "headline": "DŁUGI NAGŁÓWEK " * 8, "duration": .5}])
        plan = refine_plan(spec, baseline(spec))
        self.assertEqual(plan_issues(plan)[0]["code"], "craft_reading_hold_review")
        self.assertEqual(spec["shots"][0]["duration"], .5)
        self.assertNotIn("font_size", plan[0]["scene_defaults"])

    def test_photograph_leads_supporting_copy(self):
        spec = source([{"id": "a", "headline": "REALIZACJA", "asset": "a.png"}])
        cues = refine_plan(spec, baseline(spec))[0]["scene_defaults"]["cues"]
        self.assertLess(cues["visual"], cues["headline"])
        self.assertLess(cues["headline"], cues["body"])

    def test_identity_and_count_mismatch_fail(self):
        with self.assertRaises(ValueError):
            refine_plan(source(), [])
        with self.assertRaises(ValueError):
            refine_plan(source(), [{"id": "wrong"}])

    def test_calibration_is_not_self_certification(self):
        report = calibration_report({"x": "A", "y": "B"}, {"x": "A", "y": "A"})
        self.assertEqual(report["accuracy"], .5)
        self.assertFalse(report["certifies_aesthetic_quality"])

    def test_calibration_rejects_missing_extra_and_invalid_choices(self):
        for expected, predicted in [({}, {}), ({"x": "A"}, {}),
                                    ({"x": "A"}, {"x": "A", "y": "B"}),
                                    ({"x": "A"}, {"x": "C"})]:
            with self.assertRaises(ValueError):
                calibration_report(expected, predicted)


class ProfessionalDirectionIntegrationTests(unittest.TestCase):
    def test_compiler_consumes_real_scene_defaults(self):
        from reels_maker.creative.professional_direction import compile_professional_spec as compile_creative_spec
        spec = source()
        manifest, report = compile_creative_spec(spec, check_assets=False)
        scene = manifest["scenes"][0]
        self.assertEqual(scene["composition"], "statement")
        self.assertEqual(scene["typography_motion"], "fade-up")
        self.assertLess(scene["cues"]["headline"], scene["cues"]["body"])
        self.assertEqual(scene["entrance_presets"]["headline"], "fade-up")
        self.assertEqual(report["craft_decisions"][0]["craft"]["recipe_status"], "experimental")

    def test_source_is_unchanged_and_legacy_entry_point_is_unchanged(self):
        from reels_maker.creative.professional_direction import compile_professional_spec
        from reels_maker.creative.compiler import compile_creative_spec
        spec = source()
        old = copy.deepcopy(spec)
        legacy_before, _ = compile_creative_spec(spec, check_assets=False)
        compile_professional_spec(spec, check_assets=False)
        legacy_after, _ = compile_creative_spec(spec, check_assets=False)
        self.assertEqual(spec, old)
        self.assertEqual(legacy_before, legacy_after)

    def test_existing_builder_receives_choreography(self):
        from reels_maker.creative.professional_direction import compile_professional_spec as compile_creative_spec
        from reels_maker.components.base import SceneContext
        from reels_maker.components.scenes import build_scene
        from reels_maker.design.tokens import resolve_tokens
        from reels_maker.textkit.typesetter import FontBook
        manifest, _ = compile_creative_spec(source(), check_assets=False)
        tokens = resolve_tokens("editorial-premium", width=360, height=640)
        ctx = SceneContext(360, 640, 24, 4.0, tokens, "editorial-premium", FontBook())
        built = build_scene(ctx, manifest["scenes"][0])
        self.assertTrue(built)


if __name__ == "__main__":
    unittest.main()
