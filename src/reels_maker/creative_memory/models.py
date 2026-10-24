"""Creative Feedback Memory & Quality Gates — typed contracts.

This module defines the immutable, serializable domain types used by the
creative-memory subsystem: feedback classification, rule lifecycle, policy
scopes, QA gate results and exit codes.  No I/O is performed here; types are
plain dataclasses so they round-trip through JSON and SQLite transparently.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


SCHEMA_VERSION = 1


class FeedbackType(str, enum.Enum):
    HARD_DONT = "hard_dont"
    HARD_DO = "hard_do"
    PREFERENCE = "preference"
    APPROVED_PATTERN = "approved_pattern"
    PROJECT_FIX = "project_fix"
    TEMPORARY_EXCEPTION = "temporary_exception"
    NEGATIVE_EXAMPLE = "negative_example"
    FACT_CORRECTION = "fact_correction"
    RETRACTION = "retraction"
    QUESTION_AMBIGUOUS = "question_ambiguous"

    @property
    def is_persistent(self) -> bool:
        return self in (
            FeedbackType.HARD_DONT,
            FeedbackType.HARD_DO,
            FeedbackType.PREFERENCE,
            FeedbackType.APPROVED_PATTERN,
            FeedbackType.NEGATIVE_EXAMPLE,
        )


class ScopeLevel(str, enum.Enum):
    GLOBAL = "global"
    BRAND = "brand"
    PROJECT = "project"
    VIDEO = "video"
    SCENE = "scene"

    @property
    def precedence(self) -> int:
        return {
            ScopeLevel.GLOBAL: 0,
            ScopeLevel.BRAND: 1,
            ScopeLevel.PROJECT: 2,
            ScopeLevel.VIDEO: 3,
            ScopeLevel.SCENE: 4,
        }[self]


class RuleStatus(str, enum.Enum):
    PROPOSED = "proposed"
    NEEDS_CONFIRMATION = "needs_confirmation"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REVOKED = "revoked"
    ARCHIVED = "archived"

    @property
    def is_terminal(self) -> bool:
        return self in (RuleStatus.ACTIVE, RuleStatus.REVOKED,
                        RuleStatus.SUPERSEDED, RuleStatus.ARCHIVED)


class OverridePolicy(str, enum.Enum):
    NEVER = "never"
    EXPLICIT_OWNER_PER_RUN = "explicit_owner_per_run"
    OWNER_APPROVED = "owner_approved"


class Severity(str, enum.Enum):
    BLOCKER = "blocker"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Gate(str, enum.Enum):
    G0_SOURCE = "g0_source_truth"
    G1_SPEC = "g1_creative_spec"
    G2_STRUCTURAL = "g2_structural"
    G3_PREVIEW = "g3_preview"
    G4_ENCODED = "g4_encoded"
    G5_HUMAN = "g5_human_signoff"


class ExitCode(int, enum.Enum):
    OK = 0
    INVALID_REQUEST = 2
    POLICY_VIOLATION = 3
    UNVERIFIED_CONDITION = 4
    SECURITY_BLOCK = 5
    UNRESOLVED_QA = 6
    PERMISSION_DENIED = 7
    RENDERER_ERROR = 8


class Classification(str, enum.Enum):
    CORRECTIVE_PATCH = "corrective_patch"
    PERSISTENT_RULE = "persistent_rule"
    PREFERENCE = "preference"
    POSITIVE_PATTERN = "positive_pattern"
    OVERRIDE = "override"
    RETRACT = "retract"
    AMBIGUOUS = "ambiguous"


class Observability(str, enum.Enum):
    DETERMINISTIC = "deterministic"
    PERCEPTUAL = "perceptual"
    MIXED = "mixed"


class ActorRole(str, enum.Enum):
    OWNER = "owner"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    SYSTEM = "system"


@dataclass(frozen=True)
class Scope:
    level: ScopeLevel
    target: str = "*"
    brand: str | None = None
    project: str | None = None
    video_id: str | None = None
    scene_id: str | None = None
    platform: str | None = None
    context: str | None = None

    def applies_to(self, other: "Scope") -> bool:
        """Check whether this rule's scope applies to *other* (the target scope).

        A rule applies to a target if the rule's scope is broader than or
        equal to the target's scope, and the brand/project/video/scene
        identifiers match where applicable.
        """
        # GLOBAL applies to everything
        if self.level == ScopeLevel.GLOBAL:
            return True
        # BRAND applies to everything within that brand
        if self.level == ScopeLevel.BRAND:
            if other.level in (ScopeLevel.BRAND, ScopeLevel.PROJECT,
                               ScopeLevel.VIDEO, ScopeLevel.SCENE):
                return self.brand == other.brand
            return False
        # PROJECT applies to everything within that project
        if self.level == ScopeLevel.PROJECT:
            if other.level in (ScopeLevel.PROJECT, ScopeLevel.VIDEO,
                               ScopeLevel.SCENE):
                return self.project == other.project
            return False
        # VIDEO applies to everything within that video
        if self.level == ScopeLevel.VIDEO:
            if other.level in (ScopeLevel.VIDEO, ScopeLevel.SCENE):
                return self.video_id == other.video_id
            return False
        # SCENE applies only to that specific scene
        if self.level == ScopeLevel.SCENE:
            return self.scene_id == other.scene_id
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level.value,
            "target": self.target,
            "brand": self.brand,
            "project": self.project,
            "video_id": self.video_id,
            "scene_id": self.scene_id,
            "platform": self.platform,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Scope":
        return cls(
            level=ScopeLevel(data["level"]),
            target=data.get("target", "*"),
            brand=data.get("brand"),
            project=data.get("project"),
            video_id=data.get("video_id"),
            scene_id=data.get("scene_id"),
            platform=data.get("platform"),
            context=data.get("context"),
        )


@dataclass(frozen=True)
class EntityTarget:
    node_types: tuple[str, ...] = ()
    contexts: tuple[str, ...] = ("all",)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_types": list(self.node_types),
            "contexts": list(self.contexts),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EntityTarget":
        return cls(
            node_types=tuple(data.get("node_types", [])),
            contexts=tuple(data.get("contexts", ["all"])),
        )


@dataclass(frozen=True)
class FeedbackContext:
    job_id: str | None = None
    scene_id: str | None = None
    time: float | None = None
    time_seconds: float | None = None
    frame: int | None = None
    render_id: str | None = None
    render_sha256: str | None = None
    spec_sha256: str | None = None
    brand: str | None = None
    project: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "scene_id": self.scene_id,
            "time": self.time,
            "time_seconds": self.time_seconds,
            "frame": self.frame,
            "render_id": self.render_id,
            "render_sha256": self.render_sha256,
            "spec_sha256": self.spec_sha256,
            "brand": self.brand,
            "project": self.project,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeedbackContext":
        return cls(
            job_id=data.get("job_id"),
            scene_id=data.get("scene_id"),
            time=data.get("time"),
            time_seconds=data.get("time_seconds"),
            frame=data.get("frame"),
            render_id=data.get("render_id"),
            render_sha256=data.get("render_sha256"),
            spec_sha256=data.get("spec_sha256"),
            brand=data.get("brand"),
            project=data.get("project"),
        )


@dataclass(frozen=True)
class Origin:
    feedback_event_id: str | None = None
    actor: ActorRole = ActorRole.OWNER
    actor_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "feedback_event_id": self.feedback_event_id,
            "actor": self.actor.value,
            "actor_id": self.actor_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Origin":
        return cls(
            feedback_event_id=data.get("feedback_event_id"),
            actor=ActorRole(data.get("actor", "owner")),
            actor_id=data.get("actor_id"),
        )


@dataclass
class FeedbackEvent:
    event_id: str
    text: str
    context: FeedbackContext
    recorded_at: str
    normalized_intent: str | None = None
    scope: Scope | None = None
    feedback_type: FeedbackType | None = None
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "text": self.text,
            "context": self.context.to_dict(),
            "recorded_at": self.recorded_at,
            "normalized_intent": self.normalized_intent,
            "scope": self.scope.to_dict() if self.scope else None,
            "feedback_type": self.feedback_type.value if self.feedback_type else None,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class PredicateSpec:
    operator: str
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"operator": self.operator, "parameters": self.parameters}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PredicateSpec":
        return cls(
            operator=data["operator"],
            parameters=data.get("parameters", {}),
        )


@dataclass
class RuleRevision:
    revision: int
    rule_id: str
    status: RuleStatus
    kind: FeedbackType
    scope: Scope
    applies_to: EntityTarget
    predicate: PredicateSpec | None
    override_policy: OverridePolicy
    enforcement: tuple[str, ...]
    repair_strategy: str | None
    origin: Origin
    rationale: str
    created_at: str
    evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "revision": self.revision,
            "rule_id": self.rule_id,
            "status": self.status.value,
            "kind": self.kind.value,
            "scope": self.scope.to_dict(),
            "applies_to": self.applies_to.to_dict(),
            "predicate": self.predicate.to_dict() if self.predicate else None,
            "override_policy": self.override_policy.value,
            "enforcement": list(self.enforcement),
            "repair_strategy": self.repair_strategy,
            "origin": self.origin.to_dict(),
            "rationale": self.rationale,
            "created_at": self.created_at,
            "evidence": list(self.evidence),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RuleRevision":
        return cls(
            revision=data["revision"],
            rule_id=data["rule_id"],
            status=RuleStatus(data["status"]),
            kind=FeedbackType(data["kind"]),
            scope=Scope.from_dict(data["scope"]),
            applies_to=EntityTarget.from_dict(data["applies_to"]),
            predicate=PredicateSpec.from_dict(data["predicate"]) if data.get("predicate") else None,
            override_policy=OverridePolicy(data["override_policy"]),
            enforcement=tuple(data.get("enforcement", [])),
            repair_strategy=data.get("repair_strategy"),
            origin=Origin.from_dict(data["origin"]),
            rationale=data["rationale"],
            created_at=data["created_at"],
            evidence=tuple(data.get("evidence", [])),
        )


@dataclass
class Rule:
    rule_id: str
    kind: FeedbackType
    scope: Scope
    applies_to: EntityTarget
    predicate: PredicateSpec | None
    override_policy: OverridePolicy
    enforcement: tuple[str, ...]
    repair_strategy: str | None
    status: RuleStatus
    current_revision: int
    origin: Origin
    rationale: str
    created_at: str
    evidence: tuple[str, ...] = ()
    revoked_at: str | None = None
    superseded_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "kind": self.kind.value,
            "scope": self.scope.to_dict(),
            "applies_to": self.applies_to.to_dict(),
            "predicate": self.predicate.to_dict() if self.predicate else None,
            "override_policy": self.override_policy.value,
            "enforcement": list(self.enforcement),
            "repair_strategy": self.repair_strategy,
            "status": self.status.value,
            "current_revision": self.current_revision,
            "origin": self.origin.to_dict(),
            "rationale": self.rationale,
            "created_at": self.created_at,
            "evidence": list(self.evidence),
            "revoked_at": self.revoked_at,
            "superseded_by": self.superseded_by,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Rule":
        return cls(
            rule_id=data["rule_id"],
            kind=FeedbackType(data["kind"]),
            scope=Scope.from_dict(data["scope"]),
            applies_to=EntityTarget.from_dict(data["applies_to"]),
            predicate=PredicateSpec.from_dict(data["predicate"]) if data.get("predicate") else None,
            override_policy=OverridePolicy(data["override_policy"]),
            enforcement=tuple(data.get("enforcement", [])),
            repair_strategy=data.get("repair_strategy"),
            status=RuleStatus(data["status"]),
            current_revision=data["current_revision"],
            origin=Origin.from_dict(data["origin"]),
            rationale=data["rationale"],
            created_at=data["created_at"],
            evidence=tuple(data.get("evidence", [])),
            revoked_at=data.get("revoked_at"),
            superseded_by=data.get("superseded_by"),
        )


@dataclass(frozen=True)
class RuleException:
    exception_id: str
    rule_id: str
    job_id: str
    scope: Scope
    actor: ActorRole
    actor_id: str | None
    reason: str
    created_at: str
    expires_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "exception_id": self.exception_id,
            "rule_id": self.rule_id,
            "job_id": self.job_id,
            "scope": self.scope.to_dict(),
            "actor": self.actor.value,
            "actor_id": self.actor_id,
            "reason": self.reason,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RuleException":
        return cls(
            exception_id=data["exception_id"],
            rule_id=data["rule_id"],
            job_id=data["job_id"],
            scope=Scope.from_dict(data["scope"]),
            actor=ActorRole(data["actor"]),
            actor_id=data.get("actor_id"),
            reason=data["reason"],
            created_at=data["created_at"],
            expires_at=data.get("expires_at"),
        )


@dataclass(frozen=True)
class PolicySnapshot:
    snapshot_id: str
    sha256: str
    rules: tuple[tuple[str, int], ...]
    exceptions_applied: tuple[str, ...]
    compiled_at: str
    engine_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "sha256": self.sha256,
            "rules": [list(r) for r in self.rules],
            "exceptions_applied": list(self.exceptions_applied),
            "compiled_at": self.compiled_at,
            "engine_version": self.engine_version,
        }


@dataclass
class QAIssue:
    code: str
    gate: Gate
    severity: Severity
    message: str
    rule_id: str | None = None
    revision: int | None = None
    scene_id: str | None = None
    time: float | None = None
    frame: int | None = None
    elements: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    remediation: str | None = None
    policy_sha256: str | None = None
    status: str = "unverified"

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "gate": self.gate.value,
            "severity": self.severity.value,
            "message": self.message,
            "rule_id": self.rule_id,
            "revision": self.revision,
            "scene_id": self.scene_id,
            "time": self.time,
            "frame": self.frame,
            "elements": list(self.elements),
            "evidence": list(self.evidence),
            "remediation": self.remediation,
            "policy_sha256": self.policy_sha256,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QAIssue":
        return cls(
            code=data["code"],
            gate=Gate(data["gate"]),
            severity=Severity(data["severity"]),
            message=data["message"],
            rule_id=data.get("rule_id"),
            revision=data.get("revision"),
            scene_id=data.get("scene_id"),
            time=data.get("time"),
            frame=data.get("frame"),
            elements=tuple(data.get("elements", [])),
            evidence=tuple(data.get("evidence", [])),
            remediation=data.get("remediation"),
            policy_sha256=data.get("policy_sha256"),
            status=data.get("status", "unverified"),
        )


@dataclass
class GateResult:
    gate: Gate
    ok: bool
    status: str
    violations: list[QAIssue] = field(default_factory=list)
    warnings: list[QAIssue] = field(default_factory=list)
    checked_rules: list[str] = field(default_factory=list)
    unchecked_rules: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    policy_sha256: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate": self.gate.value,
            "ok": self.ok,
            "status": self.status,
            "violations": [issue.to_dict() for issue in self.violations],
            "warnings": [issue.to_dict() for issue in self.warnings],
            "checked_rules": list(self.checked_rules),
            "unchecked_rules": list(self.unchecked_rules),
            "limitations": list(self.limitations),
            "policy_sha256": self.policy_sha256,
        }


@dataclass(frozen=True)
class RepairAttempt:
    attempt: int
    action: str
    violations_before: int
    violations_after: int
    new_violations: int
    description: str
    patch_diff: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt": self.attempt,
            "action": self.action,
            "violations_before": self.violations_before,
            "violations_after": self.violations_after,
            "new_violations": self.new_violations,
            "description": self.description,
            "patch_diff": self.patch_diff,
        }


@dataclass(frozen=True)
class RegressionCase:
    case_id: str
    rule_id: str
    spec: dict[str, Any]
    expected_violation: str
    description: str
    added_at: str
    added_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "rule_id": self.rule_id,
            "spec": self.spec,
            "expected_violation": self.expected_violation,
            "description": self.description,
            "added_at": self.added_at,
            "added_by": self.added_by,
        }


@dataclass(frozen=True)
class ApprovedPattern:
    pattern_id: str
    context: str
    recipe: dict[str, Any]
    evidence_refs: tuple[str, ...]
    human_rating: int | None
    constraints: tuple[str, ...]
    created_at: str
    approved_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "context": self.context,
            "recipe": self.recipe,
            "evidence_refs": list(self.evidence_refs),
            "human_rating": self.human_rating,
            "constraints": list(self.constraints),
            "created_at": self.created_at,
            "approved_by": self.approved_by,
        }


@dataclass
class RuleProposal:
    proposal_id: str
    original_text: str
    normalized_intent: str
    classification: Classification
    candidate_scope: Scope
    feedback_type: FeedbackType | None
    target_element_ids: tuple[str, ...]
    scene_ids: tuple[str, ...]
    timestamps: tuple[float, ...]
    predicate_candidates: tuple[PredicateSpec, ...]
    observability: Observability
    is_global_intent_explicit: bool
    needs_confirmation: bool
    confidence: float
    proposed_fix: str | None
    evidence_refs: tuple[str, ...]
    conflicts: tuple[str, ...]
    questions: tuple[str, ...]
    recorded_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "original_text": self.original_text,
            "normalized_intent": self.normalized_intent,
            "classification": self.classification.value,
            "candidate_scope": self.candidate_scope.to_dict(),
            "feedback_type": self.feedback_type.value if self.feedback_type else None,
            "target_element_ids": list(self.target_element_ids),
            "scene_ids": list(self.scene_ids),
            "timestamps": list(self.timestamps),
            "predicate_candidates": [p.to_dict() for p in self.predicate_candidates],
            "observability": self.observability.value,
            "is_global_intent_explicit": self.is_global_intent_explicit,
            "needs_confirmation": self.needs_confirmation,
            "confidence": self.confidence,
            "proposed_fix": self.proposed_fix,
            "evidence_refs": list(self.evidence_refs),
            "conflicts": list(self.conflicts),
            "questions": list(self.questions),
            "recorded_at": self.recorded_at,
        }


__all__ = [
    "SCHEMA_VERSION",
    "FeedbackType",
    "ScopeLevel",
    "RuleStatus",
    "OverridePolicy",
    "Severity",
    "Gate",
    "ExitCode",
    "Classification",
    "Observability",
    "ActorRole",
    "Scope",
    "EntityTarget",
    "FeedbackContext",
    "Origin",
    "FeedbackEvent",
    "PredicateSpec",
    "RuleRevision",
    "Rule",
    "RuleException",
    "PolicySnapshot",
    "QAIssue",
    "GateResult",
    "RepairAttempt",
    "RegressionCase",
    "ApprovedPattern",
    "RuleProposal",
]
