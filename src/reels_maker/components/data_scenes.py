"""Data visualization scene builders for the Studio scene graph."""
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
from .scenes import (
    _background, _decor, _finish, _headline, _measure,
    _spec, _subtitle, _theme,
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
    row_gap = ctx.tokens.space("md")
    row_h = (chart.h - row_gap * (len(parsed) - 1)) / len(parsed)
    for index, item in enumerate(parsed):
        y = chart.y + index * (row_h + row_gap)
        label_style = TextStyle(ctx.tokens.px(26), theme["ink"], "bold",
                                uppercase=True, tracking=1)
        label = text_node(f"bar-label-{index}", item["label"], label_style,
                          Rect(chart.x, y, chart.w, row_h * .34), ctx.fonts,
                          valign="center")
        base = Node(kind="round", role="bar-base",
                    props={"x": chart.x, "y": y + row_h * .50,
                           "w": chart.w, "h": ctx.tokens.px(22),
                           "r": ctx.tokens.px(11),
                           "fill": mix(theme["base"], theme["ink"], .13)},
                    opacity=.55)
        bar = Node(kind="round", role=f"bar-{index}",
                   props={"x": chart.x, "y": y + row_h * .50,
                          "w": chart.w * item["value"] / max_value,
                          "h": ctx.tokens.px(22), "r": ctx.tokens.px(11),
                          "fill": theme["accent"], "progress": 1.0},
                   qa_class="decor")
        value_style = TextStyle(ctx.tokens.px(28), theme["accent"], "bold",
                                align="right")
        value = text_node(
            f"bar-value-{index}",
            format_value(item["value"], {
                "suffix": item.get("suffix", ""),
                "prefix": item.get("prefix", ""), "thousands": " "}),
                          value_style, Rect(chart.x, y + row_h * .62,
                                            chart.w, row_h * .28),
                          ctx.fonts, align="right", valign="top")
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
                   elements, specs, decor=_decor(ctx, scene, theme),
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
    plot = Rect(chart.x + chart.w * .23, chart.y + chart.h * .15,
                chart.w * .75, chart.h * .62)
    row_height = plot.h / len(parsed_categories)
    colors = [theme["accent"], theme["ink"],
              mix(theme["accent"], theme["base"], .48),
              mix(theme["ink"], theme["base"], .55)]
    children: list[Node] = []
    category_style = TextStyle(max(12, ctx.tokens.px(18)), theme["ink"], "bold")
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
                                    "color": mix(theme["base"], theme["ink"], .18)},
                             qa_class="decor"))
        tick = text_node(f"stack-tick-{index}", f"{index * 25}%",
                         TextStyle(max(12, ctx.tokens.px(15)), theme["muted"],
                                   "regular", align="center"),
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
            TextStyle(max(11, ctx.tokens.px(14)), theme["muted"], "regular"),
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
    plot = Rect(chart.x + chart.w * .20, chart.y + chart.h * .13,
                chart.w * .77, chart.h * .63)
    elements: dict[str, Node] = {
        "headline": text_node("headline", headline, headline_style,
                              layout.region("headline"), ctx.fonts,
                              align="center", valign="center")
    }
    children: list[Node] = []
    tick_values = [low + (high - low) * index / 4 for index in range(5)]
    step = (high - low) / 4
    decimals = 0 if float(step).is_integer() else min(4, max(1, math.ceil(-math.log10(step)) + 1))
    tick_style = TextStyle(max(12, ctx.tokens.px(15)), theme["muted"], "regular",
                           align="right")
    grid_color = mix(theme["base"], theme["ink"], .18)
    for index, tick in enumerate(tick_values):
        y = plot.bottom - plot.h * index / 4
        children.append(Node(kind="line", role=f"y-grid-{index}",
                             props={"x1": plot.x, "y1": y, "x2": plot.right,
                                    "y2": y, "width": 1, "color": grid_color},
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
                                "width": 2, "color": theme["ink"]},
                         qa_class="decor"))
    y_points = [plot.bottom - (item["value"] - low) / (high - low) * plot.h
                for item in parsed]
    x_points = [plot.x + fraction * plot.w for fraction in x_values]
    for index in range(len(parsed) - 1):
        children.append(Node(kind="line", role=f"series-segment-{index}",
                             props={"x1": x_points[index], "y1": y_points[index],
                                    "x2": x_points[index + 1], "y2": y_points[index + 1],
                                    "width": max(2, ctx.tokens.px(4)),
                                    "color": theme["accent"]}, qa_class="decor"))
    point_radius = max(3, ctx.tokens.px(7))
    label_style = TextStyle(max(12, ctx.tokens.px(16)), theme["ink"], "regular",
                            align="center")
    x_label_y = plot.bottom + ctx.tokens.px(12)
    x_boundaries = [plot.x]
    x_boundaries.extend((x_points[index - 1] + x_points[index]) / 2
                        for index in range(1, len(x_points)))
    x_boundaries.append(chart.right)
    for index, item in enumerate(parsed):
        children.append(Node(kind="circle", role=f"series-point-{index}",
                             props={"cx": x_points[index], "cy": y_points[index],
                                    "r": point_radius, "fill": theme["accent"]},
                             qa_class="decor"))
        point_label = text_node(
            f"x-label-{index}", item["label"], label_style,
            Rect(x_boundaries[index], x_label_y,
                 x_boundaries[index + 1] - x_boundaries[index],
                 ctx.tokens.px(32)),
            ctx.fonts, align="center", valign="top")
        if point_label:
            children.append(point_label)
    axis_style = TextStyle(max(13, ctx.tokens.px(18)), theme["ink"], "bold",
                           align="center")
    x_title = text_node("x-axis-title", x_axis_label.strip(), axis_style,
                        Rect(plot.x, chart.bottom - ctx.tokens.px(34),
                             plot.w, ctx.tokens.px(28)), ctx.fonts,
                        align="center", valign="center")
    y_title = text_node("y-axis-title", y_axis_label.strip(), axis_style,
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


def _data_panel_scaffold(ctx: SceneContext, scene: dict, default_headline: str):
    theme = _theme(ctx, scene)
    headline = _headline(scene) or default_headline
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
    elements: dict[str, Node] = {
        "headline": text_node("headline", headline, title_style,
                              layout.region("headline"), ctx.fonts,
                              align="center", valign="center"),
    }
    if subtitle and layout.optional("body"):
        elements["body"] = text_node("body", subtitle, body_style,
                                     layout.region("body"), ctx.fonts,
                                     align="center", valign="center")
    return theme, layout, elements


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
    plot = Rect(chart.x + chart.w * .08, chart.y + chart.h * .10,
                chart.w * .84, chart.h * .72)
    slot_w = plot.w / len(parsed)
    bar_w = slot_w * .62
    children: list[Node] = []
    lbl_style = TextStyle(max(12, ctx.tokens.px(15)), theme["ink"], "bold", align="center")
    for idx, item in enumerate(parsed):
        x = plot.x + idx * slot_w + (slot_w - bar_w) / 2
        y_top = plot.bottom - (max(item["start"], item["end"]) - low) / span * plot.h
        y_bot = plot.bottom - (min(item["start"], item["end"]) - low) / span * plot.h
        h = max(ctx.tokens.px(4), y_bot - y_top)
        fill = (theme["ink"] if item["kind"] in ("opening", "total")
                else (theme["accent"] if item["value"] >= 0 else ctx.tokens.palette.danger))
        children.append(Node(
            kind="round", role=f"waterfall-bar-{idx}",
            props={"x": x, "y": y_top, "w": bar_w, "h": h,
                   "r": ctx.tokens.px(4), "fill": fill},
            qa_class="decor", meta={"stable_row_id": item["id"], "value": item["value"]},
        ))
        lbl = text_node(f"waterfall-label-{idx}", item["label"], lbl_style,
                        Rect(plot.x + idx * slot_w, plot.bottom + ctx.tokens.px(6),
                             slot_w, ctx.tokens.px(28)),
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
    plot = Rect(chart.x + chart.w * .20, chart.y + chart.h * .14,
                chart.w * .74, chart.h * .74)
    cw, ch = plot.w / len(cols), plot.h / len(rows)
    children: list[Node] = []
    hdr_style = TextStyle(max(12, ctx.tokens.px(15)), theme["ink"], "bold", align="center")
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
            fill = mix(theme["surface"], theme["accent"], .15 + .80 * t)
            cx = plot.x + c_idx * cw + ctx.tokens.px(2)
            cy = plot.y + r_idx * ch + ctx.tokens.px(2)
            children.append(Node(
                kind="round", role=f"heatmap-cell-{r_idx}-{c_idx}",
                props={"x": cx, "y": cy, "w": cw - ctx.tokens.px(4),
                       "h": ch - ctx.tokens.px(4), "r": ctx.tokens.px(4), "fill": fill},
                qa_class="decor",
            ))
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
    plot = Rect(chart.x + chart.w * .14, chart.y + chart.h * .10,
                chart.w * .78, chart.h * .72)
    children: list[Node] = [
        Node(kind="line", role="scatter-x-axis",
             props={"x1": plot.x, "y1": plot.bottom, "x2": plot.right, "y2": plot.bottom,
                    "width": 2, "color": theme["ink"]}, qa_class="decor"),
        Node(kind="line", role="scatter-y-axis",
             props={"x1": plot.x, "y1": plot.y, "x2": plot.x, "y2": plot.bottom,
                    "width": 2, "color": theme["ink"]}, qa_class="decor"),
    ]
    parsed = []
    r = max(4, ctx.tokens.px(8))
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
            props={"cx": px, "cy": py, "r": r, "fill": theme["accent"]},
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
    lbl_style = TextStyle(max(12, ctx.tokens.px(16)), theme["ink"], "bold", align="center")
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
    lbl_style = TextStyle(max(12, ctx.tokens.px(15)), theme["ink"], "bold", align="center")
    src_centers: dict[str, float] = {}
    dst_centers: dict[str, float] = {}
    src_h = plot.h / len(sources)
    for idx, (s_name, s_val) in enumerate(sources.items()):
        y = plot.y + idx * src_h
        src_centers[s_name] = y + src_h / 2
        children.append(Node(
            kind="round", role=f"sankey-src-{idx}",
            props={"x": left_x, "y": y + src_h * .12, "w": node_w,
                   "h": src_h * .76, "r": ctx.tokens.px(6), "fill": theme["accent"]},
            qa_class="decor",
        ))
        lbl = text_node(f"sankey-src-label-{idx}", s_name, lbl_style,
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
        lbl = text_node(f"sankey-dst-label-{idx}", t_name, lbl_style,
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
