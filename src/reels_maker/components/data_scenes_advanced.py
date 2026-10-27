"""Advanced scene builders for Studio data visualizations."""
from __future__ import annotations

import math

from ..core.scene_graph import Node
from ..design.color import ensure_contrast, mix
from ..layout.engine import Rect
from ..motionkit.keyframes import Keyframe, Track
from ..textkit.typesetter import TextStyle
from .chart_style import (
    axis_style, chart_card, chart_colors, grid_width,
)
from .base import (
    BuiltScene, SceneContext, animate_progress, format_value, number_node,
    resolve_text_style, safe_number, text_node,
)
from .scene_support import (
    _background, _data_panel_scaffold, _decor, _finish, _headline,
    _measure, _spec, _subtitle, _theme,
)

def build_waterfall(ctx: SceneContext, scene: dict) -> BuiltScene:
    """Render an opening-to-closing bridge waterfall chart with conservation check (DM-102)."""
    theme, layout, elements = _data_panel_scaffold(ctx, scene, "MOST FINANSOWY")
    steps = scene.get("steps")
    if not isinstance(steps, list) or not 3 <= len(steps) <= 8:
        raise ValueError("waterfall requires 3..8 explicit steps (opening, deltas..., closing)")
    parsed = []
    running = 0.0
    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError(f"waterfall step {idx} must be an object")
        kind = str(step.get("kind", "delta" if 0 < idx < len(steps) - 1 else "total"))
        if kind not in ("opening", "delta", "total"):
            raise ValueError("waterfall step kind must be opening, delta or total")
        label = str(step.get("label", "")).strip()
        if not label:
            raise ValueError(f"waterfall step {idx} requires a non-empty label")
        val = safe_number(step.get("value"))
        if idx == 0:
            start, end = 0.0, val
            running = val
        elif kind == "total" or idx == len(steps) - 1:
            if abs(running - val) > 1e-4:
                raise ValueError(
                    f"waterfall closing total {val} does not equal running sum {running}"
                )
            start, end = 0.0, val
        else:
            start, end = running, running + val
            running = end
        parsed.append({"id": str(step.get("id") or label), "label": label,
                       "value": val, "kind": kind, "start": start, "end": end})
    all_vals = [0.0] + [p["start"] for p in parsed] + [p["end"] for p in parsed]
    low, high = min(all_vals), max(all_vals)
    span = max(1e-6, high - low)
    chart = layout.region("chart")
    colors = chart_colors(theme)
    plot = Rect(chart.x + chart.w * .09, chart.y + chart.h * .10,
                chart.w * .82, chart.h * .68)
    slot_w = plot.w / len(parsed)
    bar_w = slot_w * .62
    children: list[Node] = [chart_card("waterfall-chart-surface", chart,
                                       ctx.tokens, theme)]
    lbl_style = axis_style(ctx.tokens, colors, align="center", weight="bold")
    for idx, item in enumerate(parsed):
        x = plot.x + idx * slot_w + (slot_w - bar_w) / 2
        y_top = plot.bottom - (max(item["start"], item["end"]) - low) / span * plot.h
        y_bot = plot.bottom - (min(item["start"], item["end"]) - low) / span * plot.h
        h = max(ctx.tokens.px(4), y_bot - y_top)
        fill = (colors["axis"] if item["kind"] in ("opening", "total")
                else (colors["series"][3] if item["value"] >= 0
                      else ensure_contrast(ctx.tokens.palette.danger,
                                           colors["plot"], 3.0)))
        children.append(Node(
            kind="round", role=f"waterfall-bar-{idx}",
            props={"x": x, "y": y_top, "w": bar_w, "h": h,
                   "r": ctx.tokens.px(4), "fill": fill},
            qa_class="decor", meta={"stable_row_id": item["id"], "value": item["value"]},
        ))
        lbl = text_node(f"waterfall-label-{idx}", item["label"], lbl_style,
                        Rect(plot.x + idx * slot_w, plot.bottom + ctx.tokens.px(6),
                             slot_w, max(14.0, ctx.tokens.px(28))),
                        ctx.fonts, align="center", valign="top", fit=True)
        if lbl:
            children.append(lbl)
    elements["chart"] = Node(kind="group", role="chart", children=children, qa_class="control")
    specs = [_spec("headline", 7), _spec("chart", 9, "control"), _spec("body", 3)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "waterfall", "data": parsed,
                         "row_ids": [p["id"] for p in parsed]})

