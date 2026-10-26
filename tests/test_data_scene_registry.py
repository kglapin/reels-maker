"""Data scene builders remain available through the stable scene registry."""
from __future__ import annotations

import unittest

from reels_maker.components.data_scenes import DATA_BUILDERS
from reels_maker.components import scenes
from reels_maker.components.scenes import BUILDERS


class DataSceneRegistryTests(unittest.TestCase):
    def test_data_builder_names_match_the_lazy_scene_registry(self):
        expected = {
            "bars", "line_chart", "stacked_bars_100", "waterfall",
            "diverging_bar", "bullet", "heatmap", "scatter", "funnel",
            "sankey", "chart_morph",
        }
        self.assertEqual(set(DATA_BUILDERS), expected)
        self.assertTrue(expected <= set(BUILDERS))

    def test_all_lazy_registry_wrappers_dispatch_to_the_domain_builder(self):
        for name, builder in DATA_BUILDERS.items():
            with self.subTest(name=name):
                self.assertIsNot(BUILDERS[name], builder)
                self.assertEqual(BUILDERS[name].__name__, f"build_{name}")
                self.assertIs(BUILDERS[name], getattr(scenes, f"build_{name}"))


if __name__ == "__main__":
    unittest.main()
