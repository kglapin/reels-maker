"""Synthetic ordering checks for the Studio vector-bar ranking variant."""
import unittest

from reels_maker.components.base import SceneContext
from reels_maker.components.scenes import build_scene
from reels_maker.design.tokens import resolve_tokens
from reels_maker.renderers.scene import RenderOptions, SceneRenderer
from reels_maker.textkit.typesetter import FontBook


def context():
    width, height = 720, 1280
    return SceneContext(width, height, 30, 3.0,
                        resolve_tokens("editorial-premium", width=width, height=height),
                        "editorial-premium", FontBook(), scene_index=0)


class RankingChartTests(unittest.TestCase):
    def scene(self, **overrides):
        return {
            "type": "bars", "duration": 3.0, "headline": "Ranking",
            "data_order": "descending",
            "bars": [{"label": "Alpha", "value": 12},
                     {"label": "Beta", "value": 18},
                     {"label": "Gamma", "value": 18},
                     {"label": "Delta", "value": 3}],
            **overrides,
        }

    def test_descending_ranking_is_stable_and_source_order_is_preserved_by_default(self):
        ranked = build_scene(context(), self.scene())
        self.assertEqual([item["label"] for item in ranked.meta["data"]],
                         ["Beta", "Gamma", "Alpha", "Delta"])
        self.assertEqual(ranked.meta["data_order"], "descending")
        source = build_scene(context(), {**self.scene(), "data_order": "source"})
        self.assertEqual([item["label"] for item in source.meta["data"]],
                         ["Alpha", "Beta", "Gamma", "Delta"])

    def test_ranking_rejects_duplicate_categories_and_negative_values(self):
        duplicate = self.scene(bars=[{"label": "A", "value": 1},
                                     {"label": "A", "value": 2}])
        with self.assertRaisesRegex(ValueError, "unique non-empty"):
            build_scene(context(), duplicate)
        negative = self.scene(bars=[{"label": "A", "value": -1},
                                    {"label": "B", "value": 2}])
        with self.assertRaisesRegex(ValueError, "non-negative"):
            build_scene(context(), negative)

    def test_ranking_uses_shared_card_tracks_and_direct_values(self):
        ctx = context()
        built = build_scene(ctx, self.scene())
        roles = {node.role for root in built.nodes for node in root.flatten()}
        self.assertIn("bar-chart-card", roles)
        self.assertEqual(len([role for role in roles if role.startswith("bar-track-")]), 4)
        self.assertEqual(len([role for role in roles if role.startswith("bar-value-")]), 4)
        renderer = SceneRenderer(ctx.width, ctx.height, ctx.tokens, ctx.fonts,
                                 options=RenderOptions(supersample=1))
        frame = renderer.render(built, 2.5)
        self.assertEqual(frame.size, (ctx.width, ctx.height))
        self.assertGreater(len(frame.getcolors(ctx.width * ctx.height) or []), 20)


if __name__ == "__main__":
    unittest.main()
