"""Basic scene builders for Studio data visualizations."""
from __future__ import annotations

import math

from ..core.scene_graph import Node
from ..design.color import mix
from ..layout.engine import Rect
from ..motionkit.keyframes import Keyframe, Track
from ..textkit.typesetter import TextStyle
from .chart_style import (
    axis_style, chart_card, chart_colors, grid_width, mark_width, value_style,
)
from .base import (
    BuiltScene, SceneContext, animate_progress, format_value, number_node,
    resolve_text_style, safe_number, text_node,
)
from .scene_support import (
    _background, _data_panel_scaffold, _decor, _finish, _headline,
    _measure, _spec, _subtitle, _theme,
)

def build_bars(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    headline = _headline(scene) or "PORÓWNANIE"
    subtitle = str(scene.get("subtitle") or _subtitle(scene) or "")
    data = scene.get("bars") or scene.get("data") or [
        {"label": "DZIŚ", "value": 32}, {"label": "Z MAGAZYNEM", "value": 78}]
    if not isinstance(data, list) or not data:
        raise ValueError("bars requires a nonempty data list")
    parsed = [{"id": str(item.get("id") or item.get("label") or f"bar-{idx}"),
               "label": str(item.get("label", "")),
               "value": safe_number(item.get("value", 0)),
               "suffix": str(item.get("suffix", "")),
               "prefix": str(item.get("prefix", ""))}
              for idx, item in enumerate(data)]
    data_order = scene.get("data_order", "source")
    if data_order not in ("source", "ascending", "descending"):
        raise ValueError("bars data_order must be source, ascending or descending")
    if data_order != "source":
        labels = [item["label"].strip() for item in parsed]
        if any(not label for label in labels) or len(set(labels)) != len(labels):
            raise ValueError("ranked bars require unique non-empty category labels")
        if any(item["value"] < 0 for item in parsed):
            raise ValueError("ranked bars currently require non-negative values")
        indexed = list(enumerate(parsed))
        indexed.sort(key=(lambda item: (-item[1]["value"], item[0]))
                     if data_order == "descending" else
                     (lambda item: (item[1]["value"], item[0])))
        parsed = [item for _, item in indexed]
    max_value = max(item["value"] for item in parsed) or 1
    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "title", theme["ink"],
                                        align="center", balance=True)
    body_style = resolve_text_style(ctx.tokens, "body", theme["muted"],
                                    align="center")
    layout = ctx.layout.layout("data-panel", {
        "headline": _measure(headline, headline_style, width, ctx),
        "body": _measure(subtitle, body_style, width, ctx)})
    elements: dict[str, Node] = {
        "headline": text_node("headline", headline, headline_style,
                              layout.region("headline"), ctx.fonts,
                              align="center", valign="center")}
    chart = layout.region("chart")
    colors = chart_colors(theme)
    row_gap = max(ctx.tokens.px(18), chart.h * .035)
    inset_x = ctx.tokens.px(20)
    plot = Rect(chart.x + inset_x, chart.y + ctx.tokens.px(14),
                chart.w - 2 * inset_x, chart.h - ctx.tokens.px(28))
    row_h = (plot.h - row_gap * (len(parsed) - 1)) / len(parsed)
    track_h = max(8.0, min(ctx.tokens.px(14), row_h * .17))
    for index, item in enumerate(parsed):
        y = plot.y + index * (row_h + row_gap)
        label_style = TextStyle(max(9.0, ctx.tokens.px(22)), colors["axis"], "bold",
                                uppercase=True, tracking=.35, line_height=1.0)
        label = text_node(f"bar-label-{index}", item["label"], label_style,
                          Rect(plot.x, y, plot.w * .70, row_h * .40), ctx.fonts,
                          valign="center")
        value_color = colors["accent"] if index == 0 else colors["axis"]
        value_style_ = value_style(ctx.tokens, colors, color=value_color)
        value_text = format_value(item["value"], {
            "suffix": item.get("suffix", ""),
            "prefix": item.get("prefix", ""), "thousands": " "})
        value = text_node(
            f"bar-value-{index}", value_text, value_style_,
            Rect(plot.x + plot.w * .70, y, plot.w * .30, row_h * .40),
            ctx.fonts, align="right", valign="center")
        track_y = y + row_h * .57
        base = Node(kind="round", role=f"bar-track-{index}",
                    props={"x": plot.x, "y": track_y,
                           "w": plot.w, "h": track_h,
                           "r": track_h / 2, "fill": colors["grid"]},
                    qa_class="decor")
        bar = Node(kind="round", role=f"bar-{index}",
                   props={"x": plot.x, "y": track_y,
                          "w": plot.w * item["value"] / max_value,
                          "h": track_h, "r": track_h / 2,
                          "fill": value_color, "progress": 1.0},
                   qa_class="decor")
        if index > 0:
            bar.opacity = .72
        group = Node(kind="group", role=f"bar-row-{index}",
                     children=[child for child in (label, base, bar, value)
                               if child], qa_class="control",
                     meta={"stable_row_id": item["id"]})
        elements[f"bar-row-{index}"] = group
    if subtitle and layout.optional("body"):
        elements["body"] = text_node(
            "body", subtitle, body_style, layout.region("body"), ctx.fonts,
            align="center", valign="center")
    specs = [_spec("headline", 7)]
    specs += [_spec(f"bar-row-{index}", 5 - index * .4, "control",
                    order=index)
              for index in range(len(parsed))]
    if "body" in elements:
        specs.append(_spec("body", 3))
    plan = _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs,
                   decor=[chart_card("bar-chart-card", chart, ctx.tokens, theme),
                          *_decor(ctx, scene, theme)],
                   meta={"component": "bars", "data": parsed,
                         "data_order": data_order,
                         "row_ids": [item["id"] for item in parsed],
                         "data_provenance": scene.get("data_provenance")})
    for index, item in enumerate(parsed):
        entry = plan.choreography.entries.get(f"bar-row-{index}")
        if entry:
            group = plan.elements[f"bar-row-{index}"]
            for child in group.children:
                if child.role == f"bar-{index}":
                    animate_progress(child, entry.onset,
                                     max(.3, entry.duration * 1.4),
                                     easing="out-quart")
    return plan

