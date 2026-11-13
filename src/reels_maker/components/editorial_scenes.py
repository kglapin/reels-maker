"""Scene builders for the editorial family."""
from __future__ import annotations

import math
from pathlib import Path

from ..core.scene_graph import Node
from ..design.color import ensure_contrast, mix
from ..layout.engine import Rect
from ..motionkit.keyframes import Keyframe, Track
from ..textkit.typesetter import TextStyle, typeset, typeset_runs
from . import icons
from .base import (BuiltScene, SceneContext, image_node, panel_node,
                   resolve_text_style, rich_text_node, text_node)
from .scene_support import (
    _background, _card_fill, _decor, _external_icon, _finish, _headline,
    _measure, _runs, _spec, _subtitle, _text_elements, _theme, tokens_line,
)



def build_announcement(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    kicker = str(scene.get("kicker", "PROGRAM DOTACYJNY"))
    lines = scene.get("headline")
    if isinstance(lines, dict):
        headline_copy = _headline(scene)
        runs = _runs(scene, ctx.tokens, theme["ink"], theme["accent"])
    else:
        headline_copy = str(lines or "SZCZEGÓŁY\nOFERTY")
        runs = None
    subtitle = str(scene.get("subtitle") or _subtitle(scene)
                   or "INFORMACJE O PROGRAMIE")
    width = ctx.layout.safe.w
    kicker_style = resolve_text_style(ctx.tokens, "kicker", theme["accent"], align="center")
    headline_style = resolve_text_style(ctx.tokens, "display", theme["ink"],
                                        align="center", line_height=.96)
    body_style = resolve_text_style(ctx.tokens, "subtitle", theme["muted"],
                                    align="center", line_height=1.3)
    if runs:
        headline_height = typeset(
            " ".join(run.text for run in runs), headline_style, width,
            ctx.fonts).height
    else:
        headline_height = typeset(headline_copy, headline_style, width,
                                  ctx.fonts).height
    measurements = {
        "headline": (width, headline_height),
        "body": _measure(subtitle, body_style, width, ctx),
    }
    layout = ctx.layout.layout("calendar", measurements)
    elements: dict[str, Node] = {}
    if kicker:
        elements["kicker"] = text_node("kicker", kicker, kicker_style,
                                       layout.region("kicker"), ctx.fonts,
                                       align="center", valign="bottom")
    region = layout.region("headline")
    if runs:
        elements["headline"] = rich_text_node(
            "headline", runs, headline_style, region, ctx.fonts,
            align="center", valign="center")
    else:
        elements["headline"] = text_node("headline", headline_copy,
                                         headline_style, region, ctx.fonts,
                                         align="center", valign="center")
    if scene.get("visual", True) is not False:
        calendar_region = layout.region("visual")
        day = str(scene.get("day", "20"))
        month = str(scene.get("calendar_label", "PAŹDZIERNIKA 2026"))
        card = Node(kind="group", role="visual",
                    children=_calendar_card(ctx, calendar_region, day, month, theme))
        elements["visual"] = card
    if subtitle:
        elements["body"] = text_node("body", subtitle, body_style,
                                     layout.region("body"), ctx.fonts,
                                     align="center", valign="top")
    specs = [_spec("kicker", 3), _spec("headline", 10, "display")]
    if "visual" in elements:
        specs.append(_spec("visual", 5, "control", hint="pop-settle"))
    specs.append(_spec("body", 4))
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "calendar",
                         "day": scene.get("day"),
                         "calendar_label": scene.get("calendar_label")})


def _calendar_card(ctx: SceneContext, region: Rect, day: str, month: str,
                   theme: dict) -> list[Node]:
    card = Rect(region.x, region.y, region.w, region.h)
    children = [panel_node("calendar-panel", card, ctx.tokens,
                           fill=_card_fill(theme),
                           radius="lg", shadow=True)]
    accent = Node(kind="round", role="calendar-band",
                  props={"x": card.x, "y": card.y, "w": card.w,
                         "h": card.h * .16, "r": ctx.tokens.radius("lg"),
                         "fill": theme["accent"]})
    day_style = TextStyle(ctx.tokens.px(150), theme["accent"], "bold",
                          line_height=.9, align="center")
    month_style = TextStyle(ctx.tokens.px(30), theme["ink"] if theme["light"]
                            else theme["ink"], "bold", align="center",
                            uppercase=True, tracking=1.5)
    day_node = text_node("calendar-day", day, day_style,
                         Rect(card.x, card.y + card.h * .20,
                              card.w, card.h * .48), ctx.fonts,
                         align="center", valign="center", fit=True)
    month_node = text_node("calendar-month", month, month_style,
                           Rect(card.x + card.w * .08, card.y + card.h * .70,
                                card.w * .84, card.h * .18), ctx.fonts,
                           align="center", valign="center")
    children.extend([accent, day_node, month_node])
    return children