def build_diverging_bar(ctx: SceneContext, scene: dict) -> BuiltScene:
    """Render horizontal diverging bars around an explicit baseline (DM-102)."""
    theme, layout, elements = _data_panel_scaffold(ctx, scene, "ODCHYLENIE OD CELU")
    baseline = safe_number(scene.get("baseline", 0.0))
    items = scene.get("items") or scene.get("bars")
    if not isinstance(items, list) or not 2 <= len(items) <= 8:
        raise ValueError("diverging_bar requires 2..8 items")
    parsed = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict) or not str(item.get("label", "")).strip():
            raise ValueError(f"diverging_bar item {idx} requires a label")
        val = safe_number(item.get("value"))
        delta = val - baseline
        parsed.append({"id": str(item.get("id") or item["label"]),
                       "label": str(item["label"]).strip(),
                       "value": val, "delta": delta})
    max_abs = max((abs(p["delta"]) for p in parsed), default=1.0) or 1.0
    chart = layout.region("chart")
    plot = Rect(chart.x + chart.w * .24, chart.y + chart.h * .08,
                chart.w * .70, chart.h * .80)
    mid_x = plot.center_x
    row_h = plot.h / len(parsed)
    children: list[Node] = [
        Node(kind="line", role="diverging-baseline",
             props={"x1": mid_x, "y1": plot.y, "x2": mid_x, "y2": plot.bottom,
                    "width": 2, "color": theme["ink"]}, qa_class="decor")
    ]
    lbl_style = TextStyle(max(12, ctx.tokens.px(16)), theme["ink"], "bold", align="right")
    for idx, item in enumerate(parsed):
        y = plot.y + idx * row_h
        w_bar = (abs(item["delta"]) / max_abs) * (plot.w * .46)
        x_bar = mid_x if item["delta"] >= 0 else mid_x - w_bar
        fill = theme["accent"] if item["delta"] >= 0 else ctx.tokens.palette.danger
        children.append(Node(
            kind="round", role=f"diverging-bar-{idx}",
            props={"x": x_bar, "y": y + row_h * .22, "w": max(2.0, w_bar),
                   "h": row_h * .56, "r": ctx.tokens.px(5), "fill": fill},
            qa_class="decor", meta={"stable_row_id": item["id"], "delta": item["delta"]},
        ))
        lbl = text_node(f"diverging-label-{idx}", item["label"], lbl_style,
                        Rect(chart.x, y, plot.x - chart.x - ctx.tokens.px(8), row_h),
                        ctx.fonts, align="right", valign="center", fit=True)
        if lbl:
            children.append(lbl)
    elements["chart"] = Node(kind="group", role="chart", children=children, qa_class="control")
    specs = [_spec("headline", 7), _spec("chart", 9, "control"), _spec("body", 3)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "diverging_bar", "baseline": baseline, "data": parsed})

