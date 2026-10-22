"""Format-independent typography scale and pixel-precise platform margins.

The brand identity does not define video dimensions. Every project may choose
portrait, landscape or square; explicit *_pixels values are literal pixels
in that project's output resolution, NEVER multiplied by a reference format.
"""
from __future__ import annotations

from .ffmpeg import RenderError


def design_scale(width: int, height: int) -> float:
    """Keep text proportions predictable when rotating a frame."""
    if min(width, height) <= 0:
        raise RenderError("Canvas dimensions must be positive")
    return min(width, height) / 1080.0


def resolve_safe_areas(width: int, height: int, safe: dict | None):
    """Return (horizontal, top, bottom), all in actual output pixels.

    By default the margins are proportional to the current canvas. Platform
    safe zones are optional project overrides, not part of the brandbook.
    """
    if safe is None:
        safe = {}
    if not isinstance(safe, dict):
        raise RenderError("branding.safe_areas must be an object")
    allowed = {"horizontal_pixels", "top_pixels", "bottom_pixels"}
    if set(safe) - allowed:
        raise RenderError("Unknown safe-area fields: " + ", ".join(sorted(set(safe)-allowed)))
    defaults = {
        "horizontal_pixels": round(width * .085),
        "top_pixels": round(height * .085),
        "bottom_pixels": round(height * .13),
    }
    results = {}
    for name in allowed:
        value = safe.get(name, defaults[name])
        if type(value) is not int or value < 0:
            raise RenderError(f"branding.safe_areas.{name} must be nonnegative integer pixels")
        results[name] = value
    margin, top, bottom = (results["horizontal_pixels"],
                           results["top_pixels"], results["bottom_pixels"])
    if (margin >= width / 3 or top >= height / 2 or
            bottom >= height / 2 or top + bottom >= height * .75):
        raise RenderError("Safe areas leave too little space for the output frame")
    return margin, top, bottom
