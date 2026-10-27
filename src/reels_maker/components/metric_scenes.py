"""Scene builders for the metric family."""
from __future__ import annotations

from ..core.scene_graph import Node
from ..design.color import mix
from ..layout.engine import Rect
from ..motionkit.keyframes import Keyframe, Track
from ..textkit.typesetter import TextStyle
from . import icons
from .base import (BuiltScene, SceneContext, animate_counter, animate_progress,
                   format_value, number_node, panel_node, resolve_text_style,
                   safe_number, text_node)
from .scene_support import (
    _background, _card_fill, _decor, _external_icon, _finish, _fmt,
    _headline, _measure, _panel_with_text,
    _spec, _subtitle, _theme,
)



def _counter_onset(value: float, entry, *, duration_factor: float = 1.15) -> tuple[float, float]:
    return (entry.onset, max(.18, min(entry.duration * duration_factor,
                                      entry.duration * 1.6)))


def _find_node(container, role: str) -> Node | None:
    if isinstance(container, dict):
        return container.get(role)
    if isinstance(container, Node):
        for node in container.flatten():
            if node.role == role:
                return node
        return None
    if isinstance(container, (list, tuple)):
        for item in container:
            found = _find_node(item, role)
            if found is not None:
                return found
    return None


def _number_in(container, role: str, target: float, entry,
               ctx: SceneContext) -> None:
    node = _find_node(container, role)
    if node is None:
        return
    onset, duration = _counter_onset(target, entry)
    animate_counter(node, target, onset, duration)


def build_amount(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    value = safe_number(scene.get("value", 16000))
    fmt = _fmt(scene)
    kicker = str(scene.get("kicker", "DOTACJA DO"))
    subtitle = str(scene.get("subtitle") or _subtitle(scene)
                   or "NA MAGAZYN ENERGII")
    has_visual = scene.get("visual", "battery") != "none"
    headline_copy = format_value(value, fmt)
    width = ctx.layout.safe.w
    kicker_style = resolve_text_style(ctx.tokens, "kicker", theme["accent"], align="center")
    hero_style = resolve_text_style(ctx.tokens, "hero", theme["accent"], align="center")
    body_style = resolve_text_style(ctx.tokens, "subtitle", theme["muted"],
                                    align="center", line_height=1.3)
    measurements = {
        "kicker": _measure(kicker, kicker_style, width, ctx),
        "headline": _measure(headline_copy, hero_style, width, ctx),
        "body": _measure(subtitle, body_style, width, ctx),
    }
    layout = ctx.layout.layout("hero-number", measurements, has_visual=has_visual)
    elements: dict[str, Node] = {}
    elements["kicker"] = text_node("kicker", kicker, kicker_style,
                                   layout.region("kicker"), ctx.fonts,
                                   align="center", valign="bottom")
    elements["amount"] = number_node("amount", value, layout.region("headline"),
                                     ctx.tokens, fmt=fmt, size_role="hero",
                                     color=theme["accent"], align="center",
                                     meta={"font_size": "hero"})
    elements["body"] = text_node("body", subtitle, body_style,
                                 layout.region("body"), ctx.fonts,
                                 align="center", valign="center")
    specs = [_spec("kicker", 4), _spec("amount", 10, "display"),
             _spec("body", 5)]
    if has_visual:
        region = layout.region("visual")
        size = min(region.w * .72, region.h * .76)
        cx, cy = region.center_x, region.center_y
        battery = (_external_icon(scene, "battery", cx, cy, size, theme["accent"])
                   or icons.battery(cx, cy, size, theme["accent"],
                                    shell=theme["ink"], level=.7))
        elements["visual"] = battery
        specs.append(_spec("visual", 3, "visual", hint="scale-focus"))
    plan = _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"value": value, "format": fmt, "component": "counter"})
    entry = plan.choreography.entries.get("amount")
    if entry:
        _number_in(plan.elements, "amount", value, entry, ctx)
    if has_visual and "visual" in plan.elements:
        _animate_battery_cells(plan.elements["visual"],
                               plan.choreography.entries.get("visual"),
                               target=.7)
    return plan


