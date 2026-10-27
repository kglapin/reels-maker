"""Shared, theme-aware chart grammar for Studio data visualizations.

These are reusable chart-system primitives (card, plot surface, grid and data
series), not per-scene decoration. The visual language borrows general, public
charting conventions used by Observable, Tremor and Datawrapper: quiet grids,
direct labels, restrained series color and clear reading hierarchy. No web or
charting-library runtime is required by the frame renderer.
"""
from __future__ import annotations

from ..design.color import ensure_contrast, mix, parse_hex
from ..layout.engine import Rect
from ..textkit.typesetter import TextStyle
from .base import panel_node


# Purposeful categorical colors, ordered for distinguishability. The first
# series remains the brand accent; further colors avoid relying on lightness
# alone to separate values. Every returned color is contrast-adjusted against
# the scene's actual plot surface.
_SERIES = (
    "#4F8CFF", "#A78BFA", "#F59E0B", "#2DD4BF", "#F472B6", "#A3E635",
)


def chart_colors(theme: dict) -> dict[str, tuple[int, int, int]]:
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
            "border": mix(plot, ink, .16 if theme["light"] else .20)}


def chart_card(role: str, rect: Rect, tokens, theme: dict):
    """Quiet inset chart card with a fine edge and no decorative shadow."""
    colors = chart_colors(theme)
    return panel_node(role, rect, tokens, fill=colors["plot"], radius="lg",
                      border=colors["border"], shadow=False, qa_class="decor")


def axis_style(tokens, colors: dict, *, align="center", weight="regular"):
    return TextStyle(max(12, tokens.px(15)), colors["muted"], weight,
                     align=align, line_height=1.0)


def value_style(tokens, colors: dict, *, align="right", color=None):
    return TextStyle(max(13, tokens.px(18)), color or colors["axis"], "bold",
                     align=align, line_height=1.0)


def grid_width(tokens) -> float:
    return max(1.0, tokens.px(1))


def mark_width(tokens) -> float:
    return max(2.0, tokens.px(3.5))
