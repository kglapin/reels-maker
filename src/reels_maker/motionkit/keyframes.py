"""Property keyframes: position, scale, opacity, rotation, colour and data.

A track is immutable from the renderer's point of view. It is sampled at an
absolute scene-local time in seconds, which keeps rendering independent of
frame rate and makes interpolation testable without video encoding.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable

from .easing import ease


Number = float
Value = float | tuple[float, ...]


def interpolate(first: Value, second: Value, amount: float) -> Value:
    if isinstance(first, (int, float)) and isinstance(second, (int, float)):
        return first + (second - first) * amount
    if (isinstance(first, tuple) and isinstance(second, tuple)
            and len(first) == len(second)):
        return tuple(a + (b - a) * amount for a, b in zip(first, second))
    raise ValueError("Keyframe values must be numbers or equal-length tuples")


@dataclass(frozen=True)
class Keyframe:
    time: float
    value: Value
    easing: str = "out-cubic"
    params: tuple[tuple[str, float], ...] = ()

    def __post_init__(self) -> None:
        if not math.isfinite(self.time) or self.time < 0:
            raise ValueError("Keyframe time must be finite and nonnegative")
        if isinstance(self.value, bool):
            raise ValueError("Boolean keyframe values are not interpolated")
        if isinstance(self.value, (int, float)):
            if not math.isfinite(float(self.value)):
                raise ValueError("Keyframe value must be finite")
        elif not isinstance(self.value, tuple):
            raise ValueError("Keyframe value must be a number or tuple")

    def evaluated_amount(self, amount: float) -> float:
        return ease(self.easing, amount, **dict(self.params))


@dataclass
class Track:
    keys: list[Keyframe] = field(default_factory=list)
    clamp_before: bool = True
    clamp_after: bool = True

    def __post_init__(self) -> None:
        self.keys = sorted(self.keys, key=lambda key: key.time)

    @classmethod
    def from_pairs(cls, pairs: Iterable[tuple[float, Value]],
                   easing: str = "out-cubic") -> "Track":
        return cls([Keyframe(time, value, easing) for time, value in pairs])

    def add(self, time: float, value: Value, easing: str = "out-cubic") -> "Track":
        self.keys.append(Keyframe(time, value, easing))
        self.keys.sort(key=lambda key: key.time)
        return self

    @property
    def start(self) -> float:
        return self.keys[0].time

    @property
    def end(self) -> float:
        return self.keys[-1].time

    def value(self, time: float) -> Value:
        if not self.keys:
            raise ValueError("Cannot sample an empty track")
        if not math.isfinite(time):
            raise ValueError("Sample time must be finite")
        keys = self.keys
        if time <= keys[0].time:
            if not self.clamp_before:
                raise ValueError("Sample precedes first keyframe")
            return keys[0].value
        if time >= keys[-1].time:
            if not self.clamp_after:
                raise ValueError("Sample exceeds last keyframe")
            return keys[-1].value
        for left, right in zip(keys, keys[1:]):
            if left.time <= time <= right.time:
                span = right.time - left.time
                amount = 0.0 if span <= 0 else (time - left.time) / span
                return interpolate(left.value, right.value,
                                   right.evaluated_amount(amount))
        return keys[-1].value

    def merge(self, other: "Track") -> "Track":
        return Track(self.keys + other.keys)


def opacity_track(onset: float, duration: float, peak: float = 1.0,
                  easing: str = "out-cubic") -> Track:
    if duration <= 0:
        raise ValueError("Entrance duration must be positive")
    return Track([Keyframe(max(0.0, onset), 0.0, easing),
                  Keyframe(onset + duration, peak, easing)])


def offset_track(onset: float, duration: float, distance: float,
                 axis: str = "y", easing: str = "out-cubic") -> Track:
    if axis not in ("x", "y"):
        raise ValueError("Offset axis must be x or y")
    start = (distance, 0.0) if axis == "x" else (0.0, distance)
    return Track([Keyframe(max(0.0, onset), start, easing),
                  Keyframe(onset + duration, (0.0, 0.0), easing)])


def scale_track(onset: float, duration: float, start: float = .88,
                end: float = 1.0, easing: str = "back") -> Track:
    if start <= 0 or end <= 0:
        raise ValueError("Scale must be positive")
    return Track([Keyframe(max(0.0, onset), start, easing),
                  Keyframe(onset + duration, end, easing)])


def value_track(onset: float, duration: float, start: float,
                end: float, easing: str = "out-cubic") -> Track:
    return Track([Keyframe(max(0.0, onset), start, easing),
                  Keyframe(onset + duration, end, easing)])


def sample_tracks(tracks: dict[str, Track], time: float,
                  base: dict[str, Any] | None = None) -> dict[str, Any]:
    resolved = dict(base or {})
    for name, track in tracks.items():
        resolved[name] = track.value(time)
    return resolved