def _animate_battery_cells(node: Node, entry, target: float = .7) -> None:
    onset = entry.onset if entry else 0.0
    duration = entry.duration if entry else .4
    for index, child in enumerate(node.children):
        if not child.role.startswith("battery-cell-"):
            continue
        start = onset + index * duration * .16
        child.opacity = 0.0
        child.track("opacity", Track([
            Keyframe(0.0, 0.0), Keyframe(start, 0.0),
            Keyframe(start + .18, 1.0, "out-cubic")]))


def build_breakdown(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    items = scene.get("items")
    if not isinstance(items, list) or not items:
        items = [{"label": "MAGAZYN ENERGII", "value": 16000},
                 {"label": "MAGAZYN CIEPŁA", "value": 1000},
                 {"label": "PREMIA UE", "value": 2000}]
    parsed = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("breakdown items must be objects")
        parsed.append({"label": str(item.get("label", "")),
                       "value": safe_number(item.get("value", 0))})
    total = safe_number(scene.get("total", sum(item["value"] for item in parsed)))
    fmt = _fmt(scene)
    headline_copy = str(scene.get("kicker", "ŁĄCZNIE NAWET"))
    subtitle = str(scene.get("subtitle") or _subtitle(scene) or "")
    width = ctx.layout.safe.w
    kicker_style = resolve_text_style(ctx.tokens, "kicker", theme["accent"], align="center")
    total_style = resolve_text_style(ctx.tokens, "hero", theme["accent"], align="center")
    body_style = resolve_text_style(ctx.tokens, "body", theme["muted"], align="center")
    measurements = {
        "kicker": _measure(headline_copy, kicker_style, width, ctx),
        "headline": _measure(format_value(total, fmt), total_style, width, ctx),
        "rows": (width, ctx.tokens.px(112) * len(parsed)),
        "body": _measure(subtitle, body_style, width, ctx),
    }
    layout = ctx.layout.layout("breakdown", measurements)
    # The generic breakdown recipe anchors rows; adapt to the measured count.
    rows_region = layout.region("rows")
    elements: dict[str, Node] = {
        "kicker": text_node("kicker", headline_copy, kicker_style,
                            layout.region("kicker"), ctx.fonts,
                            align="center", valign="bottom"),
        "total": number_node("total", total, layout.region("headline"),
                             ctx.tokens, fmt=fmt, size_role="title",
                             color=theme["accent"], align="center"),
    }
    specs = [_spec("kicker", 3), _spec("total", 9, "display")]
    row_gap = ctx.tokens.space("sm")
    row_h = min(ctx.tokens.px(112), (rows_region.h - row_gap * (len(parsed) - 1))
                / len(parsed))
    max_value = max(item["value"] for item in parsed) or 1
    for index, item in enumerate(parsed):
        region = Rect(rows_region.x, rows_region.y + index * (row_h + row_gap),
                      rows_region.w, row_h)
        group = Node(kind="group", role=f"row-{index}",
                     children=_breakdown_row(ctx, region, item, max_value,
                                             theme, index, fmt))
        group.qa_class = "control"
        elements[f"row-{index}"] = group
        specs.append(_spec(f"row-{index}", 7 - index * 1.2, "control",
                           hint="reveal-right" if index == 0 else "fade-up",
                           order=index))
    if subtitle:
        region = layout.optional("body")
        if region:
            node = text_node("body", subtitle, body_style, region, ctx.fonts,
                             align="center", valign="center")
            if node:
                elements["body"] = node
                specs.append(_spec("body", 4))
    plan = _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "breakdown", "items": parsed,
                         "total": total})
    entry = plan.choreography.entries.get("total")
    if entry:
        _number_in(plan.elements, "total", total, entry, ctx)
    for index in range(len(parsed)):
        role = f"row-{index}"
        entry = plan.choreography.entries.get(role)
        if entry:
            _number_in(plan.elements[role].children, "value", parsed[index]["value"], entry, ctx)
            _progress_child(plan.elements[role], "bar", entry,
                            parsed[index]["value"] / max_value)
    return plan


