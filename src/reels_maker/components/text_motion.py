"""Reusable timing curves for authored text-entry animations."""
from __future__ import annotations

import math

from ..motionkit.keyframes import Keyframe, Track


def typing_track(text: str, start: float, duration: float, *,
                 profile: str = "steady") -> Track:
    """Reveal a string with deterministic cadence and punctuation pauses.

    `human` varies inter-key intervals gently and pauses at word boundaries;
    `fast` tightens the spacing between keys while preserving the total duration.
    The animation remains reproducible and ends on the exact character count.
    """
    if profile not in ("steady", "human", "fast"):
        raise ValueError("typing profile must be steady, human or fast")
    if not isinstance(text, str):
        raise ValueError("typed text must be a string")
    if not math.isfinite(float(start)) or not math.isfinite(float(duration)):
        raise ValueError("typing start and duration must be finite")
    if duration <= 0:
        raise ValueError("typing duration must be positive")
    if not text:
        return Track([Keyframe(start, 0.0, "linear")])

    weights = []
    for index, char in enumerate(text):
        weight = 1.0
        if profile == "human":
            # Deterministic micro-variation avoids metronomic typing without
            # introducing randomness into tests or cache keys.
            weight += .11 * math.sin((index + 1) * 2.17)
            if char.isspace():
                weight += .65
            elif char in ",.;:!?…—-":
                weight += 1.35
            elif index and text[index - 1].isspace():
                weight += .18
        elif profile == "fast":
            weight = .78 + .07 * math.sin((index + 1) * 1.71)
            if char in ",.;:!?…—-":
                weight += .7
        weights.append(max(.2, weight))

    total_weight = sum(weights)
    elapsed = 0.0
    keys = [Keyframe(start, 0.0, "linear")]
    for index, weight in enumerate(weights, start=1):
        elapsed += weight
        keys.append(Keyframe(start + duration * elapsed / total_weight,
                             float(index), "linear"))
    return Track(keys)


def render_units(block) -> str:
    """Flatten TextBlock using the renderer's character-progress accounting."""
    lines = []
    for line in block.lines:
        lines.append(" ".join(word.text for word in line.words))
    return "\n".join(lines)
