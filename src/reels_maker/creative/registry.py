"""Live capability registry exposed to LLM clients.

Only capabilities backed by the current renderer are advertised as available.
Planned techniques are never passed off as renderable effects.
"""
from __future__ import annotations

from ..design.styles import STYLE_SYSTEMS
from ..motionkit.presets import PRESETS
from ..renderers.transition_engine import EFFECTS
from ..motionkit.editorial_rotation import FAMILIES as ROTATION_FAMILIES

SCHEMA_VERSION = 1

# Actual renderer implementations, not aspirational prose names.
CAMERA_LAYOUTS = ("photo-above", "photo-left", "offset", "diagonal")
CAMERA_TEXT_MOTIONS = ("fade", "slide-up", "mask-rise", "scale-focus")
STUDIO_COMPOSITIONS = (
    "statement", "stack-center", "split-editorial", "full-bleed-type",
    "spotlight", "quote", "amount", "stats", "bars", "checklist", "cta",
)
CAMERA_SHOT_LIMIT = 6

def capabilities() -> dict:
    """Small versioned machine-readable public contract for LLM authors."""
    return {
        "schema_version": SCHEMA_VERSION,
        "creative_spec_version": 1,
        "status": "ok",
        "modes": {
            "studio": {
                "status": "implemented",
                "compositions": list(STUDIO_COMPOSITIONS),
                "typography_presets": sorted(PRESETS),
                "transitions": sorted(EFFECTS),
                "editorial_rotations": list(ROTATION_FAMILIES),
                "photo_required": False,
            },
            "camera_canvas": {
                "status": "implemented",
                "layouts": list(CAMERA_LAYOUTS),
                "typography_motions": list(CAMERA_TEXT_MOTIONS),
                "camera_fields": [
                    "x", "y", "angle", "zoom", "move_duration",
                    "reveal_delay", "reveal_duration",
                ],
                "photo_required": True,
                "max_shots": CAMERA_SHOT_LIMIT,
                "world_limit_pixels": 32_000_000,
            },
        },
        "styles": sorted(STYLE_SYSTEMS),
        "editing": {
            "status": "implemented",
            "format": "JSON Patch subset: add/replace/remove",
            "scope": "Creative Spec (not arbitrary source files)",
        },
        "limitations": [
            "No LLM network inference inside the backend; LLM supplies Creative Spec JSON.",
            "Only explicit local image paths can be compiled; images are not fabricated.",
            "Automatic aesthetic scoring and semantic photo sourcing are not implemented.",
            "Camera-canvas geometry uses authored or deterministic waypoints; "
            "subject detection, complex 3D camera moves and motion blur are not implemented.",
            "Audio-to-beat automation and per-letter type morphs remain separate capabilities.",
        ],
    }
