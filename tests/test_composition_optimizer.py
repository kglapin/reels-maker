import unittest
from reels_maker.layout.composition_optimizer import (
    CompositionCandidate, evaluate_candidates, WEIGHTS)


def candidate(name, quality, **kwargs):
    return CompositionCandidate(name, "editorial_split",
                                {k: quality for k in WEIGHTS}, **kwargs)


class CompositionOptimizerTests(unittest.TestCase):
    def test_rejects_unsafe_even_when_score_is_higher(self):
        result = evaluate_candidates([
            candidate("unsafe", 1, violations=("text_overlap",)),
            candidate("safe", .6)])
        self.assertEqual(result["selected_id"], "safe")
        self.assertFalse(result["candidates"][-1]["valid"])

    def test_stable_tie_break_prefers_less_clutter(self):
        result = evaluate_candidates([
            candidate("busy", .8, element_count=8),
            candidate("clean", .8, element_count=3)])
        self.assertEqual(result["selected_id"], "clean")

    def test_rejects_all_unsafe(self):
        result = evaluate_candidates([candidate("x", .9, violations=("crop",))])
        self.assertIsNone(result["selected_id"])

    def test_no_candidates(self):
        self.assertIsNone(evaluate_candidates([])["selected_id"])

    def test_invalid_scores_rejected(self):
        with self.assertRaises(ValueError):
            candidate("x", float("nan"))
        with self.assertRaises(ValueError):
            candidate("x", 1.1)

    def test_invalid_weights_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_candidates([candidate("x", .5)], {"hierarchy":1})

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_candidates([candidate("x", .5), candidate("x", .8)])

    def test_weighted_ranking(self):
        low = {k:.5 for k in WEIGHTS}
        high = dict(low)
        high["legibility"] = 1.
        result = evaluate_candidates([
            CompositionCandidate("a","full_bleed",low),
            CompositionCandidate("b","split",high)])
        self.assertEqual(result["selected_id"],"b")


if __name__ == "__main__":
    unittest.main()