def build_bullet(ctx: SceneContext, scene: dict) -> BuiltScene:
    """Render bullet charts comparing actual measures against explicit targets (DM-102)."""
    theme, layout, elements = _data_panel_scaffold(ctx, scene, "REALIZACJA CELU")
    metrics = scene.get("metrics") or scene.get("items")
    if not isinstance(metrics, list) or not 1 <= len(metrics) <= 5:
        raise ValueError("bullet requires 1..5 metrics with value and target")
    parsed = []
    for idx, item in enumerate(metrics):
        if not isinstance(item, dict) or not str(item.get("label", "")).strip():
            raise ValueError(f"bullet metric {idx} requires a label")
        val = safe_number(item.get("value"))
        target = safe_number(item.get("target"))
        max_v = safe_number(item.get("max", max(val, target) * 1.2 or 1.0))
        if val < 0 or target < 0 or max_v <= 0:
            raise ValueError("bullet values and targets must be non-negative with positive max")
        parsed.append({"id": str(item.get("id") or item["label"]),
                       "label": str(item["label"]).strip(),
                       "value": val, "target": target, "max": max_v})
    chart = layout.region("chart")
    plot = Rect(chart.x + chart.w * .24, chart.y + chart.h * .12,
                chart.w * .70, chart.h * .76)
    row_h = plot.h / len(parsed)
    children: list[Node] = []
    lbl_style = TextStyle(max(12, ctx.tokens.px(16)), theme["ink"], "bold", align="right")
    for idx, item in enumerate(parsed):
        y = plot.y + idx * row_h
        track_h = min(ctx.tokens.px(32), row_h * .55)
        ty = y + (row_h - track_h) / 2
        children.append(Node(
            kind="round", role=f"bullet-range-{idx}",
            props={"x": plot.x, "y": ty, "w": plot.w, "h": track_h,
                   "r": ctx.tokens.px(6), "fill": mix(theme["base"], theme["ink"], .15)},
            qa_class="decor",
        ))
        val_w = min(plot.w, plot.w * (item["value"] / item["max"]))
        children.append(Node(
            kind="round", role=f"bullet-actual-{idx}",
            props={"x": plot.x, "y": ty + track_h * .22, "w": max(2.0, val_w),
                   "h": track_h * .56, "r": ctx.tokens.px(4), "fill": theme["accent"]},
            qa_class="decor", meta={"stable_row_id": item["id"]},
        ))
        tx = plot.x + min(plot.w, plot.w * (item["target"] / item["max"]))
        children.append(Node(
            kind="line", role=f"bullet-target-{idx}",
            props={"x1": tx, "y1": ty - ctx.tokens.px(4),
                   "x2": tx, "y2": ty + track_h + ctx.tokens.px(4),
                   "width": max(2, ctx.tokens.px(4)), "color": theme["ink"]},
            qa_class="decor",
        ))
        lbl = text_node(f"bullet-label-{idx}", item["label"], lbl_style,
                        Rect(chart.x, y, plot.x - chart.x - ctx.tokens.px(8), row_h),
                        ctx.fonts, align="right", valign="center", fit=True)
        if lbl:
            children.append(lbl)
    elements["chart"] = Node(kind="group", role="chart", children=children, qa_class="control")
    specs = [_spec("headline", 7), _spec("chart", 9, "control"), _spec("body", 3)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "bullet", "data": parsed})

def build_heatmap(ctx: SceneContext, scene: dict) -> BuiltScene:
    """Render a 2D matrix heatmap with row/column headers and exact cell values (DM-102)."""
    theme, layout, elements = _data_panel_scaffold(ctx, scene, "MAPA CIEPLNA")
    rows = scene.get("row_labels")
    cols = scene.get("col_labels")
    matrix = scene.get("values")
    if (not isinstance(rows, list) or not isinstance(cols, list)
            or not isinstance(matrix, list) or not 2 <= len(rows) <= 6
            or not 2 <= len(cols) <= 6 or len(matrix) != len(rows)):
        raise ValueError("heatmap requires 2..6 row_labels, 2..6 col_labels and matching values matrix")
    flat = []
    for r_idx, row in enumerate(matrix):
        if not isinstance(row, list) or len(row) != len(cols):
            raise ValueError("heatmap matrix row length must match col_labels")
        for c_idx, val in enumerate(row):
            flat.append(safe_number(val))
    low, high = min(flat), max(flat)
    span = max(1e-6, high - low)
    chart = layout.region("chart")
    colors = chart_colors(theme)
    plot = Rect(chart.x + chart.w * .20, chart.y + chart.h * .14,
                chart.w * .74, chart.h * .66)
    cw, ch = plot.w / len(cols), plot.h / len(rows)
    children: list[Node] = [chart_card("heatmap-chart-surface", chart,
                                       ctx.tokens, theme)]
    hdr_style = axis_style(ctx.tokens, colors, align="center", weight="bold")
    for c_idx, col_lbl in enumerate(cols):
        node = text_node(f"heatmap-col-{c_idx}", str(col_lbl), hdr_style,
                         Rect(plot.x + c_idx * cw, chart.y, cw, plot.y - chart.y),
                         ctx.fonts, align="center", valign="center", fit=True)
        if node:
            children.append(node)
    for r_idx, row_lbl in enumerate(rows):
        rnode = text_node(f"heatmap-row-{r_idx}", str(row_lbl), hdr_style,
                          Rect(chart.x, plot.y + r_idx * ch,
                               plot.x - chart.x - ctx.tokens.px(6), ch),
                          ctx.fonts, align="right", valign="center", fit=True)
        if rnode:
            children.append(rnode)
        for c_idx, raw_val in enumerate(matrix[r_idx]):
            val = float(raw_val)
            t = (val - low) / span
            fill = mix(colors["plot"], colors["series"][0], .18 + .76 * t)
            cx = plot.x + c_idx * cw + ctx.tokens.px(2)
            cy = plot.y + r_idx * ch + ctx.tokens.px(2)
            children.append(Node(
                kind="round", role=f"heatmap-cell-{r_idx}-{c_idx}",
                props={"x": cx, "y": cy, "w": cw - ctx.tokens.px(4),
                       "h": ch - ctx.tokens.px(5), "r": ctx.tokens.px(6), "fill": fill},
                qa_class="decor",
            ))
            value_text = text_node(
                f"heatmap-value-{r_idx}-{c_idx}",
                format_value(val, {"decimals": 0, "thousands": " "}),
                TextStyle(max(12, ctx.tokens.px(15)),
                          ensure_contrast(theme["ink"], fill, 4.5),
                          "bold", align="center", line_height=1.0),
                Rect(cx, cy, cw - ctx.tokens.px(4), ch - ctx.tokens.px(5)),
                ctx.fonts, align="center", valign="center")
            if value_text:
                children.append(value_text)
    elements["chart"] = Node(kind="group", role="chart", children=children, qa_class="control")
    specs = [_spec("headline", 7), _spec("chart", 9, "control"), _spec("body", 3)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "heatmap", "row_labels": rows,
                         "col_labels": cols, "values": matrix})