def _breakdown_row(ctx: SceneContext, region: Rect, item: dict,
                   max_value: float, theme: dict, index: int,
                   fmt: dict | None = None) -> list[Node]:
    panel = panel_node(f"row-panel-{index}", region, ctx.tokens,
                       fill=_card_fill(theme), radius="md", opacity=.96)
    label_style = resolve_text_style(ctx.tokens, "caption",
                                     theme["ink"] if theme["light"] else theme["ink"],
                                     weight="bold")
    value_style = resolve_text_style(ctx.tokens, "subtitle", theme["accent"],
                                     weight="bold")
    inset = ctx.tokens.space("md")
    label = text_node("label", item["label"], label_style,
                      Rect(region.x + inset, region.y + region.h * .12,
                           region.w * .55, region.h * .46), ctx.fonts,
                      valign="center")
    value = number_node("value", item["value"],
                        Rect(region.x + region.w * .52, region.y + region.h * .04,
                             region.w * .40 - inset, region.h * .54),
                        ctx.tokens, fmt=dict(fmt or {}), size_role="subtitle",
                        color=theme["accent"], align="right")
    bar_y = region.y + region.h * .70
    bar_w = region.w - inset * 2
    base_bar = Node(kind="round", role="bar-base",
                    props={"x": region.x + inset, "y": bar_y, "w": bar_w,
                           "h": ctx.tokens.px(7), "r": ctx.tokens.px(4),
                           "fill": mix(theme["base"], theme["ink"], .16)},
                    opacity=.45)
    value_bar = Node(kind="round", role="bar",
                     props={"x": region.x + inset, "y": bar_y,
                            "w": bar_w * item["value"] / max_value,
                            "h": ctx.tokens.px(7), "r": ctx.tokens.px(4),
                            "fill": theme["accent"], "progress": 1.0})
    return [child for child in (panel, label, value, base_bar, value_bar)
            if child is not None]


def _progress_child(node: Node, role: str, entry, target: float = 1.0) -> None:
    for child in node.children:
        if child.role == role:
            animate_progress(child, entry.onset, max(.2, entry.duration * 1.2))
            child.props["target_width"] = float(child.props.get("w", 0))


def build_donut(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    percent = safe_number(scene.get("value", scene.get("percent", 30)))
    headline = _headline(scene) or "MAGAZYN ENERGII"
    subtitle = str(scene.get("subtitle") or _subtitle(scene)
                   or "DO 30% KOSZTÓW")
    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "title", theme["ink"],
                                        align="center", balance=True)
    body_style = resolve_text_style(ctx.tokens, "body", theme["muted"],
                                    align="center")
    measurements = {
        "headline": _measure(headline, headline_style, width, ctx),
        "body": _measure(subtitle, body_style, width, ctx),
    }
    layout = ctx.layout.layout("data-panel", measurements)
    chart = layout.region("chart")
    elements: dict[str, Node] = {
        "headline": text_node("headline", headline, headline_style,
                              layout.region("headline"), ctx.fonts,
                              align="center", valign="center"),
    }
    radius = min(chart.w, chart.h) * .36
    cx, cy = chart.center_x, chart.center_y
    track = Node(kind="ring", role="donut-track",
                 props={"cx": cx, "cy": cy, "r": radius,
                        "width": max(8, radius * .20),
                        "color": mix(theme["base"], theme["ink"], .18)},
                 opacity=.45)
    ring = Node(kind="ring", role="chart",
                props={"cx": cx, "cy": cy, "r": radius,
                       "width": max(8, radius * .20), "color": theme["accent"],
                       "progress": 0.0, "start_angle": -90},
                qa_class="control")
    center_value = number_node(
        "percent", percent, Rect(cx - radius * .7, cy - radius * .30,
                                 radius * 1.4, radius * .56),
        ctx.tokens, fmt={"suffix": "%", "thousands": ""},
        size_role="hero", color=theme["accent"], align="center")
    label_style = TextStyle(max(14, ctx.tokens.px(24)), theme["muted"], "bold",
                            align="center", uppercase=True, tracking=1)
    label = text_node("chart-label", str(scene.get(
        "label", "KOSZTÓW")), label_style,
        Rect(cx - radius * .8, cy + radius * .34, radius * 1.6,
             radius * .30), ctx.fonts, align="center", valign="center")
    visual = Node(kind="group", role="visual",
                  children=[track, ring, center_value, label],
                  qa_class="control")
    elements["visual"] = visual
    if subtitle:
        elements["body"] = text_node("body", subtitle, body_style,
                                     layout.region("body"), ctx.fonts,
                                     align="center", valign="center")
    specs = [_spec("headline", 6), _spec("visual", 10, "display",
                                         hint="scale-focus"),
             _spec("body", 4)]
    plan = _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "donut", "value": percent})
    entry = plan.choreography.entries.get("visual")
    if entry:
        for child in plan.elements["visual"].children:
            if child.role == "chart":
                animate_progress(child, entry.onset, entry.duration * 1.5,
                                 easing="out-quart")
            elif child.role == "percent":
                animate_counter(child, percent, entry.onset,
                                entry.duration * 1.5)
    return plan