def build_deadline(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    kicker = str(scene.get("kicker", "TERMIN"))
    date = str(scene.get("date") or _headline(scene) or "—")
    subtitle = str(scene.get("subtitle") or _subtitle(scene) or "")
    width = ctx.layout.safe.w
    kicker_style = resolve_text_style(ctx.tokens, "kicker", theme["accent"], align="center")
    date_style = resolve_text_style(ctx.tokens, "display", theme["ink"],
                                    align="center")
    body_style = resolve_text_style(ctx.tokens, "body", theme["muted"],
                                    align="center")
    measurements = {
        "headline": _measure(date, date_style, width, ctx),
        "body": _measure(subtitle, body_style, width, ctx),
    }
    layout = ctx.layout.layout("timeline", measurements)
    elements: dict[str, Node] = {
        "kicker": text_node("kicker", kicker, kicker_style,
                            layout.region("kicker"), ctx.fonts,
                            align="center", valign="bottom"),
        "headline": text_node("headline", date, date_style,
                              layout.region("headline"), ctx.fonts,
                              align="center", valign="center"),
    }
    specs = [_spec("kicker", 3), _spec("headline", 10, "display")]
    extra_decor: list[Node] = []
    if str(scene.get("timeline_orientation") or "horizontal") == "vertical":
        labels = scene.get("milestones")
        items = labels if isinstance(labels, list) and labels else []
        region = layout.region("timeline")
        count = max(1, len(items))
        rail_x = region.x + ctx.tokens.px(64)
        # A vertical rail needs far more travel than the compact horizontal
        # strip: extend the span downward into free space and stop above the
        # body copy when a subtitle is present.
        if subtitle:
            rail_bottom = layout.region("body").y - ctx.tokens.px(30)
        else:
            rail_bottom = ctx.layout.safe.bottom - ctx.tokens.px(40)
        span_h = max(region.h, rail_bottom - region.y)
        row_h = span_h / count
        rail_top = region.y + row_h * .5
        if items:
            extra_decor.append(Node(
                kind="round", role="timeline-rail",
                props={"x": rail_x - ctx.tokens.px(3), "y": rail_top,
                       "w": ctx.tokens.px(6), "h": span_h - row_h,
                       "r": ctx.tokens.px(3),
                       "fill": mix(theme["base"], theme["ink"], .25)},
                opacity=.55))
        for index, item in enumerate(items):
            cy = rail_top + row_h * index
            accent = index == len(items) - 1
            if isinstance(item, dict):
                label_text = str(item.get("label", ""))
                value_text = str(item.get("value", ""))
            else:
                label_text, value_text = str(item), ""
            text_x = rail_x + ctx.tokens.px(56)
            text_w = region.right - text_x
            children = [
                node for node in (
                    Node(kind="circle", role="milestone-dot",
                         props={"cx": rail_x, "cy": cy,
                                "r": ctx.tokens.px(20 if accent else 14),
                                "fill": (theme["accent"] if accent
                                         else theme["ink"])}),
                    text_node("milestone-label", label_text,
                              TextStyle(ctx.tokens.px(34), theme["muted"],
                                        "bold", uppercase=True, tracking=1.5),
                              Rect(text_x, cy - ctx.tokens.px(72), text_w,
                                   ctx.tokens.px(46)), ctx.fonts,
                              align="left", valign="bottom"),
                    text_node("milestone-value", value_text,
                              TextStyle(ctx.tokens.px(54), theme["ink"],
                                        "bold"),
                              Rect(text_x, cy + ctx.tokens.px(10), text_w,
                                   ctx.tokens.px(74)), ctx.fonts,
                              align="left", valign="top"),
                ) if node is not None]
            role = f"milestone-{index}"
            elements[role] = Node(kind="group", role=role, children=children,
                                  qa_class="control")
            specs.append(_spec(role, 10 - index, "control",
                               hint="pop-settle", order=index))
    else:
        elements["timeline"] = Node(kind="group", role="timeline",
                                    children=_timeline_graphic(
                                        ctx, layout.region("timeline"),
                                        scene.get("milestones"), theme),
                                    qa_class="control")
        specs.append(_spec("timeline", 6, "control", hint="reveal-right"))
    if subtitle:
        elements["body"] = text_node("body", subtitle, body_style,
                                     layout.region("body"), ctx.fonts,
                                     align="center", valign="center")
        specs.append(_spec("body", 4))
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs,
                   decor=extra_decor + _decor(ctx, scene, theme),
                   meta={"component": "timeline", "date": date,
                         "budget_consumption_shown": False})


