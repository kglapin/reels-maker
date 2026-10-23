"""Deterministic, explainable selection of editorial composition candidates.

Scores are normalized 0..1. Hard constraints always dominate aesthetics.
This module does not claim to replace visual review.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Mapping

WEIGHTS = {
    "hierarchy": .25,
    "legibility": .25,
    "subject_retention": .20,
    "balance": .15,
    "continuity": .10,
    "brand": .05,
}

@dataclass(frozen=True)
class CompositionCandidate:
    candidate_id: str
    layout: str
    scores: Mapping[str, float]
    violations: tuple[str, ...] = ()
    element_count: int = 0
    motion_intensity: float = 0.
    crop_loss: float = 0.
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        if not self.candidate_id or not self.layout:
            raise ValueError("candidate_id and layout are required")
        if self.element_count < 0:
            raise ValueError("element_count must be nonnegative")
        for value in (self.motion_intensity, self.crop_loss):
            if not isfinite(value) or not 0 <= value <= 1:
                raise ValueError("motion_intensity and crop_loss must be 0..1")
        for name in WEIGHTS:
            value = self.scores.get(name)
            if value is None or not isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"Missing or invalid normalized score: {name}")


def evaluate_candidates(candidates: list[CompositionCandidate],
                        weights: Mapping[str, float] | None = None) -> dict:
    """Reject unsafe candidates, rank remaining and report why.

    Stable tie-breaks favor fewer elements, less motion and lower crop loss.
    """
    weights = dict(WEIGHTS if weights is None else weights)
    if set(weights) != set(WEIGHTS):
        raise ValueError("Weights must specify all composition dimensions")
    if any(not isfinite(w) or w < 0 for w in weights.values()):
        raise ValueError("Weights must be finite and nonnegative")
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("Weights must sum to a positive number")
    weights = {k: v / total for k, v in weights.items()}
    seen = set()
    results = []
    for c in candidates:
        if c.candidate_id in seen:
            raise ValueError(f"Duplicate candidate ID: {c.candidate_id}")
        seen.add(c.candidate_id)
        breakdown = {k: round(c.scores[k] * w, 6) for k, w in weights.items()}
        score = sum(c.scores[k] * w for k, w in weights.items())
        results.append({
            "candidate_id": c.candidate_id,
            "layout": c.layout,
            "valid": not bool(c.violations),
            "violations": list(c.violations),
            "score": round(score, 6),
            "breakdown": breakdown,
            "element_count": c.element_count,
            "motion_intensity": c.motion_intensity,
            "crop_loss": c.crop_loss,
        })
    results.sort(key=lambda r: (
        not r["valid"], -r["score"] if r["valid"] else 0,
        r["element_count"], r["motion_intensity"], r["crop_loss"],
        r["candidate_id"]))
    selected = next((r for r in results if r["valid"]), None)
    return {
        "selected_id": selected["candidate_id"] if selected else None,
        "selected_reason": (
            "Highest weighted quality score among hard-constraint-valid candidates"
            if selected else "No candidate satisfies hard constraints"),
        "weights": weights,
        "candidates": results,
    }
