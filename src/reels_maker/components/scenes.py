"""Scene compositions built from measured content, not fixed coordinates.

Legacy kinetic scene ``type`` values remain valid. New manifests can opt into
any composition directly and provide richer component data. A scene is built
once into a retained graph; the renderer and QA then sample that same graph at
different timestamps, so what is checked is exactly what is shown.
"""
from __future__ import annotations

from .base import BuiltScene, SceneContext
from .scene_support import (
    _background, _card_fill, _data_panel_scaffold, _decor, _external_icon,
    _extra_icons, _finish, _fmt, _headline, _icon_collisions, _is_light,
    _measure, _panel_with_text, _runs, _spec, _subtitle, _text_elements,
    _theme, _validate_icon_spacing, tokens_line,
)
from .metric_scenes import (
    _animate_battery_cells, _breakdown_row, _comparison_card,
    _counter_onset, _find_node, _number_in, _progress_child,
    build_amount, build_breakdown, build_comparison, build_donut,
    build_europe, build_heat, build_stats,
)
from .editorial_scenes import (
    _calendar_card, _timeline_graphic, build_announcement, build_checklist,
    build_cta, build_deadline, build_energy, build_quote, build_spotlight,
    build_statement, build_urgency,
)
from .table_scenes import build_table
from .media_scenes import build_polaroid_burst, build_product_3d
from .custom_scenes import _build_full_bleed, _build_split, _build_stack


TYPE_COMPOSITION = {
    "amount": "hero-number",
    "breakdown": "breakdown",
    "announcement": "calendar",
    "donut": "data-panel",
    "comparison": "comparison",
    "heat": "hero-number",
    "europe": "hero-number",
    "deadline": "timeline",
    "urgency": "stack-center",
    "cta": "cta-panel",
    "spotlight": "spotlight",
    "statement": "statement",
    "checklist": "checklist",
    "stats": "stat-grid",
    "bars": "data-panel",
    "line_chart": "data-panel",
    "stacked_bars_100": "data-panel",
    "waterfall": "data-panel",
    "diverging_bar": "data-panel",
    "bullet": "data-panel",
    "heatmap": "data-panel",
    "scatter": "data-panel",
    "funnel": "data-panel",
    "sankey": "data-panel",
    "chart_morph": "data-panel",
    "product_3d": "data-panel",
    "table": "table",
    "energy": "energy-flow",
    "quote": "quote",
    "product": "spotlight",
    "photo_carousel": "photo-carousel",
    "photo_marquee": "photo-marquee",
}

SIZE_FOR_COMPOSITION = {
    "hero-number": "hero",
    "full-bleed-type": "display",
    "statement": "display",
    "spotlight": "hero",
}


def _scene_type(scene: dict) -> str:
    kind = scene.get("type") or scene.get("kind")
    if kind:
        return str(kind)
    composition = scene.get("composition")
    if not composition:
        return "statement"
    composition = str(composition)
    # A manifest may name a component directly (`amount`, `bars`) or a layout
    # recipe (`hero-number`, `data-panel`). Direct component names are
    # unambiguous; recipes map back only when exactly one component owns them.
    if composition in BUILDERS:
        return composition
    if composition == "line-chart":
        return "line_chart"
    if composition in ("stack-center", "full-bleed-type", "split-editorial"):
        return "custom"
    if composition == "hero-number":
        return "heat" if scene.get("component") == "heat" else "amount"
    if composition == "data-panel":
        if scene.get("bars") is not None or scene.get("data") is not None:
            return "bars"
        return "donut"
    matches = [name for name, value in TYPE_COMPOSITION.items()
               if value == composition]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(
            f"Composition {composition!r} is shared by {', '.join(matches)}; "
            "set an explicit scene type to choose the component.")
    return "statement"


def _lazy_data_builder(name: str):
    """Load chart builders only when a data scene is selected.

    The module-level aliases below preserve the former import paths while
    keeping the data-scene implementation in its own module.
    """
    def build(ctx: SceneContext, scene: dict) -> BuiltScene:
        from .data_scenes import DATA_BUILDERS

        return DATA_BUILDERS[name](ctx, scene)

    build.__name__ = f"build_{name}"
    return build


build_bars = _lazy_data_builder("bars")
build_line_chart = _lazy_data_builder("line_chart")
build_stacked_bars_100 = _lazy_data_builder("stacked_bars_100")
build_waterfall = _lazy_data_builder("waterfall")
build_diverging_bar = _lazy_data_builder("diverging_bar")
build_bullet = _lazy_data_builder("bullet")
build_heatmap = _lazy_data_builder("heatmap")
build_scatter = _lazy_data_builder("scatter")
build_funnel = _lazy_data_builder("funnel")
build_sankey = _lazy_data_builder("sankey")
build_chart_morph = _lazy_data_builder("chart_morph")


BUILDERS = {
    "amount": build_amount,
    "breakdown": build_breakdown,
    "announcement": build_announcement,
    "donut": build_donut,
    "comparison": build_comparison,
    "heat": build_heat,
    "europe": build_europe,
    "deadline": build_deadline,
    "urgency": build_urgency,
    "cta": build_cta,
    "spotlight": build_spotlight,
    "statement": build_statement,
    "checklist": build_checklist,
    "stats": build_stats,
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
    "product_3d": build_product_3d,
    "polaroid_burst": build_polaroid_burst,
    "table": build_table,
    "energy": build_energy,
    "quote": build_quote,
}


def build_scene(ctx: SceneContext, scene: dict) -> BuiltScene:
    kind = _scene_type(scene)
    if kind == "photo_carousel":
        from .photo_carousel import build_photo_carousel
        built = build_photo_carousel(ctx, scene)
        built.meta.setdefault("type", kind)
        return built
    if kind == "photo_marquee":
        from .photo_marquee import build_photo_marquee
        built = build_photo_marquee(ctx, scene)
        built.meta.setdefault("type", kind)
        return built
    if kind in BUILDERS:
        built = BUILDERS[kind](ctx, scene)
        built.meta.setdefault("type", kind)
        return built
    composition = scene.get("composition", "stack-center")
    if composition in ("stack-center", "full-bleed-type", "split-editorial",
                       "spotlight", "statement", "quote"):
        # Generic copy-led scene with an explicit composition.
        original = scene
        scene = {**scene, "composition": composition}
        if composition == "spotlight":
            built = build_spotlight(ctx, scene)
        elif composition == "full-bleed-type":
            built = _build_full_bleed(ctx, scene)
        elif composition == "split-editorial":
            built = _build_split(ctx, scene)
        elif composition in ("statement", "quote"):
            built = build_statement(ctx, scene)
        else:
            built = _build_stack(ctx, scene)
        built.meta.setdefault("type", "custom")
        return built
    raise ValueError(f"Unknown scene type/composition: {kind!r} / {composition!r}")