def _timeline_graphic(ctx: SceneContext, region: Rect,
                      milestones, theme: dict) -> list[Node]:
    labels = milestones if isinstance(milestones, list) and milestones else [
        {"label": "START", "value": "—"},
        {"label": "DZIŚ", "value": "—"},
        {"label": "TERMIN", "value": "—"},
    ]
    y = region.center_y
    # One label column per milestone; centres sit half a column inside the
    # region so the first and last columns cannot leave the safe rectangle.
    step = region.w / max(1, len(labels))
    x0 = region.x + step / 2
    x1 = region.right - step / 2
    children = [Node(kind="round", role="timeline-line",
                     props={"x": x0, "y": y - ctx.tokens.px(2),
                            "w": x1 - x0, "h": ctx.tokens.px(4),
                            "r": ctx.tokens.px(2),
                            "fill": mix(theme["base"], theme["ink"], .25)},
                     opacity=.55)]
    for index, item in enumerate(labels):
        cx = x0 + step * index
        accent = index == len(labels) - 1
        children.append(Node(kind="circle", role=f"timeline-dot-{index}",
                             props={"cx": cx, "cy": y,
                                    "r": ctx.tokens.px(13 if accent else 9),
                                    "fill": theme["accent"] if accent
                                    else theme["ink"]},
                             opacity=1 if accent else .8))
        label_style = TextStyle(ctx.tokens.px(23), theme["muted"], "bold",
                                align="center", uppercase=True, tracking=1)
        value_style = TextStyle(ctx.tokens.px(30), theme["ink"], "bold",
                                align="center")
        if isinstance(item, dict):
            label_text = str(item.get("label", ""))
            value_text = str(item.get("value", ""))
        else:
            label_text, value_text = str(item), ""
        label = text_node(f"timeline-label-{index}", label_text, label_style,
                          Rect(max(region.x, cx - step * .46), y + ctx.tokens.px(24),
                               min(step * .92, region.right - max(region.x, cx - step * .46)),
                               ctx.tokens.px(34)), ctx.fonts,
                          align="center", valign="top")
        value = text_node(f"timeline-value-{index}", value_text, value_style,
                          Rect(max(region.x, cx - step * .46), y - ctx.tokens.px(66),
                               min(step * .92, region.right - max(region.x, cx - step * .46)),
                               ctx.tokens.px(38)), ctx.fonts,
                          align="center", valign="bottom")
        if label:
            children.append(label)
        if value:
            children.append(value)
    return children


