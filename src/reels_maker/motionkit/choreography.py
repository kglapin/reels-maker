"""Narrative choreography: who enters, when, and with which motion.

Timing is driven by explicit narration cues when available and otherwise by a
deterministic, importance-weighted stagger. The planner actively avoids
repeating the same preset in consecutive scenes, which was the main reason the
previous generator felt templated.

The optional ``intent``, ``personality`` and ``beat`` arguments wire the
art-direction layer (``reels_maker.art``) into choreography.  When omitted the
behaviour is unchanged — existing callers need no modification.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping

from ..art.dramaturgy import SceneBeat
from ..art.intent import SceneIntent
from ..art.motion_personality import MotionPersonality
from ..core.scene_graph import Node
from ..design.styles import STYLE_SYSTEMS
from ..design.tokens import DesignTokens
from .presets import (
    PRESETS,
    apply_entrance,
    apply_exit,
    canonical_preset,
    select_text_mechanism,
)


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


@dataclass(frozen=True)
class ExitTiming:
    """Restrained, motivated fade-out shortly before the cut.

    Reference-board grammar #3: exits are fewer and quieter than entrances.
    A scene only gets an exit when the full reading hold survives before the
    fade starts; otherwise the element runs to the cut unchanged.
    """
    role: str
    onset: float
    duration: float


@dataclass
class Choreography:
    entries: dict[str, EntranceTiming]
    warnings: list[dict] = field(default_factory=list)
    scene_index: int = 0
    exits: dict[str, ExitTiming] = field(default_factory=dict)

    def timing(self, role: str) -> EntranceTiming:
        if role not in self.entries:
            raise KeyError(f"No choreography entry for {role!r}")
        return self.entries[role]

    def apply(self, nodes: Mapping[str, Node], tokens: DesignTokens,
              *, seed: int = 0,
              safe_bounds: tuple[float, float, float, float] | None = None) -> dict[str, Node]:
        result = {}
        for role, node in nodes.items():
            if role in self.entries:
                entry = self.entries[role]
                apply_entrance(node, entry.preset, entry.onset,
                               entry.duration, tokens, seed=seed,
                               safe_bounds=safe_bounds)
                node.meta["motion"] = entry.preset
                node.meta["onset"] = round(entry.onset, 4)
            if role in self.exits:
                exit_entry = self.exits[role]
                apply_exit(node, exit_entry.onset, exit_entry.duration, tokens)
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
            "exits": {
                role: {"onset": round(item.onset, 4),
                       "duration": round(item.duration, 4)}
                for role, item in self.exits.items()
            },
            "warnings": list(self.warnings),
        }


def _choose_preset(
    spec: ElementSpec,
    style: str,
    scene_index: int,
    position: int,
    previous: Iterable[str],
    *,
    intent: SceneIntent | None = None,
    personality: MotionPersonality | None = None,
) -> str:
    if spec.hint:
        return canonical_preset(spec.hint)
    system = STYLE_SYSTEMS[style]
    if intent is not None:
        # Intent families are mechanism names (e.g. "curtain-mask"), not preset
        # names.  Resolve them through select_text_mechanism so an intent
        # never produces an unknown-preset crash.
        family_presets = []
        for family in intent.preset_families:
            try:
                family_presets.append(select_text_mechanism(family))
            except ValueError:
                continue
        menu = tuple(dict.fromkeys(family_presets)) or system.motions
    else:
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


def plan_choreography(
    elements: Iterable[ElementSpec],
    *,
    style: str,
    scene_index: int,
    scene_duration: float,
    tokens: DesignTokens,
    cues: Mapping[str, float] | None = None,
    intent: SceneIntent | None = None,
    personality: MotionPersonality | None = None,
    beat: SceneBeat | None = None,
) -> Choreography:
    """Build a deterministic entrance plan and explain every compromise.

    Optional art-direction arguments (``intent``, ``personality``, ``beat``)
    influence preset family choice, duration scale, stagger tightness and exit
    restraint.  When omitted the behaviour is identical to the pre-existing
    planner; existing callers need no change.
    """
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
    if personality is not None:
        stagger = personality.scaled_stagger(stagger)
    cursor = min(cues.values()) if cues else .04
    hold = tokens.motion.hold
    if intent is not None and intent.hold_profile == "airy":
        hold *= 1.18
    safe_end = max(0.0, scene_duration - hold)

    for position, spec in enumerate(ordered):
        preset = _choose_preset(
            spec, style, scene_index, position, used_presets,
            intent=intent,
        )
        used_presets.append(preset)
        duration = _duration_for(spec, preset, tokens)
        if intent is not None:
            duration *= intent.duration_scale
        if personality is not None:
            duration *= personality.entrance_duration_scale
        duration = max(.12, round(duration, 4))
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
    # Restrained exits (reference-board grammar #3). An element only fades
    # out when the complete reading hold still fits between its settle and
    # the fade onset; otherwise it runs unchanged to the cut.
    exits: dict[str, ExitTiming] = {}
    exit_duration = max(0.0, float(tokens.motion.exit))
    if personality is not None:
        exit_duration *= personality.exit_restraint
    if exit_duration > 0:
        for spec in specs:
            if spec.kind == "decor":
                continue
            entry = entries.get(spec.role)
            if entry is None:
                continue
            window = scene_duration - entry.settle
            if window - exit_duration < hold:
                continue
            exits[spec.role] = ExitTiming(
                spec.role, round(scene_duration - exit_duration, 4),
                round(exit_duration, 4))
    return Choreography(entries, warnings, scene_index, exits)


def verify_shared_element_continuity(
    built_scenes: list,
    *,
    max_anchor_jump_px: float = 320.0,
) -> dict:
    """Verify object identity and spatial continuity across consecutive BuiltScenes (MD-305)."""
    transitions = []
    violations = []
    for idx in range(len(built_scenes) - 1):
        left, right = built_scenes[idx], built_scenes[idx + 1]
        left_map: dict[str, tuple[float, float, float, float]] = {}
        right_map: dict[str, tuple[float, float, float, float]] = {}
        for root in left.at(max(0.0, left.duration - 1e-3)):
            for node in root.flatten():
                sid = node.meta.get("stable_row_id") or node.meta.get("shared_element_id")
                if sid:
                    wb = node.world_bounds()
                    if wb is not None:
                        left_map[str(sid)] = wb
        for root in right.at(0.0):
            for node in root.flatten():
                sid = node.meta.get("stable_row_id") or node.meta.get("shared_element_id")
                if sid:
                    wb = node.world_bounds()
                    if wb is not None:
                        right_map[str(sid)] = wb
        shared_ids = sorted(set(left_map) & set(right_map))
        pairs = []
        for sid in shared_ids:
            lb, rb = left_map[sid], right_map[sid]
            lcx, lcy = (lb[0] + lb[2]) / 2.0, (lb[1] + lb[3]) / 2.0
            rcx, rcy = (rb[0] + rb[2]) / 2.0, (rb[1] + rb[3]) / 2.0
            jump = ((rcx - lcx) ** 2 + (rcy - lcy) ** 2) ** 0.5
            pairs.append({
                "id": sid,
                "from_center": [round(lcx, 2), round(lcy, 2)],
                "to_center": [round(rcx, 2), round(rcy, 2)],
                "jump_px": round(jump, 2),
            })
            if jump > max_anchor_jump_px:
                violations.append({
                    "from_scene": idx + 1,
                    "to_scene": idx + 2,
                    "id": sid,
                    "jump_px": round(jump, 2),
                    "max_anchor_jump_px": max_anchor_jump_px,
                })
        transitions.append({
            "from_scene": idx + 1,
            "to_scene": idx + 2,
            "shared_count": len(shared_ids),
            "shared_ids": shared_ids,
            "pairs": pairs,
        })
    return {
        "ok": not violations,
        "transitions": transitions,
        "violations": violations,
    }


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
