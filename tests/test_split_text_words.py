"""Word-level text splitting for staggered per-word entrances."""
from __future__ import annotations

import unittest

from reels_maker.components.scene_support import _split_text_lines
from reels_maker.core.scene_graph import Node
from reels_maker.motionkit.choreography import ElementSpec
from reels_maker.motionkit.keyframes import Keyframe, Track
from reels_maker.textkit.models import Line, TextBlock, TextStyle, Word


def _word(text: str, x: float, width: float) -> Word:
    return Word(text=text, x=x, width=width, font_path="/f.ttf",
                font_index=0, color=(255, 255, 255), size=48)


def _block() -> TextBlock:
    style = TextStyle(size=48, line_height=1.2)
    first = Line(words=(_word("Witaj", 100.0, 200.0),
                       _word("świecie", 320.0, 220.0)),
                 width=440.0, ascent=50, descent=12, baseline=50,
                 height=62)
    second = Line(words=(_word("Drugi", 140.0, 180.0),
                         _word("wiersz", 340.0, 200.0)),
                  width=400.0, ascent=50, descent=12,
                  baseline=50 + 62, height=62)
    return TextBlock(lines=(first, second), width=440.0, height=124,
                     style=style, text="Witaj świecie Drugi wiersz")


def _node(block: TextBlock) -> Node:
    return Node(kind="text", role="headline", qa_class="text",
                props={"x": 40.0, "y": 300.0, "w": 902.0, "h": 200.0,
                       "block": block},
                meta={"text": block.text,
                      "bounds": (40.0, 300.0, 942.0, 500.0)})


class SplitTextWordsTest(unittest.TestCase):

    def test_words_mode_emits_one_node_per_word(self) -> None:
        elements = {"headline": _node(_block())}
        specs = [ElementSpec(role="headline", weight=10.0, kind="display",
                             order=0)]
        nodes, out_specs = _split_text_lines(elements, specs, None,
                                             mode="words")
        self.assertEqual(sorted(nodes), [f"headline-{i}" for i in range(4)])
        self.assertEqual(len(out_specs), 4)

    def test_word_nodes_preserve_absolute_position(self) -> None:
        elements = {"headline": _node(_block())}
        specs = [ElementSpec(role="headline", weight=10.0, kind="display",
                             order=0)]
        nodes, _ = _split_text_lines(elements, specs, None, mode="words")
        # "świecie" was at x=320 within line 1 whose row starts at y=300.
        word = nodes["headline-1"].props["block"].lines[0].words[0]
        self.assertEqual(word.text, "świecie")
        self.assertEqual(word.x, 0.0)
        node = nodes["headline-1"]
        self.assertEqual(node.props["x"], 40.0 + 320.0)
        self.assertEqual(node.props["y"], 300.0)
        self.assertEqual(node.props["w"], 220.0)
        # Second line words land one row lower.
        self.assertEqual(nodes["headline-2"].props["y"], 300.0 + 62.0)

    def test_word_specs_inherit_display_hint(self) -> None:
        elements = {"headline": _node(_block())}
        specs = [ElementSpec(role="headline", weight=10.0, kind="display",
                             order=0)]
        _, out_specs = _split_text_lines(elements, specs, None,
                                         mode="words")
        self.assertEqual(out_specs[0].hint, "word-cascade")
        for index, spec in enumerate(out_specs):
            self.assertIsInstance(spec.order, int)
            if index % 2 == 0:
                self.assertEqual(spec.hint, "word-cascade")
            else:
                self.assertNotEqual(spec.hint, "word-cascade")

    def test_single_word_block_is_not_split(self) -> None:
        block = _block()
        single = TextBlock(
            lines=(Line(words=(_word("Solo", 10.0, 100.0),),
                        width=100.0, ascent=50, descent=12,
                        baseline=50, height=62),),
            width=100.0, height=62, style=block.style, text="Solo")
        elements = {"headline": _node(single)}
        specs = [ElementSpec(role="headline", weight=10.0, kind="display",
                             order=0)]
        nodes, out_specs = _split_text_lines(elements, specs, None,
                                             mode="words")
        self.assertEqual(list(nodes), ["headline"])
        self.assertEqual(len(out_specs), 1)

    def test_lines_mode_still_splits_per_line(self) -> None:
        elements = {"headline": _node(_block())}
        specs = [ElementSpec(role="headline", weight=10.0, kind="display",
                             order=0)]
        nodes, out_specs = _split_text_lines(elements, specs, None,
                                             mode="lines")
        self.assertEqual(sorted(nodes), ["headline-0", "headline-1"])
        self.assertEqual(len(out_specs), 2)

    def test_fragments_own_independent_track_dicts(self) -> None:
        """Regression: copy.copy shared ``tracks`` so the last entrance won."""
        elements = {"headline": _node(_block())}
        specs = [ElementSpec(role="headline", weight=10.0, kind="display",
                             order=0)]
        nodes, _ = _split_text_lines(elements, specs, None, mode="words")
        for index, node in enumerate(nodes.values()):
            node.track("opacity", Track([
                Keyframe(0.1 * index, 0.0), Keyframe(0.1 * index + 0.2, 1.0)]))
        for index, node in enumerate(nodes.values()):
            self.assertEqual(node.tracks["opacity"].start, 0.1 * index)


if __name__ == "__main__":
    unittest.main()
