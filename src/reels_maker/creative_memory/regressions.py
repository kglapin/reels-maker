"""Regression case catalog (spec section 14).

Stores and runs minimal, reproducible test cases for policy rules.
Each regression case captures the spec, the rule it exercises, and the
expected violation so that a policy change cannot silently re-introduce
a previously caught error.
"""
from __future__ import annotations

import json
from typing import Any

from .models import RegressionCase
from .preflight import audit_creative_spec


class RegressionSuite:
    """Minimal in-memory regression runner over a list of cases."""

    def __init__(self, cases: list[RegressionCase] | None = None) -> None:
        self._cases: list[RegressionCase] = list(cases or [])

    def add(self, case: RegressionCase) -> None:
        self._cases.append(case)

    def cases_for_rule(self, rule_id: str) -> list[RegressionCase]:
        return [c for c in self._cases if c.rule_id == rule_id]

    @property
    def all_cases(self) -> list[RegressionCase]:
        return list(self._cases)

    def run(self, rules: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        passed = 0
        failed = 0
        for case in self._cases:
            try:
                gate = audit_creative_spec(case.spec, rules=rules)
                violation_codes = {v.code for v in gate.violations}
                expected = case.expected_violation
                matched = expected in violation_codes
                if matched:
                    passed += 1
                else:
                    failed += 1
                results.append({
                    "case_id": case.case_id,
                    "rule_id": case.rule_id,
                    "passed": matched,
                    "expected_violation": expected,
                    "actual_codes": sorted(violation_codes),
                    "description": case.description,
                })
            except Exception as exc:
                failed += 1
                results.append({
                    "case_id": case.case_id,
                    "rule_id": case.rule_id,
                    "passed": False,
                    "expected_violation": case.expected_violation,
                    "actual_codes": [],
                    "error": str(exc),
                })
        return {
            "schema_version": 1,
            "ok": failed == 0,
            "cases_run": len(self._cases),
            "passed": passed,
            "failed": failed,
            "results": results,
        }

    def to_json(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._cases]

    @classmethod
    def from_json(cls, data: list[dict[str, Any]]) -> "RegressionSuite":
        cases = [RegressionCase(
            case_id=c["case_id"],
            rule_id=c["rule_id"],
            spec=c["spec"],
            expected_violation=c["expected_violation"],
            description=c["description"],
            added_at=c["added_at"],
            added_by=c.get("added_by"),
        ) for c in data]
        return cls(cases)


def load_regression_suite(path: str | Any) -> RegressionSuite:
    """Load a regression suite from a JSON file."""
    import pathlib
    p = pathlib.Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "cases" in data:
        data = data["cases"]
    return RegressionSuite.from_json(data)


def save_regression_suite(suite: RegressionSuite, path: str | Any) -> None:
    """Save a regression suite to a JSON file."""
    import pathlib
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(suite.to_json(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


KICKER_FORBIDDEN_REGRESSIONS: list[dict[str, Any]] = [
    {
        "case_id": "REG-KICKER-001",
        "rule_id": "CF-0001",
        "spec": {
            "creative_schema_version": 1,
            "name": "kicker-test",
            "mode": "studio",
            "style": "editorial-premium",
            "video": {"width": 540, "height": 960, "fps": 24},
            "shots": [{
                "id": "s01",
                "headline": "TEST",
                "kicker": "UNAUTHORIZED",
                "duration": 3.0,
            }],
        },
        "expected_violation": "CF_POLICY_FORBIDDEN_ELEMENT",
        "description": "Kicker present — must be caught by HARD_DONT rule.",
    },
]


__all__ = [
    "RegressionSuite",
    "load_regression_suite",
    "save_regression_suite",
    "KICKER_FORBIDDEN_REGRESSIONS",
]
