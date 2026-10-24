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


if __name__ == "__main__":
    unittest.main()
