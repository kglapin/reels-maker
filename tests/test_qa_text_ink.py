"""Focused Studio QA integration tests for measured text ink geometry."""
import unittest
from types import SimpleNamespace

from reels_maker.core.scene_graph import Node
from reels_maker.qa.report import _text_ink_safe_area
from reels_maker.textkit.typesetter import FontBook, TextStyle, typeset


FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"


class TextInkSafeAreaTests(unittest.TestCase):
    def setUp(self):
        self.safe = SimpleNamespace(x=0, y=0, right=100, bottom=100)
        self.built = SimpleNamespace(layout=SimpleNamespace(safe=self.safe), index=0)
        self.block = typeset("word", TextStyle(24), 200,
                             FontBook(regular=FONT, bold=FONT))

    def text_node(self, *, bounds=(5, 20, 80, 60), block=None):
        return Node("text", role="headline", props={"block": block or self.block},
                    meta={"bounds": bounds})

    def test_checks_actual_word_ink_after_leaf_and_ancestor_transforms(self):
        leaf = self.text_node(bounds=(75, 20, 100, 60))
        parent = Node("group", role="container", children=[leaf], dx=10)
        issues = _text_ink_safe_area([parent], self.built, 0.5, 12)
        self.assertEqual([issue.code for issue in issues], ["text_ink_safe_area"])
        self.assertIn("word", issues[0].message)
        self.assertEqual(issues[0].frame, 12)

    def test_contained_text_passes_and_repeated_failure_is_deduplicated(self):
        contained = self.text_node()
        self.assertEqual(_text_ink_safe_area([contained], self.built, 0, 0), [])
        outside = self.text_node(bounds=(95, 20, 120, 60))
        issues = _text_ink_safe_area([outside, outside], self.built, 0, 0)
        self.assertEqual(len(issues), 1)

    def test_missing_font_metrics_are_reported_not_skipped(self):
        block = typeset("word", TextStyle(24), 200,
                        FontBook(regular=FONT, bold=FONT))
        from dataclasses import replace
        word = replace(block.lines[0].words[0], font_path="/missing/local-font.ttf")
        line = replace(block.lines[0], words=(word,))
        invalid = replace(block, lines=(line,))
        issues = _text_ink_safe_area([self.text_node(block=invalid)],
                                     self.built, 0, 0)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "text_ink_safe_area")
        self.assertIn("could not be checked", issues[0].message)


if __name__ == "__main__":
    unittest.main()
