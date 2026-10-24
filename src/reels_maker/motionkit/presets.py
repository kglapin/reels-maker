"""Entrance presets expressed as property tracks.

Presets are functions, not one monolithic ``pop()``. Every preset touches only
the axes it needs, and choreography decides which preset an element receives
based on narrative role, style and scene position.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math

from ..core.scene_graph import Node
from ..design.tokens import DesignTokens
from .keyframes import Keyframe, Track


@dataclass(frozen=True)
class Preset:
    name: str
    role: str
    distance: float
    scale_from: float
    reveal: str | None
    easing: str
    default_duration: float
    per_word: bool = False


PRESETS = {
    "fade-up": Preset("fade-up", "support", 26, 1.0, None, "out-cubic", .42),
    "rise": Preset("rise", "support", 40, 1.0, None, "out-quart", .46),
    "mask-rise": Preset("mask-rise", "display", 0, 1.0, "up", "out-quart", .52),
    "word-cascade": Preset("word-cascade", "display", 22, .97, "up", "out-cubic", .34),
    "pop-settle": Preset("pop-settle", "display", 18, .88, None, "back", .40),
    "slide-left": Preset("slide-left", "support", 54, 1.0, None, "out-quart", .46),
    "slide-right": Preset("slide-right", "support", 54, 1.0, None, "out-quart", .46),
    "reveal-right": Preset("reveal-right", "panel", 0, 1.0, "right", "in-out-quart", .52),
    "tracking-in": Preset("tracking-in", "display", 0, 1.0, None, "out-expo", .60),
    "scale-focus": Preset("scale-focus", "visual", 0, 1.06, None, "out-expo", .72),
    "none": Preset("none", "support", 0, 1.0, None, "linear", 0.0),
}

PRESET_ALIASES = {
    "mask": "mask-rise", "cascade": "word-cascade", "pop": "pop-settle",
    "slide": "slide-left", "fade": "fade-up", "rise-soft": "rise",
    "kinetic-rise": "pop-settle", "scale": "scale-focus",
}


def _safe_translation(node: Node, distance: float, axis: str,
                      safe_bounds: tuple[float, float, float, float] | None) -> float:
    """Clamp an entrance offset so every translated node AABB stays safe."""
    if safe_bounds is None or distance == 0:
        return distance
    if len(safe_bounds) != 4:
        raise ValueError("safe_bounds must be left, top, right, bottom")
    if not all(math.isfinite(value) for value in safe_bounds):
        raise ValueError("safe_bounds values must be finite")
    box = node.world_bounds()
    if box is None:
        return distance
    if axis == "x":
        low, high = safe_bounds[0] - box[0], safe_bounds[2] - box[2]
    elif axis == "y":
        low, high = safe_bounds[1] - box[1], safe_bounds[3] - box[3]
    else:
        raise ValueError("safe translation axis must be x or y")
    if distance > 0:
        return min(distance, max(0.0, high))
    return max(distance, min(0.0, low))


def _safe_scale(node: Node, requested: float,
                safe_bounds: tuple[float, float, float, float] | None) -> float:
    """Limit scale-up to the largest factor that fits the safe rectangle."""
    if safe_bounds is None or requested <= 1:
        return requested
    box = node.world_bounds()
    if box is None:
        return requested
    anchor = node.anchor or ((box[0] + box[2]) / 2,
                             (box[1] + box[3]) / 2)
    ax, ay = anchor
    limits = [requested]
    for extent, pivot, safe_min, safe_max in (
        (box[0], ax, safe_bounds[0], safe_bounds[2]),
        (box[2], ax, safe_bounds[0], safe_bounds[2]),
        (box[1], ay, safe_bounds[1], safe_bounds[3]),
        (box[3], ay, safe_bounds[1], safe_bounds[3]),
    ):
        distance = extent - pivot
        boundary = safe_min if distance < 0 else safe_max
        if distance:
            limits.append((boundary - pivot) / distance)
    return max(.01, min(limits))


def canonical_preset(name: str | None) -> str:
    if not name:
        return "fade-up"
    key = name.strip().lower().replace("_", "-")
    key = PRESET_ALIASES.get(key, key)
    if key not in PRESETS:
        raise ValueError(f"Unknown motion preset {name!r}; choose one of "
                         + ", ".join(sorted(PRESETS)))
    return key


def apply_entrance(node: Node, preset: str, onset: float, duration: float,
                   tokens: DesignTokens, *, seed: int = 0,
                   distance: float | None = None,
                   safe_bounds: tuple[float, float, float, float] | None = None) -> Node:
    """Attach entrance tracks to a node; leave static nodes untouched."""
    key = canonical_preset(preset)
    spec = PRESETS[key]
    if spec.name == "none" or duration <= 0:
        return node
    if onset < 0 or not duration > 0:
        raise ValueError("Entrance timing must be non-negative")
    scale = tokens.scale
    travel = (spec.distance if distance is None else distance) * scale
    end = onset + duration
    fade_in = min(max(duration * .65, .12), duration)
    if key in ("fade-up", "rise"):
        node.track("opacity", Track([
            Keyframe(onset, 0.0, "out-cubic"),
            Keyframe(onset + fade_in, 1.0, "out-cubic")]))
        node.track("dy", Track([
            Keyframe(onset, _safe_translation(node, travel, "y", safe_bounds), spec.easing),
            Keyframe(end, 0.0, spec.easing)]))
    elif key in ("slide-left", "slide-right"):
        node.track("opacity", Track([
            Keyframe(onset, 0.0, "out-cubic"),
            Keyframe(onset + fade_in, 1.0, "out-cubic")]))
        requested = travel if key == "slide-left" else -travel
        start = _safe_translation(node, requested, "x", safe_bounds)
        node.track("dx", Track([
            Keyframe(onset, start, spec.easing),
            Keyframe(end, 0.0, spec.easing)]))
    elif key == "pop-settle":
        start_scale = _safe_scale(node, spec.scale_from, safe_bounds)
        scale_easing = ("back" if safe_bounds is None or
                        _safe_scale(node, tokens.motion.overshoot, safe_bounds)
                        >= tokens.motion.overshoot else "out-cubic")
        node.track("opacity", Track([
            Keyframe(onset, 0.0, "out-cubic"),
            Keyframe(onset + min(duration * .55, .2), 1.0, "out-cubic")]))
        node.track("scale", Track([
            Keyframe(onset, start_scale, scale_easing),
            Keyframe(end, 1.0, scale_easing)]))
        node.track("dy", Track([
            Keyframe(onset, _safe_translation(node, travel * .5, "y", safe_bounds), "out-quart"),
            Keyframe(end, 0.0, "out-quart")]))
    elif key == "mask-rise":
        node.reveal = {**(node.reveal or {}), "direction": "up", "progress": 0.0}
        node.track("reveal", Track([
            Keyframe(onset, 0.0, spec.easing),
            Keyframe(end, 1.0, spec.easing)]))
        node.track("dy", Track([
            Keyframe(onset, _safe_translation(node, travel * .35, "y", safe_bounds), "out-quart"),
            Keyframe(end, 0.0, "out-quart")]))
    elif key == "reveal-right":
        node.reveal = {**(node.reveal or {}), "direction": "right", "progress": 0.0}
        node.track("reveal", Track([
            Keyframe(onset, 0.0, spec.easing),
            Keyframe(end, 1.0, spec.easing)]))
    elif key == "word-cascade":
        node.track("opacity", Track([
            Keyframe(onset, 0.0, "out-cubic"),
            Keyframe(onset + min(.22, duration), 1.0, "out-cubic")]))
        node.track("dy", Track([
            Keyframe(onset, _safe_translation(node, travel, "y", safe_bounds), spec.easing),
            Keyframe(end, 0.0, spec.easing)]))
        node.track("scale", Track([
            Keyframe(onset, _safe_scale(node, spec.scale_from, safe_bounds), "out-cubic"),
            Keyframe(end, 1.0, "out-cubic")]))
    elif key == "tracking-in":
        node.track("opacity", Track([
            Keyframe(onset, 0.0, "out-cubic"),
            Keyframe(onset + .2, 0.92, "out-cubic")]))
        node.track("prop.tracking_offset", Track([
            Keyframe(onset, tokens.px(14), "out-expo"),
            Keyframe(end, 0.0, "out-expo")]))
    elif key == "scale-focus":
        start_scale = _safe_scale(node, spec.scale_from, safe_bounds)
        node.track("opacity", Track([
            Keyframe(onset, 0.0, "out-cubic"),
            Keyframe(onset + duration * .45, 1.0, "out-cubic")]))
        node.track("scale", Track([
            Keyframe(onset, start_scale, "out-expo"),
            Keyframe(end, 1.0, "out-expo")]))
    else:  # pragma: no cover - canonical_preset already guards this
        raise ValueError(f"Unhandled preset {key!r}")
    return node


def apply_exit(node: Node, onset: float, duration: float,
               tokens: DesignTokens, *, drift_px: float | None = None) -> Node:
    """Restrained, motivated exit fade (reference-board grammar #3).

    The exit is a pure opacity fade: quieter than any entrance, no new motion
    axis, no positional drift (late drift can push settled type out of the
    safe area — verified by QA sampling). onset/duration must have been
    planned so the full reading hold precedes the fade.
    """
    if duration <= 0:
        raise ValueError("Exit duration must be positive")
    if onset < 0:
        raise ValueError("Exit onset must be nonnegative")
    end = onset + duration
    opacity = node.tracks.get("opacity")
    if opacity is None:
        node.track("opacity", Track([Keyframe(onset, 1.0, "out-quad"),
                                     Keyframe(end, 0.0, "out-quad")]))
    else:
        current = float(opacity.value(onset))
        easing = opacity.keys[-1].easing
        opacity.add(onset, current, easing)
        opacity.add(end, 0.0, "out-quad")
    node.meta["exit_onset"] = round(onset, 4)
    node.meta["exit_duration"] = round(duration, 4)
    return node


def camera_track(duration: float, intensity: float = .06,
                 direction: str = "push-in") -> dict[str, Track]:
    """Subtle photo camera motion. Never a fast zoom or a whip pan."""
    if duration <= 0:
        raise ValueError("Camera duration must be positive")
    if not 0 <= intensity <= .22:
        raise ValueError("Camera intensity must be between 0 and 0.22")
    if direction not in ("push-in", "pull-out", "pan-right", "pan-left",
                         "drift-up"):
        raise ValueError("Unsupported camera direction")
    start, end = 1.0, 1.0 + intensity
    if direction == "pull-out":
        start, end = 1.0 + intensity, 1.0
    zoom = Track([Keyframe(0.0, start, "smooth"),
                  Keyframe(duration, end, "smooth")])
    pan_x = Track([Keyframe(0.0, 0.0, "smooth"),
                   Keyframe(duration, intensity * .35 if direction == "pan-right"
                            else -intensity * .35 if direction == "pan-left" else 0.0,
                            "smooth")])
    pan_y = Track([Keyframe(0.0, 0.0, "smooth"),
                   Keyframe(duration, -intensity * .22
                            if direction == "drift-up" else 0.0, "smooth")])
    return {"zoom": zoom, "x": pan_x, "y": pan_y}


def progress_track(onset: float, duration: float, *,
                   easing: str = "out-cubic", start: float = 0.0) -> Track:
    if duration <= 0:
        raise ValueError("Progress duration must be positive")
    return Track([Keyframe(max(0.0, onset), start, easing),
                  Keyframe(onset + duration, 1.0, easing)])


def number_track(value: float, onset: float, duration: float, *,
                 start: float = 0.0, easing: str = "out-cubic") -> Track:
    return Track([Keyframe(max(0.0, onset), start, easing),
                  Keyframe(onset + duration, float(value), easing)])


def restyle(node: Node, *, opacity: float | None = None,
            color: tuple[int, int, int] | None = None) -> Node:
    """Convenience for components that need a static variant."""
    node = replace(node) if False else node
    if opacity is not None:
        node.opacity = opacity
    if color is not None:
        node.props["color"] = color
    return node
