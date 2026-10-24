"""Tests for the deterministic feedback interpreter."""
import unittest

from reels_maker.creative_memory.interpreter import (
    FeedbackInterpreter, interpret_feedback, to_rule_revision,
)
from reels_maker.creative_memory.models import (
    Classification, ScopeLevel, FeedbackType,
)


class InterpreterTests(unittest.TestCase):
    def test_polish_global_dont(self):
        proposal = interpret_feedback(
            "Nigdy nie dodawaj kickerów nad nagłówkami",
            context={"actor_role": "owner"},
        )
        self.assertEqual(proposal.classification, Classification.PERSISTENT_RULE)
        self.assertEqual(proposal.feedback_type, FeedbackType.HARD_DONT)
        self.assertTrue(proposal.is_global_intent_explicit)
        self.assertGreater(proposal.confidence, 0.8)
        self.assertIn("kicker", proposal.target_element_ids)

    def test_english_global_dont(self):
        proposal = interpret_feedback(
            "Never add kicker text over headlines",
            context={"actor_role": "owner"},
        )
        self.assertEqual(proposal.classification, Classification.PERSISTENT_RULE)
        self.assertEqual(proposal.feedback_type, FeedbackType.HARD_DONT)

    def test_polish_brand_scope(self):
        proposal = interpret_feedback(
            "W filmach ASTA nie używaj kickerów",
            context={"actor_role": "owner", "brand": "asta-energy"},
        )
        self.assertEqual(proposal.candidate_scope.level, ScopeLevel.BRAND)
        self.assertEqual(proposal.candidate_scope.brand, "asta-energy")

    def test_polish_video_scope(self):
        proposal = interpret_feedback(
            "W tym filmie nie dodawaj kickerów",
            context={"actor_role": "owner", "job_id": "JOB-1"},
        )
        self.assertEqual(proposal.candidate_scope.level, ScopeLevel.VIDEO)
        self.assertEqual(proposal.candidate_scope.video_id, "JOB-1")

    def test_polish_scene_scope(self):
        proposal = interpret_feedback(
            "W scenie s03 nie dodawaj kickerów",
            context={"actor_role": "owner", "scene_id": "s03"},
        )
        self.assertEqual(proposal.candidate_scope.level, ScopeLevel.SCENE)
        self.assertEqual(proposal.candidate_scope.scene_id, "s03")

    def test_retraction(self):
        proposal = interpret_feedback(
            "Cofnij moją poprzednią zasadę o kickerach",
            context={"actor_role": "owner"},
        )
        self.assertEqual(proposal.classification, Classification.RETRACT)
        self.assertEqual(proposal.feedback_type, FeedbackType.RETRACTION)
        self.assertFalse(proposal.needs_confirmation)

    def test_preference(self):
        proposal = interpret_feedback(
            "Wolę dłuższe, spokojniejsze ujęcia",
            context={"actor_role": "owner"},
        )
        self.assertEqual(proposal.classification, Classification.PREFERENCE)
        self.assertEqual(proposal.feedback_type, FeedbackType.PREFERENCE)

    def test_exception(self):
        proposal = interpret_feedback(
            "Tylko tutaj zastosuj kicker, tylko w tym klipie",
            context={"actor_role": "owner", "job_id": "JOB-1"},
        )
        self.assertEqual(proposal.classification, Classification.OVERRIDE)
        self.assertEqual(proposal.feedback_type, FeedbackType.TEMPORARY_EXCEPTION)

    def test_ambiguous(self):
        proposal = interpret_feedback(
            "To wygląda dziwnie",
            context={"actor_role": "owner"},
        )
        self.assertEqual(proposal.classification, Classification.AMBIGUOUS)
        self.assertTrue(proposal.needs_confirmation)
        self.assertGreater(len(proposal.questions), 0)

    def test_to_rule_revision(self):
        proposal = interpret_feedback(
            "Nigdy nie dodawaj kickerów",
            context={"actor_role": "owner"},
        )
        revision = to_rule_revision(proposal)
        self.assertEqual(revision.kind, FeedbackType.HARD_DONT)
        self.assertEqual(revision.rule_id[:3], "CF-")
        self.assertEqual(revision.scope.level, ScopeLevel.GLOBAL)
        self.assertIsNotNone(revision.predicate)


class InterpreterElementDetectionTests(unittest.TestCase):
    def test_detect_kicker(self):
        proposal = interpret_feedback(
            "Nigdy nie dodawaj kickerów",
            context={"actor_role": "owner"},
        )
        self.assertIn("kicker", proposal.target_element_ids)

    def test_detect_chart(self):
        proposal = interpret_feedback(
            "Nigdy nie używaj wykresów",
            context={"actor_role": "owner"},
        )
        self.assertIn("chart", proposal.target_element_ids)

    def test_detect_headline(self):
        proposal = interpret_feedback(
            "Nigdy nie używaj małych nagłówek",
            context={"actor_role": "owner"},
        )
        self.assertIn("headline", proposal.target_element_ids)


if __name__ == "__main__":
    unittest.main()