def build_urgency(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    headline = _headline(scene) or "DZIAŁAJ TERAZ"
    subtitle = str(scene.get("subtitle") or _subtitle(scene) or "")
    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "display", theme["ink"],
                                        align="center", balance=True)
    body_style = resolve_text_style(ctx.tokens, "subtitle", theme["muted"],
                                    align="center")
    measurements = {
        "headline": _measure(headline, headline_style, width, ctx),
        "body": _measure(subtitle, body_style, width, ctx),
    }
    layout = ctx.layout.layout("stack-center", measurements, has_visual=True)
    elements: dict[str, Node] = {
        "headline": text_node("headline", headline, headline_style,
                              layout.region("headline"), ctx.fonts,
                              align="center", valign="center"),
    }
    region = layout.region("visual")
    size = min(region.w * .44, region.h * .84)
    cy = region.center_y
    hands = Node(kind="group", role="clock-hands", anchor=(region.center_x, cy),
                 children=[
                     Node(kind="line", role="clock-minute",
                          props={"x1": region.center_x, "y1": cy,
                                 "x2": region.center_x,
                                 "y2": cy - size * .23,
                                 "color": theme["accent"],
                                 "width": size * .03, "cap": "round"}),
                     Node(kind="line", role="clock-hour",
                          props={"x1": region.center_x, "y1": cy,
                                 "x2": region.center_x + size * .14,
                                 "y2": cy - size * .10,
                                 "color": theme["accent"],
                                 "width": size * .022, "cap": "round"})])
    hands.track("rotation", Track([
        Keyframe(0.0, 0.0, "smooth"),
        Keyframe(max(.8, ctx.duration * .9), 16.0, "smooth")]))
    face_asset = scene.get("clock_face_asset")
    if isinstance(face_asset, str) and face_asset:
        side = size * .86
        face_rect = Rect(region.center_x - side / 2, cy - side / 2,
                         side, side)
        face = image_node("clock-face", face_asset, face_rect,
                          qa_class="visual")
        face.anchor = (region.center_x, cy)
        face_children = [face]
    else:
        face_children = [icons.clock(region.center_x, cy, size,
                                     theme["ink"])]
    clock = Node(kind="group", role="visual",
                 children=[*face_children, hands],
                 qa_class="control")
    elements["visual"] = clock
    if subtitle:
        elements["body"] = text_node("body", subtitle, body_style,
                                     layout.region("body"), ctx.fonts,
                                     align="center", valign="center")
    specs = [_spec("headline", 10, "display", hint="pop-settle"),
             _spec("visual", 5, "visual", hint="scale-focus"),
             _spec("body", 4)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "clock"})


def build_cta(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    headline = _headline(scene) or "SKONTAKUJ SIĘ"
    phone = str(scene.get("phone", "CONTACT"))
    line_one = str(scene.get("line_one", "SPRAWDŹ DOTACJĘ"))
    line_two = str(scene.get("line_two", ""))
    website = str(scene.get("website", "example.com"))
    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "title", theme["ink"],
                                        align="center", balance=True)
    button_text = ensure_contrast(theme["surface"], theme["accent"], 4.5)
    phone_size = int(scene.get("phone_size", 72))
    if not 24 <= phone_size <= 220:
        raise ValueError("phone_size must be between 24 and 220 px")
    phone_style = TextStyle(ctx.tokens.px(phone_size), button_text, "bold",
                            align="center")
    body_style = resolve_text_style(ctx.tokens, "body", theme["muted"],
                                    align="center")
    measurements = {
        "headline": _measure(headline, headline_style, width, ctx),
        "body": _measure(line_one, body_style, width, ctx),
    }
    layout = ctx.layout.layout("cta-panel", measurements)
    elements: dict[str, Node] = {
        "headline": text_node("headline", headline, headline_style,
                              layout.region("headline"), ctx.fonts,
                              align="center", valign="center")}
    card_region = layout.region("cta")
    panel = panel_node("cta-panel", card_region, ctx.tokens,
                       fill=theme["accent"], radius="lg", shadow=True)
    tall_phone = phone_size > 96
    phone_node = Node(kind="text", role="phone", props={
        "x": card_region.x + ctx.tokens.space("md"),
        "y": card_region.y + card_region.h * (.20 if tall_phone else .30),
        "w": card_region.w - ctx.tokens.space("md") * 2,
        "h": card_region.h * (.46 if tall_phone else .32),
        "block": typeset(phone, phone_style,
                         card_region.w - ctx.tokens.space("md") * 2,
                         ctx.fonts),
        "align": "center", "color": theme["surface"],
        "size": phone_style.size, "weight": "bold",
        "tracking_offset": 0.0},
        qa_class="text", meta={"text": phone})
    tag_style = TextStyle(ctx.tokens.px(26), button_text, "bold",
                          align="center", uppercase=True, tracking=1.5)
    tag = text_node("cta-tag", line_one, tag_style,
                    Rect(card_region.x + ctx.tokens.space("md"),
                         card_region.y + card_region.h * (.68 if tall_phone else .66),
                         card_region.w - ctx.tokens.space("md") * 2,
                         card_region.h * (.18 if tall_phone else .20)), ctx.fonts,
                    align="center", valign="center", fit=False)
    elements["cta"] = Node(kind="group", role="cta",
                           children=[panel, phone_node, tag],
                           qa_class="control")
    footer_text = line_two or website
    elements["body"] = text_node("body", footer_text, body_style,
                                  layout.region("body"), ctx.fonts,
                                  align="center", valign="center")
    logo_value = scene.get("logo")
    if logo_value:
        logo_path = Path(str(logo_value))
        if not logo_path.is_absolute() and ctx.assets is not None:
            logo_path = Path(ctx.assets.brand_root) / logo_path
        if not logo_path.is_file():
            raise ValueError(f"Configured CTA logo does not exist: {logo_path}")
        from PIL import Image
        with Image.open(logo_path) as logo_image:
            aspect = logo_image.width / max(1, logo_image.height)
        logo_w = min(ctx.layout.safe.w * .48, ctx.tokens.px(360))
        logo_h = logo_w / max(.1, aspect)
        logo_rect = Rect(ctx.layout.safe.center_x - logo_w / 2,
                         ctx.layout.safe.bottom - logo_h - ctx.tokens.space("md"),
                         logo_w, logo_h)
        elements["logo"] = image_node("logo", str(logo_path), logo_rect,
                                      meta={"asset_role": "brand-logo"})
    specs = [_spec("headline", 8), _spec("cta", 10, "control",
                                           hint="pop-settle"),
             _spec("body", 4)]
    if "logo" in elements:
        specs.append(_spec("logo", 2, "decor"))
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "cta", "phone": phone,
                         "website": website})


