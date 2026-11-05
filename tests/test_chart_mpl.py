"""Edge-case and geometry tests for the optional matplotlib chart engine."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from reels_maker.chart_mpl import engine
from reels_maker.chart_mpl.engine import (
    _clip, _fit_fs, _stagger, _text_frac, frame_paths,
)

THEME = {"base": (10, 10, 16), "ink": (240, 240, 245),
         "muted": (150, 150, 160), "accent": (96, 165, 250),
         "light": False}


def _frames(scene: dict, duration: float = 1.5, fps: int = 15):
    return frame_paths(scene, THEME, 300, 300, duration, fps)


class StaggerTests(unittest.TestCase):
    def test_dense_count_still_completes(self):
        # Regression: large item counts used to push later items past the
        # end of the timeline so they never appeared.
        prog = _stagger(1.0, 168, start=.08, step=.012)
        self.assertAlmostEqual(prog[-1], 1.0)
        self.assertTrue(all(0.0 <= p <= 1.0 for p in prog))

    def test_small_count_completes(self):
        prog = _stagger(1.0, 3, start=.10, step=.06)
        self.assertTrue(all(p == 1.0 for p in prog))

    def test_per_item_monotonic_over_time(self):
        # Each item's progress must be nondecreasing as t grows; across
        # items at fixed t earlier items lead (stagger), so the list is
        # expected to be nonincreasing, not nondecreasing.
        prev = [_stagger(t, 10) for t in (0.0, .3, .6, 1.0)]
        for i in range(10):
            series = [p[i] for p in prev]
            self.assertTrue(all(a <= b + 1e-9 for a, b in zip(series, series[1:])))
        self.assertTrue(all(a >= b - 1e-9
                            for a, b in zip(prev[-1], prev[-1][1:])))


class TextFitTests(unittest.TestCase):
    def test_clip_short_text_unchanged(self):
        self.assertEqual(_clip("ALPHA", 26, .2, 1204), "ALPHA")

    def test_clip_long_text_ellipsized(self):
        out = _clip("GENERACJA ENERGII", 26, .1, 1204)
        self.assertTrue(out.endswith("..."))
        self.assertLess(_text_frac(out, 26, 1204), .11)

    def test_fit_fs_scales_to_box(self):
        big = _fit_fs("1 234", 30, 400, 200)
        small = _fit_fs("1 234", 30, 60, 40)
        self.assertEqual(big, 30)
        self.assertLess(small, 30)
        self.assertGreaterEqual(small, 9.0)


class DrawerEdgeCases(unittest.TestCase):
    """Every supported drawer must render hostile inputs without raising."""

    CASES = {
        "bars_negative": {"type": "bars", "bars": [
            {"label": "A", "value": -50}, {"label": "B", "value": -20}]},
        "bars_single": {"type": "bars", "bars": [
            {"label": "ONLY", "value": 10}]},
        "bars_empty": {"type": "bars", "bars": []},
        "line_two_points": {"type": "line_chart", "points": [
            {"label": "A", "value": 5}, {"label": "B", "value": 9}]},
        "line_out_of_domain": {"type": "line_chart", "points": [
            {"label": "A", "value": -500}, {"label": "B", "value": 9000}],
            "y_domain": [0, 100]},
        "waterfall_single": {"type": "waterfall", "steps": [
            {"label": "T", "value": 42, "kind": "total"}]},
        "bullet_zero_max": {"type": "bullet", "metrics": [
            {"label": "X", "value": 5, "target": 9, "max": 0}]},
        "bullet_many": {"type": "bullet", "metrics": [
            {"label": f"M{i}", "value": i * 10, "target": 50, "max": 100}
            for i in range(8)]},
        "heatmap_dense": {"type": "heatmap",
                          "row_labels": [f"R{i}" for i in range(12)],
                          "col_labels": [f"C{i}" for i in range(10)],
                          "values": [[i * j % 7 for j in range(10)]
                                     for i in range(12)]},
        "heatmap_negative": {"type": "heatmap", "row_labels": ["A", "B"],
                             "col_labels": ["X", "Y"],
                             "values": [[-3, 2], [5, -1]]},
        "funnel_growing": {"type": "funnel", "stages": [
            {"label": "A", "value": 10}, {"label": "B", "value": 50},
            {"label": "C", "value": 30}]},
        "funnel_ten": {"type": "funnel", "stages": [
            {"label": f"S{i}", "value": 100 - i * 9} for i in range(10)]},
        "diverging_mixed": {"type": "diverging_bar", "baseline": 0,
                            "items": [{"label": "A", "value": -30},
                                      {"label": "B", "value": 80},
                                      {"label": "C", "value": -10}]},
        "scatter_degenerate_domain": {"type": "scatter", "points": [
            {"x": 1, "y": 2}, {"x": 1, "y": 3}, {"x": 2, "y": 1}],
            "x_domain": [1, 1], "y_domain": [1, 5]},
        "scatter_out_of_domain": {"type": "scatter", "points": [
            {"x": -50, "y": 999}, {"x": 1, "y": 2}],
            "x_domain": [0, 10], "y_domain": [0, 10]},
        "donut_multi": {"type": "donut", "segments": [
            {"label": "A", "value": 30}, {"label": "B", "value": 70}]},
        "donut_over_100": {"type": "donut", "value": 150, "label": "OVER"},
        "donut_negative_segment": {"type": "donut", "segments": [
            {"label": "A", "value": -10}, {"label": "B", "value": 50}]},
        "donut_many_segments": {"type": "donut", "segments": [
            {"label": f"SEG{i}", "value": 10 + i} for i in range(8)]},
    }

    def test_all_edge_cases_render(self):
        for name, scene in self.CASES.items():
            with self.subTest(case=name):
                frames = _frames(scene)
                self.assertIsNotNone(frames, f"{name} returned no frames")
                self.assertGreater(len(frames), 0)

    def test_unsupported_type_returns_none(self):
        self.assertIsNone(_frames({"type": "table", "rows": []}))
        self.assertIsNone(_frames({"type": "chart_morph"}))

    def test_empty_scene_renders_card_only(self):
        frames = _frames({"type": "bars", "bars": []})
        self.assertIsNotNone(frames)


class CacheTests(unittest.TestCase):
    def test_deterministic_paths(self):
        scene = {"type": "bars", "bars": [{"label": "A", "value": 1}]}
        a = _frames(scene)
        b = _frames(scene)
        self.assertEqual(a, b)

    def test_engine_version_invalidates(self):
        # Bumping _ENGINE_VERSION must change cache keys so stale frames
        # (e.g. transparent or buggy layouts) are never reused.
        scene = {"type": "bars", "bars": [{"label": "A", "value": 1}]}
        before = engine._cache_dir(scene, 600, 600, 1.5, 15, THEME)
        old = engine._ENGINE_VERSION
        try:
            engine._ENGINE_VERSION = old + 1000
            after = engine._cache_dir(scene, 600, 600, 1.5, 15, THEME)
            self.assertNotEqual(before, after)
        finally:
            engine._ENGINE_VERSION = old


if __name__ == "__main__":
    unittest.main()
