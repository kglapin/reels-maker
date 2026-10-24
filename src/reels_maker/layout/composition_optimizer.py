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


DEFAULT_CANDIDATE_COMPOSITIONS = (
    "stack-center",
    "split-editorial",
    "full-bleed-type",
    "statement",
)


def solve_scene_layout(
    ctx,
    scene: Mapping[str, object],
    candidate_compositions: tuple[str, ...] | list[str] | None = None,
    *,
    fps: int = 30,
    samples_per_scene: int = 6,
    weights: Mapping[str, float] | None = None,
) -> dict:
    """Build candidate scene layouts, hard-reject timeline QA violations and pick best (MD-205).

    Each candidate composition is built into a real ``BuiltScene`` and sampled across
    all keyframe/extremum/interval frames using Studio's geometry and FreeType ink
    checkers. Any candidate with a safe-area, collision or text-ink violation at any
    sampled frame is marked invalid and cannot be selected.
    """
    from types import SimpleNamespace
    from ..components.scenes import build_scene
    from ..core.scene_graph import collect_qa_elements
    from ..qa.report import (
        _collisions, _safe_area, _text_ink_safe_area, sample_geometry_frames,
    )

    compositions = tuple(
        candidate_compositions if candidate_compositions is not None
        else DEFAULT_CANDIDATE_COMPOSITIONS
    )
    if not compositions:
        raise ValueError("candidate_compositions must not be empty")
    duration = float(scene.get("duration", getattr(ctx, "duration", 3.0)))
    frames = max(2, round(duration * fps))
    timing = SimpleNamespace(frames=frames)
    safe = ctx.layout.safe
    safe_area_px = max(1.0, safe.area)
    preferred = str(scene.get("composition") or "stack-center")
    has_visual = bool(scene.get("photo"))

    candidates: list[CompositionCandidate] = []
    built_by_id: dict[str, object] = {}

    for composition in compositions:
        candidate_id = f"layout:{composition}"
        trial_scene = dict(scene)
        trial_scene["composition"] = composition
        trial_scene.pop("type", None)
        violations: list[str] = []
        try:
            built = build_scene(ctx, trial_scene)
        except Exception as exc:
            candidates.append(CompositionCandidate(
                candidate_id=candidate_id,
                layout=composition,
                scores={k: 0.0 for k in WEIGHTS},
                violations=(f"build_error:{exc}",),
            ))
            continue

        sample_frames = sample_geometry_frames(
            built, timing, fps, samples_per_scene=samples_per_scene
        )
        seen_codes: set[str] = set()
        settled_elements: list[dict] = []
        for frame_idx in sample_frames:
            t = frame_idx / fps
            nodes = built.at(t)
            elems: list[dict] = []
            for node in nodes:
                elems.extend(collect_qa_elements(node))
            if frame_idx == sample_frames[-1]:
                settled_elements = elems
            for issue in (
                _safe_area(elems, built, t, frame_idx)
                + _collisions(elems, set(), built, t, frame_idx)
                + _text_ink_safe_area(nodes, built, t, frame_idx)
            ):
                tag = f"{issue.code}@{issue.frame}:{','.join(issue.elements)}"
                if tag not in seen_codes:
                    seen_codes.add(tag)
                    violations.append(tag)

        # Compute deterministic geometry-derived scores in 0..1
        occupied = sum(
            max(0.0, (e["bounds"][2] - e["bounds"][0]) * (e["bounds"][3] - e["bounds"][1]))
            for e in settled_elements if e.get("class") != "decor"
        )
        density = min(1.0, occupied / safe_area_px)
        # Ideal editorial density sits around 0.28..0.55 of safe area
        legibility = max(0.1, min(1.0, 1.0 - abs(density - 0.40) * 1.4))
        has_headline = "headline" in built.elements
        has_body = "body" in built.elements
        hierarchy = 0.92 if (has_headline and has_body) else (0.82 if has_headline else 0.55)
        if composition == "full-bleed-type" and not has_visual:
            hierarchy = min(1.0, hierarchy + 0.06)
        subject_retention = (
            0.95 if (has_visual and composition in ("split-editorial", "spotlight"))
            else (0.72 if has_visual else 0.90)
        )
        if settled_elements:
            cx_mean = sum((e["bounds"][0] + e["bounds"][2]) / 2 for e in settled_elements) / len(settled_elements)
            balance = max(0.2, min(1.0, 1.0 - abs(cx_mean - safe.center_x) / (safe.w / 2)))
        else:
            balance = 0.5
        continuity = 0.95 if composition == preferred else 0.80
        brand_score = 0.90
        track_count = sum(len(n.tracks) for root in built.nodes for n in root.flatten())
        motion_intensity = min(1.0, track_count / 16.0)
        crop_loss = 0.0 if not has_visual else (0.15 if composition == "split-editorial" else 0.25)

        candidates.append(CompositionCandidate(
            candidate_id=candidate_id,
            layout=composition,
            scores={
                "hierarchy": round(hierarchy, 4),
                "legibility": round(legibility, 4),
                "subject_retention": round(subject_retention, 4),
                "balance": round(balance, 4),
                "continuity": round(continuity, 4),
                "brand": round(brand_score, 4),
            },
            violations=tuple(violations),
            element_count=len(settled_elements),
            motion_intensity=round(motion_intensity, 4),
            crop_loss=round(crop_loss, 4),
        ))
        built_by_id[candidate_id] = built

    evaluation = evaluate_candidates(candidates, weights=weights)
    selected_id = evaluation["selected_id"]
    return {
        **evaluation,
        "selected_built": built_by_id.get(selected_id) if selected_id else None,
    }
