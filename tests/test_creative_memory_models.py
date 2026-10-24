"""Unit tests for creative_memory models (spec section 14.1)."""
import unittest

from reels_maker.creative_memory.models import (
    ActorRole, ApprovedPattern, EntityTarget, FeedbackType, Gate, GateResult,
    Origin, OverridePolicy, PolicySnapshot, QAIssue, PredicateSpec, Rule,
    RuleException, RuleRevision, RuleStatus, Scope, ScopeLevel, Severity,
)


class ScopeTests(unittest.TestCase):
    def test_global_applies_to_all(self):
        g = Scope(ScopeLevel.GLOBAL, target="*")
        for lvl in ScopeLevel:
            self.assertTrue(g.applies_to(Scope(lvl, target="*")))

    def test_scene_only_matches_same(self):
        s1 = Scope(ScopeLevel.SCENE, scene_id="s01")
        self.assertTrue(s1.applies_to(Scope(ScopeLevel.SCENE, scene_id="s01")))
        self.assertFalse(s1.applies_to(Scope(ScopeLevel.SCENE, scene_id="s02")))

    def test_brand_matches_same(self):
        b = Scope(ScopeLevel.BRAND, brand="asta")
        self.assertTrue(b.applies_to(Scope(ScopeLevel.VIDEO, brand="asta")))
        self.assertFalse(b.applies_to(Scope(ScopeLevel.VIDEO, brand="other")))

    def test_roundtrip(self):
        s = Scope(ScopeLevel.SCENE, scene_id="s03", brand="asta")
        back = Scope.from_dict(s.to_dict())
        self.assertEqual(back.scene_id, "s03")
        self.assertEqual(back.brand, "asta")

    def test_precedence(self):
        levels = [ScopeLevel.GLOBAL, ScopeLevel.BRAND, ScopeLevel.PROJECT,
                  ScopeLevel.VIDEO, ScopeLevel.SCENE]
        for i in range(len(levels) - 1):
            self.assertLess(levels[i].precedence, levels[i + 1].precedence)


class FeedbackTypeTests(unittest.TestCase):
    def test_hard_dont_persistent(self):
        self.assertTrue(FeedbackType.HARD_DONT.is_persistent)

    def test_project_fix_not_persistent(self):
        self.assertFalse(FeedbackType.PROJECT_FIX.is_persistent)


class RuleRevisionTests(unittest.TestCase):
    def test_roundtrip(self):
        rev = RuleRevision(
            revision=1, rule_id="CF-0001", status=RuleStatus.ACTIVE,
            kind=FeedbackType.HARD_DONT, scope=Scope(ScopeLevel.GLOBAL),
            applies_to=EntityTarget(node_types=("kicker",), contexts=("all",)),
            predicate=PredicateSpec(operator="element_type_absent",
                                    parameters={"element_types": ["kicker"]}),
            override_policy=OverridePolicy.NEVER,
            enforcement=("creative_spec", "render_graph"),
            repair_strategy="remove_element_and_reflow",
            origin=Origin(feedback_event_id="FE-123", actor=ActorRole.OWNER),
            rationale="Test", created_at="2026-10-24T16:00:00Z",
            evidence=("FE-123",),
        )
        back = RuleRevision.from_dict(rev.to_dict())
        self.assertEqual(back.rule_id, "CF-0001")
        self.assertEqual(back.kind, FeedbackType.HARD_DONT)
        self.assertEqual(back.predicate.operator, "element_type_absent")


class RuleTests(unittest.TestCase):
    def test_roundtrip(self):
        rule = Rule(
            rule_id="CF-0002", kind=FeedbackType.HARD_DO,
            scope=Scope(ScopeLevel.GLOBAL),
            applies_to=EntityTarget(node_types=("chart",), contexts=("all",)),
            predicate=PredicateSpec(operator="chart_zero_origin", parameters={}),
            override_policy=OverridePolicy.NEVER,
            enforcement=("creative_spec",), repair_strategy=None,
            status=RuleStatus.ACTIVE, current_revision=1,
            origin=Origin(actor=ActorRole.OWNER), rationale="Charts must start at zero",
            created_at="2026-10-24T16:00:00Z", evidence=(),
        )
        back = Rule.from_dict(rule.to_dict())
        self.assertEqual(back.rule_id, "CF-0002")
        self.assertEqual(back.kind, FeedbackType.HARD_DO)
        self.assertTrue(back.status.is_terminal)


class QAIssueTests(unittest.TestCase):
    def test_roundtrip(self):
        issue = QAIssue(
            code="CF_POLICY_FORBIDDEN_ELEMENT", gate=Gate.G1_SPEC,
            severity=Severity.ERROR, message="Kicker forbidden",
            rule_id="CF-0001", scene_id="s01", elements=("kicker",),
        )
        back = QAIssue.from_dict(issue.to_dict())
        self.assertEqual(back.code, "CF_POLICY_FORBIDDEN_ELEMENT")
        self.assertEqual(back.gate, Gate.G1_SPEC)
        self.assertEqual(back.severity, Severity.ERROR)


class PolicySnapshotTests(unittest.TestCase):
    def test_serialization(self):
        snap = PolicySnapshot(
            snapshot_id="POL-abc123", sha256="deadbeef",
            rules=(("CF-0001", 1), ("CF-0002", 1)),
            exceptions_applied=("EXC-001",),
            compiled_at="2026-10-24T16:00:00Z",
            engine_version="creative_memory/1.0",
        )
        d = snap.to_dict()
        self.assertEqual(d["rules"], [["CF-0001", 1], ["CF-0002", 1]])
        self.assertEqual(d["exceptions_applied"], ["EXC-001"])


class GateResultTests(unittest.TestCase):
    def test_ok_result(self):
        result = GateResult(
            gate=Gate.G1_SPEC, ok=True, status="pass",
            checked_rules=["CF-0001"], limitations=["test"],
            policy_sha256="abc123",
        )
        d = result.to_dict()
        self.assertTrue(d["ok"])
        self.assertEqual(d["status"], "pass")


if __name__ == "__main__":
    unittest.main()