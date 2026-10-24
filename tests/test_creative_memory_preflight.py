"""Tests for preflight gates (G1/G2)."""
import unittest

from reels_maker.creative_memory.preflight import (
    audit_creative_spec, audit_render_graph, evaluate_predicate_issues,
    gate_result_to_exit_code,
)
from reels_maker.creative_memory.models import Gate, Severity


def _spec_with_kicker():
    return {
        "creative_schema_version": 1,
        "name": "test-kicker",
        "mode": "studio",
        "style": "editorial-premium",
        "video": {"width": 540, "height": 960, "fps": 24},
        "shots": [{
            "id": "s01",
            "headline": "TEST",
            "kicker": "UNAUTHORIZED",
            "duration": 3.0,
        }],
    }


def _spec_without_kicker():
    spec = _spec_with_kicker()
    spec["shots"][0] = {k: v for k, v in spec["shots"][0].items() if k != "kicker"}
    return spec


def _kicker_rule():
    return [{
        "rule_id": "CF-0001",
        "kind": "hard_dont",
        "scope": {"level": "global", "target": "*"},
        "applies_to": {"node_types": ["kicker"], "contexts": ["all"]},
        "predicate": {
            "operator": "element_type_absent",
            "parameters": {"element_types": ["kicker"], "contexts": ["all"]},
        },
        "override_policy": "never",
        "enforcement": ["creative_spec"],
        "repair_strategy": "remove_element_and_reflow",
        "status": "active",
        "current_revision": 1,
        "rationale": "No kickers",
        "created_at": "2026-10-24T16:00:00Z",
        "evidence": [],
    }]


class PreflightTests(unittest.TestCase):
    def test_audit_creative_spec_with_kicker(self):
        result = audit_creative_spec(_spec_with_kicker(), rules=_kicker_rule())
        self.assertFalse(result.ok)
        self.assertEqual(len(result.violations), 1)
        self.assertEqual(result.violations[0].code, "CF_POLICY_FORBIDDEN_ELEMENT")
        self.assertEqual(result.violations[0].rule_id, "CF-0001")

    def test_audit_creative_spec_without_kicker(self):
        result = audit_creative_spec(_spec_without_kicker(), rules=_kicker_rule())
        self.assertTrue(result.ok)
        self.assertEqual(len(result.violations), 0)

    def test_audit_creative_spec_with_invalid_schema(self):
        bad_spec = {"name": "bad", "shots": []}
        result = audit_creative_spec(bad_spec, rules=_kicker_rule())
        self.assertFalse(result.ok)
        self.assertEqual(result.violations[0].code, "CF_SCHEMA_INVALID")

    def test_audit_render_graph(self):
        manifest = {
            "schema_version": 1,
            "name": "test",
            "video": {"width": 540, "height": 960, "fps": 24},
            "scenes": [{"id": "s01", "duration": 3.0, "headline": "TEST"}],
        }
        result = audit_render_graph(manifest, rules=_kicker_rule())
        self.assertTrue(result.ok)

    def test_gate_result_to_exit_code(self):
        from reels_maker.creative_memory.models import GateResult, QAIssue
        result = GateResult(
            gate=Gate.G1_SPEC, ok=False, status="blocked",
            violations=[QAIssue(code="X", gate=Gate.G1_SPEC,
                                severity=Severity.ERROR, message="x")],
        )
        self.assertEqual(gate_result_to_exit_code(result), 3)

    def test_gate_result_to_exit_code_blocker(self):
        from reels_maker.creative_memory.models import GateResult, QAIssue
        result = GateResult(
            gate=Gate.G1_SPEC, ok=False, status="blocked",
            violations=[QAIssue(code="X", gate=Gate.G1_SPEC,
                                severity=Severity.BLOCKER, message="x")],
        )
        self.assertEqual(gate_result_to_exit_code(result), 5)


class PredicateTests(unittest.TestCase):
    def test_element_type_absent(self):
        from reels_maker.creative_memory.predicates import evaluate_predicate
        spec = _spec_with_kicker()
        issues = evaluate_predicate(
            {"operator": "element_type_absent",
             "parameters": {"element_types": ["kicker"], "contexts": ["all"]}},
            spec, "CF-0001",
        )
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["code"], "CF_POLICY_FORBIDDEN_ELEMENT")

    def test_element_type_present(self):
        from reels_maker.creative_memory.predicates import evaluate_predicate
        spec = _spec_without_kicker()
        issues = evaluate_predicate(
            {"operator": "element_type_present",
             "parameters": {"element_types": ["kicker"], "contexts": ["all"]}},
            spec, "CF-0002",
        )
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["code"], "CF_POLICY_REQUIRED_ELEMENT_MISSING")

    def test_chart_zero_origin(self):
        from reels_maker.creative_memory.predicates import evaluate_predicate
        spec = {
            "creative_schema_version": 1, "name": "test", "mode": "studio",
            "style": "editorial-premium",
            "video": {"width": 540, "height": 960, "fps": 24},
            "shots": [{
                "id": "s01", "headline": "TEST", "duration": 3.0,
                "chart": {
                    "points": [{"label": "A", "value": 10}],
                    "x_axis_label": "X", "y_axis_label": "Y",
                    "y_domain": [0, 100],
                },
            }],
        }
        issues = evaluate_predicate(
            {"operator": "chart_zero_origin", "parameters": {}},
            spec, "CF-0003",
        )
        self.assertEqual(len(issues), 0)

    def test_chart_non_zero_origin(self):
        from reels_maker.creative_memory.predicates import evaluate_predicate
        spec = {
            "creative_schema_version": 1, "name": "test", "mode": "studio",
            "style": "editorial-premium",
            "video": {"width": 540, "height": 960, "fps": 24},
            "shots": [{
                "id": "s01", "headline": "TEST", "duration": 3.0,
                "chart": {
                    "points": [{"label": "A", "value": 10}],
                    "x_axis_label": "X", "y_axis_label": "Y",
                    "y_domain": [5, 100],
                },
            }],
        }
        issues = evaluate_predicate(
            {"operator": "chart_zero_origin", "parameters": {}},
            spec, "CF-0003",
        )
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["code"], "CF_POLICY_CHART_NO_ZERO_ORIGIN")


if __name__ == "__main__":
    unittest.main()