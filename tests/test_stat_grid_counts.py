"""stat-grid accepts any count from one to four stats.

The grid used to hard-require exactly four items, which forced
meaningless filler stats into manifests. Fewer stats now render as a
single centred row of the same card height as the 2x2 layout.
"""
import unittest

from reels_maker.components.base import SceneContext
from reels_maker.components.scenes import build_scene
from reels_maker.design.tokens import resolve_tokens
from reels_maker.textkit.typesetter import FontBook


def context(duration=4.0):
    tokens = resolve_tokens("editorial-premium", width=720, height=1280)
    return SceneContext(720, 1280, 30, duration, tokens,
                        "editorial-premium", FontBook(), scene_index=0)


def stats_scene(count):
    return {
        "type": "stats", "duration": 4.0,
        "headline": "DANE",
        "stats": [{"label": f"POLE {index}", "value": index + 1,
                   "suffix": ""} for index in range(count)],
    }


class StatGridCountTests(unittest.TestCase):
    def test_accepts_one_to_four_stats(self):
        for count in (1, 2, 3, 4):
            with self.subTest(count=count):
                built = build_scene(context(), stats_scene(count))
                for index in range(count):
                    self.assertIn(f"stat-{index}", built.elements)
                    self.assertIn(f"stat-{index}",
                                  built.choreography.entries)

    def test_rejects_zero_and_five_stats(self):
        for count in (0, 5):
            with self.subTest(count=count), self.assertRaises(ValueError):
                build_scene(context(), stats_scene(count))

    def test_three_stats_share_one_row(self):
        built = build_scene(context(), stats_scene(3))
        panels = [built.elements[f"stat-{index}"].children[0]
                  for index in range(3)]
        heights = {round(panel.props["h"], 3) for panel in panels}
        self.assertEqual(len(heights), 1)
        tops = sorted(round(panel.props["y"], 3) for panel in panels)
        self.assertEqual(tops[0], tops[1])
        self.assertEqual(tops[1], tops[2])


if __name__ == "__main__":
    unittest.main()
