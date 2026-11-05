"""Deterministic motion and editing checks for the QA report.

These guards catch the obvious animation/editing mistakes that make
short-form video look amateur: elements left faded out, strobing or
fluttering motion, exaggerated transforms, dead static tails, crowded
entrances, monotonous transitions and duplicated adjacent scenes.

Everything here is a warning unless stated otherwise; aesthetic judgement
still requires human review on a real device.
"""
from __future__ import annotations

import math

from ..core.scene_graph import Node
from .models import Issue

_SAMPLE_DT = 1.0 / 30.0
_MAX_REVERSALS_PER_SECOND = 4
_MIN_OPACITY = 0.15
_MAX_SCALE = 2.2
_MAX_ROTATION_DEG = 25.0
_MAX_FINAL_OPACITY_GAP = 0.05
_STATIC_TAIL_MIN_SECONDS = 1.5
_STATIC_TAIL_RATIO = 0.35
_CROWD_WINDOW = 0.30
_CROWD_LIMIT = 4


_TIME_DEPENDENT = frozenset({"video", "mesh3d", "sequence"})


def _subtree_settle(node: Node) -> float:
    settle = 0.0
    for descendant in node.flatten():
        if descendant.kind in _TIME_DEPENDENT:
            return math.inf
        for track in descendant.tracks.values():
            settle = max(settle, track.end)
    return settle


def _iter_nodes(built) -> list[Node]:
    nodes = []
    for root in built.nodes:
        nodes.extend(root.flatten())
    return nodes


