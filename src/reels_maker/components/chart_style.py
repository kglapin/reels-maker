"""Shared, theme-aware chart grammar for Studio data visualizations.

These are reusable chart-system primitives (card, plot surface, grid and data
series), not per-scene decoration. The visual language borrows general, public
charting conventions used by Observable, Tremor, shadcn/ui and Datawrapper:
quiet grids, direct labels, restrained series color, hairline axes, rounded
marks and clear reading hierarchy. No web or charting-library runtime is
required by the frame renderer.
"""
from __future__ import annotations

import math

from ..design.color import ensure_contrast, mix, parse_hex
from ..layout.engine import Rect
from ..textkit.typesetter import TextStyle
from .base import panel_node


# Restrained categorical ramp tuned for dark editorial canvases: a leading
# brand-adjacent blue, then violet/amber/teal/pink/lime accents that stay
# distinguishable without relying on lightness alone. Every returned color is
# contrast-adjusted against the scene's actual plot surface.
_SERIES = (
    "#60A5FA", "#A78BFA", "#FBBF24", "#34D399", "#F472B6", "#A3E635",
)


def chart_colors(theme: dict) -> dict[str, tuple[int, int, int] | tuple]:
    """Return reusable semantic colors against the current light/dark theme."""
    base = theme["base"]
    ink = theme["ink"]
    # `theme.surface` is sometimes a foreground color (e.g. text on a button),
    # not a plot fill. Build chart surfaces from the actual scene backdrop so a
    # dark chart never gets an accidental light-gray card.
    plot = mix(base, ink, .035 if theme["light"] else .105)
    grid = mix(plot, ink, .105 if theme["light"] else .18)
    axis = ensure_contrast(ink, plot, 4.5)
    muted = ensure_contrast(theme["muted"], plot, 3.0)
    accent = ensure_contrast(theme["accent"], plot, 3.0)
    series = tuple(ensure_contrast(parse_hex(color), plot, 3.0)
                   for color in _SERIES)
    return {"plot": plot, "grid": grid, "axis": axis, "muted": muted,
            "accent": accent, "series": series,
            "border": mix(plot, ink, .16 if theme["light"] else .20),
            "hairline": mix(plot, ink, .30 if theme["light"] else .34)}


def chart_card(role: str, rect: Rect, tokens, theme: dict):
    """Quiet inset chart card with a fine edge and no decorative shadow."""
    colors = chart_colors(theme)
    return panel_node(role, rect, tokens, fill=colors["plot"], radius="lg",
                      border=colors["border"], shadow=False, qa_class="decor")


def axis_style(tokens, colors: dict, *, align="center", weight="regular"):
    # Chart chrome must read at arm's length on a phone: axis ticks sit only
    # ~10% below body copy size in most premium chart systems.
    return TextStyle(max(16, tokens.px(26)), colors["muted"], weight,
                     align=align, line_height=1.0)


def value_style(tokens, colors: dict, *, align="right", color=None):
    return TextStyle(max(18, tokens.px(32)), color or colors["axis"], "bold",
                     align=align, line_height=1.0)


def grid_width(tokens) -> float:
    return max(1.0, tokens.px(1.5))


def mark_width(tokens) -> float:
    return max(3.0, tokens.px(6))


def series_color(colors: dict, index: int = 0):
    """Categorical series color; index 0 falls back to the brand accent."""
    series = colors.get("series") or ()
    if index <= 0:
        return colors["accent"]
    return series[(index - 1) % len(series)] if series else colors["accent"]


def alpha(color, opacity: float):
    """Return an RGBA tuple with scaled alpha for fills under marks."""
    r, g, b = color[:3]
    a = color[3] if len(color) == 4 else 255
    return (r, g, b, int(round(a * max(0.0, min(1.0, opacity)))))


def smooth_points(points: list[tuple[float, float]],
                  samples_per_segment: int = 8
                  ) -> list[tuple[float, float]]:
    """Catmull-Rom spline through ``points`` sampled as a polyline.

    Produces the smooth, eased curve convention used by shadcn/Tremor line
    charts instead of visible segment joints. Endpoints are duplicated so the
    curve passes exactly through the first and last data points.
    """
    if len(points) < 3 or samples_per_segment < 1:
        return list(points)
    padded = [points[0]] + list(points) + [points[-1]]
    out: list[tuple[float, float]] = []
    for i in range(len(padded) - 3):
        p0, p1, p2, p3 = padded[i:i + 4]
        for step in range(samples_per_segment):
            t = step / samples_per_segment
            t2, t3 = t * t, t * t * t
            out.append((
                .5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t
                      + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                      + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
                .5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t
                      + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                      + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3),
            ))
    out.append(points[-1])
    return out


def area_points(line_points: list[tuple[float, float]], baseline: float
                ) -> list[tuple[float, float]]:
    """Close a series polyline down to ``baseline`` for a filled area."""
    if not line_points:
        return []
    return list(line_points) + [(line_points[-1][0], baseline),
                                (line_points[0][0], baseline)]
