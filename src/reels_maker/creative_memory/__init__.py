"""Creative Feedback Memory & Quality Gates subsystem."""
from __future__ import annotations

from .models import (
    ActorRole, ApprovedPattern, Classification, EntityTarget, ExitCode,
    FeedbackContext, FeedbackEvent, FeedbackType, Gate, GateResult,
    Origin, OverridePolicy, PolicySnapshot, QAIssue, PredicateSpec,
    RegressionCase, RepairAttempt, Rule, RuleException, RuleProposal,
    RuleRevision, RuleStatus, Scope, ScopeLevel, Severity,
)
from .store import (
    SCHEMA_VERSION, ENGINE_VERSION, STORE_FILENAME, CreativeMemoryError,
    CreativeMemoryStore, open_store,
)
from .interpreter import (
    FeedbackInterpreter, interpret_feedback, to_rule_revision,
)
from .resolver import (
    PolicyResolver, PolicyConflictError, resolve_policy, check_conflict,
)
from .preflight import (
    audit_creative_spec, audit_render_graph, evaluate_predicate_issues,
    gate_result_to_exit_code, gate_result_to_json,
)
from .reporting import build_qa_report, gate_result_to_report
from .repair import plan_repair, run_repair_loop, RepairError
from .regressions import RegressionSuite, load_regression_suite, save_regression_suite
from .positive_patterns import PatternLibrary
from .visual_review import VisualReview, file_sha256
from .temporal_review import TemporalReview

__version__ = "1.0"

__all__ = [
    "ActorRole", "ApprovedPattern", "Classification", "EntityTarget",
    "ExitCode", "FeedbackContext", "FeedbackEvent", "FeedbackType",
    "Gate", "GateResult", "Origin", "OverridePolicy", "PolicySnapshot",
    "QAIssue", "PredicateSpec", "RegressionCase", "RepairAttempt",
    "Rule", "RuleException", "RuleProposal", "RuleRevision", "RuleStatus",
    "Scope", "ScopeLevel", "Severity",
    "FeedbackInterpreter", "interpret_feedback", "to_rule_revision",
    "PolicyResolver", "PolicyConflictError", "resolve_policy", "check_conflict",
    "CreativeMemoryStore", "open_store", "CreativeMemoryError",
    "SCHEMA_VERSION", "ENGINE_VERSION", "STORE_FILENAME",
    "audit_creative_spec", "audit_render_graph",
    "evaluate_predicate_issues", "gate_result_to_exit_code",
    "gate_result_to_json", "build_qa_report", "gate_result_to_report",
    "PatternLibrary", "plan_repair", "run_repair_loop", "RepairError",
    "RegressionSuite", "load_regression_suite", "save_regression_suite",
    "VisualReview", "file_sha256", "TemporalReview",
]
