"""Narrative arc and per-scene beat typing.

Wraps :func:`audiokit.cues.plan_audio_dramaturgy` into a typed, queryable
structure that the art-direction layer can read without touching the audio
pipeline.  Every scene receives a ``SceneBeat`` describing its phase, energy
and accent flag; the choreography layer uses these to choose preset families
and timing curves instead of relying on scene index alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from ..audiokit.cues import plan_audio_dramaturgy

VALID_PHASES = ("hook", "build", "climax", "resolve")


@dataclass(frozen=True)
class SceneBeat:
    """One scene's position in the narrative arc."""

    scene_index: int
    phase: str
    energy: float
    accent_hit: bool
    start_s: float
    duration_s: float

    def __post_init__(self) -> None:
        if self.phase not in VALID_PHASES:
            raise ValueError(f"Unknown phase {self.phase!r}; choose one of {VALID_PHASES}")
        if not 0.0 <= self.energy <= 1.0:
            raise ValueError("energy must be between 0.0 and 1.0")

    @property
    def end_s(self) -> float:
        return self.start_s + self.duration_s

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene": self.scene_index + 1,
            "phase": self.phase,
            "energy": round(self.energy, 3),
            "accent_hit": self.accent_hit,
            "start_s": round(self.start_s, 4),
            "duration_s": round(self.duration_s, 4),
            "end_s": round(self.end_s, 4),
        }


@dataclass(frozen=True)
class DramaturgyPlan:
    """Full narrative arc across all scenes."""

    style: str
    beats: tuple[SceneBeat, ...]
    accent_density: float
    over_synchronized: bool

    def beat_for(self, scene_index: int) -> SceneBeat:
        for beat in self.beats:
            if beat.scene_index == scene_index:
                return beat
        raise KeyError(f"No beat for scene {scene_index}")

    def phases(self) -> list[str]:
        return [b.phase for b in self.beats]

    def energies(self) -> list[float]:
        return [b.energy for b in self.beats]

    def to_dict(self) -> dict[str, Any]:
        return {
            "style": self.style,
            "scene_count": len(self.beats),
            "accented_cuts": sum(1 for b in self.beats if b.accent_hit),
            "accent_density": round(self.accent_density, 3),
            "over_synchronized": self.over_synchronized,
            "beats": [b.to_dict() for b in self.beats],
        }


def plan_dramaturgy(
    scene_durations: Iterable[float],
    *,
    style: str = "editorial-premium",
) -> DramaturgyPlan:
    """Build a typed narrative arc from scene durations.

    Thin wrapper over :func:`audiokit.cues.plan_audio_dramaturgy` — the audio
    pipeline keeps its own copy of the raw dict; this is the typed view used by
    the art-direction layer.

    Accent hits land on the hook, the climax and the resolve, plus every third
    build scene when the reel is long enough that a wall of SFX would otherwise
    blur the rhythm.  The ``over_synchronized`` guard trips when accent density
    exceeds 0.75, which would mean the cut track is doing all the work.
    """
    durations = [float(d) for d in scene_durations]
    raw = plan_audio_dramaturgy(durations, style=style)
    beats = tuple(
        SceneBeat(
            scene_index=stage["scene"] - 1,
            phase=stage["phase"],
            energy=float(stage["energy"]),
            accent_hit=bool(stage["accent_hit"]),
            start_s=float(stage["start_s"]),
            duration_s=float(stage["duration_s"]),
        )
        for stage in raw["stages"]
    )
    return DramaturgyPlan(
        style=raw["style"],
        beats=beats,
        accent_density=float(raw["sync_density"]),
        over_synchronized=bool(raw["over_synchronized"]),
    )


def resolve_beat_for_scene(
    plan: DramaturgyPlan, scene_index: int
) -> SceneBeat:
    """Return the beat for a scene, falling back to a neutral build beat."""
    try:
        return plan.beat_for(scene_index)
    except KeyError:
        return SceneBeat(
            scene_index=scene_index,
            phase="build",
            energy=0.70,
            accent_hit=False,
            start_s=0.0,
            duration_s=0.0,
        )


__all__ = [
    "DramaturgyPlan",
    "SceneBeat",
    "plan_dramaturgy",
    "resolve_beat_for_scene",
]