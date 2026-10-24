"""Deterministic predicate engine for creative-policy rules.

Each predicate evaluates a concrete, checkable property of the Creative Spec
or the compiled Studio manifest.  An LLM can never override these checks:
they are pure functions of structured data.

Supported operators (per spec section 5.2 / 9):

element_type_absent / element_type_present
value_range_check
text_matches / text_excludes
chart_zero_origin
rotation_angle_within
duration_minimum
hold_minimum
safe_area_violation
contrast_minimum
data_consistency
"""
from __future__ import annotations

from typing import Any, Callable

from ..design.color import contrast_ratio
from ..creative.spec import validate_creative_spec


PredicateFunc = Callable[[dict, str | None], list[dict]]


def _issue(code: str, severity: str, message: str,
           json_pointer: str | None, rule_id: str | None) -> dict:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "json_pointer": json_pointer,
        "rule_id": rule_id,
    }


def _find_shot(spec: dict, shot_id: str | None) -> dict | None:
    for shot in spec.get("shots", []):
        if shot.get("id") == shot_id:
            return shot
    return None if shot_id else (spec.get("shots", [{}])[0] if spec.get("shots") else None)


def _iter_shot_elements(shot: dict) -> list[tuple[str, Any]]:
    """Yield (role, value) pairs for known element roles in a shot."""
    result = []
    for role in ("kicker", "headline", "subtitle"):
        if role in shot and shot[role]:
            result.append((role, shot[role]))
    if "chart" in shot:
        result.append(("chart", shot["chart"]))
    if "value" in shot:
        result.append(("value", shot["value"]))
    return result


# --------------------------------------------------------------------------- #
#  individual predicate implementations
# --------------------------------------------------------------------------- #
def _pred_element_type_absent(spec: dict, params: dict, rule_id: str | None) -> list[dict]:
    issues = []
    node_types = params.get("element_types", [params.get("element_type", "kicker")])
    contexts = set(params.get("contexts", ["all"]))
    mode = spec.get("mode", "studio")
    for idx, shot in enumerate(spec.get("shots", [])):
        if "all" not in contexts and mode not in contexts:
            continue
        for role, value in _iter_shot_elements(shot):
            if role in node_types and value:
                issues.append(_issue(
                    "CF_POLICY_FORBIDDEN_ELEMENT", "error",
                    f"Forbidden element '{role}' present in shot '{shot.get('id')}'.",
                    f"$.shots[{idx}].{role}", rule_id,
                ))
    return issues


def _pred_element_type_present(spec: dict, params: dict, rule_id: str | None) -> list[dict]:
    issues = []
    node_types = params.get("element_types", [params.get("element_type", "kicker")])
    contexts = set(params.get("contexts", ["all"]))
    mode = spec.get("mode", "studio")
    for idx, shot in enumerate(spec.get("shots", [])):
        if "all" not in contexts and mode not in contexts:
            continue
        found = any(role in node_types and shot.get(role) for role, _ in _iter_shot_elements(shot))
        if not found:
            issues.append(_issue(
                "CF_POLICY_REQUIRED_ELEMENT_MISSING", "error",
                f"Required element type {list(node_types)} missing from shot '{shot.get('id')}'.",
                f"$.shots[{idx}]", rule_id,
            ))
    return issues


def _pred_value_range_check(spec: dict, params: dict, rule_id: str | None) -> list[dict]:
    issues = []
    path = params.get("path", "chart")
    lo = params.get("min")
    hi = params.get("max")
    shot_id = params.get("shot_id")
    shot = _find_shot(spec, shot_id) if shot_id else None
    shots_to_check = [shot] if shot else spec.get("shots", [])
    for idx, s in enumerate(spec.get("shots", [])):
        if shot is not None and s.get("id") != shot_id:
            continue
        chart = s.get("chart")
        if not chart:
            continue
        for pi, point in enumerate(chart.get("points", [])):
            val = point.get("value")
            if lo is not None and val < lo:
                issues.append(_issue(
                    "CF_POLICY_VALUE_BELOW_MIN", "error",
                    f"Value {val} below minimum {lo} in chart point {pi}.",
                    f"$.shots[{idx}].chart.points[{pi}].value", rule_id,
                ))
            if hi is not None and val > hi:
                issues.append(_issue(
                    "CF_POLICY_VALUE_ABOVE_MAX", "error",
                    f"Value {val} above maximum {hi} in chart point {pi}.",
                    f"$.shots[{idx}].chart.points[{pi}].value", rule_id,
                ))
    return issues