def _numeric(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _sampled_track_values(track, duration: float) -> list[float]:
    steps = max(2, int(math.ceil(duration / _SAMPLE_DT)) + 1)
    values = []
    for index in range(steps):
        number = _numeric(track.value(index * _SAMPLE_DT))
        if number is None:
            return []
        values.append(number)
    return values


def _reversal_count(values: list[float]) -> int:
    """Count direction reversals, ignoring flat runs shorter than a frame."""
    diffs = [b - a for a, b in zip(values, values[1:])]
    significant = [d for d in diffs if abs(d) > 1e-6]
    if len(significant) < 3:
        return 0
    reversals = 0
    previous_sign = 1 if significant[0] > 0 else -1
    for diff in significant[1:]:
        sign = 1 if diff > 0 else -1
        if sign != previous_sign:
            reversals += 1
            previous_sign = sign
    return reversals


def _flutter_issues(built) -> list[Issue]:
    issues = []
    duration = built.duration
    for node in _iter_nodes(built):
        for name, track in node.tracks.items():
            values = _sampled_track_values(track, duration)
            if not values:
                continue
            label = f"{node.role}/{name}"
            if name == "opacity" and _reversal_count(values) >= 6:
                dips = sum(1 for value in values if value < _MIN_OPACITY)
                if dips >= 3:
                    issues.append(Issue(
                        "blink_cycle", "warning",
                        f"Element {node.role!r} fades below {_MIN_OPACITY:.0%} "
                        "opacity repeatedly; strobe/blink cycles are a "
                        "photosensitivity risk and usually look like a bug.",
                        built.index + 1, None, [node.role],
                        "Replace the blink loop with a single motivated "
                        "pulse or remove it."))
            window = max(1, int(round(1.0 / _SAMPLE_DT)))
            peak = 0
            for start in range(0, len(values) - window + 1):
                peak = max(peak, _reversal_count_local(values, start, window))
            if peak > _MAX_REVERSALS_PER_SECOND:
                issues.append(Issue(
                    "motion_flutter", "warning",
                    f"Track {label!r} oscillates {peak} times per second; "
                    "rapid back-and-forth motion reads as jitter, not style.",
                    built.index + 1, None, [node.role],
                    "Smooth the curve, reduce the frequency or replace it "
                    "with a single eased move."))
                break
    return issues


def _reversal_count_local(values: list[float], start: int,
                          window: int) -> int:
    segment = values[start:start + window]
    diffs = [b - a for a, b in zip(segment, segment[1:])]
    significant = [d for d in diffs if abs(d) > 1e-6]
    if len(significant) < 3:
        return 0
    reversals = 0
    previous_sign = 1 if significant[0] > 0 else -1
    for diff in significant[1:]:
        sign = 1 if diff > 0 else -1
        if sign != previous_sign:
            reversals += 1
            previous_sign = sign
    return reversals


def _endpoint_issues(built) -> list[Issue]:
    """Flag tracks whose settled value looks like an unfinished animation."""
    issues = []
    for node in _iter_nodes(built):
        for name, track in node.tracks.items():
            if not track.keys:
                continue
            end_value = _numeric(track.value(track.end))
            if end_value is None:
                continue
            if name == "opacity" and end_value < 1.0 - _MAX_FINAL_OPACITY_GAP:
                issues.append(Issue(
                    "low_final_opacity", "warning",
                    f"Element {node.role!r} settles at {end_value:.0%} "
                    "opacity and stays faded for the rest of the scene.",
                    built.index + 1, round(track.end, 3), [node.role],
                    "Add a keyframe returning opacity to 1.0, or remove the "
                    "track if the fade was unintended."))
            if name == "scale" and end_value > _MAX_SCALE:
                issues.append(Issue(
                    "exaggerated_scale", "warning",
                    f"Element {node.role!r} ends at {end_value:.1f}x scale; "
                    "extreme magnification usually crops copy and looks like "
                    "a mistake rather than a choice.",
                    built.index + 1, round(track.end, 3), [node.role],
                    "Reduce the peak scale or simplify the move."))
            if name == "rotation" and abs(end_value) > _MAX_ROTATION_DEG:
                issues.append(Issue(
                    "exaggerated_rotation", "warning",
                    f"Element {node.role!r} ends rotated "
                    f"{end_value:.0f}°; steep angles distort text and icons.",
                    built.index + 1, round(track.end, 3), [node.role],
                    "Reduce the angle or switch to a subtler tilt."))
    return issues


def _static_tail_issue(built) -> list[Issue]:
    """Warn when everything stops moving long before the scene ends."""
    duration = built.duration
    activity_end = 0.0
    settle_fn = getattr(built, "_subtree_settle", None)
    for node in built.nodes:
        settle = (settle_fn(node) if settle_fn is not None
                  else _subtree_settle(node))
        if not math.isfinite(settle):
            return []  # video/sequence/mesh keeps the frame alive
        if settle > activity_end:
            activity_end = settle
    tail = duration - activity_end
    if tail <= max(_STATIC_TAIL_MIN_SECONDS,
                   duration * _STATIC_TAIL_RATIO):
        return []
    return [Issue(
        "static_tail", "warning",
        f"All motion settles at {activity_end:.2f}s but the scene runs "
        f"{duration:.2f}s; the last {tail:.1f}s is a frozen frame.",
        built.index + 1, round(activity_end, 3), [],
        "Shorten the shot, add motivated ambient motion, or extend an "
        "entrance/cue so the frame keeps living.")]


def _crowding_issue(built) -> list[Issue]:
    choreography = getattr(built, "choreography", None)
    entries = getattr(choreography, "entries", {}) or {}
    onsets = sorted(entry.onset for entry in entries.values())
    for start in range(len(onsets)):
        crowded = sum(1 for onset in onsets[start:]
                      if onset - onsets[start] <= _CROWD_WINDOW)
        if crowded > _CROWD_LIMIT:
            return [Issue(
                "entrance_crowding", "warning",
                f"{crowded} elements enter within {_CROWD_WINDOW:.2f}s; "
                "simultaneous entrances read as noise rather than hierarchy.",
                built.index + 1, round(onsets[start], 3), [],
                "Increase the stagger or group related elements into one "
                "composite entrance.")]
    return []


def audit_motion(built_scenes, project) -> list[Issue]:
    """Per-scene motion hygiene plus project-level edit checks."""
    issues: list[Issue] = []
    for built in built_scenes:
        issues.extend(_flutter_issues(built))
        issues.extend(_endpoint_issues(built))
        issues.extend(_static_tail_issue(built))
        issues.extend(_crowding_issue(built))
    issues.extend(_shared_element_issues(built_scenes))
    issues.extend(_transition_monotony(project))
    issues.extend(_repeated_adjacent_scenes(built_scenes))
    return issues


def _shared_element_issues(built_scenes) -> list[Issue]:
    from ..motionkit.choreography import verify_shared_element_continuity

    if not all(hasattr(built, "at") for built in built_scenes):
        return []
    report = verify_shared_element_continuity(built_scenes)
    issues = []
    for violation in report["violations"]:
        issues.append(Issue(
            "shared_element_jump", "error",
            f"Shared element {violation['id']!r} jumps "
            f"{violation['jump_px']:.0f}px between scenes "
            f"{violation['from_scene']} and {violation['to_scene']}.",
            violation["to_scene"], None, [str(violation["id"])],
            "Keep the shared element's position continuous or drop the "
            "shared-element marker if the jump is intentional."))
    return issues


def _transition_config(scene: dict) -> dict:
    for key in ("transition_out", "transition_in"):
        config = scene.get(key)
        if isinstance(config, dict) and config.get("type") not in (None, "cut"):
            return config
    return {}


def _transition_monotony(project) -> list[Issue]:
    configs = [_transition_config(scene) for scene in project.scenes]
    active = [config.get("type", "cut") for config in configs]
    cuts = sum(1 for kind in active if kind == "cut")
    if len(active) < 3:
        return []
    non_cut = [kind for kind in active if kind != "cut"]
    if non_cut:
        counts: dict[str, int] = {}
        for kind in non_cut:
            counts[kind] = counts.get(kind, 0) + 1
        dominant, dominant_count = max(counts.items(),
                                       key=lambda item: item[1])
        if dominant_count / len(non_cut) > .6:
            return [Issue(
                "transition_monotony", "warning",
                f"{dominant_count}/{len(non_cut)} transitions use "
                f"{dominant!r}; repeated transitions become wallpaper.",
                None, None, [],
                "Reserve each transition type for a specific narrative "
                "beat or return to hard cuts.")]
    if cuts / len(active) < .5 and len(non_cut) > 2:
        return [Issue(
            "transition_overuse", "warning",
            "More than half of the edits use a non-cut transition; "
            "constant transitions hide weak shot-to-shot reasoning.",
            None, None, [],
            "Default to cuts and keep transitions for genuine emphasis.")]
    return []


def _scene_text(scene: dict) -> str:
    parts = []
    for key in ("kicker", "headline", "title"):
        value = scene.get(key)
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, dict):
            runs = value.get("runs") or []
            text = "".join(str(run.get("text", "")) for run in runs
                           if isinstance(run, dict))
            if text:
                parts.append(text)
    return " ".join(parts).strip().lower()


def _repeated_adjacent_scenes(built_scenes) -> list[Issue]:
    issues = []
    for previous, current in zip(built_scenes, built_scenes[1:]):
        prev_layout = getattr(previous, "layout", None)
        curr_layout = getattr(current, "layout", None)
        same_recipe = (getattr(prev_layout, "recipe", None)
                       == getattr(curr_layout, "recipe", None)
                       and getattr(prev_layout, "recipe", None) is not None)
        same_text = (_scene_text(getattr(previous, "scene", {}) or {})
                     == _scene_text(getattr(current, "scene", {}) or {})
                     and _scene_text(getattr(current, "scene", {}) or {})
                     != "")
        if same_recipe and same_text:
            issues.append(Issue(
                "repeated_adjacent_scene", "warning",
                f"Scenes {previous.index + 1} and {current.index + 1} use "
                "the same composition and copy back-to-back.",
                current.index + 1, None, [],
                "Merge them or differentiate the copy/composition; a "
                "duplicate shot usually signals an editing mistake."))
    return issues
