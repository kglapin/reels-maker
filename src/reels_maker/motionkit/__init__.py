"""Easing, keyframes, presets and narrative choreography."""
from .choreography import (
    Choreography, ElementSpec, EntranceTiming, plan_choreography, variety_report,
)
from .easing import EASINGS, clamp01, ease, progress
from .keyframes import Keyframe, Track, interpolate
from .presets import PRESETS, apply_entrance, camera_track, canonical_preset

__all__ = ["Choreography", "ElementSpec", "EntranceTiming",
           "plan_choreography", "variety_report", "EASINGS", "clamp01", "ease",
           "progress", "Keyframe", "Track", "interpolate", "PRESETS",
           "apply_entrance", "camera_track", "canonical_preset"]