def _pred_text_matches(spec: dict, params: dict, rule_id: str | None) -> list[dict]:
    import re
    issues = []
    role = params.get("role", "kicker")
    pattern = params.get("pattern", "")
    flags = re.IGNORECASE if params.get("ignore_case", True) else 0
    regex = re.compile(pattern, flags)
    for idx, shot in enumerate(spec.get("shots", [])):
        val = shot.get(role, "")
        if val and not regex.search(val):
            issues.append(_issue(
                "CF_POLICY_TEXT_MISMATCH", "warning",
                f"Text in '{role}' of shot '{shot.get('id')}' does not match required pattern.",
                f"$.shots[{idx}].{role}", rule_id,
            ))
    return issues


def _pred_text_excludes(spec: dict, params: dict, rule_id: str | None) -> list[dict]:
    import re
    issues = []
    role = params.get("role")
    pattern = params.get("pattern", "")
    flags = re.IGNORECASE if params.get("ignore_case", True) else 0
    regex = re.compile(pattern, flags)
    for idx, shot in enumerate(spec.get("shots", [])):
        if role:
            val = shot.get(role, "")
            if isinstance(val, str) and regex.search(val):
                issues.append(_issue(
                    "CF_POLICY_TEXT_EXCLUDES", "error",
                    f"Forbidden text pattern found in '{role}' of shot '{shot.get('id')}'.",
                    f"$.shots[{idx}].{role}", rule_id,
                ))
        else:
            for r, v in _iter_shot_elements(shot):
                if isinstance(v, str) and regex.search(v):
                    issues.append(_issue(
                        "CF_POLICY_TEXT_EXCLUDES", "error",
                        f"Forbidden text pattern found in '{r}' of shot '{shot.get('id')}'.",
                        f"$.shots[{idx}].{r}", rule_id,
                    ))
    return issues


def _pred_chart_zero_origin(spec: dict, params: dict, rule_id: str | None) -> list[dict]:
    issues = []
    for idx, shot in enumerate(spec.get("shots", [])):
        chart = shot.get("chart")
        if not chart:
            continue
        y_domain = chart.get("y_domain", [])
        if not y_domain or y_domain[0] != 0:
            issues.append(_issue(
                "CF_POLICY_CHART_NO_ZERO_ORIGIN", "error",
                f"Chart in shot '{shot.get('id')}' does not start y-axis at 0.",
                f"$.shots[{idx}].chart.y_domain", rule_id,
            ))
    return issues


def _pred_rotation_angle_within(spec: dict, params: dict, rule_id: str | None) -> list[dict]:
    issues = []
    max_angle = params.get("max_degrees", 25)
    for idx, shot in enumerate(spec.get("shots", [])):
        rotation = shot.get("rotation", {})
        if not rotation:
            continue
        for role, rot in rotation.items():
            angle = rot.get("angle", 0)
            if abs(angle) > max_angle:
                issues.append(_issue(
                    "CF_POLICY_ROTATION_EXCEEDS_LIMIT", "error",
                    f"Rotation angle {angle}° for '{role}' exceeds limit {max_angle}°.",
                    f"$.shots[{idx}].rotation.{role}.angle", rule_id,
                ))
    return issues


def _pred_duration_minimum(spec: dict, params: dict, rule_id: str | None) -> list[dict]:
    issues = []
    min_dur = params.get("min_seconds", 1.0)
    for idx, shot in enumerate(spec.get("shots", [])):
        dur = float(shot.get("duration", 2.8))
        if dur < min_dur:
            issues.append(_issue(
                "CF_POLICY_DURATION_TOO_SHORT", "error",
                f"Shot '{shot.get('id')}' duration {dur}s below minimum {min_dur}s.",
                f"$.shots[{idx}].duration", rule_id,
            ))
    return issues


def _pred_hold_minimum(spec: dict, params: dict, rule_id: str | None) -> list[dict]:
    issues = []
    min_hold = params.get("min_seconds", 0.55)
    mode = spec.get("mode", "studio")
    for idx, shot in enumerate(spec.get("shots", [])):
        dur = float(shot.get("duration", 2.8))
        if mode == "camera_canvas":
            cam = shot.get("camera", {})
            move = cam.get("move_duration", 0.88)
            reveal_delay = cam.get("reveal_delay", 0.18)
            reveal = cam.get("reveal_duration", 0.56)
            hold = dur - move - reveal_delay - reveal
        else:
            hold = dur * 0.45
        if hold < min_hold:
            issues.append(_issue(
                "CF_POLICY_HOLD_TOO_SHORT", "error",
                f"Shot '{shot.get('id')}' has only {hold:.2f}s readable hold (minimum {min_hold}s).",
                f"$.shots[{idx}].duration", rule_id,
            ))
    return issues


