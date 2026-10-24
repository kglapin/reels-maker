"""Brand motion personality.

A :class:`MotionPersonality` controls *how* motion feels without touching
geometry: acceleration curve, overshoot tolerance, entrance-direction bias,
entrance duration scale, stagger tightness and exit restraint.

Two brands with identical layouts can feel completely different because one is
snappy and elastic while the other is slow and restrained.  The personality
is resolved from the brand's ``motion`` block in ``brand.json`` with safe
defaults, and never overrides a hard QA gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..design.tokens import MotionTokens

VALID_ACCELERATIONS = ("snappy", "balanced", "relaxed", "cinematic")
VALID_OVERSHOOT = ("none", "subtle", "expressive")
VALID_DIRECTION_BIAS = ("none", "left", "right", "up", "down")


class MotionPersonalityError(ValueError):
    """Raised when a brand motion block is invalid."""


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class MotionPersonality:
    """Declarative motion feel for a brand."""

    acceleration: str = "balanced"
    overshoot: str = "subtle"
    direction_bias: str = "none"
    entrance_scale: float = 1.0
    stagger_scale: float = 1.0
    exit_restraint: float = 1.0
    camera_intensity_scale: float = 1.0
    accent_hit_scale: float = 1.0

    def __post_init__(self) -> None:
        if self.acceleration not in VALID_ACCELERATIONS:
            raise MotionPersonalityError(
                f"acceleration must be one of {VALID_ACCELERATIONS}, got {self.acceleration!r}")
        if self.overshoot not in VALID_OVERSHOOT:
            raise MotionPersonalityError(
                f"overshoot must be one of {VALID_OVERSHOOT}, got {self.overshoot!r}")
        if self.direction_bias not in VALID_DIRECTION_BIAS:
            raise MotionPersonalityError(
                f"direction_bias must be one of {VALID_DIRECTION_BIAS}, "
                f"got {self.direction_bias!r}")
        for name, value in (
            ("entrance_scale", self.entrance_scale),
            ("stagger_scale", self.stagger_scale),
            ("exit_restraint", self.exit_restraint),
            ("camera_intensity_scale", self.camera_intensity_scale),
            ("accent_hit_scale", self.accent_hit_scale),
        ):
            if not 0.2 <= value <= 5.0:
                raise MotionPersonalityError(
                    f"{name} must be between 0.2 and 5.0, got {value}")

    # -- derived properties ------------------------------------------------ #
    @property
    def easing_preference(self) -> str:
        """The easing curve this personality prefers for entrances."""
        return {
            "snappy": "out-expo",
            "balanced": "out-cubic",
            "relaxed": "out-quart",
            "cinematic": "out-quart",
        }[self.acceleration]

    @property
    def overshoot_factor(self) -> float:
        """Multiplier on the base overshoot token (1.045)."""
        return {
            "none": 0.0,
            "subtle": 1.0,
            "expressive": 1.6,
        }[self.overshoot]

    @property
    def allows_overshoot(self) -> bool:
        return self.overshoot != "none"

    @property
    def entrance_duration_scale(self) -> float:
        """Scale on the base entrance duration."""
        return self.entrance_scale

    def scaled_stagger(self, base: float) -> float:
        return _clamp(base * self.stagger_scale, 0.0, 2.0)

    def scaled_camera_intensity(self, base: float) -> float:
        return _clamp(base * self.camera_intensity_scale, 0.0, 0.22)

    def scaled_accent_hit(self, base: float) -> float:
        return _clamp(base * self.accent_hit_scale, 0.0, 1.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "acceleration": self.acceleration,
            "overshoot": self.overshoot,
            "direction_bias": self.direction_bias,
            "entrance_scale": self.entrance_scale,
            "stagger_scale": self.stagger_scale,
            "exit_restraint": self.exit_restraint,
            "camera_intensity_scale": self.camera_intensity_scale,
            "accent_hit_scale": self.accent_hit_scale,
            "easing_preference": self.easing_preference,
            "overshoot_factor": self.overshoot_factor,
            "allows_overshoot": self.allows_overshoot,
        }


DEFAULT_PERSONALITY = MotionPersonality()


def resolve_motion_personality(
    brand_data: dict[str, Any] | None = None,
    *,
    style: str | None = None,
) -> MotionPersonality:
    """Resolve a brand's motion personality from ``brand.json``.

    Falls back to defaults when the brand block is missing or partial.  Unknown
    keys raise :class:`MotionPersonalityError` so a typo in brand config is a
    hard failure, not a silent default.
    """
    if not isinstance(brand_data, dict):
        return DEFAULT_PERSONALITY

    raw = brand_data.get("motion")
    if not isinstance(raw, dict):
        return DEFAULT_PERSONALITY

    known_keys = {
        "acceleration", "overshoot", "direction_bias",
        "entrance_scale", "stagger_scale", "exit_restraint",
        "camera_intensity_scale", "accent_hit_scale",
    }
    extra = set(raw) - known_keys
    if extra:
        raise MotionPersonalityError(
            f"Unknown motion keys: {sorted(extra)}; allowed: {sorted(known_keys)}")

    values = {k: raw.get(k, getattr(DEFAULT_PERSONALITY, k)) for k in known_keys}
    return MotionPersonality(**values)


__all__ = [
    "MotionPersonality",
    "MotionPersonalityError",
    "DEFAULT_PERSONALITY",
    "resolve_motion_personality",
]