def build_stacked_bars_100(ctx: SceneContext, scene: dict) -> BuiltScene:
    """Render caller-provided positive categories as 100% vector-stacked bars.

    Each row is normalized only by its explicitly supplied segment sum. Category
    and segment IDs/order are preserved; the source values and computed shares
    are reported. No missing segment is imputed as zero.
    """
    theme = _theme(ctx, scene)
    headline = _headline(scene)
    categories = scene.get("categories")
    if not isinstance(categories, list) or not 1 <= len(categories) <= 4:
        raise ValueError("stacked_bars_100 requires 1..4 explicit categories")
    segment_specs = None
    parsed_categories = []
    category_ids = set()
    for category_index, category in enumerate(categories):
        if not isinstance(category, dict):
            raise ValueError(f"stacked category {category_index} must be an object")
        category_id = category.get("id")
        label = category.get("label")
        segments = category.get("segments")
        if not isinstance(category_id, str) or not category_id.strip() or category_id in category_ids:
            raise ValueError("stacked category IDs must be unique non-empty strings")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"stacked category {category_id!r} requires a label")
        if not isinstance(segments, list) or not 2 <= len(segments) <= 4:
            raise ValueError(f"stacked category {category_id!r} requires 2..4 segments")
        parsed_segments = []
        for segment_index, segment in enumerate(segments):
            if not isinstance(segment, dict):
                raise ValueError("stacked segments must be objects")
            segment_id, segment_label = segment.get("id"), segment.get("label")
            value = safe_number(segment.get("value"))
            if not isinstance(segment_id, str) or not segment_id.strip():
                raise ValueError("stacked segment IDs must be non-empty strings")
            if not isinstance(segment_label, str) or not segment_label.strip():
                raise ValueError(f"stacked segment {segment_id!r} requires a label")
            if value < 0:
                raise ValueError("100% stacked bars require non-negative segment values")
            parsed_segments.append({"id": segment_id, "label": segment_label,
                                    "value": value})
        ids = tuple(segment["id"] for segment in parsed_segments)
        labels = tuple(segment["label"] for segment in parsed_segments)
        if len(set(ids)) != len(ids):
            raise ValueError("segment IDs must be unique within a category")
        if segment_specs is None:
            segment_specs = tuple((item["id"], item["label"])
                                  for item in parsed_segments)
        elif tuple(zip(ids, labels)) != segment_specs:
            raise ValueError("every category must provide the same ordered segment IDs and labels")
        total = sum(segment["value"] for segment in parsed_segments)
        if total <= 0:
            raise ValueError(f"stacked category {category_id!r} has zero total")
        parsed_categories.append({
            "id": category_id, "label": label.strip(),
            "segments": [{**segment, "share": segment["value"] / total}
                         for segment in parsed_segments],
            "total": total,
        })
        category_ids.add(category_id)

    subtitle = str(scene.get("subtitle") or _subtitle(scene) or "")
    width = ctx.layout.safe.w
    title_style = resolve_text_style(ctx.tokens, "title", theme["ink"],
                                     align="center", balance=True)
    body_style = resolve_text_style(ctx.tokens, "body", theme["muted"],
                                    align="center")
    layout = ctx.layout.layout("data-panel", {
        "headline": _measure(headline, title_style, width, ctx),
        "body": _measure(subtitle, body_style, width, ctx),
    })
    chart = layout.region("chart")
    chart_theme = chart_colors(theme)
    plot = Rect(chart.x + chart.w * .23, chart.y + chart.h * .15,
                chart.w * .75, chart.h * .62)
    row_height = plot.h / len(parsed_categories)
    colors = list(chart_theme["series"][:len(segment_specs)])
    children: list[Node] = [chart_card("stacked-chart-surface", chart,
                                       ctx.tokens, theme)]
    category_style = TextStyle(max(12, ctx.tokens.px(18)),
                               chart_theme["axis"], "bold")
    for row_index, category in enumerate(parsed_categories):
        y = plot.y + row_index * row_height
        category_node = text_node(
            f"stack-category-{category['id']}", category["label"], category_style,
            Rect(chart.x, y, plot.x - chart.x - ctx.tokens.px(8), row_height),
            ctx.fonts, align="right", valign="center", fit=True)
        if category_node:
            children.append(category_node)
        x = plot.x
        for segment_index, segment in enumerate(category["segments"]):
            segment_width = plot.w * segment["share"]
            if segment_width > 0:
                children.append(Node(
                    kind="rect", role=f"stack-{category['id']}-{segment['id']}",
                    props={"x": x, "y": y + row_height * .18,
                           "w": segment_width, "h": row_height * .64,
                           "fill": colors[segment_index]}, qa_class="decor",
                    meta={"category_id": category["id"],
                          "segment_id": segment["id"],
                          "source_value": segment["value"],
                          "share": segment["share"]}))
            x += segment_width

    # A percentage axis is intrinsic to the declared 100%-normalization.
    for index in range(5):
        fraction = index / 4
        x = plot.x + plot.w * fraction
        children.append(Node(kind="line", role=f"stack-grid-{index}",
                             props={"x1": x, "y1": plot.y,
                                    "x2": x, "y2": plot.bottom,
                                    "width": 1,
                                     "color": chart_theme["grid"]},
                             qa_class="decor"))
        tick = text_node(f"stack-tick-{index}", f"{index * 25}%",
                          axis_style(ctx.tokens, chart_theme, align="center"),
                         Rect(x - plot.w * .08, plot.bottom + ctx.tokens.px(5),
                              plot.w * .16, ctx.tokens.px(24)), ctx.fonts,
                         align="center", valign="center")
        if tick:
            children.append(tick)
    legend_width = chart.w / len(segment_specs)
    legend_y = chart.bottom - ctx.tokens.px(32)
    for index, (segment_id, label) in enumerate(segment_specs):
        x = chart.x + index * legend_width
        children.append(Node(kind="round", role=f"stack-legend-mark-{segment_id}",
                             props={"x": x + ctx.tokens.px(4), "y": legend_y + ctx.tokens.px(6),
                                    "w": ctx.tokens.px(12), "h": ctx.tokens.px(12),
                                    "r": ctx.tokens.px(3), "fill": colors[index]},
                             qa_class="decor"))
        legend = text_node(
            f"stack-legend-{segment_id}", label,
             axis_style(ctx.tokens, chart_theme),
            Rect(x + ctx.tokens.px(20), legend_y,
                 legend_width - ctx.tokens.px(22), ctx.tokens.px(26)),
            ctx.fonts, valign="center", fit=True)
        if legend:
            children.append(legend)

    elements: dict[str, Node] = {
        "headline": text_node("headline", headline, title_style,
                              layout.region("headline"), ctx.fonts,
                              align="center", valign="center"),
        "chart": Node(kind="group", role="chart", children=children,
                       qa_class="control"),
    }
    if subtitle and layout.optional("body"):
        elements["body"] = text_node("body", subtitle, body_style,
                                      layout.region("body"), ctx.fonts,
                                      align="center", valign="center")
    specs = [_spec("headline", 7), _spec("chart", 9, "control"),
             _spec("body", 3)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "stacked_bars_100",
                         "normalization": "segment value / explicit category total",
                         "data": parsed_categories})

