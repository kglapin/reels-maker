"""Procedural isometric explainer engine (2.5D world, phenomena, film timeline).

Clean-room engine implementing the techniques proven by the ASTA heat-pump
defrost study: an isometric-projected illustration world with physical
phenomena layers (frost, heat glow, vapour plume, snowfall, drips, puddles),
a continuous 110 s cause-and-effect timeline and eased world-space cameras.

Everything is a pure function of ``(spec, time)`` with seeded randomness,
so frames are deterministic and safe to render in parallel workers.
"""
from __future__ import annotations

from .film import COPY_BEATS, FILM_DURATION, render_iso_frame
from .projection import resolve_font

__all__ = ["COPY_BEATS", "FILM_DURATION", "render_iso_frame", "resolve_font"]
