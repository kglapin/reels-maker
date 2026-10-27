"""Property keyframes: position, scale, opacity, rotation, colour and data.

A track is immutable from the renderer's point of view. It is sampled at an
absolute scene-local time in seconds, which keeps rendering independent of
frame rate and makes interpolation testable without video encoding.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable

from .easing import EASINGS, ease


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
        if (isinstance(self.time, bool) or not isinstance(self.time, (int, float))
                or not math.isfinite(float(self.time)) or self.time < 0):
            raise ValueError("Keyframe time must be finite and nonnegative")
        if isinstance(self.value, bool):
            raise ValueError("Boolean keyframe values are not interpolated")
        if isinstance(self.value, (int, float)):
            if not math.isfinite(float(self.value)):
                raise ValueError("Keyframe value must be finite")
        elif isinstance(self.value, tuple):
            if not self.value:
                raise ValueError("Keyframe tuple values cannot be empty")
            if any(isinstance(value, bool)
                   or not isinstance(value, (int, float))
                   or not math.isfinite(float(value)) for value in self.value):
                raise ValueError("Keyframe tuple values must be finite numbers")
        else:
            raise ValueError("Keyframe value must be a number or tuple")
        if not isinstance(self.easing, str) or not self.easing.strip():
            raise ValueError("Keyframe easing must be a non-empty string")
        if not isinstance(self.params, (tuple, list)):
            raise ValueError("Keyframe easing params must be key/value pairs")
        normalized = []
        for item in self.params:
            if (not isinstance(item, (tuple, list)) or len(item) != 2
                    or not isinstance(item[0], str) or not item[0]):
                raise ValueError("Keyframe easing params must be key/value pairs")
            value = item[1]
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))):
                raise ValueError("Keyframe easing params must be finite numbers")
            normalized.append((item[0], float(value)))
        names = [name for name, _ in normalized]
        if len(names) != len(set(names)):
            raise ValueError("Keyframe easing params cannot repeat a name")
        object.__setattr__(self, "params", tuple(normalized))
        easing_name = self.easing.strip().lower().replace("_", "-")
        if easing_name not in EASINGS:
            raise ValueError(f"Unknown easing {self.easing!r}")
        allowed_params = ({"back": {"overshoot"},
                           "spring": {"damping"}}.get(easing_name, set()))
        unsupported = set(names) - allowed_params
        if unsupported:
            raise ValueError(
                f"Unsupported {self.easing!r} easing params: "
                + ", ".join(sorted(unsupported)))
        # Validate the curve and parameter names at construction, so a bad
        # easing in a late keyframe fails before a potentially long render.
        ease(self.easing, .5, **dict(self.params))

    def evaluated_amount(self, amount: float) -> float:
        return ease(self.easing, amount, **dict(self.params))


@dataclass
class Track:
    keys: list[Keyframe] = field(default_factory=list)
    clamp_before: bool = True
    clamp_after: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.keys, (tuple, list)):
            raise ValueError("Track keys must be a sequence of Keyframes")
        if any(not isinstance(key, Keyframe) for key in self.keys):
            raise ValueError("Track keys must contain only Keyframes")
        self.keys = sorted(self.keys, key=lambda key: key.time)
        shape = ("scalar" if not isinstance(self.keys[0].value, tuple)
                 else len(self.keys[0].value)) if self.keys else None
        for key in self.keys:
            key_shape = ("scalar" if not isinstance(key.value, tuple)
                         else len(key.value))
            if key_shape != shape:
                raise ValueError("Track keyframe values must have matching shapes")
        for left, right in zip(self.keys, self.keys[1:]):
            if left.time == right.time and left.value != right.value:
                raise ValueError(
                    "Track cannot have different values at the same keyframe time")

    @classmethod
    def from_pairs(cls, pairs: Iterable[tuple[float, Value]],
                   easing: str = "out-cubic") -> "Track":
        return cls([Keyframe(time, value, easing) for time, value in pairs])

    def add(self, time: float, value: Value, easing: str = "out-cubic") -> "Track":
        updated = Track([*self.keys, Keyframe(time, value, easing)],
                        clamp_before=self.clamp_before,
                        clamp_after=self.clamp_after)
        self.keys = updated.keys
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