def build_scatter(ctx: SceneContext, scene: dict) -> BuiltScene:
    """Render a paired quantitative scatter plot with explicit domains (DM-102)."""
    theme, layout, elements = _data_panel_scaffold(ctx, scene, "KORELACJA")
    pts = scene.get("points")
    x_dom = scene.get("x_domain")
    y_dom = scene.get("y_domain")
    if (not isinstance(pts, list) or not 2 <= len(pts) <= 24
            or not isinstance(x_dom, list) or len(x_dom) != 2
            or not isinstance(y_dom, list) or len(y_dom) != 2):
        raise ValueError("scatter requires 2..24 points and explicit x_domain, y_domain")
    x0, x1 = safe_number(x_dom[0]), safe_number(x_dom[1])
    y0, y1 = safe_number(y_dom[0]), safe_number(y_dom[1])
    if x1 <= x0 or y1 <= y0:
        raise ValueError("scatter domains must have max > min")
    chart = layout.region("chart")
    colors = chart_colors(theme)
    plot = Rect(chart.x + chart.w * .17, chart.y + chart.h * .12,
                chart.w * .75, chart.h * .66)
    children: list[Node] = [chart_card("scatter-chart-surface", chart,
                                       ctx.tokens, theme)]
    for tick_index in range(5):
        fraction = tick_index / 4
        y = plot.bottom - plot.h * fraction
        x = plot.x + plot.w * fraction
        children.extend((
            Node(kind="line", role=f"scatter-y-grid-{tick_index}",
                 props={"x1": plot.x, "y1": y, "x2": plot.right, "y2": y,
                        "width": grid_width(ctx.tokens), "color": colors["grid"]},
                 qa_class="decor"),
            Node(kind="line", role=f"scatter-x-grid-{tick_index}",
                 props={"x1": x, "y1": plot.y, "x2": x, "y2": plot.bottom,
                        "width": grid_width(ctx.tokens), "color": colors["grid"]},
                 qa_class="decor"),
        ))
        y_tick = text_node(
            f"scatter-y-tick-{tick_index}",
            format_value(y0 + (y1 - y0) * fraction,
                         {"decimals": 0, "thousands": " "}),
            axis_style(ctx.tokens, colors, align="right"),
            Rect(chart.x, y - ctx.tokens.px(13),
                 plot.x - chart.x - ctx.tokens.px(6), ctx.tokens.px(26)),
            ctx.fonts, align="right", valign="center")
        x_tick = text_node(
            f"scatter-x-tick-{tick_index}",
            format_value(x0 + (x1 - x0) * fraction,
                         {"decimals": 0, "thousands": " "}),
            axis_style(ctx.tokens, colors),
            Rect(x - plot.w * .08, plot.bottom + ctx.tokens.px(4),
                 plot.w * .16, ctx.tokens.px(26)),
            ctx.fonts, align="center", valign="center")
        children.extend(node for node in (y_tick, x_tick) if node)
    children.extend((
        Node(kind="line", role="scatter-x-axis",
             props={"x1": plot.x, "y1": plot.bottom, "x2": plot.right, "y2": plot.bottom,
                    "width": max(1.0, ctx.tokens.px(1.5)), "color": colors["axis"]}, qa_class="decor"),
        Node(kind="line", role="scatter-y-axis",
             props={"x1": plot.x, "y1": plot.y, "x2": plot.x, "y2": plot.bottom,
                    "width": max(1.0, ctx.tokens.px(1.5)), "color": colors["axis"]}, qa_class="decor"),
    ))
    parsed = []
    r = max(5, ctx.tokens.px(9))
    for idx, pt in enumerate(pts):
        if not isinstance(pt, dict):
            raise ValueError(f"scatter point {idx} must be an object")
        xv, yv = safe_number(pt.get("x")), safe_number(pt.get("y"))
        if not (x0 <= xv <= x1 and y0 <= yv <= y1):
            raise ValueError(f"scatter point {idx} falls outside declared domains")
        px = plot.x + (xv - x0) / (x1 - x0) * plot.w
        py = plot.bottom - (yv - y0) / (y1 - y0) * plot.h
        children.append(Node(
            kind="circle", role=f"scatter-point-{idx}",
            props={"cx": px, "cy": py, "r": r, "fill": colors["accent"],
                   "border": colors["plot"],
                   "border_width": max(2, ctx.tokens.px(2))},
            qa_class="decor",
        ))
        parsed.append({"id": str(pt.get("id") or pt.get("label") or f"pt-{idx}"),
                       "x": xv, "y": yv})
    elements["chart"] = Node(kind="group", role="chart", children=children, qa_class="control")
    specs = [_spec("headline", 7), _spec("chart", 9, "control"), _spec("body", 3)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "scatter", "data": parsed,
                         "x_domain": [x0, x1], "y_domain": [y0, y1]})