def build_comparison(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    headline = _headline(scene) or "PORÓWNANIE"
    columns = scene.get("columns")
    if not isinstance(columns, list) or len(columns) != 2:
        columns = [{"label": "NET-BILLING", "value": 16000},
                   {"label": "NET-METERING", "value": 8000}]
    parsed = [{"label": str(item.get("label", "")),
               "value": safe_number(item.get("value", 0)),
               "suffix": str(item.get("suffix", scene.get("suffix", " zł"))),
               "prefix": str(item.get("prefix", scene.get("prefix", "")))}
              for item in columns]
    subtitle = str(scene.get("subtitle") or _subtitle(scene) or "")
    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "title", theme["ink"],
                                        align="center", balance=True)
    body_style = resolve_text_style(ctx.tokens, "body", theme["muted"],
                                    align="center")
    measurements = {
        "headline": _measure(headline, headline_style, width, ctx),
        "body": _measure(subtitle, body_style, width, ctx),
    }
    layout = ctx.layout.layout("comparison", measurements)
    elements: dict[str, Node] = {
        "headline": text_node("headline", headline, headline_style,
                              layout.region("headline"), ctx.fonts,
                              align="center", valign="center")}
    max_value = max(item["value"] for item in parsed) or 1
    specs = [_spec("headline", 7)]
    for index, item in enumerate(parsed):
        region = layout.region("column-left" if index == 0 else "column-right")
        group = Node(kind="group", role=f"column-{index}",
                     children=_comparison_card(ctx, region, item, max_value,
                                               theme, index),
                     qa_class="control")
        elements[f"column-{index}"] = group
        specs.append(_spec(f"column-{index}", 9 - index, "control",
                           hint="slide-left" if index == 0 else "slide-right"))
    if subtitle:
        region = layout.optional("body")
        if region:
            elements["body"] = text_node("body", subtitle, body_style,
                                         region, ctx.fonts,
                                         align="center", valign="center")
            specs.append(_spec("body", 4))
    plan = _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "comparison", "columns": parsed})
    for index, item in enumerate(parsed):
        entry = plan.choreography.entries.get(f"column-{index}")
        if entry:
            _number_in(plan.elements[f"column-{index}"].children, "value",
                       item["value"], entry, ctx)
            _progress_child(plan.elements[f"column-{index}"], "bar", entry,
                            item["value"] / max_value)
    return plan


