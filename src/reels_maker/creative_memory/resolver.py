"""Policy resolver.

For a given job context, computes the immutable set of active rules that
apply, layered by scope precedence (SCENE > VIDEO > PROJECT > BRAND > GLOBAL).
Local policies may **strengthen** but never **relax** a harder global rule.
Detects HARD_DO vs HARD_DONT conflicts and surfaces them rather than silently
choosing one.

This module performs no I/O itself — it consumes in-memory rule lists and
produces a :class:`~reels_maker.creative_memory.models.PolicySnapshot`.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Iterable

from .models import (
    OverridePolicy,
    PolicySnapshot,
    Rule,
    RuleException,
    RuleStatus,
    Scope,
    ScopeLevel,
)
from .store import CreativeMemoryStore

ENGINE_VERSION = "creative_memory/1.0"


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class PolicyConflictError(Exception):
    """Two hard rules of opposite kind cannot both be satisfied."""


class PolicyResolver:
    """Resolves the effective policy set for a given job/scope context.

    Parameters
    ----------
    rules:
        Iterable of :class:`Rule` objects (typically all active rules).
    exceptions:
        Iterable of :class:`RuleException` objects for a specific job.
    """

    def __init__(
        self,
        rules: Iterable[Rule],
        exceptions: Iterable[RuleException] | None = None,
    ) -> None:
        self._rules = list(rules)
        self._exceptions = list(exceptions or [])

    def resolve(
        self,
        *,
        job_id: str | None = None,
        brand: str | None = None,
        project: str | None = None,
        video_id: str | None = None,
        scene_id: str | None = None,
        platform: str | None = None,
        context: str | None = None,
    ) -> tuple[PolicySnapshot, list[dict[str, Any]]]:
        """Build an immutable :class:`PolicySnapshot` for the given scope.

        Returns ``(snapshot, diagnostics)``.  Raises
        :class:`PolicyConflictError` when an unresolved conflict exists.
        """
        effective_scope = Scope(
            level=(
                ScopeLevel.SCENE if scene_id
                else ScopeLevel.VIDEO if job_id
                else ScopeLevel.BRAND if brand
                else ScopeLevel.PROJECT
            ),
            target="*",
            brand=brand,
            project=project,
            video_id=video_id or job_id,
            scene_id=scene_id,
            platform=platform,
            context=context,
        )

        applied_exceptions: set[str] = set()
        conflict_checks: list[dict[str, Any]] = []

        active: list[Rule] = []
        for rule in self._rules:
            if rule.status != RuleStatus.ACTIVE:
                continue
            if not self._scope_matches(rule.scope, effective_scope):
                continue
            exc = self._find_exception(rule.rule_id, job_id, effective_scope)
            if exc is not None:
                applied_exceptions.add(exc.exception_id)
                conflict_checks.append({
                    "type": "exception_applied",
                    "rule_id": rule.rule_id,
                    "exception_id": exc.exception_id,
                    "scope": effective_scope.to_dict(),
                })
                continue
            active.append(rule)

        hard_dont_ids: set[str] = set()
        hard_do_ids: set[str] = set()
        for rule in active:
            if rule.kind.name == "HARD_DONT":
                hard_dont_ids.add(rule.rule_id)
            elif rule.kind.name == "HARD_DO":
                hard_do_ids.add(rule.rule_id)

        # Detect conflicts between different rules with opposite kinds
        # that share the same predicate type (e.g. both element_type_absent/present
        # on the same node types).
        conflicts: set[str] = set()
        for dont_rule in active:
            if dont_rule.kind.name != "HARD_DONT":
                continue
            for do_rule in active:
                if do_rule.kind.name != "HARD_DO":
                    continue
                if self._rules_conflict(dont_rule, do_rule):
                    conflicts.add(dont_rule.rule_id)
                    conflicts.add(do_rule.rule_id)
                    conflict_checks.append({
                        "type": "policy_conflict",
                        "severity": "blocker",
                        "rule_id": dont_rule.rule_id,
                        "other_rule_id": do_rule.rule_id,
                        "message": (
                            f"Rule {dont_rule.rule_id} ({dont_rule.kind.value}) "
                            f"conflicts with {do_rule.rule_id} ({do_rule.kind.value}) "
                            f"for the current scope; human decision required."
                        ),
                    })

        if conflicts:
            raise PolicyConflictError(
                "Policy conflict between HARD_DO and HARD_DONT rules: "
                + ", ".join(sorted(conflicts))
            )

        sorted_rules = sorted(
            active,
            key=lambda r: r.scope.level.precedence,
        )
        rule_refs = tuple(
            (rule.rule_id, rule.current_revision) for rule in sorted_rules
        )

        snapshot_data = {
            "rules": [r.to_dict() for r in sorted_rules],
            "exceptions_applied": sorted(applied_exceptions),
            "scope": effective_scope.to_dict(),
        }
        sha = hashlib.sha256(
            json.dumps(
                snapshot_data, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        snapshot = PolicySnapshot(
            snapshot_id=f"POL-{sha[:12]}",
            sha256=sha,
            rules=rule_refs,
            exceptions_applied=tuple(sorted(applied_exceptions)),
            compiled_at=_utcnow(),
            engine_version=ENGINE_VERSION,
        )

        return snapshot, conflict_checks

    def _scope_matches(self, rule_scope: Scope, target: Scope) -> bool:
        if not rule_scope.applies_to(target):
            return False
        if rule_scope.brand and target.brand and rule_scope.brand != target.brand:
            return False
        if rule_scope.project and target.project and rule_scope.project != target.project:
            return False
        if rule_scope.level == ScopeLevel.SCENE and target.scene_id:
            return rule_scope.scene_id == target.scene_id or rule_scope.scene_id == "*"
        return True

    def _rules_conflict(self, dont_rule: Rule, do_rule: Rule) -> bool:
        """Two rules conflict if they have opposite kinds and overlapping predicates."""
        if dont_rule.predicate is None or do_rule.predicate is None:
            return False
        if dont_rule.predicate.operator == do_rule.predicate.operator:
            return True
        # Check if they target the same node types
        dont_types = set(dont_rule.predicate.parameters.get("element_types", []))
        do_types = set(do_rule.predicate.parameters.get("element_types", []))
        if dont_types and do_types and dont_types & do_types:
            return True
        return False

    def _find_exception(
        self,
        rule_id: str,
        job_id: str | None,
        target_scope: Scope,
    ) -> RuleException | None:
        if not job_id:
            return None
        now = _utcnow()
        for exc in self._exceptions:
            if exc.rule_id != rule_id or exc.job_id != job_id:
                continue
            if exc.expires_at and exc.expires_at < now:
                continue
            if exc.scope.applies_to(target_scope):
                return exc
        return None


def resolve_policy(
    store: CreativeMemoryStore | None = None,
    *,
    job_id: str | None = None,
    brand: str | None = None,
    project: str | None = None,
    video_id: str | None = None,
    scene_id: str | None = None,
    platform: str | None = None,
    context: str | None = None,
    rules: list[dict[str, Any]] | None = None,
    exceptions: list[dict[str, Any]] | None = None,
) -> tuple[PolicySnapshot, list[dict[str, Any]]]:
    """High-level entry point: resolve effective policy.

    Either pass a ``store`` (to load from the DB) or pass explicit
    ``rules`` and ``exceptions`` as dict lists.
    """
    if store is not None:
        active = list(store.get_active_rules())
        excs: list[RuleException] = []
        if job_id:
            excs = list(store.get_exceptions_for_job(job_id))
        resolver = PolicyResolver(active, excs)
    else:
        rule_objs = [Rule.from_dict(r) for r in (rules or [])]
        exc_objs = [RuleException.from_dict(e) for e in (exceptions or [])]
        resolver = PolicyResolver(rule_objs, exc_objs)

    return resolver.resolve(
        job_id=job_id, brand=brand, project=project,
        video_id=video_id, scene_id=scene_id, platform=platform,
        context=context,
    )


def check_conflict(new_rule: Rule, existing: Iterable[Rule]) -> list[str]:
    """Check whether ``new_rule`` would create a hard conflict with existing rules."""
    conflicts = []
    for rule in existing:
        if rule.status != RuleStatus.ACTIVE:
            continue
        if rule.rule_id == new_rule.rule_id:
            continue
        if (
            rule.kind.name == "HARD_DONT" and new_rule.kind.name == "HARD_DO"
            or rule.kind.name == "HARD_DO" and new_rule.kind.name == "HARD_DONT"
        ):
            conflicts.append(
                f"Conflict: {rule.rule_id} ({rule.kind.value}) vs "
                f"{new_rule.rule_id} ({new_rule.kind.value})"
            )
    return conflicts


__all__ = [
    "PolicyResolver",
    "PolicyConflictError",
    "resolve_policy",
    "check_conflict",
    "ENGINE_VERSION",
]
