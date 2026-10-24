"""Tests for the repair planner."""
import copy
import unittest

from reels_maker.creative_memory.repair import (
    RepairError, plan_repair, run_repair_loop, SAFE_TRANSFORMS,
)
from reels_maker.creative_memory.models import QAIssue, Severity, Gate


def _spec_with_kicker():
    return {
        "creative_schema_version": 1, "name": "test", "mode": "studio",
        "style": "editorial-premium",
        "video": {"width": 540, "height": 960, "fps": 24},
        "shots": [{
            "id": "s01", "headline": "TEST", "kicker": "UNAUTHORIZED",
            "duration": 3.0,
        }],
    }


class RepairTests(unittest.TestCase):
    def test_plan_repair_removes_kicker(self):
        spec = _spec_with_kicker()
        issue = QAIssue(
            code="CF_POLICY_FORBIDDEN_ELEMENT", gate=Gate.G1_SPEC,
            severity=Severity.ERROR, message="Kicker forbidden",
            rule_id="CF-0001", scene_id="s01",
            remediation="remove_element_and_reflow",
        )
        candidates = plan_repair(spec, [issue], max_attempts=1)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["action"], "remove_element_and_reflow")
        self.assertNotIn("kicker", candidates[0]["spec"]["shots"][0])

    def test_run_repair_loop(self):
        spec = _spec_with_kicker()
        issue = QAIssue(
            code="CF_POLICY_FORBIDDEN_ELEMENT", gate=Gate.G1_SPEC,
            severity=Severity.ERROR, message="Kicker forbidden",
            rule_id="CF-0001", scene_id="s01",
            remediation="remove_element_and_reflow",
        )
        result = run_repair_loop(spec, [issue], max_attempts=3)
        self.assertTrue(result["ok"])
        self.assertTrue(result["repaired"])
        self.assertGreater(len(result["attempts"]), 0)
        self.assertNotIn("kicker", result["spec"]["shots"][0])

    def test_safe_transforms_registered(self):
        self.assertIn("remove_element_and_reflow", SAFE_TRANSFORMS)
        self.assertIn("increase_hold", SAFE_TRANSFORMS)
        self.assertIn("adjust_duration", SAFE_TRANSFORMS)
        self.assertIn("fix_chart_zeros", SAFE_TRANSFORMS)
        self.assertIn("reset_rotation", SAFE_TRANSFORMS)


if __name__ == "__main__":
    unittest.main()