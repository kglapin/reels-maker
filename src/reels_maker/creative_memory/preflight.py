"""Policy preflight gates (G1 Creative Spec, G2 Render Graph/Geometry).

Checks a Creative Spec or compiled Studio manifest against an active
:class:`~reels_maker.creative_memory.models.PolicySnapshot`.  Each check is
deterministic; an LLM can never override a hard gate result.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from .models import (
    Gate,
    GateResult,
    QAIssue,
    Severity,
)
from .predicates import predicate_evaluators, validate_rule_predicate
from .store import CreativeMemoryStore


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class PreflightError(Exception):
    """Raised when the spec fails schema validation before policy checks."""


def _spec_sha256(spec: dict[str, Any]) -> str:
    encoded = json.dumps(spec, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class _SafeEnum:
    def __init__(self, value: str) -> None:
        self._value = value

    @property
    def value(self) -> str:
        return self._value

    @property
    def name(self) -> str:
        return self._value.upper()


class _SafeScope:
    def __init__(self, data: dict[str, Any]) -> None:
        self.level = _SafeEnum(data.get("level", "global"))
        self.brand = data.get("brand")
        self.project = data.get("project")
        self.scene_id = data.get("scene_id")
        self.target = data.get("target", "*")


class _SafePredicate:
    def __init__(self, data: dict[str, Any]) -> None:
        self.operator = data.get("operator", "")
        self.parameters = data.get("parameters", {})

    def to_dict(self) -> dict[str, Any]:
        return {"operator": self.operator, "parameters": self.parameters}


class _SimpleRule:
    def __init__(self, data: dict[str, Any]) -> None:
        self.rule_id = data["rule_id"]
        self.kind = _SafeEnum(data["kind"])
        self.scope = _SafeScope(data["scope"])
        self.applies_to = data.get("applies_to", {})
        pred = data.get("predicate")
        self.predicate = _SafePredicate(pred) if pred else None
        self.override_policy = data.get("override_policy", "never")
        self.enforcement = tuple(data.get("enforcement", []))
        self.repair_strategy = data.get("repair_strategy")
        self.status = _SafeEnum(data.get("status", "active"))
        self.current_revision = data.get("current_revision", 1)
        self.rationale = data.get("rationale", "")


def _dict_to_rule(data: dict[str, Any]) -> _SimpleRule:
    return _SimpleRule(data)


def evaluate_predicate_issues(
    predicate: _SafePredicate,
    spec: dict[str, Any],
    rule_id: str | None = None,
) -> list[dict[str, Any]]:
    """Evaluate a predicate and return raw issue dicts with enriched context."""
    evaluator = predicate_evaluators().get(predicate.operator)
    if evaluator is None:
        return []
    return evaluator(spec, predicate.parameters, rule_id)


def audit_creative_spec(
    spec: dict[str, Any],
    *,
    policy_snapshot: dict[str, Any] | None = None,
    rules: list[dict[str, Any]] | None = None,
    store: CreativeMemoryStore | None = None,
) -> GateResult:
    """Gate 1: validate Creative Spec schema + policy rules.

    Parameters
    ----------
    spec:
        The Creative Spec v1 document.
    policy_snapshot:
        Optional pre-computed snapshot dict with ``rules`` (list of rule dicts).
    rules:
        Optional explicit list of active rule dicts (overrides snapshot).
    store:
        Optional store from which to load active rules.
    """
    limitations = [
        "Policy checks are limited to structurally detectable predicates.",
        "Perceptual decisions require post-render visual QA (Gate G3/G4).",
    ]

    rule_list: list[dict[str, Any]] = []
    if rules is not None:
        rule_list = list(rules)
    elif policy_snapshot is not None:
        rule_list = list(policy_snapshot.get("rules", []))
    elif store is not None:
        rule_list = [r.to_dict() for r in store.get_active_rules()]

    try:
        from ..creative.spec import validate_creative_spec
        validate_creative_spec(spec)
        spec_ok = True
        schema_errors = []
    except Exception as exc:
        spec_ok = False
        schema_errors = [str(exc)]

    checked_rules: list[str] = []
    unchecked_rules: list[str] = []
    violations: list[QAIssue] = []
    warnings: list[QAIssue] = []

    if not spec_ok:
        for err in schema_errors:
            violations.append(QAIssue(
                code="CF_SCHEMA_INVALID",
                gate=Gate.G1_SPEC,
                severity=Severity.BLOCKER,
                message=err,
            ))
        return GateResult(
            gate=Gate.G1_SPEC,
            ok=False,
            status="blocked",
            violations=violations,
            warnings=warnings,
            checked_rules=[],
            unchecked_rules=[],
            limitations=limitations,
            policy_sha256=policy_snapshot.get("sha256") if policy_snapshot else None,
        )

    for rule_dict in rule_list:
        rule_obj = _dict_to_rule(rule_dict)
        rule_id = rule_obj.rule_id
        pred = rule_obj.predicate
        if pred is None:
            unchecked_rules.append(rule_id)
            continue

        param_errors = validate_rule_predicate(pred.to_dict())
        if param_errors:
            unchecked_rules.append(rule_id)
            warnings.append(QAIssue(
                code="CF_POLICY_INVALID_PREDICATE",
                gate=Gate.G1_SPEC,
                severity=Severity.WARNING,
                message=f"Rule {rule_id} has invalid predicate: {param_errors}",
            ))
            continue

        checked_rules.append(rule_id)
        issues = evaluate_predicate_issues(pred, spec, rule_id)

        for issue in issues:
            qa = QAIssue(
                code=issue["code"],
                gate=Gate.G1_SPEC,
                severity=Severity(issue["severity"]),
                message=issue["message"],
                rule_id=rule_id,
                revision=rule_obj.current_revision,
                scene_id=issue.get("scene_id"),
                elements=tuple(issue.get("elements", [])),
                remediation=issue.get("remediation"),
                policy_sha256=policy_snapshot.get("sha256") if policy_snapshot else None,
                status="unverified",
            )
            if qa.severity in (Severity.ERROR, Severity.BLOCKER):
                violations.append(qa)
            else:
                warnings.append(qa)

    has_blockers = any(v.severity == Severity.BLOCKER for v in violations)
    ok = spec_ok and not violations and not has_blockers
    return GateResult(
        gate=Gate.G1_SPEC,
        ok=ok,
        status="pass" if ok else ("blocked" if has_blockers else "review_required"),
        violations=violations,
        warnings=warnings,
        checked_rules=checked_rules,
        unchecked_rules=unchecked_rules,
        limitations=limitations,
        policy_sha256=policy_snapshot.get("sha256") if policy_snapshot else None,
    )


def audit_render_graph(
    manifest: dict[str, Any],
    *,
    policy_snapshot: dict[str, Any] | None = None,
    rules: list[dict[str, Any]] | None = None,
    spec: dict[str, Any] | None = None,
    store: CreativeMemoryStore | None = None,
) -> GateResult:
    """Gate 2: validate compiled manifest/render graph against policy rules.

    Checks the actual compiled scene properties — not just what the LLM
    requested, but what the compiler actually produced.
    """
    limitations = [
        "Render-graph geometry checks are structural; pixel-level QA "
        "requires Gate G3/G4.",
        "Transformations applied by the renderer are not fully reconstructed here.",
    ]

    rule_list: list[dict[str, Any]] = []
    if rules is not None:
        rule_list = list(rules)
    elif policy_snapshot is not None:
        rule_list = list(policy_snapshot.get("rules", []))
    elif store is not None:
        rule_list = [r.to_dict() for r in store.get_active_rules()]

    checked_rules: list[str] = []
    unchecked_rules: list[str] = []
    violations: list[QAIssue] = []
    warnings: list[QAIssue] = []

    for rule_dict in rule_list:
        rule_obj = _dict_to_rule(rule_dict)
        rule_id = rule_obj.rule_id
        pred = rule_obj.predicate
        if pred is None:
            unchecked_rules.append(rule_id)
            continue

        checked_rules.append(rule_id)
        target_spec = spec if spec is not None else manifest
        issues = evaluate_predicate_issues(pred, target_spec, rule_id)

        for issue in issues:
            qa = QAIssue(
                code=issue["code"],
                gate=Gate.G2_STRUCTURAL,
                severity=Severity(issue["severity"]),
                message=issue["message"],
                rule_id=rule_id,
                revision=rule_obj.current_revision,
                scene_id=issue.get("scene_id"),
                elements=tuple(issue.get("elements", [])),
                remediation=issue.get("remediation"),
                policy_sha256=policy_snapshot.get("sha256") if policy_snapshot else None,
                status="unverified",
            )
            if qa.severity == Severity.ERROR:
                violations.append(qa)
            else:
                warnings.append(qa)

    ok = not violations
    return GateResult(
        gate=Gate.G2_STRUCTURAL,
        ok=ok,
        status="pass" if ok else "review_required",
        violations=violations,
        warnings=warnings,
        checked_rules=checked_rules,
        unchecked_rules=unchecked_rules,
        limitations=limitations,
        policy_sha256=policy_snapshot.get("sha256") if policy_snapshot else None,
    )


def gate_result_to_exit_code(result: GateResult) -> int:
    """Map a GateResult to the appropriate exit code (spec section 12)."""
    if result.ok:
        return 0
    for issue in result.violations:
        if issue.severity == Severity.BLOCKER:
            return 5
        if issue.severity == Severity.ERROR:
            return 3
    return 6


def gate_result_to_json(result: GateResult) -> dict[str, Any]:
    """Serialize a GateResult to the JSON-first CLI contract."""
    return {
        "schema_version": 1,
        "status": "ok" if result.ok else "error",
        "ok": result.ok,
        "gate": result.gate.value,
        "check_result": {
            "ok": result.ok,
            "status": result.status,
            "errors": sum(
                1 for v in result.violations
                if v.severity in (Severity.ERROR, Severity.BLOCKER)
            ),
            "warnings": len(result.warnings),
            "violations": [v.to_dict() for v in result.violations],
            "warnings_list": [w.to_dict() for w in result.warnings],
            "checked_rules": result.checked_rules,
            "unchecked_rules": result.unchecked_rules,
            "limitations": result.limitations,
            "policy_sha256": result.policy_sha256,
            "next_action": "repair" if result.violations else "proceed",
            "human_review_required": any(
                v.severity == Severity.WARNING for v in result.warnings
            ),
        },
    }


__all__ = [
    "PreflightError",
    "audit_creative_spec",
    "audit_render_graph",
    "evaluate_predicate_issues",
    "gate_result_to_exit_code",
    "gate_result_to_json",
]
