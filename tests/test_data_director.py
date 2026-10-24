import unittest
from decimal import Decimal

from reels_maker.data_director import recommend_visualizations
from reels_maker.data_sources import ColumnSpec, DataSchema, LoadedData, RightsProvenance


RIGHTS = RightsProvenance("Synthetic fixture", "test", "synthetic", "generated for tests", True)


def sample_data():
    schema = DataSchema((
        ColumnSpec("month", "date", "none", "reject"),
        ColumnSpec("region", "string", "none", "reject"),
        ColumnSpec("value", "decimal", "widgets", "reject", currency="none"),
        ColumnSpec("other", "integer", "none", "reject"),
    ), "en_US", "none")
    return LoadedData((
        {"month": __import__("datetime").date(2026, 1, 1), "region": "North", "value": Decimal("2"), "other": 3},
        {"month": __import__("datetime").date(2026, 2, 1), "region": "South", "value": Decimal("4"), "other": 5},
    ), schema, "synthetic.json", "a" * 64, RIGHTS)


class DataDirectorTests(unittest.TestCase):
    def test_time_question_returns_explainable_plan_with_declared_fields(self):
        plan = recommend_visualizations(
            sample_data(), question="How did value change by month?", intent="change_over_time")
        self.assertEqual([v.family for v in plan.variants], ["line", "bar"])
        self.assertEqual((plan.row_count, plan.column_count, plan.series_count), (2, 4, 2))
        self.assertEqual(plan.variants[0].required_axes, ("month", "value"))
        self.assertIn("month", plan.variants[0].required_labels)
        self.assertIn("value (widgets)", plan.variants[0].required_labels)
        self.assertTrue(plan.planning_only)
        self.assertEqual(plan.variants[0].renderer_status, "partial")
        self.assertIn("axis labels and y-domain", plan.variants[0].missing_fields[-1])
        self.assertTrue(all(v.planning_only for v in plan.variants))
        self.assertEqual(plan.source_sha256, "a" * 64)

    def test_question_and_intent_are_mandatory_and_variants_bounded(self):
        for question, intent, count in (("", "exact_lookup", 2), ("Q?", "unknown", 2), ("Q?", [], 2), ("Q?", "exact_lookup", 4)):
            with self.assertRaises(ValueError):
                recommend_visualizations(sample_data(), question=question, intent=intent, max_variants=count)
        plan = recommend_visualizations(sample_data(), question="Which values?", intent="exact_lookup", max_variants=1)
        self.assertEqual([v.family for v in plan.variants], ["table"])

    def test_no_causal_or_geospatial_facts_are_inferred(self):
        scatter = recommend_visualizations(sample_data(), question="Are these related?", intent="correlation")
        self.assertIn("no causal", scatter.variants[0].rationale)
        geographic = recommend_visualizations(sample_data(), question="Compare places", intent="geographic_difference")
        self.assertIn("no map is asserted to be valid", geographic.variants[1].rationale)
        self.assertTrue(any("explicit geospatial field" in item
                            for item in geographic.variants[1].missing_fields))

    def test_planning_only_variants_report_missing_required_fields(self):
        data = LoadedData(
            ({"label": "North"},),
            DataSchema((ColumnSpec("label", "string", "none", "reject"),), "en_US", "none"),
            "synthetic.json", "a" * 64, RIGHTS)
        plan = recommend_visualizations(data, question="Rank", intent="magnitude_ranking")
        self.assertEqual(plan.variants[0].required_axes, ("label",))
        self.assertEqual(plan.variants[0].missing_fields, ("numeric measure",))
        self.assertIn("Required but absent or untyped fields", plan.variants[0].rationale)

    def test_chart_semantics_requiring_extra_structure_are_not_inferred(self):
        part = recommend_visualizations(
            sample_data(), question="Show composition", intent="part_to_whole")
        self.assertIn("explicit whole/denominator definition", part.variants[1].missing_fields)
        bridge = recommend_visualizations(
            sample_data(), question="Explain the change", intent="financial_bridge")
        self.assertIn("explicit signed deltas and opening/closing totals",
                      bridge.variants[0].missing_fields)

    def test_multiple_alternatives_and_rejection_reasons(self):
        plan = recommend_visualizations(sample_data(), question="Rank values", intent="magnitude_ranking")
        self.assertEqual(len(plan.variants), 2)
        self.assertTrue(plan.variants[0].alternatives_rejected)
        self.assertTrue(all("not selected" in reason for reason in plan.variants[0].alternatives_rejected))


if __name__ == "__main__":
    unittest.main()
