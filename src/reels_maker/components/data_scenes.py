"""Compatibility facade and registry for data-driven scene builders."""
from __future__ import annotations

from .scene_support import _data_panel_scaffold
from .data_scenes_basic import (
    build_bars, build_line_chart, build_stacked_bars_100,
)
from .data_scenes_advanced import (
    build_waterfall, build_diverging_bar, build_bullet, build_heatmap,
    build_scatter, build_funnel, build_sankey,
)
from .data_scenes_morph import build_chart_morph

DATA_BUILDERS = {
    "bars": build_bars,
    "line_chart": build_line_chart,
    "stacked_bars_100": build_stacked_bars_100,
    "waterfall": build_waterfall,
    "diverging_bar": build_diverging_bar,
    "bullet": build_bullet,
    "heatmap": build_heatmap,
    "scatter": build_scatter,
    "funnel": build_funnel,
    "sankey": build_sankey,
    "chart_morph": build_chart_morph,
}

__all__ = ["DATA_BUILDERS", "build_bars", "build_line_chart",
           "build_stacked_bars_100", "build_waterfall", "build_diverging_bar",
           "build_bullet", "build_heatmap", "build_scatter", "build_funnel",
           "build_sankey", "build_chart_morph"]