def _comparison_card(ctx: SceneContext, region: Rect, item: dict,
                     max_value: float, theme: dict, index: int) -> list[Node]:
    panel = panel_node(f"comparison-panel-{index}", region, ctx.tokens,
                       fill=_card_fill(theme), radius="lg", shadow=True)
    label_style = TextStyle(ctx.tokens.px(28), theme["ink"] if theme["light"]
                            else theme["ink"], "bold", align="center",
                            uppercase=True, tracking=1)
    label = text_node("label", item["label"], label_style,
                      Rect(region.x + region.w * .08, region.y + region.h * .10,
                           region.w * .84, region.h * .14), ctx.fonts,
                      align="center", valign="center")
    value = number_node("value", item["value"],
                        Rect(region.x + region.w * .06, region.y + region.h * .26,
                             region.w * .88, region.h * .30),
                        ctx.tokens,
                        fmt={"suffix": item.get("suffix", " zł"),
                             "prefix": item.get("prefix", ""),
                             "thousands": " "}, size_role="title",
                        color=theme["accent"], align="center")
    bar_w = region.w * .76
    bar_x = region.x + region.w * .12
    bar_y = region.y + region.h * .72
    base = Node(kind="round", role="bar-base",
                props={"x": bar_x, "y": bar_y, "w": bar_w,
                       "h": ctx.tokens.px(10), "r": ctx.tokens.px(5),
                       "fill": mix(theme["base"], theme["ink"], .16)},
                opacity=.5)
    bar = Node(kind="round", role="bar",
               props={"x": bar_x, "y": bar_y,
                      "w": bar_w * item["value"] / max_value,
                      "h": ctx.tokens.px(10), "r": ctx.tokens.px(5),
                      "fill": theme["accent"], "progress": 1.0})
    return [panel, label, value, base, bar]


def build_heat(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    value = safe_number(scene.get("value", 1000))
    fmt = _fmt(scene)
    headline = _headline(scene) or "MAGAZYN CIEPŁA"
    subtitle = str(scene.get("subtitle") or _subtitle(scene) or "")
    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "kicker", theme["ink"],
                                        align="center", weight="bold",
                                        uppercase=True)
    body_style = resolve_text_style(ctx.tokens, "subtitle", theme["muted"],
                                    align="center")
    measurements = {
        "headline": _measure(headline, headline_style, width, ctx),
        "body": _measure(subtitle, body_style, width, ctx),
    }
    layout = ctx.layout.layout("hero-number", measurements, has_visual=True)
    elements: dict[str, Node] = {
        "headline": text_node("headline", headline, headline_style,
                               layout.region("kicker"), ctx.fonts,
                              align="center", valign="bottom",
                              meta={"typography_role": "kicker"}),
    }
    amount_region = layout.region("headline")
    elements["amount"] = number_node(
        "amount", value, amount_region, ctx.tokens, fmt=fmt,
        size_role="hero", color=theme["accent"], align="center")
    visual_region = layout.region("visual")
    size = min(visual_region.w * .46, visual_region.h * .86)
    visual = Node(kind="group", role="visual",
                  children=[icons.heat_waves(visual_region.center_x,
                                             visual_region.center_y,
                                             size, theme["accent"])],
                  qa_class="control")
    elements["visual"] = visual
    if subtitle:
        elements["body"] = text_node("body", subtitle, body_style,
                                     layout.region("body"), ctx.fonts,
                                     align="center", valign="center")
    specs = [_spec("headline", 5), _spec("amount", 9, "display"),
             _spec("visual", 6, "visual", hint="scale-focus"),
             _spec("body", 4)]
    plan = _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "heat", "value": value})
    entry = plan.choreography.entries.get("amount")
    if entry:
        _number_in(plan.elements, "amount", value, entry, ctx)
    return plan


