"""Professional typography profiles and QA regression tests."""
from __future__ import annotations

import copy
import unittest
from dataclasses import replace

from reels_maker.creative.quality import audit_creative_spec
from reels_maker.creative.compiler import compile_creative_spec
from reels_maker.design.tokens import resolve_tokens
from reels_maker.design.typography_policy import (
    audit_creative_typography, audit_typography_blocks, audit_typography_spacing, audit_typography_tokens,
    load_typography_profiles, suggested_typography,
)
from reels_maker.textkit.typesetter import FontBook, TextStyle, typeset


def _block(text, size=48, *, width=650, line_height=1.2, tracking=0):
    return typeset(text, TextStyle(size, line_height=line_height, tracking=tracking),
                   width, FontBook())


def _spec(headline="Oszczędności w 2026", subtitle="Porównanie realnych danych"):
    return {"creative_schema_version": 1, "name": "typography-quality-sample",
            "mode": "studio", "style": "editorial-premium",
            "shots": [{"id": "intro", "intent": "opening",
                       "headline": headline, "subtitle": subtitle,
                       "duration": 3.5, "layout": "statement"}]}


class TypographyPolicyTests(unittest.TestCase):
    def test_reference_sources_complete_and_unique(self):
        lib = load_typography_profiles()
        self.assertEqual(lib["schema_version"], 1)
        self.assertGreaterEqual(len(lib["source_references"]), 9)
        ids = [source["id"] for source in lib["source_references"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(source["url"].startswith("https://") for source in lib["source_references"]))
        for family in lib["styles"].values():
            self.assertIn("title", family["roles"])
            self.assertIn("caption", family["roles"])
            self.assertGreater(family["roles"]["display"]["size_px"],
                               family["roles"]["body"]["size_px"])

    def test_defensive_copy(self):
        lib = load_typography_profiles()
        lib["styles"].clear()
        self.assertGreater(len(load_typography_profiles()["styles"]), 0)

    def test_suggested_scale_responsive_short_side(self):
        base = suggested_typography("editorial-premium", 1080, 1920)
        portrait = suggested_typography("editorial-premium", 540, 960)
        wide = suggested_typography("editorial-premium", 1920, 1080)
        self.assertEqual(base["roles"]["title"]["size_px"], 82)
        self.assertEqual(portrait["roles"]["title"]["size_px"], 41)
        self.assertEqual(wide["roles"]["title"]["size_px"], 82)
        self.assertEqual(base["stack_gaps_px"], [16, 24, 32, 48, 64, 96])
        with self.assertRaises(ValueError):
            suggested_typography("editorial-premium", 0, 1920)

    def test_good_measured_hierarchy_remains_clean(self):
        findings = audit_typography_blocks([
            ("headline", _block("EFEKTYWNIEJ", 112)),
            ("subtitle", _block("Mniej energii z sieci", 54)),
            ("body", _block("Dane z instalacji", 42)),
        ], width=1080, height=1920)
        self.assertEqual(findings, [], findings)

    def test_critical_text_size_rejected_only_after_canvas_scale(self):
        text = _block("Mikrotekst", 12)
        at_1080 = audit_typography_blocks([("caption", text)], width=1080, height=1920)
        self.assertIn("typography_critical_size", [i["code"] for i in at_1080])
        at_360 = audit_typography_blocks([("caption", text)], width=360, height=640)
        self.assertNotIn("typography_critical_size", [i["code"] for i in at_360])

    def test_measured_small_text_and_weak_hierarchy(self):
        findings = audit_typography_blocks([
            ("headline", _block("Główny przekaz", 44)),
            ("subtitle", _block("Informacja dodatkowa", 44)),
        ], width=1080, height=1920)
        self.assertIn("typography_small_text", {x["code"] for x in findings})
        self.assertIn("typography_weak_hierarchy", {x["code"] for x in findings})

    def test_tight_leading_tracking_and_too_many_lines(self):
        text = _block(
            "Długie zdanie wyświetlane w bardzo ciasnym i wyjątkowo niewygodnym "
            "bloku tekstowym, który utrudnia odbiór informacji na telefonie",
            38, width=250, line_height=1.0, tracking=8)
        findings = audit_typography_blocks([("body", text)], width=1080, height=1920)
        codes = {x["code"] for x in findings}
        self.assertIn("typography_tight_leading", codes)
        self.assertIn("typography_long_copy_leading", codes)
        self.assertIn("typography_extreme_tracking", codes)
        self.assertIn("typography_too_many_lines", codes)

    def test_no_html_only_wcag_spacing_rule_applied_to_video_headings(self):
        findings = audit_typography_blocks(
            [("headline", _block("KORZYŚCI", 112, line_height=1.08))],
            width=1080, height=1920)
        self.assertNotIn("typography_tight_leading", {x["code"] for x in findings})

    def test_cramped_text_stacks_are_measured_but_columns_are_allowed(self):
        vertical = audit_typography_spacing([
            ("headline", (60, 70, 650, 160)),
            ("subtitle", (60, 166, 700, 240)),
        ], width=1080, height=1920)
        self.assertIn("typography_cramped_stack", {item["code"] for item in vertical})
        columns = audit_typography_spacing([
            ("headline", (60, 70, 450, 180)),
            ("subtitle", (600, 70, 980, 180)),
        ], width=1080, height=1920)
        self.assertEqual(columns, [])
        comfortable = audit_typography_spacing([
            ("headline", (60, 70, 700, 170)),
            ("subtitle", (60, 202, 750, 266)),
        ], width=1080, height=1920)
        self.assertEqual(comfortable, [])
        # Same spacing on a 360px preview scales the warning threshold.
        preview = audit_typography_spacing([
            ("headline", (20, 20, 205, 55)),
            ("subtitle", (20, 59, 210, 80)),
        ], width=360, height=640)
        self.assertEqual(preview, [])

    def test_inverted_font_and_spacing_tokens_warn(self):
        tokens = resolve_tokens("editorial-premium", width=1080, height=1920)
        self.assertEqual(audit_typography_tokens(tokens), [])
        bad = replace(tokens, typography=replace(tokens.typography, subtitle=101),
                      spacing=replace(tokens.spacing, lg=18))
        codes = {issue["code"] for issue in audit_typography_tokens(bad)}
        self.assertEqual(codes, {"typography_token_hierarchy", "typography_token_spacing"})

    def test_creative_quality_hook_detects_long_heading_and_caps(self):
        text = "TO JEST ZDECYDOWANIE ZBYT DŁUGI NAGŁÓWEK NA JEDEN KADR I MUSI BYĆ SKRÓCONY"
        spec = _spec(headline=text)
        codes = {i["code"] for i in audit_creative_typography(spec)}
        self.assertIn("typography_long_headline", codes)
        self.assertIn("typography_caps_overuse", codes)
        compiled, _ = compile_creative_spec(spec, check_assets=False)
        overall = audit_creative_spec(spec, compiled)
        self.assertTrue(any(i["code"] == "typography_long_headline" for i in overall["issues"]))
        self.assertTrue(any(i["code"] == "typography_caps_overuse" for i in overall["issues"]))
        self.assertTrue(overall["ok"])  # warnings alone do not silently block an intentional aesthetic decision


if __name__ == "__main__":
    unittest.main()