def build_line_chart(ctx: SceneContext, scene: dict) -> BuiltScene:
    """Render one explicit, typed-by-contract vector line series.

    Axis labels and a numeric domain are mandatory. Date labels preserve the
    supplied order and are positioned by elapsed days; categorical labels use
    evenly spaced slots. No units, dates, missing points or y-domain are guessed.
    """
    from datetime import date

    theme = _theme(ctx, scene)
    headline = _headline(scene)
    raw_points = scene.get("points")
    if not isinstance(raw_points, list) or not 2 <= len(raw_points) <= 12:
        raise ValueError("line_chart requires 2..12 explicit points")
    x_axis_label = scene.get("x_axis_label")
    y_axis_label = scene.get("y_axis_label")
    if not isinstance(x_axis_label, str) or not x_axis_label.strip():
        raise ValueError("line_chart requires an explicit x_axis_label")
    if not isinstance(y_axis_label, str) or not y_axis_label.strip():
        raise ValueError("line_chart requires an explicit y_axis_label including units")
    x_axis_type = scene.get("x_axis_type", "category")
    if x_axis_type not in ("category", "date"):
        raise ValueError("line_chart x_axis_type must be category or date")
    domain = scene.get("y_domain")
    if not isinstance(domain, list) or len(domain) != 2:
        raise ValueError("line_chart requires an explicit two-value y_domain")
    low, high = (safe_number(value) for value in domain)
    if high <= low:
        raise ValueError("line_chart y_domain maximum must exceed its minimum")

    parsed = []
    seen = set()
    for index, point in enumerate(raw_points):
        if not isinstance(point, dict):
            raise ValueError(f"line_chart point {index} must be an object")
        label = point.get("label")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"line_chart point {index} requires a non-empty label")
        if label in seen:
            raise ValueError(f"line_chart point labels must be unique: {label!r}")
        seen.add(label)
        value = safe_number(point.get("value"))
        if not low <= value <= high:
            raise ValueError(f"line_chart value for {label!r} is outside explicit y_domain")
        parsed.append({"label": label, "value": value})

    if x_axis_type == "date":
        try:
            dates = [date.fromisoformat(item["label"]) for item in parsed]
        except ValueError as exc:
            raise ValueError("date-axis labels must use ISO YYYY-MM-DD") from exc
        if any(current <= previous for previous, current in zip(dates, dates[1:])):
            raise ValueError("date-axis labels must be strictly increasing")
        first_day = dates[0].toordinal()
        day_span = dates[-1].toordinal() - first_day
        x_values = [(item.toordinal() - first_day) / day_span for item in dates]
    else:
        x_values = [index / (len(parsed) - 1) for index in range(len(parsed))]

    subtitle = str(scene.get("subtitle") or _subtitle(scene) or "")
    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "title", theme["ink"],
                                        align="center", balance=True)
    body_style = resolve_text_style(ctx.tokens, "body", theme["muted"],
                                    align="center")
    layout = ctx.layout.layout("data-panel", {
        "headline": _measure(headline, headline_style, width, ctx),
        "body": _measure(subtitle, body_style, width, ctx),
    })
    chart = layout.region("chart")
    colors = chart_colors(theme)
    plot = Rect(chart.x + chart.w * .21, chart.y + chart.h * .15,
                chart.w * .74, chart.h * .59)
    elements: dict[str, Node] = {
        "headline": text_node("headline", headline, headline_style,
                              layout.region("headline"), ctx.fonts,
                              align="center", valign="center")
    }
    children: list[Node] = [chart_card("line-chart-surface", chart,
                                        ctx.tokens, theme)]
    tick_values = [low + (high - low) * index / 4 for index in range(5)]
    step = (high - low) / 4
    decimals = 0 if float(step).is_integer() else min(4, max(1, math.ceil(-math.log10(step)) + 1))
    tick_style = axis_style(ctx.tokens, colors, align="right")
    grid_color = colors["grid"]
    for index, tick in enumerate(tick_values):
        y = plot.bottom - plot.h * index / 4
        children.append(Node(kind="line", role=f"y-grid-{index}",
                             props={"x1": plot.x, "y1": y, "x2": plot.right,
                                     "y2": y, "width": grid_width(ctx.tokens),
                                     "color": grid_color},
                             qa_class="decor"))
        label = text_node(
            f"y-tick-{index}", format_value(tick, {"decimals": decimals,
                                                      "thousands": " "}),
            tick_style, Rect(chart.x, y - ctx.tokens.px(14),
                             plot.x - chart.x - ctx.tokens.px(7),
                             ctx.tokens.px(28)), ctx.fonts, align="right",
            valign="center")
        if label:
            children.append(label)
    children.append(Node(kind="line", role="x-axis",
                         props={"x1": plot.x, "y1": plot.bottom,
                                "x2": plot.right, "y2": plot.bottom,
                                 "width": max(1.0, ctx.tokens.px(1.5)),
                                 "color": colors["axis"]},
                         qa_class="decor"))
    y_points = [plot.bottom - (item["value"] - low) / (high - low) * plot.h
                for item in parsed]
    x_points = [plot.x + fraction * plot.w for fraction in x_values]
    for index in range(len(parsed) - 1):
        children.append(Node(kind="line", role=f"series-segment-{index}",
                             props={"x1": x_points[index], "y1": y_points[index],
                                    "x2": x_points[index + 1], "y2": y_points[index + 1],
                                     "width": mark_width(ctx.tokens),
                                     "color": colors["accent"]}, qa_class="decor"))
    point_radius = max(4, ctx.tokens.px(8))
    label_style = axis_style(ctx.tokens, colors, align="center")
    x_label_y = plot.bottom + ctx.tokens.px(12)
    x_boundaries = [plot.x]
    x_boundaries.extend((x_points[index - 1] + x_points[index]) / 2
                        for index in range(1, len(x_points)))
    x_boundaries.append(chart.right)
    for index, item in enumerate(parsed):
        children.append(Node(kind="circle", role=f"series-point-{index}",
                             props={"cx": x_points[index], "cy": y_points[index],
                                    "r": point_radius, "fill": colors["plot"],
                                    "border": colors["accent"],
                                    "border_width": max(2, ctx.tokens.px(2))},
                             qa_class="decor"))
        children.append(Node(kind="circle", role=f"series-core-{index}",
                             props={"cx": x_points[index], "cy": y_points[index],
                                    "r": max(2.0, point_radius * .42),
                                    "fill": colors["accent"]},
                             qa_class="decor"))
        point_label = text_node(
            f"x-label-{index}", item["label"], label_style,
            Rect(x_boundaries[index], x_label_y,
                 x_boundaries[index + 1] - x_boundaries[index],
                 ctx.tokens.px(32)),
            ctx.fonts, align="center", valign="top")
        if point_label:
            children.append(point_label)
    latest_label = text_node(
        "latest-value",
        format_value(parsed[-1]["value"], {"decimals": decimals,
                                           "thousands": " "}),
        TextStyle(max(14, ctx.tokens.px(19)), colors["accent"], "bold",
                  align="right", line_height=1.0),
        Rect(plot.right - ctx.tokens.px(138),
             max(plot.y + ctx.tokens.px(2), y_points[-1] - ctx.tokens.px(38)),
             ctx.tokens.px(128), ctx.tokens.px(30)),
        ctx.fonts, align="right", valign="center")
    if latest_label:
        children.append(latest_label)
    title_style = TextStyle(max(13, ctx.tokens.px(17)), colors["axis"], "bold",
                            align="center")
    x_title = text_node("x-axis-title", x_axis_label.strip(), title_style,
                        Rect(plot.x, chart.bottom - ctx.tokens.px(34),
                             plot.w, ctx.tokens.px(28)), ctx.fonts,
                        align="center", valign="center")
    y_title = text_node("y-axis-title", y_axis_label.strip(), title_style,
                        Rect(chart.x, chart.y + ctx.tokens.px(2),
                             chart.w, ctx.tokens.px(28)), ctx.fonts,
                        align="center", valign="center")
    children.extend(item for item in (x_title, y_title) if item)
    elements["chart"] = Node(kind="group", role="chart", children=children,
                              qa_class="control")
    if subtitle and layout.optional("body"):
        elements["body"] = text_node("body", subtitle, body_style,
                                      layout.region("body"), ctx.fonts,
                                      align="center", valign="center")
    specs = [_spec("headline", 7), _spec("chart", 9, "control"),
             _spec("body", 3)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "line_chart", "data": parsed,
                         "x_axis_type": x_axis_type,
                         "x_axis_label": x_axis_label,
                         "y_axis_label": y_axis_label,
                         "y_domain": [low, high]})
