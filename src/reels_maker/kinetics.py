"""Deterministic animation curves extracted from reels11.py techniques.

Frame-indexed primitives for future graphical counters and kinetic overlays.
Pure functions: no Cairo, file I/O, fonts, frame buffers or global renderer state.
"""
from __future__ import annotations

import math


def clamp01(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("Animation progress must be finite")
    return max(0.0, min(1.0, float(value)))


def ease_out_cubic(value: float) -> float:
    """Natural fast-entry motion (reels11.py eo)."""
    p = clamp01(value)
    return 1 - (1 - p) ** 3


def settle_back(value: float, overshoot: float = 1.10) -> float:
    """A single constrained accent settle, never an infinite bounce."""
    p = clamp01(value)
    if not 1 <= overshoot <= 1.15:
        raise ValueError("overshoot must be between 1 and 1.15")
    s = 1.70158 * (1 + (overshoot - 1) * 2)
    q = p - 1
    return 1 + (s + 1) * q ** 3 + s * q ** 2


def progress(frame: int, onset: int, duration: int) -> float:
    if duration < 1 or onset < 0 or frame < 0:
        raise ValueError("Invalid animation frame timing")
    return clamp01((frame - onset) / duration)


def counter_value(target: int, frame: int, onset: int,
                  duration: int, start: int = 0) -> int:
    """Count toward a finite monetary / percentage value without overshoot."""
    if type(target) is not int or type(start) is not int:
        raise ValueError("Counter endpoints must be integers")
    p = ease_out_cubic(progress(frame, onset, duration))
    return round(start + (target - start) * p)


def format_pln(amount: int) -> str:
    if type(amount) is not int:
        raise ValueError("Amount must be an integer")
    return f"{amount:,}".replace(",", " ") + " zł"


def animated_crop(start: tuple[float, float, float],
                  end: tuple[float, float, float], frame: int,
                  onset: int, duration: int) -> tuple[float, float, float]:
    """Interpolate (zoom, x, y) for deliberate photo-pan keyframes."""
    if len(start) != 3 or len(end) != 3:
        raise ValueError("Crop keyframes require zoom, x, y")
    if any(not math.isfinite(v) for v in (*start, *end)):
        raise ValueError("Nonfinite crop keyframe")
    if start[0] <= 0 or end[0] <= 0:
        raise ValueError("Crop zoom must be positive")
    if any(not 0 <= v <= 1 for v in (*start[1:], *end[1:])):
        raise ValueError("Crop focal coordinates must be normalized")
    t = ease_out_cubic(progress(frame, onset, duration))
    return tuple(a + (b-a)*t for a,b in zip(start,end))
