"""Synthetic 100%-stacked vector-bar renderer contract."""
import unittest

from reels_maker.components.base import SceneContext
from reels_maker.components.scenes import build_scene
from reels_maker.design.tokens import resolve_tokens
from reels_maker.renderers.scene import RenderOptions, SceneRenderer
from reels_maker.textkit.typesetter import FontBook


class StackedBarTests(unittest.TestCase):
    def context(self):
        width, height = 720, 1280
        tokens = resolve_tokens("editorial-premium", width=width, height=height)
        fonts = FontBook()
        return SceneContext(width, height, 30, 3.0, tokens,
                            "editorial-premium", fonts, scene_index=0)

    def scene(self):
        return {
            "type": "stacked_bars_100", "duration": 3.0,
            "headline": "Energy mix by region",
            "categories": [
                {"id": "north", "label": "North", "segments": [
                    {"id": "solar", "label": "Solar", "value": 30},
                    {"id": "wind", "label": "Wind", "value": 20},
                    {"id": "grid", "label": "Grid", "value": 50}]},
                {"id": "south", "label": "South", "segments": [
                    {"id": "solar", "label": "Solar", "value": 20},
                    {"id": "wind", "label": "Wind", "value": 60},
                    {"id": "grid", "label": "Grid", "value": 20}]},
            ],
        }

    def test_normalizes_each_declared_category_to_one_hundred_percent(self):
        built = build_scene(self.context(), self.scene())
        self.assertEqual(built.meta["normalization"],
                         "segment value / explicit category total")
        categories = built.meta["data"]
        self.assertEqual([item["id"] for item in categories], ["north", "south"])
        for category in categories:
            self.assertAlmostEqual(sum(segment["share"]
                                       for segment in category["segments"]), 1.0)
        rects = [node for node in built.elements["chart"].children
                 if node.kind == "rect"]
        self.assertEqual(len(rects), 6)
        north = [node for node in rects if node.role.startswith("stack-north-")]
        self.assertEqual([node.role for node in north],
                         ["stack-north-solar", "stack-north-wind", "stack-north-grid"])

    def test_vector_chart_renders_to_frame(self):
        context = self.context()
        built = build_scene(context, self.scene())
        renderer = SceneRenderer(context.width, context.height, context.tokens,
                                 context.fonts,
                                 options=RenderOptions(supersample=1))
        frame = renderer.render(built, 1.5)
        self.assertEqual(frame.size, (720, 1280))
        self.assertGreater(len(frame.getcolors(720 * 1280) or []), 20)

    def test_missing_or_inconsistent_segment_values_fail_closed(self):
        scene = self.scene()
        scene["categories"][1]["segments"].pop()
        with self.assertRaisesRegex(ValueError, "same ordered segment IDs"):
            build_scene(self.context(), scene)
        scene = self.scene()
        scene["categories"][0]["segments"][0]["value"] = -1
        with self.assertRaisesRegex(ValueError, "non-negative"):
            build_scene(self.context(), scene)
        scene = self.scene()
        scene["categories"][0]["segments"] = [
            {"id": "solar", "label": "Solar", "value": 0},
            {"id": "wind", "label": "Wind", "value": 0},
            {"id": "grid", "label": "Grid", "value": 0},
        ]
        with self.assertRaisesRegex(ValueError, "zero total"):
            build_scene(self.context(), scene)


if __name__ == "__main__":
    unittest.main()
