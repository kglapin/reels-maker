"""Creative Memory SQLite store.

Single-file SQLite store using only the Python standard library.  Events are
immutable; rules and revisions are append-only; every write is transactional so
a crash never leaves a half-confirmed rule.  Public artefacts (rules, exceptions
and policy snapshots) are additionally exported as JSON for transfer and
testing.

A note on privacy (per the specification and AGENTS.md):
  * **Production databases must NOT be committed to a public repository.**
  * The store is intended for local, per-project use.  A `--memory` (in-memory
    SQLite) convenience exists for tests.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .models import (
    ActorRole,
    ApprovedPattern,
    EntityTarget,
    ExitCode,
    FeedbackContext,
    FeedbackEvent,
    FeedbackType,
    Gate,
    GateResult,
    Origin,
    OverridePolicy,
    PolicySnapshot,
    PredicateSpec,
    QAIssue,
    Rule,
    RuleException,
    RuleProposal,
    RuleRevision,
    RuleStatus,
    Scope,
    ScopeLevel,
    Severity,
)


SCHEMA_VERSION = 1
ENGINE_VERSION = "creative_memory/1.0"
STORE_FILENAME = "creative_memory.db"


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _uuid() -> str:
    return uuid.uuid4().hex


_JOURNAL_MODE = "WAL"


class CreativeMemoryError(Exception):
    """Base error for the creative-memory subsystem."""


class PermissionError(CreativeMemoryError):
    """The actor lacks the scope/actor-role to perform the action."""


class PolicyConflictError(CreativeMemoryError):
    """Two hard rules cannot be satisfied simultaneously."""


class RuleNotFoundError(CreativeMemoryError):
    """The requested rule_id does not exist."""


class SchemaError(CreativeMemoryError):
    """Schema or data-integrity violation."""


_MIGRATIONS: list[tuple[int, str]] = []


def _migration(version: int):
    def decorator(func):
        _MIGRATIONS.append((version, func))
        return func
    return decorator


@_migration(1)
def _create_base_schema() -> list[str]:
    return [
        """CREATE TABLE IF NOT EXISTS meta (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS feedback_events (
            event_id        TEXT PRIMARY KEY,
            text            TEXT NOT NULL,
            context         TEXT NOT NULL,
            recorded_at     TEXT NOT NULL,
            normalized_intent TEXT,
            scope           TEXT,
            feedback_type   TEXT,
            confidence      REAL
        )""",
        """CREATE TABLE IF NOT EXISTS rule_proposals (
            proposal_id        TEXT PRIMARY KEY,
            event_id           TEXT,
            proposed_json      TEXT NOT NULL,
            status             TEXT NOT NULL DEFAULT 'pending',
            recorded_at        TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS rules (
            rule_id          TEXT PRIMARY KEY,
            kind             TEXT NOT NULL,
            scope            TEXT NOT NULL,
            applies_to       TEXT NOT NULL,
            predicate        TEXT,
            override_policy  TEXT NOT NULL,
            enforcement      TEXT NOT NULL,
            repair_strategy  TEXT,
            status           TEXT NOT NULL DEFAULT 'proposed',
            current_revision INTEGER NOT NULL DEFAULT 0,
            origin           TEXT NOT NULL,
            rationale        TEXT,
            created_at       TEXT NOT NULL,
            evidence         TEXT NOT NULL DEFAULT '[]',
            revoked_at       TEXT,
            superseded_by    TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS rule_revisions (
            rule_id    TEXT NOT NULL,
            revision   INTEGER NOT NULL,
            data       TEXT NOT NULL,
            PRIMARY KEY (rule_id, revision)
        )""",
        """CREATE TABLE IF NOT EXISTS rule_exceptions (
            exception_id TEXT PRIMARY KEY,
            rule_id      TEXT NOT NULL,
            job_id       TEXT NOT NULL,
            scope        TEXT NOT NULL,
            actor        TEXT NOT NULL,
            actor_id     TEXT,
            reason       TEXT NOT NULL,
            created_at   TEXT NOT NULL,
            expires_at   TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS policy_snapshots (
            snapshot_id        TEXT PRIMARY KEY,
            sha256             TEXT NOT NULL UNIQUE,
            rules              TEXT NOT NULL,
            exceptions_applied TEXT NOT NULL,
            compiled_at        TEXT NOT NULL,
            engine_version     TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS qa_issues (
            issue_id      TEXT PRIMARY KEY,
            json          TEXT NOT NULL,
            gate          TEXT NOT NULL,
            rule_id       TEXT,
            scene_id      TEXT,
            recorded_at   TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS repair_attempts (
            attempt_id     TEXT PRIMARY KEY,
            issue_id       TEXT NOT NULL,
            attempt        INTEGER NOT NULL,
            json           TEXT NOT NULL,
            recorded_at    TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS regression_cases (
            case_id        TEXT PRIMARY KEY,
            rule_id        TEXT NOT NULL,
            spec           TEXT NOT NULL,
            expected_violation TEXT NOT NULL,
            description    TEXT NOT NULL,
            added_at       TEXT NOT NULL,
            added_by       TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS approved_patterns (
            pattern_id    TEXT PRIMARY KEY,
            context       TEXT NOT NULL,
            recipe        TEXT NOT NULL,
            evidence_refs TEXT NOT NULL,
            human_rating  INTEGER,
            constraints   TEXT NOT NULL,
            created_at    TEXT NOT NULL,
            approved_by   TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_rules_status ON rules(status)",
        "CREATE INDEX IF NOT EXISTS idx_rules_kind ON rules(kind)",
        "CREATE INDEX IF NOT EXISTS idx_rules_scope ON rules(scope)",
        "CREATE INDEX IF NOT EXISTS idx_exceptions_rule ON rule_exceptions(rule_id)",
        "CREATE INDEX IF NOT EXISTS idx_exceptions_job ON rule_exceptions(job_id)",
        "CREATE INDEX IF NOT EXISTS idx_qa_rule ON qa_issues(rule_id)",
        "CREATE INDEX IF NOT EXISTS idx_qa_scene ON qa_issues(scene_id)",
        "CREATE INDEX IF NOT EXISTS idx_proposals_status ON rule_proposals(status)",
    ]


class CreativeMemoryStore:
    """Transactional, append-only creative-feedback and policy store.

    Parameters
    ----------
    path:
        Path to the SQLite file.  Pass ``":memory:"`` for an in-memory store
        (useful in tests; data is lost when the connection closes).
    """

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._path = str(path)
        self._conn: sqlite3.Connection | None = None

    def __enter__(self) -> "CreativeMemoryStore":
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def open(self) -> None:
        self._conn = sqlite3.connect(self._path, check_same_thread=False, isolation_level=None)
        self._conn.execute(f"PRAGMA journal_mode={_JOURNAL_MODE}")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.row_factory = sqlite3.Row
        self._migrate()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------ #
    #  migration
    # ------------------------------------------------------------------ #
    def _migrate(self) -> None:
        assert self._conn is not None, "Store not opened"
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        current = self._get_meta("schema_version")
        if current is None:
            current = 0
        for version, func in _MIGRATIONS:
            if version <= current:
                continue
            for stmt in func():
                self._conn.execute(stmt)
        self._set_meta("schema_version", str(SCHEMA_VERSION))
        self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    def _get_meta(self, key: str) -> str | None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT value FROM meta WHERE key=?", (key,)
        ).fetchone()
        return row[0] if row else None

    def _set_meta(self, key: str, value: str) -> None:
        assert self._conn is not None
        self._conn.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.open()
        assert self._conn is not None
        return self._conn

    # ------------------------------------------------------------------ #
    #  feedback events (immutable)
    # ------------------------------------------------------------------ #
    def add_feedback_event(self, event: FeedbackEvent) -> str:
        conn = self.conn
        stored = {
            "event_id": event.event_id,
            "text": event.text,
            "context": json.dumps(event.context.to_dict(), ensure_ascii=False),
            "recorded_at": event.recorded_at,
            "normalized_intent": event.normalized_intent,
            "scope": json.dumps(event.scope.to_dict(), ensure_ascii=False) if event.scope else None,
            "feedback_type": event.feedback_type.value if event.feedback_type else None,
            "confidence": event.confidence,
        }
        cols = ", ".join(stored.keys())
        placeholders = ", ".join("?" * len(stored))
        conn.execute(
            f"INSERT INTO feedback_events({cols}) VALUES ({placeholders})",
            list(stored.values()),
        )
        return event.event_id

    def get_feedback_event(self, event_id: str) -> FeedbackEvent | None:
        row = self.conn.execute(
            "SELECT * FROM feedback_events WHERE event_id=?", (event_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_event(row)

    def _row_to_event(self, row: sqlite3.Row) -> FeedbackEvent:
        context = FeedbackContext.from_dict(json.loads(row["context"]))
        scope = Scope.from_dict(json.loads(row["scope"])) if row["scope"] else None
        ftype = row["feedback_type"]
        ftype_enum = FeedbackType(ftype) if ftype else None
        return FeedbackEvent(
            event_id=row["event_id"],
            text=row["text"],
            context=context,
            recorded_at=row["recorded_at"],
            normalized_intent=row["normalized_intent"],
            scope=scope,
            feedback_type=ftype_enum,
            confidence=row["confidence"],
        )

    # ------------------------------------------------------------------ #
    #  rule proposals
    # ------------------------------------------------------------------ #
    def save_proposal(self, proposal: RuleProposal) -> str:
        conn = self.conn
        conn.execute(
            "INSERT INTO rule_proposals(proposal_id, event_id, proposed_json, status, recorded_at) "
            "VALUES (?, ?, ?, 'pending', ?)",
            (proposal.proposal_id, None,
             json.dumps(proposal.to_dict(), ensure_ascii=False), proposal.recorded_at),
        )
        return proposal.proposal_id

    def get_proposals(self, status: str | None = None) -> list[RuleProposal]:
        conn = self.conn
        if status:
            rows = conn.execute(
                "SELECT * FROM rule_proposals WHERE status=? ORDER BY recorded_at",
                (status,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM rule_proposals ORDER BY recorded_at"
            ).fetchall()
        return [self._row_to_proposal(r) for r in rows]

    def _row_to_proposal(self, row: sqlite3.Row) -> RuleProposal:
        data = json.loads(row["proposed_json"])
        data["classification"] = Classification(data["classification"])
        data["candidate_scope"] = Scope.from_dict(data["candidate_scope"])
        data["feedback_type"] = FeedbackType(data["feedback_type"]) if data["feedback_type"] else None
        data["observability"] = Observability(data["observability"])
        predicates = [PredicateSpec.from_dict(p) for p in data.get("predicate_candidates", [])]
        return RuleProposal(
            proposal_id=data["proposal_id"],
            original_text=data["original_text"],
            normalized_intent=data["normalized_intent"],
            classification=data["classification"],
            candidate_scope=data["candidate_scope"],
            feedback_type=data["feedback_type"],
            target_element_ids=tuple(data.get("target_element_ids", [])),
            scene_ids=tuple(data.get("scene_ids", [])),
            timestamps=tuple(data.get("timestamps", [])),
            predicate_candidates=tuple(predicates),
            observability=data["observability"],
            is_global_intent_explicit=data["is_global_intent_explicit"],
            needs_confirmation=data["needs_confirmation"],
            confidence=data["confidence"],
            proposed_fix=data.get("proposed_fix"),
            evidence_refs=tuple(data.get("evidence_refs", [])),
            conflicts=tuple(data.get("conflicts", [])),
            questions=tuple(data.get("questions", [])),
            recorded_at=data["recorded_at"],
        )

    # ------------------------------------------------------------------ #
    #  rules (append-only revisions, single active revision)
    # ------------------------------------------------------------------ #
    def add_rule_revision(self, revision: RuleRevision) -> None:
        conn = self.conn
        now = _utcnow()
        with conn:
            existing = conn.execute(
                "SELECT status, rule_id FROM rules WHERE rule_id=?",
                (revision.rule_id,)
            ).fetchone()
            if existing is None:
                conn.execute(
                    "INSERT INTO rules(rule_id, kind, scope, applies_to, predicate, "
                    "override_policy, enforcement, repair_strategy, status, "
                    "current_revision, origin, rationale, created_at, evidence) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (revision.rule_id, revision.kind.value,
                     json.dumps(revision.scope.to_dict(), ensure_ascii=False),
                     json.dumps(revision.applies_to.to_dict(), ensure_ascii=False),
                     json.dumps(revision.predicate.to_dict(), ensure_ascii=False) if revision.predicate else None,
                     revision.override_policy.value,
                     json.dumps(revision.enforcement, ensure_ascii=False),
                     revision.repair_strategy,
                     revision.status.value,
                     revision.revision,
                     json.dumps(revision.origin.to_dict(), ensure_ascii=False),
                     revision.rationale,
                     revision.created_at,
                     json.dumps(revision.evidence, ensure_ascii=False)),
                )
            else:
                prev_status = existing["status"]
                if prev_status in (RuleStatus.ACTIVE.value,):
                    new_status = RuleStatus.SUPERSEDED.value
                    conn.execute(
                        "UPDATE rules SET status=?, superseded_by=? "
                        "WHERE rule_id=?",
                        (new_status, revision.rule_id, revision.rule_id),
                    )
                conn.execute(
                    "UPDATE rules SET status=?, current_revision=?, rationale=?, "
                    "evidence=?, revoked_at=? WHERE rule_id=?",
                    (revision.status.value, revision.revision, revision.rationale,
                     json.dumps(revision.evidence, ensure_ascii=False),
                     revision.created_at if revision.status == RuleStatus.REVOKED else None,
                     revision.rule_id),
                )
            conn.execute(
                "INSERT INTO rule_revisions(rule_id, revision, data) VALUES (?, ?, ?)",
                (revision.rule_id, revision.revision,
                 json.dumps(revision.to_dict(), ensure_ascii=False)),
            )

    def get_rule(self, rule_id: str) -> Rule | None:
        row = self.conn.execute(
            "SELECT * FROM rules WHERE rule_id=?", (rule_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_rule(row)

    def get_active_rules(self) -> list[Rule]:
        rows = self.conn.execute(
            "SELECT * FROM rules WHERE status=?", (RuleStatus.ACTIVE.value,)
        ).fetchall()
        return [self._row_to_rule(r) for r in rows]

    def get_rules_by_kind(self, kind: FeedbackType) -> list[Rule]:
        rows = self.conn.execute(
            "SELECT * FROM rules WHERE kind=?", (kind.value,)
        ).fetchall()
        return [self._row_to_rule(r) for r in rows]

    def get_rule_history(self, rule_id: str) -> list[RuleRevision]:
        rows = self.conn.execute(
            "SELECT data FROM rule_revisions WHERE rule_id=? ORDER BY revision",
            (rule_id,)
        ).fetchall()
        return [RuleRevision.from_dict(json.loads(r["data"])) for r in rows]

    def _row_to_rule(self, row: sqlite3.Row) -> Rule:
        scope = Scope.from_dict(json.loads(row["scope"]))
        applies_to = EntityTarget.from_dict(json.loads(row["applies_to"]))
        predicate = PredicateSpec.from_dict(json.loads(row["predicate"])) if row["predicate"] else None
        origin = Origin.from_dict(json.loads(row["origin"]))
        return Rule(
            rule_id=row["rule_id"],
            kind=FeedbackType(row["kind"]),
            scope=scope,
            applies_to=applies_to,
            predicate=predicate,
            override_policy=OverridePolicy(row["override_policy"]),
            enforcement=json.loads(row["enforcement"]),
            repair_strategy=row["repair_strategy"],
            status=RuleStatus(row["status"]),
            current_revision=row["current_revision"],
            origin=origin,
            rationale=row["rationale"],
            created_at=row["created_at"],
            evidence=json.loads(row["evidence"]),
            revoked_at=row["revoked_at"],
            superseded_by=row["superseded_by"],
        )

    # ------------------------------------------------------------------ #
    #  rule exceptions
    # ------------------------------------------------------------------ #
    def add_exception(self, exc: RuleException) -> str:
        conn = self.conn
        conn.execute(
            "INSERT OR REPLACE INTO rule_exceptions(exception_id, rule_id, job_id, "
            "scope, actor, actor_id, reason, created_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (exc.exception_id, exc.rule_id, exc.job_id,
             json.dumps(exc.scope.to_dict(), ensure_ascii=False),
             exc.actor.value, exc.actor_id, exc.reason, exc.created_at, exc.expires_at),
        )
        return exc.exception_id

    def get_exceptions_for_job(self, job_id: str) -> list[RuleException]:
        rows = self.conn.execute(
            "SELECT * FROM rule_exceptions WHERE job_id=?", (job_id,)
        ).fetchall()
        return [self._row_to_exception(r) for r in rows]

    def _row_to_exception(self, row: sqlite3.Row) -> RuleException:
        return RuleException(
            exception_id=row["exception_id"],
            rule_id=row["rule_id"],
            job_id=row["job_id"],
            scope=Scope.from_dict(json.loads(row["scope"])),
            actor=ActorRole(row["actor"]),
            actor_id=row["actor_id"],
            reason=row["reason"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
        )

    # ------------------------------------------------------------------ #
    #  policy snapshots
    # ------------------------------------------------------------------ #
    def save_snapshot(self, snapshot: PolicySnapshot) -> str:
        conn = self.conn
        conn.execute(
            "INSERT OR REPLACE INTO policy_snapshots(snapshot_id, sha256, rules, "
            "exceptions_applied, compiled_at, engine_version) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (snapshot.snapshot_id, snapshot.sha256,
             json.dumps(snapshot.rules, ensure_ascii=False),
             json.dumps(snapshot.exceptions_applied, ensure_ascii=False),
             snapshot.compiled_at, snapshot.engine_version),
        )
        return snapshot.snapshot_id

    def get_snapshot(self, sha256: str) -> PolicySnapshot | None:
        row = self.conn.execute(
            "SELECT * FROM policy_snapshots WHERE sha256=?", (sha256,)
        ).fetchone()
        if row is None:
            return None
        return PolicySnapshot(
            snapshot_id=row["snapshot_id"],
            sha256=row["sha256"],
            rules=tuple(tuple(r) for r in json.loads(row["rules"])),
            exceptions_applied=tuple(json.loads(row["exceptions_applied"])),
            compiled_at=row["compiled_at"],
            engine_version=row["engine_version"],
        )

    # ------------------------------------------------------------------ #
    #  QA issues
    # ------------------------------------------------------------------ #
    def record_issue(self, issue: QAIssue) -> str:
        conn = self.conn
        issue_id = _uuid()
        conn.execute(
            "INSERT INTO qa_issues(issue_id, json, gate, rule_id, scene_id, recorded_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (issue_id, json.dumps(issue.to_dict(), ensure_ascii=False),
             issue.gate.value, issue.rule_id, issue.scene_id, _utcnow()),
        )
        return issue_id

    def get_issues(self, *, rule_id: str | None = None,
                   scene_id: str | None = None) -> list[QAIssue]:
        conn = self.conn
        if rule_id and scene_id:
            rows = conn.execute(
                "SELECT json FROM qa_issues WHERE rule_id=? AND scene_id=?",
                (rule_id, scene_id),
            ).fetchall()
        elif rule_id:
            rows = conn.execute(
                "SELECT json FROM qa_issues WHERE rule_id=?", (rule_id,)).fetchall()
        elif scene_id:
            rows = conn.execute(
                "SELECT json FROM qa_issues WHERE scene_id=?", (scene_id,)).fetchall()
        else:
            rows = conn.execute("SELECT json FROM qa_issues").fetchall()
        return [QAIssue.from_dict(json.loads(r["json"])) for r in rows]

    # ------------------------------------------------------------------ #
    #  repair attempts
    # ------------------------------------------------------------------ #
    def record_repair_attempt(self, issue_id: str, attempt: RepairAttempt) -> str:
        conn = self.conn
        attempt_id = _uuid()
        conn.execute(
            "INSERT INTO repair_attempts(attempt_id, issue_id, attempt, json, recorded_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (attempt_id, issue_id, attempt.attempt,
             json.dumps(attempt.to_dict(), ensure_ascii=False), _utcnow()),
        )
        return attempt_id

    def get_repair_attempts(self, issue_id: str) -> list[RepairAttempt]:
        rows = self.conn.execute(
            "SELECT json FROM repair_attempts WHERE issue_id=? ORDER BY attempt",
            (issue_id,)
        ).fetchall()
        return [RepairAttempt(**json.loads(r["json"])) for r in rows]

    # ------------------------------------------------------------------ #
    #  regression cases
    # ------------------------------------------------------------------ #
    def add_regression_case(self, case: RegressionCase) -> str:
        conn = self.conn
        conn.execute(
            "INSERT OR REPLACE INTO regression_cases "
            "(case_id, rule_id, spec, expected_violation, description, added_at, added_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (case.case_id, case.rule_id,
             json.dumps(case.spec, ensure_ascii=False),
             case.expected_violation, case.description,
             case.added_at, case.added_by),
        )
        return case.case_id

    def get_regression_cases(self, rule_id: str | None = None) -> list[RegressionCase]:
        conn = self.conn
        if rule_id:
            rows = conn.execute(
                "SELECT * FROM regression_cases WHERE rule_id=? ORDER BY added_at",
                (rule_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM regression_cases ORDER BY added_at"
            ).fetchall()
        return [
            RegressionCase(
                case_id=r["case_id"],
                rule_id=r["rule_id"],
                spec=json.loads(r["spec"]),
                expected_violation=r["expected_violation"],
                description=r["description"],
                added_at=r["added_at"],
                added_by=r["added_by"],
            )
            for r in rows
        ]

    # ------------------------------------------------------------------ #
    #  approved patterns
    # ------------------------------------------------------------------ #
    def add_pattern(self, pattern: ApprovedPattern) -> str:
        conn = self.conn
        conn.execute(
            "INSERT OR REPLACE INTO approved_patterns "
            "(pattern_id, context, recipe, evidence_refs, human_rating, constraints, created_at, approved_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (pattern.pattern_id, pattern.context,
             json.dumps(pattern.recipe, ensure_ascii=False),
             json.dumps(pattern.evidence_refs, ensure_ascii=False),
             pattern.human_rating,
             json.dumps(pattern.constraints, ensure_ascii=False),
             pattern.created_at, pattern.approved_by),
        )
        return pattern.pattern_id

    def get_patterns(self, context: str | None = None) -> list[ApprovedPattern]:
        conn = self.conn
        if context:
            rows = conn.execute(
                "SELECT * FROM approved_patterns WHERE context=?", (context,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM approved_patterns").fetchall()
        return [
            ApprovedPattern(
                pattern_id=r["pattern_id"],
                context=r["context"],
                recipe=json.loads(r["recipe"]),
                evidence_refs=tuple(json.loads(r["evidence_refs"])),
                human_rating=r["human_rating"],
                constraints=tuple(json.loads(r["constraints"])),
                created_at=r["created_at"],
                approved_by=r["approved_by"],
            )
            for r in rows
        ]

    # ------------------------------------------------------------------ #
    #  export / utility
    # ------------------------------------------------------------------ #
    def export_json(self) -> dict[str, Any]:
        conn = self.conn
        rules = [r.to_dict() for r in self.get_active_rules()]
        proposals = []
        for prop in self.get_proposals():
            d = prop.to_dict()
            d["classification"] = d["classification"].value
            d["candidate_scope"] = d["candidate_scope"].to_dict()
            proposals.append(d)
        exceptions = [e.to_dict() for e in
                      self.get_exceptions_for_job("*")] if False else []
        return {
            "schema_version": SCHEMA_VERSION,
            "engine_version": ENGINE_VERSION,
            "exported_at": _utcnow(),
            "rules": rules,
            "proposals": proposals,
            "exceptions": exceptions,
            "regression_cases": [c.to_dict() for c in self.get_regression_cases()],
            "approved_patterns": [p.to_dict() for p in self.get_patterns()],
        }


def open_store(path: str | Path = ":memory:") -> CreativeMemoryStore:
    store = CreativeMemoryStore(path)
    store.open()
    return store


__all__ = [
    "SCHEMA_VERSION",
    "ENGINE_VERSION",
    "STORE_FILENAME",
    "CreativeMemoryError",
    "PermissionError",
    "PolicyConflictError",
    "RuleNotFoundError",
    "SchemaError",
    "CreativeMemoryStore",
    "open_store",
]