def build_funnel(ctx: SceneContext, scene: dict) -> BuiltScene:
    """Render an ordered conversion funnel with non-increasing stage values (DM-102)."""
    theme, layout, elements = _data_panel_scaffold(ctx, scene, "LEJEK KONWERSJI")
    stages = scene.get("stages")
    if not isinstance(stages, list) or not 2 <= len(stages) <= 6:
        raise ValueError("funnel requires 2..6 ordered stages")
    parsed = []
    prev_val = None
    for idx, st in enumerate(stages):
        if not isinstance(st, dict) or not str(st.get("label", "")).strip():
            raise ValueError(f"funnel stage {idx} requires a label")
        val = safe_number(st.get("value"))
        if val <= 0:
            raise ValueError("funnel stage values must be positive")
        if prev_val is not None and val > prev_val:
            raise ValueError("funnel stages must be monotonically non-increasing")
        prev_val = val
        parsed.append({"id": str(st.get("id") or st["label"]),
                       "label": str(st["label"]).strip(), "value": val})
    top_val = parsed[0]["value"]
    chart = layout.region("chart")
    plot = Rect(chart.x + chart.w * .08, chart.y + chart.h * .08,
                chart.w * .84, chart.h * .80)
    row_h = plot.h / len(parsed)
    children: list[Node] = []
    lbl_size = max(12, ctx.tokens.px(16))
    for idx, item in enumerate(parsed):
        share = item["value"] / top_val
        w_bar = max(plot.w * .18, plot.w * share)
        x_bar = plot.center_x - w_bar / 2
        y = plot.y + idx * row_h
        children.append(Node(
            kind="round", role=f"funnel-stage-{idx}",
            props={"x": x_bar, "y": y + row_h * .12, "w": w_bar,
                   "h": row_h * .72, "r": ctx.tokens.px(8),
                   "fill": mix(theme["accent"], theme["surface"], idx * .15)},
            qa_class="decor", meta={"stable_row_id": item["id"], "share": round(share, 4)},
        ))
        fill = mix(theme["accent"], theme["surface"], idx * .15)
        lbl_style = TextStyle(
            lbl_size, ensure_contrast(theme["ink"], fill, 4.5),
            "bold", align="center")
        lbl = text_node(
            f"funnel-label-{idx}",
            f"{item['label']} ({round(share * 100)}%)",
            lbl_style,
            Rect(plot.x, y + row_h * .12, plot.w, row_h * .72),
            ctx.fonts, align="center", valign="center", fit=True,
        )
        if lbl:
            children.append(lbl)
    elements["chart"] = Node(kind="group", role="chart", children=children, qa_class="control")
    specs = [_spec("headline", 7), _spec("chart", 9, "control"), _spec("body", 3)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "funnel", "data": parsed})

