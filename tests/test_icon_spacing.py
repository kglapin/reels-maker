"""Regression coverage for collisions between vector icons and scene typography."""
import unittest

from reels_maker.components.scenes import _icon_collisions
from reels_maker.core.scene_graph import Node


def node(kind, role, x, y, w, h):
    return Node(kind=kind, role=role,
                props={"x": x, "y": y, "w": w, "h": h})


class IconSpacingTests(unittest.TestCase):
    def test_overlap_detected_with_text(self):
        icon = node("icon", "sun", 100, 100, 64, 64)
        headline = node("text", "headline", 155, 100, 200, 60)
        self.assertEqual(_icon_collisions(icon, [headline], 8), ["headline"])

    def test_token_gap_keeps_separate_icons_clear(self):
        first = node("icon", "sun", 100, 100, 64, 64)
        arrow = node("icon", "arrow", 188, 108, 32, 32)
        second = node("icon", "house", 245, 100, 64, 64)
        self.assertEqual(_icon_collisions(first, [arrow, second], 12), [])
        self.assertEqual(_icon_collisions(arrow, [first, second], 12), [])

    def test_ignore_intentional_panel_background(self):
        icon = node("icon", "sun", 100, 100, 64, 64)
        background = node("panel", "panel", 0, 0, 500, 500)
        self.assertEqual(_icon_collisions(icon, [background], 12), [])


if __name__ == "__main__":
    unittest.main()
