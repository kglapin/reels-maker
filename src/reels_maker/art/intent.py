"""Per-scene artistic intent.

A :class:`SceneIntent` is the art-direction answer to "what is this scene for?"
It is derived from the scene's composition type, its position in the arc, and
the brand's motion personality.  The intent then drives:

* which text-mechanism family to use
* which preset menu to draw from
* how tight the stagger is
* whether the scene may use overshoot
* how long the reading hold must be

The intent is *advisory*: it is recorded in ``BuiltScene.meta`` and never
overrides a hard QA gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .dramaturgy import SceneBeat
from .motion_personality import MotionPersonality

# Composition families that map to an intent.  The mapping is intentionally
# coarse: the intent is a *creative* classification, not a geometry one.
COMPOSITION_INTENT: dict[str, str] = {
    "amount": "data_reveal",
    "breakdown": "data_reveal",
    "donut": "data_reveal",
    "bars": "data_reveal",
    "stacked_bars_100": "data_reveal",
    "table": "data_reveal",
    "line_chart": "data_reveal",
    "hero-number": "data_reveal",
    "comparison": "data_reveal",
    "announcement": "emotional",
    "photo": "emotional",
    "image": "emotional",
    "video": "emotional",
    "title": "emotional",
    "cta": "call_to_action",
    "closing": "call_to_action",
    "outro": "call_to_action",
    "text-only": "emotional",
    "quote": "emotional",
}

VALID_INTENTS = ("data_reveal", "emotional", "call_to_action")

# Preset families preferred by each intent.  The choreography layer draws
# from this menu instead of the full style menu when an intent is set.
INTENT_PRESET_FAMILIES: dict[str, tuple[str, ...]] = {
    "data_reveal": (
        "horizontal-wipe", "optical-tracking", "vertical-drift",
    ),
    "emotional": (
        "curtain-mask", "stagger-cascade", "depth-focus", "elastic-scale",
    ),
    "call_to_action": (
        "lateral-slide", "elastic-scale", "depth-focus",
    ),
}

# How much the intent scales the base entrance duration.  Data reveals are
# faster and more precise; emotional statements breathe.
INTENT_DURATION_SCALE: dict[str, float] = {
    "data_reveal": 0.88,
    "emotional": 1.18,
    "call_to_action": 0.95,
}

# Minimum reading hold multiplier per intent.  Emotional scenes need more
# time to land; CTAs need enough to read the CTA text.
INTENT_HOLD_SCALE: dict[str, str] = {
    "data_reveal": "balanced",
    "emotional": "airy",
    "call_to_action": "balanced",
}


class SceneIntentError(ValueError):
    """Raised when a scene intent cannot be resolved."""


@dataclass(frozen=True)
class SceneIntent:
    """The artistic intent for one scene."""

    intent: str
    composition: str
    beat: SceneBeat | None = None
    personality: MotionPersonality | None = None
    confidence: float = 0.8
    rationale: str = ""

    def __post_init__(self) -> None:
        if self.intent not in VALID_INTENTS:
            raise SceneIntentError(
                f"intent must be one of {VALID_INTENTS}, got {self.intent!r}")

    @property
    def preset_families(self) -> tuple[str, ...]:
        return INTENT_PRESET_FAMILIES[self.intent]

    @property
    def duration_scale(self) -> float:
        return INTENT_DURATION_SCALE[self.intent]

    @property
    def hold_profile(self) -> str:
        return INTENT_HOLD_SCALE[self.intent]

    @property
    def allows_overshoot(self) -> bool:
        if self.personality is None:
            return True
        return self.personality.allows_overshoot

    @property
    def easing(self) -> str:
        if self.personality is None:
            return "out-cubic"
        return self.personality.easing_preference

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "composition": self.composition,
            "confidence": round(self.confidence, 3),
            "rationale": self.rationale,
            "preset_families": list(self.preset_families),
            "duration_scale": self.duration_scale,
            "hold_profile": self.hold_profile,
            "allows_overshoot": self.allows_overshoot,
            "easing": self.easing,
            "beat": self.beat.to_dict() if self.beat else None,
            "personality": self.personality.to_dict() if self.personality else None,
        }


def resolve_scene_intent(
    scene: dict[str, Any],
    *,
    beat: SceneBeat | None = None,
    personality: MotionPersonality | None = None,
) -> SceneIntent:
    """Resolve a scene's artistic intent from its manifest.

    The composition is read from ``scene["composition"]`` (studio manifests)
    or ``scene["type"]`` (legacy kinetic manifests).  Unknown compositions
    default to ``emotional`` with a lowered confidence so the QA report can
    flag them for review.
    """
    composition = str(
        scene.get("composition")
        or scene.get("type")
        or scene.get("kind")
        or "unknown"
    ).lower()

    intent = COMPOSITION_INTENT.get(composition)
    if intent is None:
        return SceneIntent(
            intent="emotional",
            composition=composition,
            beat=beat,
            personality=personality,
            confidence=0.45,
            rationale=f"Unknown composition {composition!r}; defaulting to emotional intent.",
        )

    rationale = f"Composition {composition!r} maps to {intent} intent."
    if beat is not None:
        rationale += f" Scene is in {beat.phase} phase (energy {beat.energy:.2f})."

    return SceneIntent(
        intent=intent,
        composition=composition,
        beat=beat,
        personality=personality,
        confidence=0.85,
        rationale=rationale,
    )


def intent_for_composition(composition: str) -> str:
    """Return the intent for a composition name, defaulting to emotional."""
    return COMPOSITION_INTENT.get(str(composition).lower(), "emotional")


__all__ = [
    "SceneIntent",
    "SceneIntentError",
    "COMPOSITION_INTENT",
    "INTENT_PRESET_FAMILIES",
    "INTENT_DURATION_SCALE",
    "resolve_scene_intent",
    "intent_for_composition",
]