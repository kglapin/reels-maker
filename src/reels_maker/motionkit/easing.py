"""Easing curves with explicit, bounded behaviour.

Every preset maps 0 to 0 and 1 to 1. Overshoot is only exposed through
``back``/``spring`` and is intentionally bounded to avoid rubber-band motion.
"""
from __future__ import annotations

import math

EASINGS = (
    "linear", "in-quad", "out-quad", "in-out-quad",
    "in-cubic", "out-cubic", "in-out-cubic",
    "in-quart", "out-quart", "in-out-quart",
    "in-expo", "out-expo", "in-out-expo",
    "smooth", "back", "spring", "spring-physics", "cubic-bezier",
)


def clamp01(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("Animation progress must be finite")
    return max(0.0, min(1.0, float(value)))


def linear(p: float) -> float:
    return clamp01(p)


def in_quad(p: float) -> float:
    p = clamp01(p)
    return p * p


def out_quad(p: float) -> float:
    p = clamp01(p)
    return 1 - (1 - p) ** 2


def in_out_quad(p: float) -> float:
    p = clamp01(p)
    return 2 * p * p if p < .5 else 1 - (-2 * p + 2) ** 2 / 2


def in_cubic(p: float) -> float:
    p = clamp01(p)
    return p ** 3


def out_cubic(p: float) -> float:
    p = clamp01(p)
    return 1 - (1 - p) ** 3


def in_out_cubic(p: float) -> float:
    p = clamp01(p)
    return 4 * p ** 3 if p < .5 else 1 - (-2 * p + 2) ** 3 / 2


def in_quart(p: float) -> float:
    p = clamp01(p)
    return p ** 4


def out_quart(p: float) -> float:
    p = clamp01(p)
    return 1 - (1 - p) ** 4


def in_out_quart(p: float) -> float:
    p = clamp01(p)
    return 8 * p ** 4 if p < .5 else 1 - (-2 * p + 2) ** 4 / 2


def in_expo(p: float) -> float:
    p = clamp01(p)
    return 0.0 if p == 0 else 2 ** (10 * p - 10)


def out_expo(p: float) -> float:
    p = clamp01(p)
    return 1.0 if p == 1 else 1 - 2 ** (-10 * p)


def in_out_expo(p: float) -> float:
    p = clamp01(p)
    if p in (0.0, 1.0):
        return p
    return 2 ** (20 * p - 10) / 2 if p < .5 else (2 - 2 ** (-20 * p + 10)) / 2


def smooth(p: float) -> float:
    p = clamp01(p)
    return p * p * (3 - 2 * p)


def back(p: float, overshoot: float = 1.04) -> float:
    """Small, controlled overshoot; never an infinite bounce."""
    if not 1 <= overshoot <= 1.12:
        raise ValueError("overshoot must be between 1 and 1.12")
    p = clamp01(p)
    c = 1.70158 * (1 + (overshoot - 1) * 3)
    q = p - 1
    return 1 + (c + 1) * q ** 3 + c * q ** 2


def spring(p: float, damping: float = 7.0) -> float:
    """Closed-form damped spring that settles exactly at 1."""
    if damping <= 0:
        raise ValueError("damping must be positive")
    p = clamp01(p)
    if p == 0:
        return 0.0
    if p == 1:
        return 1.0
    return 1 - math.exp(-damping * p) * math.cos(10 * p)


def spring_physics(p: float, *, omega: float = 11.0,
                   zeta: float = 0.32) -> float:
    """Analytic damped-spring response (mass-spring-damper, zero initial
    velocity), normalised so progress 0 and 1 map exactly to 0 and 1.

    ``omega`` is the natural frequency and ``zeta`` the damping ratio:
    zeta < 1 overshoots and oscillates, zeta >= 1 settles monotonically.
    Unlike :func:`spring`, the shape comes from the oscillator equation, so
    stiffness/damping changes alter both overshoot and settle time.
    """
    if not math.isfinite(omega) or omega <= 0:
        raise ValueError("omega must be positive and finite")
    if not math.isfinite(zeta) or zeta < 0:
        raise ValueError("zeta must be nonnegative and finite")
    p = clamp01(p)
    if p == 0.0:
        return 0.0
    if p == 1.0:
        return 1.0

    def raw(t: float) -> float:
        if zeta < 1.0:
            wd = omega * math.sqrt(1.0 - zeta * zeta)
            envelope = math.exp(-zeta * omega * t)
            return 1.0 - envelope * (
                math.cos(wd * t) + (zeta * omega / wd) * math.sin(wd * t))
        if zeta == 1.0:
            return 1.0 - (1.0 + omega * t) * math.exp(-omega * t)
        root = math.sqrt(zeta * zeta - 1.0)
        r1 = -omega * (zeta - root)
        r2 = -omega * (zeta + root)
        return 1.0 - (r2 * math.exp(r1 * t) - r1 * math.exp(r2 * t)) / (r2 - r1)

    settled = raw(1.0)
    if settled == 0.0 or not math.isfinite(settled):
        raise ValueError("spring parameters do not settle within progress 1")
    return raw(p) / settled


def cubic_bezier(x1: float, y1: float, x2: float, y2: float, p: float,
                 *, iterations: int = 8) -> float:
    """CSS-style cubic-bezier easing solved for x, then evaluated for y.

    Control-point x values must stay in [0, 1] (monotonic time); y values
    may leave [0, 1] within [-2, 2] for anticipation/overshoot curves.
    """
    for name, value in (("x1", x1), ("x2", x2)):
        if not 0 <= value <= 1:
            raise ValueError(f"{name} must be between 0 and 1")
    for name, value in (("y1", y1), ("y2", y2)):
        if not math.isfinite(value) or not -2 <= value <= 2:
            raise ValueError(f"{name} must be finite and between -2 and 2")
    p = clamp01(p)

    def coordinate(t: float, a: float, b: float) -> float:
        return 3 * (1 - t) ** 2 * t * a + 3 * (1 - t) * t ** 2 * b + t ** 3

    low, high = 0.0, 1.0
    for _ in range(iterations * 4):
        middle = (low + high) / 2
        if coordinate(middle, x1, x2) < p:
            low = middle
        else:
            high = middle
    return coordinate((low + high) / 2, y1, y2)


def ease(name: str, p: float, **params) -> float:
    if not isinstance(name, str):
        raise ValueError("Easing name must be a string")
    key = name.strip().lower().replace("_", "-")
    functions = {
        "linear": linear, "in-quad": in_quad, "out-quad": out_quad,
        "in-out-quad": in_out_quad, "in-cubic": in_cubic,
        "out-cubic": out_cubic, "in-out-cubic": in_out_cubic,
        "in-quart": in_quart, "out-quart": out_quart,
        "in-out-quart": in_out_quart, "in-expo": in_expo,
        "out-expo": out_expo, "in-out-expo": in_out_expo,
        "smooth": smooth, "back": back, "spring": spring,
    }
    if key not in functions and key not in ("cubic-bezier", "spring-physics"):
        raise ValueError(f"Unknown easing {name!r}; choose one of "
                         + ", ".join(EASINGS))
    if key == "cubic-bezier":
        required = {"x1", "y1", "x2", "y2"}
        if set(params) != required:
            raise ValueError(
                "cubic-bezier easing requires exactly x1, y1, x2, y2 params")
        return cubic_bezier(params["x1"], params["y1"], params["x2"],
                            params["y2"], p)
    if key == "spring-physics":
        unsupported = set(params) - {"omega", "zeta"}
        if unsupported:
            raise ValueError("Unsupported spring-physics params: "
                             + ", ".join(sorted(unsupported)))
        return spring_physics(p, **params)
    function = functions[key]
    if key in ("back", "spring"):
        return function(p, **params)
    return function(p)


def progress(t: float, onset: float, duration: float) -> float:
    """Normalized elapsed fraction for an entrance starting at ``onset``."""
    if not math.isfinite(t) or not math.isfinite(onset) or duration <= 0:
        raise ValueError("Invalid animation timing")
    return clamp01((t - onset) / duration)


def easing_extrema_progress(name: str, *, overshoot: float = 1.04,
                            damping: float = 7.0, omega: float = 11.0,
                            zeta: float = 0.32) -> tuple[float, ...]:
    """Return exact interior progress values p in (0, 1) where d(ease)/dp == 0.

    Monotonic easings return ``()``; ``back`` and ``spring`` return their
    closed-form overshoot/oscillation extrema so timeline QA samples the exact
    peak displacement frame rather than relying only on fixed quarter probes.
    """
    if not isinstance(name, str):
        raise ValueError("Easing name must be a string")
    key = name.strip().lower().replace("_", "-")
    if key not in EASINGS:
        raise ValueError(f"Unknown easing {name!r}; choose one of "
                         + ", ".join(EASINGS))
    if key == "back":
        if not 1 <= overshoot <= 1.12:
            raise ValueError("overshoot must be between 1 and 1.12")
        c = 1.70158 * (1 + (overshoot - 1) * 3)
        peak = 1.0 - (2.0 * c) / (3.0 * (c + 1.0))
        return (peak,) if 0.0 < peak < 1.0 else ()
    if key == "spring":
        if damping <= 0:
            raise ValueError("damping must be positive")
        base = math.atan(-damping / 10.0)
        extrema: list[float] = []
        k = 1
        while True:
            p = (base + k * math.pi) / 10.0
            if p >= 1.0:
                break
            if p > 0.0:
                extrema.append(p)
            k += 1
        return tuple(extrema)
    if key == "spring-physics":
        if not math.isfinite(omega) or omega <= 0:
            raise ValueError("omega must be positive and finite")
        if not math.isfinite(zeta) or zeta < 0:
            raise ValueError("zeta must be nonnegative and finite")
        if zeta >= 1.0:
            return ()
        wd = omega * math.sqrt(1.0 - zeta * zeta)
        extrema = []
        k = 1
        while (p := k * math.pi / wd) < 1.0:
            extrema.append(p)
            k += 1
        return tuple(extrema)
    return ()
