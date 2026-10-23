"""Narrative choreography: who enters, when, and with which motion.

Timing is driven by explicit narration cues when available and otherwise by a
deterministic, importance-weighted stagger. The planner actively avoids
repeating the same preset in consecutive scenes, which was the main reason the
previous generator felt templated.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping

from ..core.scene_graph import Node
from ..design.styles import STYLE_SYSTEMS
from ..design.tokens import DesignTokens
from .presets import PRESETS, apply_entrance, canonical_preset


@dataclass(frozen=True)
class ElementSpec:
    role: str
    weight: float = 1.0
    hint: str | None = None
    kind: str = "support"
    order: int = 0

    def __post_init__(self) -> None:
        if not self.role:
            raise ValueError("Element role cannot be empty")
        if not 0 <= self.weight <= 10:
            raise ValueError("Element weight must be between 0 and 10")


@dataclass(frozen=True)
class EntranceTiming:
    role: str
    onset: float
    duration: float
    preset: str
    explicit: bool = False

    @property
    def settle(self) -> float:
        return self.onset + self.duration


@dataclass
class Choreography:
    entries: dict[str, EntranceTiming]
    warnings: list[dict] = field(default_factory=list)
    scene_index: int = 0

    def timing(self, role: str) -> EntranceTiming:
        if role not in self.entries:
            raise KeyError(f"No choreography entry for {role!r}")
        return self.entries[role]

    def apply(self, nodes: Mapping[str, Node], tokens: DesignTokens,
              *, seed: int = 0) -> dict[str, Node]:
        result = {}
        for role, node in nodes.items():
            if role in self.entries:
                entry = self.entries[role]
                apply_entrance(node, entry.preset, entry.onset,
                               entry.duration, tokens, seed=seed)
                node.meta["motion"] = entry.preset
                node.meta["onset"] = round(entry.onset, 4)
            result[role] = node
        return result

    def to_dict(self) -> dict:
        return {
            "scene": self.scene_index + 1,
            "entries": {
                role: {"onset": round(item.onset, 4),
                       "duration": round(item.duration, 4),
                       "settle": round(item.settle, 4),
                       "preset": item.preset,
                       "explicit": item.explicit}
                for role, item in self.entries.items()
            },
            "warnings": list(self.warnings),
        }


def _choose_preset(spec: ElementSpec, style: str, scene_index: int,
                   position: int, previous: Iterable[str]) -> str:
    if spec.hint:
        return canonical_preset(spec.hint)
    system = STYLE_SYSTEMS[style]
    menu = system.motions
    start = (scene_index * 2 + position + spec.order) % len(menu)
    avoid = list(previous)[-2:]
    for offset in range(len(menu)):
        candidate = menu[(start + offset) % len(menu)]
        if candidate not in avoid:
            return candidate
    return menu[start]


def _duration_for(spec: ElementSpec, preset: str, tokens: DesignTokens) -> float:
    base = tokens.motion.enter
    if spec.kind == "display":
        base *= 1.08
    elif spec.kind == "control":
        base *= .78
    if preset in ("mask-rise", "tracking-in", "reveal-right", "scale-focus"):
        base *= 1.08
    if preset in ("pop-settle", "word-cascade"):
        base *= .92
    return max(.16, round(base, 4))


def plan_choreography(elements: Iterable[ElementSpec], *,
                      style: str, scene_index: int, scene_duration: float,
                      tokens: DesignTokens,
                      cues: Mapping[str, float] | None = None) -> Choreography:
    """Build a deterministic entrance plan and explain every compromise."""
    specs = list(elements)
    if not specs:
        return Choreography({}, [], scene_index)
    if len({spec.role for spec in specs}) != len(specs):
        raise ValueError("Choreography element roles must be unique")
    if style not in STYLE_SYSTEMS:
        raise ValueError(f"Unknown style {style!r}")
    if scene_duration <= 0:
        raise ValueError("Scene duration must be positive")
    cues = dict(cues or {})
    known = {spec.role for spec in specs}
    unknown = set(cues) - known
    if unknown:
        raise ValueError("Cues refer to unknown elements: "
                         + ", ".join(sorted(unknown)))

    entries: dict[str, EntranceTiming] = {}
    warnings: list[dict] = []
    used_presets: list[str] = []
    # Explicit cues define the narrative anchor. Remaining elements are
    # scheduled by importance, never by JSON key order.
    ordered = sorted(
        specs,
        key=lambda spec: (cues.get(spec.role, float("inf")),
                          -spec.weight, spec.order, spec.role))
    stagger = tokens.motion.stagger
    if tokens.density == "dense":
        stagger *= .84
    cursor = min(cues.values()) if cues else .04
    hold = tokens.motion.hold
    safe_end = max(0.0, scene_duration - hold)

    for position, spec in enumerate(ordered):
        preset = _choose_preset(spec, style, scene_index, position, used_presets)
        used_presets.append(preset)
        duration = _duration_for(spec, preset, tokens)
        explicit = spec.role in cues
        onset = float(cues[spec.role]) if explicit else max(0.0, cursor)
        if not explicit and onset + duration > safe_end:
            onset = max(0.0, min(onset, safe_end - duration))
        if onset + duration > safe_end:
            compressed = max(.12, safe_end - onset)
            warnings.append({
                "code": "settle_window_compressed",
                "role": spec.role,
                "message": ("Entrance was compressed to preserve the reading "
                            "window before the cut."),
                "requested": round(duration, 4),
                "applied": round(compressed, 4),
            })
            duration = compressed
        if onset + duration + hold > scene_duration + 1e-6:
            warnings.append({
                "code": "insufficient_reading_hold",
                "role": spec.role,
                "message": ("This element settles later than the scene allows; "
                            "shorten copy, move the cue earlier or extend the shot."),
                "available": round(scene_duration - onset, 4),
                "needed": round(duration + hold, 4),
            })
        if not explicit:
            cursor = onset + stagger
        entries[spec.role] = EntranceTiming(
            role=spec.role, onset=round(onset, 4),
            duration=round(duration, 4), preset=preset, explicit=explicit)

    # A control or display element should never arrive before its supporting
    # label when both are auto-timed at the same weight; swap only when the
    # user did not specify an explicit cue for either.
    if not cues:
        text_roles = [spec for spec in specs if spec.kind == "display"]
        for display in text_roles[:1]:
            for support in specs:
                if (support.kind == "support" and support.weight > display.weight
                        and entries[support.role].onset < entries[display.role].onset):
                    first, second = entries[display.role], entries[support.role]
                    entries[display.role] = EntranceTiming(
                        first.role, second.onset, first.duration, first.preset)
                    entries[support.role] = EntranceTiming(
                        second.role, first.onset, second.duration, second.preset)
    return Choreography(entries, warnings, scene_index)


def variety_report(plans: Iterable[Choreography]) -> dict:
    """Detect monotonous rhythm without pretending to judge aesthetics."""
    plans = list(plans)
    presets = [entry.preset for plan in plans for entry in plan.entries.values()]
    counts: dict[str, int] = {}
    for preset in presets:
        counts[preset] = counts.get(preset, 0) + 1
    repeated_scenes = []
    for plan in plans:
        scene_presets = [entry.preset for entry in plan.entries.values()]
        if len(scene_presets) >= 3 and len(set(scene_presets)) == 1:
            repeated_scenes.append(plan.scene_index + 1)
    dominant = max(counts.values(), default=0)
    ratio = dominant / len(presets) if presets else 0.0
    return {
        "preset_counts": counts,
        "dominant_ratio": round(ratio, 3),
        "repeated_scene_presets": repeated_scenes,
        "status": ("review" if ratio > .55 or repeated_scenes else "pass"),
    }
