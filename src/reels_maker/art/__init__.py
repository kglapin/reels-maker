"""Artistic direction layer for motion design.

Connects the existing audio dramaturgy arc (``audiokit.cues.plan_audio_dramaturgy``)
and beat grid (``plan_beat_cue_mix``) to the scene-building pipeline so that
choreography is driven by narrative intent, not just deterministic stagger.

The layer is intentionally small and additive: it never overrides a hard QA
gate, and every decision is recorded in ``BuiltScene.meta`` for audit.
"""

from __future__ import annotations

from typing import Any

from .beat import BeatGrid, plan_beat_grid
from .dramaturgy import (
    DramaturgyPlan,
    SceneBeat,
    plan_dramaturgy,
    resolve_beat_for_scene,
)
from .intent import SceneIntent, resolve_scene_intent
from .motion_personality import (
    MotionPersonality,
    MotionPersonalityError,
    resolve_motion_personality,
)

__all__ = [
        "BeatGrid",
    "DramaturgyPlan",
    "MotionPersonality",
    "MotionPersonalityError",
    "SceneBeat",
    "SceneIntent",
    "plan_beat_grid",
    "plan_dramaturgy",
    "resolve_motion_personality",
    "resolve_scene_intent",
]