def build_cta_minimal(ctx: SceneContext, scene: dict) -> BuiltScene:
    """Minimalist closing card: kick, phone, contact lines, nothing else.

    No panel, no photo, no logo — a centered stack on the plain brand
    background. The phone number carries the single entrance motion.
    """
    theme = _theme(ctx, scene)
    kicker = str(scene.get("kicker") or "")
    phone = str(scene.get("phone") or "")
    website = str(scene.get("website") or "")
    email = str(scene.get("email") or "")
    contact = "\n".join(part for part in (website, email) if part)
    width = ctx.layout.safe.w
    kicker_style = TextStyle(ctx.tokens.px(28), theme["muted"], "bold",
                             align="center", uppercase=True, tracking=2.0)
    phone_size = ctx.tokens.px(88)
    probe = TextStyle(phone_size, theme["ink"], "bold", align="center")
    # Long numbers shrink to hold 100 px side margins on both sides.
    over = _measure(phone, probe, width, ctx)[0]
    if over > width - 200:
        phone_size = max(ctx.tokens.px(48),
                         int(phone_size * (width - 200) / over))
    phone_style = TextStyle(phone_size, theme["ink"], "bold",
                            align="center")
    body_style = resolve_text_style(ctx.tokens, "body", theme["muted"],
                                    align="center")
    layout = ctx.layout.layout("stack-center", {
        "kicker": _measure(kicker, kicker_style, width, ctx),
        "headline": _measure(phone, phone_style, width, ctx),
        "body": _measure(contact, body_style, width, ctx)})
    elements: dict[str, Node] = {
        "kicker": text_node("kicker", kicker, kicker_style,
                            layout.region("kicker"), ctx.fonts,
                            align="center", valign="center"),
        "headline": text_node("headline", phone, phone_style,
                              layout.region("headline"), ctx.fonts,
                              align="center", valign="center"),
        "body": text_node("body", contact, body_style,
                          layout.region("body"), ctx.fonts,
                          align="center", valign="center"),
    }
    specs = [_spec("kicker", 2), _spec("headline", 10, "control",
                                       hint="pop-settle"),
             _spec("body", 4)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=[],
                   meta={"component": "cta-minimal", "phone": phone,
                         "website": website})


