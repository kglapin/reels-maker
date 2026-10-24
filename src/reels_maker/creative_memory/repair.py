"""Safe repair planner (spec section 11).

Selects the smallest possible fix for a detected policy violation, runs
validation again, and caps attempts.  Each repair produces a
:class:`~reels_maker.creative_memory.models.RepairAttempt` for audit.
"""
from __future__ import annotations

import copy
from typing import Any

from .models import (
    QAIssue,
    RepairAttempt,
    Severity,
)
from .preflight import audit_creative_spec


SAFE_TRANSFORMS = {
    "remove_element_and_reflow": "_safe_remove_element",
    "increase_hold": "_safe_increase_hold",
    "adjust_duration": "_safe_adjust_duration",
    "fix_chart_zeros": "_safe_fix_chart_zeros",
    "reset_rotation": "_safe_reset_rotation",
}


class RepairError(Exception):
    """No safe repair available for the given issue."""


def _safe_remove_element(spec: dict, params: dict, issue: QAIssue) -> dict:
        """Remove a forbidden element (e.g. kicker) from all shots."""
        new_spec = copy.deepcopy(spec)
        node_types = params.get("node_types", [])
        if not node_types and issue.elements:
            node_types = list(issue.elements)
        if not node_types:
            node_types = ["kicker"]
        for shot in new_spec.get("shots", []):
            for nt in node_types:
                if nt in shot:
                    del shot[nt]
        return new_spec


def _safe_increase_hold(spec: dict, params: dict, issue: QAIssue) -> dict:
    new_spec = copy.deepcopy(spec)
    increment = params.get("increment_seconds", 1.5)
    for shot in new_spec.get("shots", []):
        shot["duration"] = round(float(shot.get("duration", 2.8)) + increment, 2)
    return new_spec


def _safe_adjust_duration(spec: dict, params: dict, issue: QAIssue) -> dict:
    new_spec = copy.deepcopy(spec)
    shot_id = params.get("shot_id")
    min_dur = params.get("min_seconds", 1.0)
    for shot in new_spec.get("shots", []):
        if shot.get("id") == shot_id:
            shot["duration"] = max(float(shot.get("duration", 2.8)), min_dur)
    return new_spec


def _safe_fix_chart_zeros(spec: dict, params: dict, issue: QAIssue) -> dict:
    new_spec = copy.deepcopy(spec)
    for shot in new_spec.get("shots", []):
        chart = shot.get("chart")
        if chart and chart.get("y_domain", [0, 0])[0] != 0:
            chart["y_domain"][0] = 0
    return new_spec


def _safe_reset_rotation(spec: dict, params: dict, issue: QAIssue) -> dict:
    new_spec = copy.deepcopy(spec)
    max_angle = params.get("max_degrees", 25)
    for shot in new_spec.get("shots", []):
        rotation = shot.get("rotation", {})
        for role, rot in rotation.items():
            angle = float(rot.get("angle", 0))
            if abs(angle) > max_angle:
                rot["angle"] = 0.0
    return new_spec


def _apply_json_pointer_remove(container: Any, pointer: str) -> None:
    parts = pointer.strip("/").split("/")
    target = container
    for part in parts[:-1]:
        if isinstance(target, list) and part.isdigit():
            target = target[int(part)]
        elif isinstance(target, dict):
            target = target.get(part, {})
        else:
            return
    last = parts[-1]
    if isinstance(target, list) and last.isdigit():
        if 0 <= int(last) < len(target):
            target.pop(int(last))
    elif isinstance(target, dict) and last in target:
        del target[last]