def _pred_safe_area_violation(spec: dict, params: dict, rule_id: str | None) -> list[dict]:
    issues = []
    w = spec.get("video", {}).get("width", 540)
    h = spec.get("video", {}).get("height", 960)
    margin = params.get("margin_percent", 5) / 100.0
    safe_w = w * (1 - 2 * margin)
    safe_h = h * (1 - 2 * margin)
    for idx, shot in enumerate(spec.get("shots", [])):
        if shot.get("headline", ""):
            issues.append(_issue(
                "CF_POLICY_SAFE_AREA_VIOLATION", "warning",
                f"Safe-area check requires frame-level rendering; shot '{shot.get('id')}' marked unverified.",
                f"$.shots[{idx}]", rule_id,
            ))
    _ = safe_w, safe_h
    return issues


def _pred_contrast_minimum(spec: dict, params: dict, rule_id: str | None) -> list[dict]:
    issues = []
    min_ratio = params.get("min_ratio", 4.5)
    for idx, shot in enumerate(spec.get("shots", [])):
        issues.append(_issue(
            "CF_POLICY_CONTRAST_UNVERIFIED", "warning",
            f"Contrast check requires rendered frame; shot '{shot.get('id')}' requires post-render verification.",
            f"$.shots[{idx}]", rule_id,
        ))
        _ = min_ratio
    return issues


def _pred_data_consistency(spec: dict, params: dict, rule_id: str | None) -> list[dict]:
    issues = []
    for idx, shot in enumerate(spec.get("shots", [])):
        chart = shot.get("chart")
        if not chart:
            continue
        points = chart.get("points", [])
        if points and any(p.get("value") is None for p in points):
            issues.append(_issue(
                "CF_POLICY_DATA_MISSING_VALUES", "error",
                f"Chart in shot '{shot.get('id')}' has null values.",
                f"$.shots[{idx}].chart", rule_id,
            ))
        y_domain = chart.get("y_domain", [])
        if y_domain and len(y_domain) == 2:
            lo, hi = y_domain
            for pi, point in enumerate(points):
                val = point.get("value")
                if val is not None and (val < lo or val > hi):
                    issues.append(_issue(
                        "CF_POLICY_VALUE_OUT_OF_DOMAIN", "error",
                        f"Value {val} outside chart domain [{lo}, {hi}]",
                        f"$.shots[{idx}].chart.points[{pi}].value", rule_id,
                    ))
    return issues


_PREDICATE_REGISTRY: dict[str, PredicateFunc] = {
    "element_type_absent": _pred_element_type_absent,
    "element_type_present": _pred_element_type_present,
    "value_range_check": _pred_value_range_check,
    "text_matches": _pred_text_matches,
    "text_excludes": _pred_text_excludes,
    "chart_zero_origin": _pred_chart_zero_origin,
    "rotation_angle_within": _pred_rotation_angle_within,
    "duration_minimum": _pred_duration_minimum,
    "hold_minimum": _pred_hold_minimum,
    "safe_area_violation": _pred_safe_area_violation,
    "contrast_minimum": _pred_contrast_minimum,
    "data_consistency": _pred_data_consistency,
}


def predicate_evaluators() -> dict[str, PredicateFunc]:
    return dict(_PREDICATE_REGISTRY)


def evaluate_predicate(predicate: dict, spec: dict, rule_id: str | None = None) -> list[dict]:
    """Evaluate a single predicate dict against a spec.  Returns issue list."""
    if not isinstance(predicate, dict):
        raise ValueError("predicate must be a dict")
    operator = predicate.get("operator")
    if not operator:
        raise ValueError("predicate missing 'operator'")
    func = _PREDICATE_REGISTRY.get(operator)
    if func is None:
        raise ValueError(f"Unknown predicate operator: {operator}")
    params = predicate.get("parameters", {})
    return func(spec, params, rule_id)


def evaluate_rule(rule: "Any", spec: dict) -> list[dict]:
    """Evaluate all predicates of a rule against a spec."""
    issues = []
    pred = rule.predicate
    if pred is None:
        return issues
    predicate_dict = pred.to_dict()
    issues.extend(evaluate_predicate(predicate_dict, spec, rule.rule_id))
    return issues


def validate_rule_predicate(predicate_dict: dict) -> list[str]:
    """Validate that a predicate dict uses known operators and valid params."""
    errors = []
    if not isinstance(predicate_dict, dict):
        return ["predicate must be a dict"]
    operator = predicate_dict.get("operator")
    if not operator:
        errors.append("predicate missing 'operator'")
    elif operator not in _PREDICATE_REGISTRY:
        errors.append(f"unknown operator: {operator}")
    params = predicate_dict.get("parameters", {})
    if not isinstance(params, dict):
        errors.append("predicate 'parameters' must be a dict")
    return errors


__all__ = [
    "evaluate_predicate",
    "evaluate_rule",
    "validate_rule_predicate",
    "predicate_evaluators",
    "SCHEMA_VERSION_COMPAT",
]

SCHEMA_VERSION_COMPAT = "v1"