def build_spotlight(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    # A photo is mandatory for this composition; fall back to the scene photo.
    if not (scene.get("photo") or (isinstance(scene.get("background"), dict)
                                   and scene["background"].get("asset"))):
        scene = {**scene, "background": {
            "kind": "gradient",
            "from": "#101A14", "to": "#1E3326"}}
    theme = _theme(ctx, scene)
    width = ctx.layout.safe.w
    align = str(scene.get("align") or "left")
    # Measure with the same role/line-height _text_elements will render, so
    # the allocated region matches the real rich-text block.
    headline_style = resolve_text_style(ctx.tokens, "hero", theme["ink"],
                                        align=align, balance=False,
                                        line_height=tokens_line(ctx))
    runs = _runs(scene, ctx.tokens, theme["ink"], theme["accent"])
    if runs:
        block = typeset_runs(runs, headline_style, width, ctx.fonts)
        headline_measure = (block.width, block.height)
    else:
        headline_measure = _measure(_headline(scene), headline_style,
                                    width, ctx)
    body_style = resolve_text_style(ctx.tokens, "body", theme["muted"],
                                    line_height=1.32)
    measurements = {
        "headline": headline_measure,
        "body": _measure(_subtitle(scene), body_style, width, ctx),
    }
    layout = ctx.layout.layout("spotlight", measurements)
    elements = _text_elements(ctx, scene, layout, theme,
                              headline_role="hero", align=align)
    specs = [_spec("kicker", 3), _spec("headline", 9, "display"),
             _spec("body", 4)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "spotlight"})


def build_statement(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    width = ctx.layout.safe.w
    headline_role = str(scene.get("headline_size_role") or "display")
    headline_style = resolve_text_style(
        ctx.tokens, headline_role, theme["ink"],
        align="center", balance=True,
        line_height=scene.get("headline_line_height", .98))
    body_style = resolve_text_style(ctx.tokens, "subtitle", theme["muted"],
                                    align="center")
    headline = _headline(scene) or _subtitle(scene)
    body = _subtitle(scene) if _headline(scene) else ""
    measurements = {
        "headline": _measure(headline, headline_style, width, ctx),
        "body": _measure(body, body_style, width, ctx),
    }
    layout = ctx.layout.layout("statement", measurements)
    lift = scene.get("lift")
    if lift is not None:
        if isinstance(lift, bool) or not isinstance(lift, (int, float)) \
                or not math.isfinite(float(lift)) \
                or not -0.5 <= float(lift) <= 0.5:
            raise ValueError("statement lift must be a finite number in [-0.5, 0.5]")
        shift = -float(lift) * ctx.layout.safe.h
        for name in ("headline", "body"):
            rect = layout.regions.get(name)
            if rect is not None:
                layout.regions[name] = Rect(
                    rect.x, max(ctx.layout.safe.y, rect.y + shift),
                    rect.w, rect.h)
    elements: dict[str, Node] = {}
    runs = _runs(scene, ctx.tokens, theme["ink"], theme["accent"])
    if runs:
        elements["headline"] = rich_text_node(
            "headline", runs, headline_style, layout.region("headline"),
            ctx.fonts, align="center", valign="center")
    else:
        elements["headline"] = text_node(
            "headline", headline, headline_style, layout.region("headline"),
            ctx.fonts, align="center", valign="center")
    if body:
        elements["body"] = text_node("body", body, body_style,
                                     layout.region("body"), ctx.fonts,
                                     align="center", valign="center")
    specs = [_spec("headline", 10, "display"), _spec("body", 5)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "statement"})