def build_sankey(ctx: SceneContext, scene: dict) -> BuiltScene:
    """Render a total-conserving Sankey / energy flow diagram with animated links (DM-103)."""
    theme, layout, elements = _data_panel_scaffold(ctx, scene, "PRZEPŁYW ENERGII")
    links = scene.get("links")
    if not isinstance(links, list) or not 1 <= len(links) <= 8:
        raise ValueError("sankey requires 1..8 explicit source->target links")
    sources: dict[str, float] = {}
    targets: dict[str, float] = {}
    parsed_links = []
    for idx, link in enumerate(links):
        if not isinstance(link, dict):
            raise ValueError(f"sankey link {idx} must be an object")
        src = str(link.get("source", "")).strip()
        dst = str(link.get("target", "")).strip()
        val = safe_number(link.get("value"))
        if not src or not dst or src == dst or val <= 0:
            raise ValueError(f"sankey link {idx} requires distinct source, target and positive value")
        sources[src] = sources.get(src, 0.0) + val
        targets[dst] = targets.get(dst, 0.0) + val
        parsed_links.append({"source": src, "target": dst, "value": val})
    total_in = sum(sources.values())
    total_out = sum(targets.values())
    if abs(total_in - total_out) > 1e-4:
        raise ValueError("sankey total inflow does not equal total outflow")
    chart = layout.region("chart")
    plot = Rect(chart.x + chart.w * .06, chart.y + chart.h * .10,
                chart.w * .88, chart.h * .78)
    left_x, right_x = plot.x, plot.right - plot.w * .22
    node_w = plot.w * .22
    children: list[Node] = []
    lbl_size = max(12, ctx.tokens.px(15))
    src_centers: dict[str, float] = {}
    dst_centers: dict[str, float] = {}
    src_h = plot.h / len(sources)
    for idx, (s_name, s_val) in enumerate(sources.items()):
        y = plot.y + idx * src_h
        src_centers[s_name] = y + src_h / 2
        source_color = ensure_contrast(theme["ink"], theme["accent"], 4.5)
        source_style = TextStyle(lbl_size, source_color, "bold", align="center")
        children.append(Node(
            kind="round", role=f"sankey-src-{idx}",
            props={"x": left_x, "y": y + src_h * .12, "w": node_w,
                   "h": src_h * .76, "r": ctx.tokens.px(6), "fill": theme["accent"]},
            qa_class="decor",
        ))
        lbl = text_node(f"sankey-src-label-{idx}", s_name, source_style,
                        Rect(left_x, y + src_h * .12, node_w, src_h * .76),
                        ctx.fonts, align="center", valign="center", fit=True)
        if lbl:
            children.append(lbl)
    dst_h = plot.h / len(targets)
    for idx, (t_name, t_val) in enumerate(targets.items()):
        y = plot.y + idx * dst_h
        dst_centers[t_name] = y + dst_h / 2
        children.append(Node(
            kind="round", role=f"sankey-dst-{idx}",
            props={"x": right_x, "y": y + dst_h * .12, "w": node_w,
                   "h": dst_h * .76, "r": ctx.tokens.px(6), "fill": theme["surface"]},
            qa_class="decor",
        ))
        target_style = TextStyle(
            lbl_size, ensure_contrast(theme["ink"], theme["surface"], 4.5),
            "bold", align="center")
        lbl = text_node(f"sankey-dst-label-{idx}", t_name, target_style,
                        Rect(right_x, y + dst_h * .12, node_w, dst_h * .76),
                        ctx.fonts, align="center", valign="center", fit=True)
        if lbl:
            children.append(lbl)
    for idx, link in enumerate(parsed_links):
        y1 = src_centers[link["source"]]
        y2 = dst_centers[link["target"]]
        x1 = left_x + node_w
        x2 = right_x
        mid_x = (x1 + x2) / 2
        pts = [(x1, y1), (mid_x, y1 * .65 + y2 * .35),
               (mid_x, y1 * .35 + y2 * .65), (x2, y2)]
        stroke_w = max(2.0, ctx.tokens.px(18) * (link["value"] / total_in))
        link_node = Node(
            kind="path", role=f"sankey-link-{idx}",
            props={"points": pts, "width": stroke_w,
                   "color": theme["accent"], "progress": 1.0},
            qa_class="decor",
        )
        animate_progress(link_node, .15 + idx * .06, .55)
        children.append(link_node)
    elements["chart"] = Node(kind="group", role="chart", children=children, qa_class="control")
    specs = [_spec("headline", 7), _spec("chart", 9, "control"), _spec("body", 3)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "sankey", "links": parsed_links,
                         "conserved_total": total_in})
