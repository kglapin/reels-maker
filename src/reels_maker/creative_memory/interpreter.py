"""Deterministic feedback interpreter.

Converts natural-language feedback (Polish and English) into structured
:class:`~reels_maker.creative_memory.models.RuleProposal` objects.  The
interpreter is **rule-based**, not LLM-based, so it works fully offline with
no network calls — consistent with the project's principle that the backend
never performs LLM inference.

The interpreter recognises common patterns (see section 7 of the spec) and
returns ``confidence`` and ``needs_confirmation`` flags.  When intent is
ambiguous the proposal is classified as :attr:`Classification.AMBIGUOUS` and
``needs_confirmation`` is set, so no rule is created without human review.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .models import (
    ActorRole,
    Classification,
    EntityTarget,
    FeedbackType,
    Observability,
    Origin,
    OverridePolicy,
    PredicateSpec,
    RuleProposal,
    RuleRevision,
    RuleStatus,
    Scope,
    ScopeLevel,
)

SCHEMA_VERSION = 1
POLISH = "pl"
ENGLISH = "en"


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class FeedbackInterpreter:
    """Parses natural-language feedback into structured proposals.

    The interpreter uses a set of regex patterns to identify:

    * **Global prohibitions** — "nigdy nie / never do not add X"
    * **Global requirements** — "każdy / every X must have Y"
    * **Brand-scoped rules** — "w filmach <brand> / in <brand> films"
    * **Video-scoped rules** — "w tym filmie / in this film"
    * **Scene-scoped rules** — "w scenie <id> / in shot <id>"
    * **Temporary exceptions** — "tylko tutaj / only here"
    * **Retractions** — "cofnij / undo / withdraw my previous rule"
    * **Preferences** — "wolę / I prefer"
    * **Fact corrections** — "kwota powinna być / the value should be"
    """

    _GLOBAL_DONT_POLISH = re.compile(
        r"\b(nigdy\s+nie|nigdy\s+nie)\b", re.IGNORECASE
    )
    _GLOBAL_DONT_ENGLISH = re.compile(
        r"\b(never\s+(?:add|use|include|put))\b", re.IGNORECASE
    )
    _GLOBAL_DO_POLISH = re.compile(
        r"\b(kazdy|każdy)\b.*\b(musi|miał|miałoby)\b", re.IGNORECASE
    )
    _GLOBAL_DO_ENGLISH = re.compile(
        r"\b(every|each)\b.*\b(must|should)\b", re.IGNORECASE
    )
    _BRAND_SCOPE_POLISH = re.compile(
        r"\bw\s+filmach\s+(\S+)", re.IGNORECASE
    )
    _BRAND_SCOPE_ENGLISH = re.compile(
        r"\bin\s+([\w-]+)\s+films?\b", re.IGNORECASE
    )
    _VIDEO_SCOPE_POLISH = re.compile(
        r"\b(w\s+filmie|tym\s+filmie|tym\s+klipie)\b", re.IGNORECASE
    )
    _VIDEO_SCOPE_ENGLISH = re.compile(
        r"\b(in\s+this\s+(?:film|video|clip)|for\s+this\s+(?:film|video))\b",
        re.IGNORECASE,
    )
    _SCENE_ID_POLISH = re.compile(
        r"\b(?:scen\w*|ujęciu)\s*[:\s]*([^\s,]+)", re.IGNORECASE
    )
    _SCENE_ID_ENGLISH = re.compile(
        r"\b(?:scene|shot)\s*[:\s]*([^\s,]+)", re.IGNORECASE,
    )
    _SCENE_NUM_POLISH = re.compile(r"\b(\d+)(?:\.)?\s*scen[ea]\b", re.IGNORECASE)
    _SCENE_NUM_ENGLISH = re.compile(r"\bscene\s+(\d+)\b", re.IGNORECASE)
    _EXCEPTION_POLISH = re.compile(
        r"\b(tylko\s+(?:tu|tuż|w\s+tym)|(?:tylko\s+)?ten\s+klip|"
        r"w\s+tym\s+klipie\s+(?:zastosuj|dodaj|umieść)|jak\s+nie\s+ma\s+innego)\b",
        re.IGNORECASE,
    )
    _EXCEPTION_ENGLISH = re.compile(
        r"\b(only\s+here|just\s+in\s+this|for\s+this\s+(?:video|clip|scene))\b",
        re.IGNORECASE,
    )
    _RETRACTION_POLISH = re.compile(
        r"\b(cofnij|cofnię|wywróć|anuluj|usuń|odwoła[łąży])\b.*"
        r"\b(zasad|regułę|politikę|poprzednią|wcześniejszą|poprzednio)\b",
        re.IGNORECASE,
    )
    _RETRACTION_ENGLISH = re.compile(
        r"\b(undo|revert|withdraw|remove|cancel)\b.*"
        r"\b(my\s+(?:previous|prior)\s+(?:rule|policy|decision))\b",
        re.IGNORECASE,
    )
    _PREFERENCE_POLISH = re.compile(
        r"\b(wolę|bardziej lubię|wolabym|preferuję|dałbym radę)\b", re.IGNORECASE
    )
    _PREFERENCE_ENGLISH = re.compile(
        r"\b(prefer|i prefer|i'd prefer|would prefer|i like)\b", re.IGNORECASE
    )
    _FACT_CORRECTION_POLISH = re.compile(
        r"\b(wartość\s+to|korzyść\s+to|liczba\s+to|kwota\s+to|"
        r"powinno\s+być|ma\s+być|wynosi)\s+(.+)",
        re.IGNORECASE,
    )
    _FACT_CORRECTION_ENGLISH = re.compile(
        r"\b(the\s+(?:value|amount|number|total)\s+(?:should|is|should be))\s+(.+)",
        re.IGNORECASE,
    )

    _ELEMENT_KEYWORDS: dict[str, str] = {
        "kicker": "kicker",
        "nagłówek": "headline",
        "nagłówków": "headline",
        "nagłówka": "headline",
        "headline": "headline",
        "tytuł": "headline",
        "title": "headline",
        "podtytuł": "subtitle",
        "subtitle": "subtitle",
        "napis": "subtitle",
        "caption": "subtitle",
        "etykieta": "label",
        "label": "label",
        "wartość": "value",
        "value": "value",
        "licznik": "value",
        "counter": "value",
        "wykres": "chart",
        "chart": "chart",
        "ikona": "icon",
        "icon": "icon",
        "efekt": "effect",
        "effect": "effect",
    }

    _FOREVER_POLISH = re.compile(
        r"\b(nigdy|w\s+żadnym|w\s+żadnym\s+filmie|na\s+zawsze)\b", re.IGNORECASE
    )
    _FOREVER_ENGLISH = re.compile(
        r"\b(never|ever|always|in\s+no|at\s+no|for\s+all|for\s+every)\b",
        re.IGNORECASE,
    )

    def interpret(self, text: str, context: dict[str, Any] | None = None) -> RuleProposal:
        """Interpret feedback text into a structural proposal.

        Parameters
        ----------
        text:
            The natural-language feedback string (Polish or English).
        context:
            Optional rendering context (job_id, scene_id, brand, spec, etc.)
        """
        context = context or {}
        raw = text.strip()
        if not raw:
            raise ValueError("Feedback text must not be empty")

        proposal = self._classify(raw, context)
        return RuleProposal(
            proposal_id=f"PROP-{uuid4().hex[:12]}",
            original_text=raw,
            normalized_intent=proposal["normalized_intent"],
            classification=proposal["classification"],
            candidate_scope=proposal["scope"],
            feedback_type=proposal.get("feedback_type"),
            target_element_ids=tuple(proposal.get("target_element_ids", [])),
            scene_ids=tuple(proposal.get("scene_ids", [])),
            timestamps=tuple(proposal.get("timestamps", [])),
            predicate_candidates=tuple(proposal.get("predicate_candidates", [])),
            observability=proposal.get("observability", Observability.MIXED),
            is_global_intent_explicit=proposal.get("is_global_intent_explicit", False),
            needs_confirmation=proposal.get("needs_confirmation", True),
            confidence=proposal.get("confidence", 0.5),
            proposed_fix=proposal.get("proposed_fix"),
            evidence_refs=tuple(proposal.get("evidence_refs", [])),
            conflicts=tuple(proposal.get("conflicts", [])),
            questions=tuple(proposal.get("questions", [])),
            recorded_at=_utcnow(),
        )

    # ------------------------------------------------------------------ #
    #  classification
    # ------------------------------------------------------------------ #
    def _classify(self, text: str, context: dict) -> dict[str, Any]:
        lang = self._detect_language(text)

        if self._is_retraction(text, lang):
            return self._proposal_classification(
                text, Classification.RETRACT, FeedbackType.RETRACTION,
                Scope(ScopeLevel.GLOBAL), "Withdraw the previously stated rule.",
                needs_confirmation=False, confidence=0.95,
                observability=Observability.DETERMINISTIC,
            )

        scope = self._detect_scope(text, lang, context)
        elements = self._detect_elements(text)

        if self._is_exception(text, lang):
            return self._proposal_classification(
                text, Classification.OVERRIDE, FeedbackType.TEMPORARY_EXCEPTION,
                scope, f"Apply exception only for {scope.level.value}.",
                needs_confirmation=True, confidence=0.90,
                observability=Observability.DETERMINISTIC,
                target_element_ids=elements,
            )

        if self._is_global_dont(text, lang):
            return self._make_hard_rule(
                text, Classification.PERSISTENT_RULE, FeedbackType.HARD_DONT,
                scope, elements, "Never / do-not prohibition.",
                needs_confirmation=not self._is_owner(context),
                confidence=0.95,
            )

        if self._is_global_do(text, lang):
            return self._make_hard_rule(
                text, Classification.PERSISTENT_RULE, FeedbackType.HARD_DO,
                scope, elements, "Mandatory requirement.",
                needs_confirmation=not self._is_owner(context),
                confidence=0.90,
            )

        if self._is_preference(text, lang):
            return self._proposal_classification(
                text, Classification.PREFERENCE, FeedbackType.PREFERENCE,
                scope, "Soft preference for future productions.",
                needs_confirmation=False, confidence=0.85,
                observability=Observability.PERCEPTUAL,
                target_element_ids=elements,
            )

        if self._is_fact_correction(text, lang):
            return self._proposal_classification(
                text, Classification.PERSISTENT_RULE, FeedbackType.FACT_CORRECTION,
                scope, "Correct a factual value based on verified source.",
                needs_confirmation=True, confidence=0.90,
                observability=Observability.DETERMINISTIC,
                target_element_ids=elements,
            )

        if self._is_approved_pattern(text, lang):
            return self._proposal_classification(
                text, Classification.POSITIVE_PATTERN, FeedbackType.APPROVED_PATTERN,
                scope, "Record this as an approved positive pattern.",
                needs_confirmation=True, confidence=0.80,
                observability=Observability.PERCEPTUAL,
                target_element_ids=elements,
            )

        if self._is_negative_example(text, lang):
            return self._proposal_classification(
                text, Classification.POSITIVE_PATTERN, FeedbackType.NEGATIVE_EXAMPLE,
                scope, "Record this anti-pattern to avoid.",
                needs_confirmation=True, confidence=0.85,
                observability=Observability.PERCEPTUAL,
                target_element_ids=elements,
            )

        return self._proposal_classification(
            text, Classification.AMBIGUOUS, None,
            scope, "Ambiguous feedback — needs human clarification.",
            needs_confirmation=True, confidence=0.20,
            observability=Observability.PERCEPTUAL,
            target_element_ids=elements,
            questions=[
                "Please clarify whether this is a permanent rule or a one-off fix.",
                "Please specify the scope (global, brand, this video, or a specific scene).",
            ],
        )

    # ------------------------------------------------------------------ #
    #  language and scope detection
    # ------------------------------------------------------------------ #
    _POLISH_WORDS = frozenset({
        "tylko", "tutaj", "zastosuj", "dodaj", "nie", "nigdy", "w", "filmie",
        "klipie", "scenie", "kickerów", "używaj",
        "ten", "ta", "to", "by", "być", "jest", "są", "ma", "mają",
        "wolę", "preferuję", "cofnij", "zasad", "regułę", "politikę",
    })

    def _detect_language(self, text: str) -> str:
        polish_chars = sum(1 for c in text if c in "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")
        words = set(re.findall(r"\b\w+\b", text.lower()))
        if polish_chars > 0 or (words & self._POLISH_WORDS):
            return POLISH
        return ENGLISH

    def _detect_scope(self, text: str, lang: str, context: dict) -> Scope:
        scene_id = context.get("scene_id")
        brand = context.get("brand")
        project = context.get("project")
        video_id = context.get("job_id")

        extracted_scene = self._extract_scene_id(text, lang)
        if extracted_scene:
            return Scope(ScopeLevel.SCENE, scene_id=extracted_scene, target="*")

        if self._detect_video_scope(text, lang):
            return Scope(ScopeLevel.VIDEO, video_id=video_id or "*",
                         target="*", project=project, brand=brand)

        if self._detect_brand_scope(text, lang):
            return Scope(ScopeLevel.BRAND, target="*", brand=brand or "*")

        return Scope(ScopeLevel.GLOBAL, target="*")

    def _detect_video_scope(self, text: str, lang: str) -> bool:
        if lang == POLISH:
            return bool(self._VIDEO_SCOPE_POLISH.search(text))
        return bool(self._VIDEO_SCOPE_ENGLISH.search(text))

    def _detect_brand_scope(self, text: str, lang: str) -> bool:
        if lang == POLISH:
            return bool(self._BRAND_SCOPE_POLISH.search(text))
        return bool(self._BRAND_SCOPE_ENGLISH.search(text))

    def _extract_scene_id(self, text: str, lang: str) -> str | None:
        if lang == POLISH:
            m = self._SCENE_ID_POLISH.search(text)
            if m:
                return m.group(1)
            m = self._SCENE_NUM_POLISH.search(text)
            if m:
                return f"s{int(m.group(1))}"
        else:
            m = self._SCENE_ID_ENGLISH.search(text)
            if m:
                return m.group(1)
            m = self._SCENE_NUM_ENGLISH.search(text)
            if m:
                return f"s{int(m.group(1))}"
        return None

    # ------------------------------------------------------------------ #
    #  element detection
    # ------------------------------------------------------------------ #
    def _detect_elements(self, text: str) -> list[str]:
        found: list[str] = []
        lower = text.lower()
        for keyword, role in self._ELEMENT_KEYWORDS.items():
            if keyword in lower and role not in found:
                found.append(role)
        return found

    def _is_owner(self, context: dict) -> bool:
        return context.get("actor_role", "owner") in ("owner", "system")

    def _is_global_dont(self, text: str, lang: str) -> bool:
        if lang == POLISH:
            return bool(self._GLOBAL_DONT_POLISH.search(text))
        return bool(self._GLOBAL_DONT_ENGLISH.search(text))

    def _is_global_dont_explicit(self, text: str, lang: str) -> bool:
        if lang == POLISH:
            return bool(self._FOREVER_POLISH.search(text))
        return bool(self._FOREVER_ENGLISH.search(text))

    def _is_global_do(self, text: str, lang: str) -> bool:
        if lang == POLISH:
            return bool(self._GLOBAL_DO_POLISH.search(text))
        return bool(self._GLOBAL_DO_ENGLISH.search(text))

    def _is_exception(self, text: str, lang: str) -> bool:
        if lang == POLISH:
            return bool(self._EXCEPTION_POLISH.search(text))
        return bool(self._EXCEPTION_ENGLISH.search(text))

    def _is_retraction(self, text: str, lang: str) -> bool:
        if lang == POLISH:
            return bool(self._RETRACTION_POLISH.search(text))
        return bool(self._RETRACTION_ENGLISH.search(text))

    def _is_preference(self, text: str, lang: str) -> bool:
        if lang == POLISH:
            return bool(self._PREFERENCE_POLISH.search(text))
        return bool(self._PREFERENCE_ENGLISH.search(text))

    def _is_fact_correction(self, text: str, lang: str) -> bool:
        if lang == POLISH:
            return bool(self._FACT_CORRECTION_POLISH.search(text))
        return bool(self._FACT_CORRECTION_ENGLISH.search(text))

    _PATTERN_APPROVED = ("dobry", "good", "idealny", "ideal",
                         "prawidłowy", "correct", "zatwierdzony",
                         "approved", "akceptowalny", "acceptable")

    _PATTERN_NEGATIVE = ("nie powtarzaj", "don't repeat", "never do this",
                         "unacceptable", "niedopuszczalny", "to nie",
                         "this is bad", "avoid this")

    def _is_approved_pattern(self, text: str, lang: str) -> bool:
        lower = text.lower()
        return any(m in lower for m in self._PATTERN_APPROVED)

    def _is_negative_example(self, text: str, lang: str) -> bool:
        lower = text.lower()
        return any(m in lower for m in self._PATTERN_NEGATIVE)

    def _proposal_classification(
        self, text: str, classification: Classification,
        feedback_type: FeedbackType | None, scope: Scope,
        normalized_intent: str, *, needs_confirmation: bool, confidence: float,
        observability: Observability,
        target_element_ids: list[str] | None = None,
        questions: list[str] | None = None,
    ) -> dict[str, Any]:
        is_global_explicit = (
            classification == Classification.PERSISTENT_RULE
            and self._is_global_dont_explicit(text, self._detect_language(text))
            and scope.level == ScopeLevel.GLOBAL
        )
        return {
            "normalized_intent": normalized_intent,
            "classification": classification,
            "scope": scope,
            "feedback_type": feedback_type,
            "target_element_ids": target_element_ids or [],
            "scene_ids": [scope.scene_id] if scope.scene_id else [],
            "timestamps": [],
            "predicate_candidates": [],
            "observability": observability,
            "is_global_intent_explicit": is_global_explicit,
            "needs_confirmation": needs_confirmation,
            "confidence": confidence,
            "proposed_fix": None,
            "evidence_refs": [],
            "conflicts": [],
            "questions": questions or [],
        }

    def _make_hard_rule(
        self, text: str, classification: Classification,
        feedback_type: FeedbackType, scope: Scope, elements: list[str],
        rationale: str, *, needs_confirmation: bool, confidence: float,
    ) -> dict[str, Any]:
        predicates: list[dict[str, Any]] = []
        if feedback_type == FeedbackType.HARD_DONT:
            if elements:
                predicates.append({
                    "operator": "element_type_absent",
                    "parameters": {"element_types": elements, "contexts": ["all"]},
                })
            else:
                predicates.append({
                    "operator": "text_excludes",
                    "parameters": {"pattern": re.escape(text)},
                })
        elif feedback_type == FeedbackType.HARD_DO:
            if elements:
                predicates.append({
                    "operator": "element_type_present",
                    "parameters": {"element_types": elements, "contexts": ["all"]},
                })

        observability = (
            Observability.DETERMINISTIC if predicates else Observability.PERCEPTUAL
        )

        return {
            "normalized_intent": rationale,
            "classification": classification,
            "scope": scope,
            "feedback_type": feedback_type,
            "target_element_ids": elements,
            "scene_ids": [scope.scene_id] if scope.scene_id else [],
            "timestamps": [],
            "predicate_candidates": predicates,
            "observability": observability,
            "is_global_intent_explicit": self._is_global_dont_explicit(
                text, self._detect_language(text)),
            "needs_confirmation": needs_confirmation,
            "confidence": confidence,
            "proposed_fix": (
                "remove_element_and_reflow"
                if feedback_type == FeedbackType.HARD_DONT else None
            ),
            "evidence_refs": [],
            "conflicts": [],
            "questions": [],
        }


def interpret_feedback(
    text: str, context: dict[str, Any] | None = None
) -> RuleProposal:
    """Module-level convenience: interpret feedback text into a proposal."""
    return FeedbackInterpreter().interpret(text, context)


def to_rule_revision(
    proposal: RuleProposal, rule_id: str | None = None
) -> RuleRevision:
    """Convert a confirmed proposal into a :class:`RuleRevision`.

    If ``rule_id`` is omitted, a deterministic ID is derived from the
    normalised intent hash.
    """
    if rule_id is None:
        stable = proposal.normalized_intent or proposal.original_text
        digest = hashlib.sha256(stable.encode("utf-8")).hexdigest()[:12]
        rule_id = f"CF-{digest}"

    predicates = list(proposal.predicate_candidates)
    if not predicates:
        predicates = [{
            "operator": "text_excludes",
            "parameters": {"pattern": re.escape(proposal.original_text)},
        }]

    first = predicates[0]
    has_visual = first.get("operator") in ("contrast_minimum", "safe_area_violation")

    enforcement = ["creative_spec", "render_graph"]
    if has_visual:
        enforcement.append("visual_qa")

    repair = proposal.proposed_fix or (
        "remove_element_and_reflow"
        if proposal.feedback_type == FeedbackType.HARD_DONT else None
    )

    if proposal.predicate_candidates:
        pred = PredicateSpec(
            operator=first.get("operator", "always_true"),
            parameters=first.get("parameters", {}),
        )
    else:
        pred = PredicateSpec(
            operator=first.get("operator", "always_true"),
            parameters=first.get("parameters", {}),
        )

    node_types: tuple[str, ...]
    if proposal.target_element_ids:
        node_types = tuple(proposal.target_element_ids)
    else:
        node_types = ("*",)

    return RuleRevision(
        revision=1,
        rule_id=rule_id,
        status=RuleStatus.PROPOSED,
        kind=proposal.feedback_type or FeedbackType.HARD_DONT,
        scope=proposal.candidate_scope,
        applies_to=EntityTarget(node_types=node_types, contexts=("all",)),
        predicate=pred,
        override_policy=(
            OverridePolicy.NEVER
            if proposal.classification == Classification.PERSISTENT_RULE
            else OverridePolicy.EXPLICIT_OWNER_PER_RUN
        ),
        enforcement=tuple(enforcement),
        repair_strategy=repair,
        origin=Origin(
            feedback_event_id=None,
            actor=(
                ActorRole.OWNER
                if proposal.is_global_intent_explicit else ActorRole.REVIEWER
            ),
            actor_id=None,
        ),
        rationale=proposal.normalized_intent or proposal.original_text,
        created_at=_utcnow(),
        evidence=tuple(proposal.evidence_refs),
    )


__all__ = [
    "FeedbackInterpreter",
    "interpret_feedback",
    "to_rule_revision",
    "POLISH",
    "ENGLISH",
]