def plan_repair(
    spec: dict[str, Any],
    issues: list[QAIssue],
    *,
    max_attempts: int = 3,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for issue in issues:
        if issue.severity == Severity.INFO:
            continue
        strategy = _infer_strategy(issue)
        if strategy is None:
            continue
        params = _infer_params(issue)
        try:
            new_spec = _apply_transform(strategy, spec, params, issue)
        except (KeyError, IndexError, TypeError):
            continue
        candidates.append({
            "action": strategy,
            "description": issue.remediation or issue.message,
            "spec": new_spec,
            "target_issue": issue.code,
            "rule_id": issue.rule_id,
        })
    return candidates[:max_attempts]


def _infer_strategy(issue: QAIssue) -> str | None:
    code = issue.code
    if code.startswith("CF_POLICY_FORBIDDEN_ELEMENT"):
        return "remove_element_and_reflow"
    if code.startswith("CF_POLICY_DURATION"):
        return "adjust_duration"
    if code.startswith("CF_POLICY_HOLD"):
        return "increase_hold"
    if code.startswith("CF_POLICY_CHART"):
        return "fix_chart_zeros"
    if code.startswith("CF_POLICY_ROTATION"):
        return "reset_rotation"
    if issue.remediation and issue.remediation in SAFE_TRANSFORMS:
        return issue.remediation
    return None


def _infer_params(issue: QAIssue) -> dict[str, Any]:
    params: dict[str, Any] = {"rule_id": issue.rule_id or ""}
    if issue.elements:
        params["json_pointers"] = [f"$.shots[@.*]" for _ in issue.elements]
    if issue.scene_id:
        params["shot_id"] = issue.scene_id
    return params


def _apply_transform(
    strategy: str, spec: dict, params: dict, issue: QAIssue
) -> dict:
    func_name = SAFE_TRANSFORMS.get(strategy)
    if func_name is None:
        raise RepairError(f"Unknown repair strategy: {strategy}")
    func = globals().get(func_name)
    if func is None:
        raise RepairError(f"Transform not implemented: {func_name}")
    return func(spec, params, issue)


def run_repair_loop(
    spec: dict[str, Any],
    issues: list[QAIssue],
    *,
    max_attempts: int = 3,
) -> dict[str, Any]:
    attempts: list[RepairAttempt] = []
    current_spec = copy.deepcopy(spec)
    current_violations = len([
        i for i in issues if i.severity in (Severity.ERROR, Severity.BLOCKER)
    ])

    for attempt_no in range(1, max_attempts + 1):
        candidates = plan_repair(current_spec, issues, max_attempts=max_attempts)
        if not candidates:
            break

        best = None
        best_score = (current_violations, 0)
        for candidate in candidates:
            candidate_spec = candidate["spec"]
            rules_for_check = _extract_rules_from_issues(issues)
            result = audit_creative_spec(candidate_spec, rules=rules_for_check)
            after = len(result.violations)
            new_violations = _count_new_violations(result.violations, issues)
            score = (after, new_violations)
            if score < best_score or best is None:
                best_score = score
                best = (candidate, result, after, new_violations)

        if best is None:
            break

        candidate, result, after, new_violations = best
        attempt = RepairAttempt(
            attempt=attempt_no,
            action=candidate["action"],
            violations_before=current_violations,
            violations_after=after,
            new_violations=new_violations,
            description=candidate["description"],
        )
        attempts.append(attempt)

        if after == 0 and new_violations == 0:
            return {
                "ok": True,
                "repaired": True,
                "attempts": [a.to_dict() for a in attempts],
                "spec": candidate["spec"],
            }
        current_spec = candidate["spec"]
        current_violations = after
        issues = result.violations

    return {
        "ok": current_violations == 0,
        "repaired": any(a.violations_after < a.violations_before for a in attempts),
        "attempts": [a.to_dict() for a in attempts],
        "spec": current_spec,
    }


def _extract_rules_from_issues(issues: list[QAIssue]) -> list[dict[str, Any]]:
    rule_ids = set()
    for issue in issues:
        if issue.rule_id:
            rule_ids.add(issue.rule_id)
    return [
        {
            "rule_id": rid,
            "kind": "hard_dont",
            "scope": {"level": "global"},
            "applies_to": {"node_types": ["*"], "contexts": ["all"]},
            "predicate": {"operator": "element_type_absent", "parameters": {}},
            "override_policy": "never",
            "enforcement": ["creative_spec"],
            "repair_strategy": None,
            "status": "active",
            "current_revision": 1,
            "rationale": "",
            "created_at": "2026-01-01T00:00:00Z",
            "evidence": [],
        }
        for rid in rule_ids
    ]


def _count_new_violations(
    new_violations: list[QAIssue], old_issues: list[QAIssue]
) -> int:
    old_codes = {i.code for i in old_issues}
    return sum(1 for v in new_violations if v.code not in old_codes)


__all__ = [
    "RepairError",
    "plan_repair",
    "run_repair_loop",
    "SAFE_TRANSFORMS",
]