def build_europe(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    value = safe_number(scene.get("value", 2000))
    fmt = _fmt(scene)
    headline = _headline(scene) or "SPRZĘT Z UE"
    subtitle = str(scene.get("subtitle") or _subtitle(scene) or "")
    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "kicker", theme["ink"],
                                        align="center", weight="bold",
                                        uppercase=True)
    body_style = resolve_text_style(ctx.tokens, "subtitle", theme["muted"],
                                    align="center")
    measurements = {
        "headline": _measure(headline, headline_style, width, ctx),
        "body": _measure(subtitle, body_style, width, ctx),
    }
    layout = ctx.layout.layout("hero-number", measurements, has_visual=True)
    elements: dict[str, Node] = {
        "headline": text_node("headline", headline, headline_style,
                               layout.region("kicker"), ctx.fonts,
                              align="center", valign="bottom",
                              meta={"typography_role": "kicker"}),
        "amount": number_node("amount", value, layout.region("headline"),
                              ctx.tokens, fmt=fmt, size_role="hero",
                              color=theme["accent"], align="center"),
    }
    visual_region = layout.region("visual")
    size = min(visual_region.w * .40, visual_region.h * .84)
    eu = icons.eu_stars(visual_region.center_x, visual_region.center_y, size,
                        (0, 51, 153), accent=(255, 204, 0))
    elements["visual"] = Node(kind="group", role="visual", children=[eu],
                              qa_class="control")
    if subtitle:
        elements["body"] = text_node("body", subtitle, body_style,
                                     layout.region("body"), ctx.fonts,
                                     align="center", valign="center")
    specs = [_spec("headline", 5), _spec("amount", 9, "display"),
             _spec("visual", 6, "control", hint="pop-settle"),
             _spec("body", 4)]
    plan = _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "europe", "value": value})
    entry = plan.choreography.entries.get("amount")
    if entry:
        _number_in(plan.elements, "amount", value, entry, ctx)
    visual_entry = plan.choreography.entries.get("visual")
    if visual_entry:
        stars = [child for child in plan.elements["visual"].children[0].children
                 if child.role.startswith("eu-star-")]
        for index, star in enumerate(stars):
            start = visual_entry.onset + index * .035
            star.opacity = 0.0
            star.track("opacity", Track([
                Keyframe(0.0, 0.0), Keyframe(start, 0.0),
                Keyframe(start + .16, 1.0)]))
    return plan


def build_stats(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    headline = _headline(scene) or "LICZBY, KTÓRE MAJĄ ZNACZENIE"
    stats = scene.get("stats") or [
        {"label": "DOTACJA", "value": 16000, "suffix": " zł"},
        {"label": "PREMIA UE", "value": 2000, "suffix": " zł"},
        {"label": "MAGAZYN", "value": 30, "suffix": "%"},
        {"label": "TERMIN", "value": 2027, "suffix": ""},
    ]
    if not isinstance(stats, list) or len(stats) != 4:
        raise ValueError("stat-grid requires exactly four stats")
    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "title", theme["ink"],
                                        align="center", balance=True)
    layout = ctx.layout.layout("stat-grid", {
        "headline": _measure(headline, headline_style, width, ctx)})
    elements: dict[str, Node] = {
        "headline": text_node("headline", headline, headline_style,
                              layout.region("headline"), ctx.fonts,
                              align="center", valign="center")}
    specs = [_spec("headline", 7)]
    for index, item in enumerate(stats):
        region = layout.region(f"stat-{index + 1}")
        value = safe_number(item.get("value", 0))
        fmt = {"suffix": item.get("suffix", ""),
               "prefix": item.get("prefix", ""), "thousands": " "}
        panel = panel_node(f"stat-panel-{index}", region, ctx.tokens,
                           fill=_card_fill(theme), radius="lg", shadow=True)
        number = number_node(f"stat-value-{index}", value,
                             Rect(region.x + region.w * .06,
                                  region.y + region.h * .16,
                                  region.w * .88, region.h * .44),
                             ctx.tokens, fmt=fmt, size_role="title",
                             color=theme["accent"], align="center")
        label_style = TextStyle(ctx.tokens.px(23), theme["ink"]
                                if theme["light"] else theme["muted"],
                                "bold", align="center", uppercase=True,
                                tracking=1)
        label = text_node(f"stat-label-{index}", str(item.get("label", "")),
                          label_style,
                          Rect(region.x + region.w * .08,
                               region.y + region.h * .64,
                               region.w * .84, region.h * .24),
                          ctx.fonts, align="center", valign="center")
        group = Node(kind="group", role=f"stat-{index}",
                     children=[child for child in (panel, number, label)
                               if child], qa_class="control")
        elements[f"stat-{index}"] = group
        specs.append(_spec(f"stat-{index}", 6 - index * .5, "control",
                           hint="pop-settle" if index == 0 else None,
                           order=index))
    plan = _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "stat-grid", "stats": stats})
    for index, item in enumerate(stats):
        entry = plan.choreography.entries.get(f"stat-{index}")
        if entry:
            _number_in(plan.elements[f"stat-{index}"].children,
                       f"stat-value-{index}", safe_number(item.get("value", 0)),
                       entry, ctx)
    return plan
