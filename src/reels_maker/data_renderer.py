"""Public facade for deterministic typed data-to-Studio scene compilation."""
from __future__ import annotations

from .data_render_support import DataRenderError, _exact_float
from .data_charts import (
    line_chart_scene, bar_chart_scene, stacked_bars_100_scene, morph_chart_scenes,
)
from .data_tables import (
    table_scene, sorted_table_scene, paginate_table_scenes, table_to_bars_scenes,
)
from .data_visualization import (
    compile_visualization_scene, credible_data_story_examples,
    add_uncertainty_band, annotate_chart_scene, validate_3d_data_justification,
)

__all__ = [
    "DataRenderError", "line_chart_scene", "table_scene", "bar_chart_scene",
    "stacked_bars_100_scene", "sorted_table_scene", "paginate_table_scenes",
    "table_to_bars_scenes", "compile_visualization_scene",
    "credible_data_story_examples", "morph_chart_scenes",
    "add_uncertainty_band", "annotate_chart_scene",
    "validate_3d_data_justification",
]
