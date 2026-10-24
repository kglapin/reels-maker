"""Reporting utilities for creative-memory QA issues and gate results."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .models import (
    Gate,
    GateResult,
    QAIssue,
    Severity,
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_qa_report(
    gate: Gate,
    snapshot_sha: str | None,
    spec_sha: str | None,
    render_sha: str | None,
    violations: list[QAIssue] | None = None,
    warnings: list[QAIssue] | None = None,
    checked_rules: list[str] | None = None,
    unchecked_rules: list[str] | None = None,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    violations = violations or []
    warnings = warnings or []
    error_count = sum(
        1 for v in violations
        if v.severity in (Severity.ERROR, Severity.BLOCKER)
    )
    warn_count = len(warnings) + sum(
        1 for v in violations if v.severity == Severity.WARNING
    )
    ok = error_count == 0
    return {
        "schema_version": 1,
        "status": "ok" if ok else "error",
        "ok": ok,
        "gate": gate.value,
        "timestamp": _utcnow(),
        "summary": {
            "checked_rules": checked_rules or [],
            "unchecked_rules": unchecked_rules or [],
            "violations": [v.to_dict() for v in violations],
            "warnings": [w.to_dict() for w in warnings],
            "errors": error_count,
            "warnings_count": warn_count,
        },
        "evidence": {
            "policy_sha256": snapshot_sha,
            "spec_sha256": spec_sha,
            "render_sha256": render_sha,
        },
        "limitations": limitations or [],
        "next_action": "repair" if violations else "proceed",
        "human_review_required": warn_count > 0,
    }


def gate_result_to_report(
    result: GateResult,
    *,
    spec_sha: str | None = None,
    render_sha: str | None = None,
) -> dict[str, Any]:
    return build_qa_report(
        gate=result.gate,
        snapshot_sha=result.policy_sha256,
        spec_sha=spec_sha,
        render_sha=render_sha,
        violations=result.violations,
        warnings=result.warnings,
        checked_rules=result.checked_rules,
        unchecked_rules=result.unchecked_rules,
        limitations=result.limitations,
    )


def format_issue_summary(issue: QAIssue) -> str:
    parts = [f"[{issue.severity.value.upper()}] {issue.code}"]
    if issue.rule_id:
        parts.append(f"rule={issue.rule_id}")
    if issue.scene_id:
        parts.append(f"scene={issue.scene_id}")
    if issue.time is not None:
        parts.append(f"time={issue.time:.2f}s")
    parts.append(issue.message)
    return " ".join(parts)


def print_report(report: dict[str, Any], *, stream=None) -> None:
    import sys
    s = stream or sys.stdout
    s.write(f"Gate: {report.get('gate', 'N/A')}\n")
    s.write(f"Status: {report['status']}\n")
    s.write(f"Errors: {report['summary']['errors']}\n")
    s.write(f"Warnings: {report['summary']['warnings_count']}\n")
    s.write(f"Checked rules: {len(report['summary']['checked_rules'])}\n")
    s.write(f"Unchecked rules: {len(report['summary']['unchecked_rules'])}\n")
    for v in report["summary"]["violations"]:
        s.write(f"  {format_issue_summary(QAIssue.from_dict(v))}\n")
    for w in report["summary"]["warnings"]:
        s.write(f"  {format_issue_summary(QAIssue.from_dict(w))}\n")
    if report.get("limitations"):
        s.write("Limitations:\n")
        for lim in report["limitations"]:
            s.write(f"  - {lim}\n")


def report_to_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)


__all__ = [
    "build_qa_report",
    "gate_result_to_report",
    "format_issue_summary",
    "print_report",
    "report_to_json",
]