def build_checklist(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    headline = _headline(scene) or "KOLEJNE KROKI"
    items = scene.get("items") or ["Pierwsza kluczowa korzyść",
                                   "Druga kluczowa korzyść",
                                   "Trzecia kluczowa korzyść"]
    if not isinstance(items, list) or not items:
        raise ValueError("checklist items must be a nonempty list")
    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "title", theme["ink"],
                                        balance=True)
    measurements = {"headline": _measure(headline, headline_style, width, ctx)}
    layout = ctx.layout.layout("checklist", measurements)
    headline_region = layout.region("headline")
    # Font ink can extend slightly above its line box. Keep the checklist title
    # a few pixels inside the authored Reels content boundary instead of
    # positioning the glyph outline directly against the platform-safe edge.
    headline_region = Rect(headline_region.x, headline_region.y + 2,
                           headline_region.w, max(1, headline_region.h - 2))
    elements: dict[str, Node] = {
        "headline": text_node("headline", headline, headline_style,
                              headline_region, ctx.fonts,
                              valign="center")}
    specs = [_spec("headline", 8)]
    list_region = layout.region("list")
    row_h = min(ctx.tokens.px(118), list_region.h / max(1, len(items)))
    rows_h = row_h * len(items)
    rows_top = list_region.y + max(0.0, (list_region.h - rows_h) / 2)
    item_style = resolve_text_style(ctx.tokens, "subtitle", theme["ink"],
                                    line_height=1.2)
    for index, item in enumerate(items):
        region = Rect(list_region.x, rows_top + index * row_h,
                      list_region.w, row_h)
        icon_size = min(row_h * .58, region.w * .10)
        check = (_external_icon(scene, "check",
                                region.x + icon_size / 2 + ctx.tokens.px(6),
                                region.center_y, icon_size, theme["accent"])
                 or icons.check(region.x + icon_size / 2 + ctx.tokens.px(6),
                                region.center_y, icon_size, theme["accent"]))
        # Match the check's left inset and reserve a full design-token gap.
        left_inset = ctx.tokens.px(6)
        text_x = region.x + left_inset + icon_size + ctx.tokens.space("md")
        text_region = Rect(text_x, region.y + row_h * .12,
                           max(1, region.right - text_x), row_h * .76)
        label = text_node(f"item-{index}", str(item), item_style, text_region,
                          ctx.fonts, valign="center")
        group = Node(kind="group", role=f"item-{index}",
                     children=[check, label], qa_class="control")
        elements[f"item-{index}"] = group
        specs.append(_spec(f"item-{index}", 6 - index * .7, "support",
                           order=index))
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "checklist", "items": list(items)})


def build_pillars(ctx: SceneContext, scene: dict) -> BuiltScene:
    """Centered 2x2 icon grid with short captions.

    Icons come from one pinned pack (``icon_library`` + ``icon_names``
    overrides); every pillar shares the same stroke family and accent color.
    """
    theme = _theme(ctx, scene)
    headline = _headline(scene) or "ATUTY OFERTY"
    items = scene.get("items") or []
    if (not isinstance(items, list) or len(items) != 4
            or not all(isinstance(item, str) and item.strip() for item in items)):
        raise ValueError("pillars requires exactly four non-empty items")
    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "title", theme["ink"],
                                        align="center", balance=True)
    layout = ctx.layout.layout("pillars", {
        "headline": _measure(headline, headline_style, width, ctx)})
    caption_style = resolve_text_style(ctx.tokens, "subtitle", theme["ink"],
                                       align="center", line_height=1.2)
    elements: dict[str, Node] = {
        "headline": text_node("headline", headline, headline_style,
                              layout.region("headline"), ctx.fonts,
                              align="center", valign="center"),
    }
    specs = [_spec("headline", 7)]
    for index, item in enumerate(items):
        region = layout.region(f"pillar-{index + 1}")
        icon_size = min(region.h * .36, region.w * .34)
        icon_cy = region.y + region.h * .30
        icon = (_external_icon(scene, f"pillar-{index}", region.center_x,
                               icon_cy, icon_size, theme["accent"])
                or icons.check(region.center_x, icon_cy, icon_size,
                               theme["accent"]))
        caption = text_node(f"pillar-caption-{index}", str(item).upper(),
                            caption_style,
                            Rect(region.x, region.y + region.h * .52,
                                 region.w, region.h * .44),
                            ctx.fonts, align="center", valign="center")
        elements[f"pillar-{index}"] = Node(
            kind="group", role=f"pillar-{index}",
            children=[icon, caption], qa_class="control")
        specs.append(_spec(f"pillar-{index}", 6 - index * .5, "control",
                           hint="pop-settle" if index == 0 else None,
                           order=index))
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "pillars", "items": list(items)})


