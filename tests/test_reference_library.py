"""Regression checks for curated professional references and anti-slop heuristics."""
from __future__ import annotations

import copy
import unittest

from reels_maker.creative.reference_library import (
    audit_reference_quality, load_reference_library, reference_guidance,
    validate_reference_library,
)
from reels_maker.creative.quality import audit_creative_spec


def spec():
    return {
        "creative_schema_version": 1,
        "name": "reference-quality-fixture",
        "mode": "studio",
        "style": "editorial-premium",
        "shots": [
            {"id": "one", "intent": "opening", "headline": "A measurable result",
             "duration": 2.8, "layout": "statement"},
            {"id": "two", "intent": "proof", "headline": "Here is how it works",
             "duration": 3.4, "layout": "stack-center"},
        ],
    }


class ReferenceLibraryTests(unittest.TestCase):
    def test_catalog_is_structured_and_sources_are_traceable(self):
        lib = load_reference_library()
        stats = validate_reference_library(lib)
        self.assertTrue(stats["valid"])
        self.assertGreaterEqual(stats["sources"], 10)
        self.assertGreaterEqual(stats["principles"], 12)
        self.assertGreaterEqual(stats["anti_patterns"], 8)
        self.assertGreaterEqual(stats["recipes"], 5)
        self.assertEqual({r["id"] for r in lib["recipes"]},
                         {"R01", "R02", "R03", "R04", "R05"})

    def test_library_is_defensively_copied(self):
        lib = load_reference_library()
        lib["principles"].clear()
        self.assertGreater(len(load_reference_library()["principles"]), 0)

    def test_missing_source_citation_is_rejected(self):
        lib = load_reference_library()
        lib["principles"][0]["source_ids"] = ["invented-source"]
        with self.assertRaisesRegex(ValueError, "Untraceable"):
            validate_reference_library(lib)

    def test_guidance_selects_data_recipe_for_chart_story(self):
        value = spec()
        value["shots"][0]["layout"] = "line-chart"
        value["shots"][0]["chart"] = {
            "points": [{"label": "2026-01-01", "value": 14},
                       {"label": "2026-02-01", "value": 30}],
            "x_axis_type": "date", "x_axis_label": "Month",
            "y_axis_label": "Energy (kWh)", "y_domain": [0, 35],
        }
        guidance = reference_guidance(value)
        self.assertEqual(guidance["recipe"]["id"], "R03")
        self.assertTrue(guidance["source_links"])
        report = audit_reference_quality(value)
        self.assertIn("reference_chart_source_review",
                      [issue["code"] for issue in report["issues"]])
        self.assertTrue(report["human_approval_required"])

    def test_placeholders_are_a_hard_error(self):
        value = spec()
        value["shots"][0]["headline"] = "Lorem ipsum test"
        report = audit_reference_quality(value)
        self.assertEqual(report["errors"], 1)
        self.assertIn("P01", report["issues"][0]["reference_rules"])
        # The existing QA function must actually consume the references.
        qa = audit_creative_spec(value)
        self.assertFalse(qa["ok"])
        self.assertTrue(any(issue["code"] == "reference_unfinished_placeholder"
                            for issue in qa["issues"]))
        self.assertEqual(qa["reference_review"]["errors"], 1)

    def test_flat_four_shot_timeline_is_flagged_but_not_automatically_failed(self):
        value = spec()
        value["shots"].extend([
            {"id": "three", "headline": "Third claim", "duration": 2.8},
            {"id": "four", "headline": "Fourth claim", "duration": 2.8},
        ])
        value["shots"][1]["duration"] = 2.8
        report = audit_reference_quality(value)
        codes = {issue["code"] for issue in report["issues"]}
        self.assertIn("reference_flat_rhythm", codes)
        self.assertIn("reference_direction_missing", codes)
        self.assertEqual(report["errors"], 0)

    def test_frequent_repeated_image_and_overloaded_subtitle(self):
        value = spec()
        value["shots"][0]["subtitle"] = "This is intentionally far too long a subtitle for a short shot duration"
        value["shots"][0]["duration"] = 1.1
        report = audit_reference_quality(value)
        self.assertIn("reference_dense_subtitle",
                      [issue["code"] for issue in report["issues"]])

    def test_good_baseline_remains_warning_free(self):
        report = audit_reference_quality(spec())
        self.assertEqual(report["errors"], 0)
        self.assertEqual(report["warnings"], 0)
        self.assertTrue(report["human_approval_required"])
        self.assertEqual(report["recommended_recipe_id"], "R01")

    def test_mixed_icon_families_warn_without_throwing(self):
        value = spec()
        value["shots"][0]["icon_library"] = "lucide"
        value["shots"][1]["icon_library"] = "heroicons"
        report = audit_reference_quality(value)
        self.assertIn("reference_icon_family_mix",
                      [issue["code"] for issue in report["issues"]])


if __name__ == "__main__":
    unittest.main()
