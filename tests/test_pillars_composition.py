"""Regression coverage for the centered pillars (icon grid) composition."""
from __future__ import annotations

import unittest

from reels_maker.components.base import SceneContext
from reels_maker.components.scenes import build_scene
from reels_maker.core.scene_graph import collect_qa_elements
from reels_maker.design.tokens import resolve_tokens
from reels_maker.textkit.typesetter import FontBook


def _context(width: int = 1080, height: int = 1920) -> SceneContext:
    tokens = resolve_tokens("editorial-premium", width=width, height=height)
    return SceneContext(width, height, 30, 5.5, tokens,
                        "editorial-premium", FontBook())


def _pillars_scene(**overrides: object) -> dict:
    scene: dict = {
        "type": "pillars",
        "duration": 5.5,
        "headline": "POTENCJAŁ TERENU",
        "items": ["USŁUGI", "MAGAZYN", "TRANSPORT", "PRODUKCJA"],
        "icon_library": "lucide",
        "icon_names": {
            "pillar-0": "store",
            "pillar-1": "warehouse",
            "pillar-2": "truck",
            "pillar-3": "factory",
        },
    }
    scene.update(overrides)
    return scene


class PillarsCompositionTests(unittest.TestCase):
    def test_pillars_builds_four_icon_caption_groups(self):
        built = build_scene(_context(), _pillars_scene())
        for index in range(4):
            group = built.elements[f"pillar-{index}"]
            self.assertEqual(group.kind, "group")
            icon, caption = group.children
            self.assertEqual(icon.kind, "icon")
            self.assertEqual(icon.props["library"], "lucide")
            self.assertIn("caption", caption.role)
        names = [built.elements[f"pillar-{index}"].children[0].props["name"]
                 for index in range(4)]
        self.assertEqual(names, ["store", "warehouse", "truck", "factory"])

    def test_pillars_block_is_vertically_centered(self):
        context = _context()
        built = build_scene(context, _pillars_scene())
        safe = context.layout.safe
        top = built.layout.region("headline").y
        bottom = built.layout.region("pillar-4").bottom
        self.assertGreaterEqual(top, safe.y)
        self.assertLessEqual(bottom, safe.bottom)
        self.assertAlmostEqual(top - safe.y, safe.bottom - bottom, delta=safe.h * .05)

    def test_pillars_without_icon_library_falls_back_to_drawn_marks(self):
        scene = _pillars_scene()
        del scene["icon_library"]
        del scene["icon_names"]
        built = build_scene(_context(), scene)
        icon = built.elements["pillar-0"].children[0]
        self.assertNotEqual(icon.kind, "icon")

    def test_pillars_rejects_anything_but_four_labels(self):
        for bad in ([], ["A", "B", "C"], ["A"] * 5, ["A", "B", None, "D"],
                    "USŁUGI", None):
            with self.assertRaises(ValueError, msg=f"items={bad!r}"):
                build_scene(_context(), _pillars_scene(items=bad))

    def test_pillars_choreography_staggers_each_cell(self):
        built = build_scene(_context(), _pillars_scene())
        onsets = [built.choreography.entries[f"pillar-{index}"].onset
                  for index in range(4)]
        self.assertEqual(len(set(onsets)), 4)
        self.assertTrue(all(earlier < later
                            for earlier, later in zip(onsets, onsets[1:])))
        self.assertIn("headline", built.choreography.entries)

    def test_pillars_cells_stay_inside_the_safe_area(self):
        context = _context()
        built = build_scene(context, _pillars_scene())
        safe = context.layout.safe
        records = [record for root in built.at(2.0)
                   for record in collect_qa_elements(root)
                   if record["path"].split("/")[0].startswith("pillar-")]
        self.assertTrue(records)
        for record in records:
            left, top, right, bottom = record["bounds"]
            self.assertGreaterEqual(left, safe.x - 1, record)
            self.assertGreaterEqual(top, safe.y - 1, record)
            self.assertLessEqual(right, safe.right + 1, record)
            self.assertLessEqual(bottom, safe.bottom + 1, record)


if __name__ == "__main__":
    unittest.main()