def build_energy(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    headline = _headline(scene) or "KROK PO KROKU"
    subtitle = _subtitle(scene) or ""
    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "title", theme["ink"],
                                        balance=True)
    body_style = resolve_text_style(ctx.tokens, "body", theme["muted"],
                                    align="center")
    layout = ctx.layout.layout("energy-flow", {
        "headline": _measure(headline, headline_style, width, ctx),
        "body": _measure(subtitle, body_style, width, ctx)})
    elements: dict[str, Node] = {
        "headline": text_node("headline", headline, headline_style,
                              layout.region("headline"), ctx.fonts,
                              valign="center")}
    diagram = layout.region("diagram")
    cy = diagram.center_y
    # Keep glyphs and arrows in separate, non-overlapping slots.  The old
    # 22%-width glyphs left only 4% for a 13.6%-width arrow: collisions.
    xs = [diagram.x + diagram.w * ratio for ratio in (.12, .37, .63, .88)]
    slot = min(xs[i + 1] - xs[i] for i in range(3))
    clearance = max(ctx.tokens.space("sm"), diagram.w * .018)
    size = min(diagram.w * .125, diagram.h * .20,
               (slot - 2 * clearance) * .60)
    arrow_size = min(diagram.w * .065, slot - size - 2 * clearance)
    if arrow_size <= 0:
        raise ValueError("Energy diagram too narrow for icons and arrows")
    sun = (_external_icon(scene, "sun", xs[0], cy, size, theme["accent"])
           or icons.sun(xs[0], cy, size, theme["accent"]))
    panel = (_external_icon(scene, "house", xs[1], cy, size, theme["ink"])
             or icons.house(xs[1], cy, size, theme["ink"]))
    battery = (_external_icon(scene, "battery", xs[2], cy, size * 1.05,
                              theme["accent"])
               or icons.battery(xs[2], cy, size * 1.05, theme["accent"],
                                shell=theme["ink"], level=.8))
    house = (_external_icon(scene, "house", xs[3], cy, size, theme["ink"])
             or icons.house(xs[3], cy, size, theme["ink"]))
    arrows = [(_external_icon(scene, "arrow",
                             (xs[i] + xs[i + 1]) / 2, cy, arrow_size,
                             theme["muted"])
               or icons.arrow((xs[i] + xs[i + 1]) / 2, cy, arrow_size,
                              theme["muted"])) for i in range(3)]
    group = Node(kind="group", role="diagram",
                 children=[sun, panel, battery, house] + arrows,
                 qa_class="control")
    elements["diagram"] = group
    if subtitle:
        elements["body"] = text_node("body", subtitle, body_style,
                                     layout.region("body"), ctx.fonts,
                                     align="center", valign="center")
    specs = [_spec("headline", 7),
             _spec("diagram", 9, "display", hint="mask-rise"),
             _spec("body", 4)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "energy-flow"})


def build_quote(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    quote = _headline(scene) or "„Energia, którą już masz, może pracować dłużej.”"
    attribution = _subtitle(scene) or ""
    width = ctx.layout.safe.w
    quote_style = resolve_text_style(ctx.tokens, "title", theme["ink"],
                                     align="center", balance=True,
                                     line_height=1.18)
    body_style = resolve_text_style(ctx.tokens, "body", theme["muted"],
                                    align="center")
    layout = ctx.layout.layout("quote", {
        "headline": _measure(quote, quote_style, width, ctx),
        "body": _measure(attribution, body_style, width, ctx)})
    mark_style = TextStyle(ctx.tokens.px(150), theme["accent"], "bold",
                           align="center")
    mark_cfg = scene.get("quote_mark")
    if isinstance(mark_cfg, dict):
        mark_rect = Rect(ctx.width * float(mark_cfg.get("x", 0.0)),
                         ctx.height * float(mark_cfg.get("y", 0.0)),
                         ctx.width * float(mark_cfg.get("w", 0.16)),
                         ctx.height * float(mark_cfg.get("h", 0.16)))
    else:
        mark_rect = Rect(ctx.layout.safe.x, ctx.layout.safe.y,
                         ctx.tokens.px(180), ctx.tokens.px(180))
    mark = text_node("quote-mark", "„", mark_style, mark_rect, ctx.fonts,
                     valign="top")
    elements: dict[str, Node] = {
        "headline": text_node("headline", quote, quote_style,
                              layout.region("headline"), ctx.fonts,
                              align="center", valign="center")}
    if mark:
        elements["quote-mark"] = mark
    if attribution:
        elements["body"] = text_node("body", attribution, body_style,
                                     layout.region("body"), ctx.fonts,
                                     align="center", valign="center")
    specs = [_spec("quote-mark", 2, "decor", hint="fade-up"),
             _spec("headline", 10, "display"),
             _spec("body", 5)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "quote"})
