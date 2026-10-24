"""Tests for the SQLite creative-memory store."""
import json
import unittest
from datetime import datetime, timezone

from reels_maker.creative_memory.models import (
    ActorRole, EntityTarget, FeedbackContext, FeedbackEvent, FeedbackType,
    Origin, OverridePolicy, PredicateSpec, Rule, RuleException, RuleRevision,
    RuleStatus, Scope, ScopeLevel,
)
from reels_maker.creative_memory.store import (
    CreativeMemoryStore, CreativeMemoryError, open_store,
)


def _utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.store = open_store(":memory:")

    def tearDown(self):
        self.store.close()

    def test_open_close(self):
        self.assertIsNotNone(self.store.conn)

    def test_add_and_get_feedback_event(self):
        event = FeedbackEvent(
            event_id="FE-001",
            text="Nigdy nie dodawaj kickerów",
            context=FeedbackContext(job_id="JOB-1", scene_id="s01"),
            recorded_at=_utcnow(),
            normalized_intent="never add kickers",
            scope=Scope(ScopeLevel.GLOBAL),
            feedback_type=FeedbackType.HARD_DONT,
            confidence=0.95,
        )
        self.store.add_feedback_event(event)
        fetched = self.store.get_feedback_event("FE-001")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.text, "Nigdy nie dodawaj kickerów")
        self.assertEqual(fetched.feedback_type, FeedbackType.HARD_DONT)

    def test_rule_revision_persistence(self):
        rev = RuleRevision(
            revision=1, rule_id="CF-0001", status=RuleStatus.ACTIVE,
            kind=FeedbackType.HARD_DONT, scope=Scope(ScopeLevel.GLOBAL),
            applies_to=EntityTarget(node_types=("kicker",), contexts=("all",)),
            predicate=PredicateSpec(operator="element_type_absent",
                                    parameters={"element_types": ["kicker"]}),
            override_policy=OverridePolicy.NEVER,
            enforcement=("creative_spec", "render_graph"),
            repair_strategy="remove_element_and_reflow",
            origin=Origin(feedback_event_id="FE-001", actor=ActorRole.OWNER),
            rationale="No kickers", created_at=_utcnow(),
            evidence=("FE-001",),
        )
        self.store.add_rule_revision(rev)
        rule = self.store.get_rule("CF-0001")
        self.assertIsNotNone(rule)
        self.assertEqual(rule.kind, FeedbackType.HARD_DONT)
        self.assertEqual(rule.status, RuleStatus.ACTIVE)
        self.assertEqual(rule.current_revision, 1)

    def test_rule_history(self):
        rev1 = RuleRevision(
            revision=1, rule_id="CF-0001", status=RuleStatus.ACTIVE,
            kind=FeedbackType.HARD_DONT, scope=Scope(ScopeLevel.GLOBAL),
            applies_to=EntityTarget(node_types=("kicker",), contexts=("all",)),
            predicate=PredicateSpec(operator="element_type_absent",
                                    parameters={"element_types": ["kicker"]}),
            override_policy=OverridePolicy.NEVER,
            enforcement=("creative_spec",), repair_strategy=None,
            origin=Origin(feedback_event_id="FE-001", actor=ActorRole.OWNER),
            rationale="No kickers", created_at=_utcnow(),
            evidence=(),
        )
        rev2 = RuleRevision(
            revision=2, rule_id="CF-0001", status=RuleStatus.SUPERSEDED,
            kind=FeedbackType.HARD_DONT, scope=Scope(ScopeLevel.GLOBAL),
            applies_to=EntityTarget(node_types=("kicker",), contexts=("all",)),
            predicate=PredicateSpec(operator="element_type_absent",
                                    parameters={"element_types": ["kicker"]}),
            override_policy=OverridePolicy.NEVER,
            enforcement=("creative_spec",), repair_strategy=None,
            origin=Origin(feedback_event_id="FE-001", actor=ActorRole.OWNER),
            rationale="Updated", created_at=_utcnow(),
            evidence=(),
        )
        self.store.add_rule_revision(rev1)
        self.store.add_rule_revision(rev2)
        history = self.store.get_rule_history("CF-0001")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].revision, 1)
        self.assertEqual(history[1].revision, 2)

    def test_active_rules(self):
        rev = RuleRevision(
            revision=1, rule_id="CF-0001", status=RuleStatus.ACTIVE,
            kind=FeedbackType.HARD_DONT, scope=Scope(ScopeLevel.GLOBAL),
            applies_to=EntityTarget(node_types=("kicker",), contexts=("all",)),
            predicate=PredicateSpec(operator="element_type_absent",
                                    parameters={"element_types": ["kicker"]}),
            override_policy=OverridePolicy.NEVER,
            enforcement=("creative_spec",), repair_strategy=None,
            origin=Origin(feedback_event_id="FE-001", actor=ActorRole.OWNER),
            rationale="No kickers", created_at=_utcnow(),
            evidence=(),
        )
        self.store.add_rule_revision(rev)
        active = self.store.get_active_rules()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].rule_id, "CF-0001")

    def test_rule_exceptions(self):
        exc = RuleException(
            exception_id="EXC-001", rule_id="CF-0001", job_id="JOB-1",
            scope=Scope(ScopeLevel.VIDEO, video_id="JOB-1"),
            actor=ActorRole.OWNER, actor_id="owner",
            reason="One-time exception", created_at=_utcnow(),
        )
        self.store.add_exception(exc)
        excs = self.store.get_exceptions_for_job("JOB-1")
        self.assertEqual(len(excs), 1)
        self.assertEqual(excs[0].exception_id, "EXC-001")

    def test_policy_snapshot(self):
        from reels_maker.creative_memory.models import PolicySnapshot
        snap = PolicySnapshot(
            snapshot_id="POL-abc123", sha256="deadbeef",
            rules=(("CF-0001", 1),),
            exceptions_applied=(),
            compiled_at=_utcnow(),
            engine_version="creative_memory/1.0",
        )
        self.store.save_snapshot(snap)
        fetched = self.store.get_snapshot("deadbeef")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.snapshot_id, "POL-abc123")

    def test_export_json(self):
        data = self.store.export_json()
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["engine_version"], "creative_memory/1.0")


if __name__ == "__main__":
    unittest.main()