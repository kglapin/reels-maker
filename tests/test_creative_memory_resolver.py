"""Tests for the policy resolver."""
import unittest

from reels_maker.creative_memory.models import (
    ActorRole, EntityTarget, FeedbackType, Origin, OverridePolicy,
    PredicateSpec, Rule, RuleException, RuleStatus, Scope, ScopeLevel,
)
from reels_maker.creative_memory.resolver import (
    PolicyConflictError, PolicyResolver, check_conflict, resolve_policy,
)


def _rule(rule_id, kind, level=ScopeLevel.GLOBAL, brand=None, scene_id=None):
    return Rule(
        rule_id=rule_id, kind=kind, scope=Scope(level, brand=brand, scene_id=scene_id),
        applies_to=EntityTarget(node_types=("kicker",), contexts=("all",)),
        predicate=PredicateSpec(operator="element_type_absent",
                                parameters={"element_types": ["kicker"]}),
        override_policy=OverridePolicy.NEVER,
        enforcement=("creative_spec",), repair_strategy=None,
        status=RuleStatus.ACTIVE, current_revision=1,
        origin=Origin(actor=ActorRole.OWNER), rationale="Test",
        created_at="2026-10-24T16:00:00Z", evidence=(),
    )


class ResolverTests(unittest.TestCase):
    def test_global_rule_applies(self):
        rules = [_rule("CF-0001", FeedbackType.HARD_DONT)]
        resolver = PolicyResolver(rules)
        snapshot, diagnostics = resolver.resolve(brand="asta")
        self.assertEqual(len(snapshot.rules), 1)
        self.assertEqual(snapshot.rules[0][0], "CF-0001")

    def test_brand_rule_applies(self):
        rules = [_rule("CF-0002", FeedbackType.HARD_DONT, level=ScopeLevel.BRAND, brand="asta")]
        resolver = PolicyResolver(rules)
        snapshot, _ = resolver.resolve(brand="asta")
        self.assertEqual(len(snapshot.rules), 1)
        snapshot2, _ = resolver.resolve(brand="other")
        self.assertEqual(len(snapshot2.rules), 0)

    def test_scene_rule_applies(self):
        rules = [_rule("CF-0003", FeedbackType.HARD_DONT, level=ScopeLevel.SCENE, scene_id="s01")]
        resolver = PolicyResolver(rules)
        snapshot, _ = resolver.resolve(job_id="JOB-1", scene_id="s01")
        self.assertEqual(len(snapshot.rules), 1)
        snapshot2, _ = resolver.resolve(job_id="JOB-1", scene_id="s02")
        self.assertEqual(len(snapshot2.rules), 0)

    def test_exception_disables_rule_for_job(self):
        rules = [_rule("CF-0001", FeedbackType.HARD_DONT)]
        exc = RuleException(
            exception_id="EXC-001", rule_id="CF-0001", job_id="JOB-1",
            scope=Scope(ScopeLevel.VIDEO, video_id="JOB-1"),
            actor=ActorRole.OWNER, actor_id="owner",
            reason="One-time", created_at="2026-10-24T16:00:00Z",
        )
        resolver = PolicyResolver(rules, [exc])
        snapshot, _ = resolver.resolve(job_id="JOB-1")
        self.assertEqual(len(snapshot.rules), 0)
        self.assertIn("EXC-001", snapshot.exceptions_applied)

    def test_conflict_raises(self):
        dont = _rule("CF-0001", FeedbackType.HARD_DONT)
        do_rule = _rule("CF-0002", FeedbackType.HARD_DO)
        resolver = PolicyResolver([dont, do_rule])
        with self.assertRaises(PolicyConflictError):
            resolver.resolve()

    def test_check_conflict(self):
        dont = _rule("CF-0001", FeedbackType.HARD_DONT)
        do_rule = _rule("CF-0002", FeedbackType.HARD_DO)
        conflicts = check_conflict(do_rule, [dont])
        self.assertEqual(len(conflicts), 1)
        self.assertIn("CF-0001", conflicts[0])
        self.assertIn("CF-0002", conflicts[0])

    def test_snapshot_has_sha(self):
        rules = [_rule("CF-0001", FeedbackType.HARD_DONT)]
        resolver = PolicyResolver(rules)
        snapshot, _ = resolver.resolve()
        self.assertIsNotNone(snapshot.sha256)
        self.assertEqual(len(snapshot.sha256), 64)


if __name__ == "__main__":
    unittest.main()