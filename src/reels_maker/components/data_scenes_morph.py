"""Morph scene builders for Studio data visualizations."""
from __future__ import annotations

import math

from ..core.scene_graph import Node
from ..design.color import mix
from ..layout.engine import Rect
from ..motionkit.keyframes import Keyframe, Track
from ..textkit.typesetter import TextStyle
from .base import (
    BuiltScene, SceneContext, animate_progress, format_value, number_node,
    resolve_text_style, safe_number, text_node,
)
from .scene_support import (
    _background, _data_panel_scaffold, _decor, _finish, _headline,
    _measure, _spec, _subtitle, _theme,
)

def build_chart_morph(ctx: SceneContext, scene: dict) -> BuiltScene:
    """Render an animated object-level morph between table/bar states in MP4 (DM-104)."""
    theme, layout, elements = _data_panel_scaffold(ctx, scene, "TRANSFORMACJA DANYCH")
    items = scene.get("items")
    if not isinstance(items, list) or not 2 <= len(items) <= 8:
        raise ValueError("chart_morph requires 2..8 items with shared IDs")
    parsed = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict) or not str(item.get("id", "")).strip():
            raise ValueError(f"chart_morph item {idx} requires a non-empty id")
        parsed.append({
            "id": str(item["id"]).strip(),
            "label": str(item.get("label") or item["id"]).strip(),
            "from_index": int(item.get("from_index", idx)),
            "to_index": int(item.get("to_index", idx)),
            "from_value": safe_number(item.get("from_value", item.get("value", 0))),
            "to_value": safe_number(item.get("to_value", item.get("value", 0))),
            "suffix": str(item.get("suffix", "")),
        })
    max_val = max(
        max(abs(p["from_value"]), abs(p["to_value"])) for p in parsed
    ) or 1.0
    chart = layout.region("chart")
    row_gap = ctx.tokens.space("sm")
    row_h = (chart.h - row_gap * (len(parsed) - 1)) / len(parsed)
    slot_step = row_h + row_gap
    trans_dur = float(scene.get("transition_duration", min(1.2, ctx.duration * .45)))
    t_start = min(0.35, ctx.duration * .18)
    t_end = min(max(t_start + 0.25, ctx.duration - 0.55), t_start + trans_dur)
    from_is_table = scene.get("from_type") == "table"

    for item in parsed:
        to_idx = item["to_index"]
        from_idx = item["from_index"]
        y = chart.y + to_idx * slot_step
        dy_start = (from_idx - to_idx) * slot_step
        w_from = (
            chart.w * .94 if from_is_table
            else max(ctx.tokens.px(18), chart.w * (item["from_value"] / max_val))
        )
        w_to = max(ctx.tokens.px(18), chart.w * (item["to_value"] / max_val))

        label_style = TextStyle(max(12, ctx.tokens.px(20)), theme["ink"], "bold")
        lbl = text_node(
            f"morph-label-{item['id']}", item["label"], label_style,
            Rect(chart.x, y, chart.w * .58, row_h * .42),
            ctx.fonts, align="left", valign="center", fit=True,
        )
        bar_node = Node(
            kind="round", role=f"morph-bar-{item['id']}",
            props={"x": chart.x, "y": y + row_h * .48,
                   "w": w_to, "h": max(ctx.tokens.px(18), row_h * .38),
                   "r": ctx.tokens.px(8), "fill": theme["accent"]},
            qa_class="decor",
        )
        bar_node.track("prop.w", Track([
            Keyframe(0.0, w_from, "in-out-cubic"),
            Keyframe(t_start, w_from, "in-out-cubic"),
            Keyframe(t_end, w_to, "in-out-cubic"),
        ]))
        val_node = number_node(
            f"morph-val-{item['id']}", item["to_value"],
            Rect(chart.x + chart.w * .60, y, chart.w * .40, row_h * .42),
            ctx.tokens,
            fmt={"suffix": item["suffix"], "thousands": " ", "decimals": 0},
            size_role="body", color=theme["accent"], align="right",
        )
        val_node.track("prop.value", Track([
            Keyframe(0.0, item["from_value"], "in-out-cubic"),
            Keyframe(t_start, item["from_value"], "in-out-cubic"),
            Keyframe(t_end, item["to_value"], "in-out-cubic"),
        ]))
        row_group = Node(
            kind="group", role=f"morph-row-{to_idx}",
            children=[c for c in (lbl, bar_node, val_node) if c],
            qa_class="control",
            meta={"stable_row_id": item["id"]},
        )
        if abs(dy_start) > 1e-3:
            row_group.track("dy", Track([
                Keyframe(0.0, dy_start, "in-out-cubic"),
                Keyframe(t_start, dy_start, "in-out-cubic"),
                Keyframe(t_end, 0.0, "in-out-cubic"),
            ]))
        elements[f"morph-row-{to_idx}"] = row_group

    specs = [_spec("headline", 7)] + [
        _spec(f"morph-row-{i}", 6 - i * .3, "control", order=i)
        for i in range(len(parsed))
    ]
    if "body" in elements:
        specs.append(_spec("body", 3))
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "chart_morph",
                         "row_ids": [p["id"] for p in parsed],
                         "data_provenance": scene.get("data_provenance")})
