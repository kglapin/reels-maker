"""Scene compositions built from measured content, not fixed coordinates.

Legacy kinetic scene ``type`` values remain valid. New manifests can opt into
any composition directly and provide richer component data. A scene is built
once into a retained graph; the renderer and QA then sample that same graph at
different timestamps, so what is checked is exactly what is shown.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

from ..core.scene_graph import Node
from ..design.color import (
    darken, ensure_contrast, lighten, mix, parse_hex, relative_luminance,
)
from ..design.tokens import DesignTokens
from ..layout.engine import Rect
from ..motionkit.choreography import ElementSpec
from ..motionkit.keyframes import Keyframe, Track
from ..motionkit.presets import apply_entrance, apply_exit
from ..textkit.typesetter import Run, TextBlock, TextStyle, fit_text, typeset
from . import icons
from .base import (
    BuiltScene, SceneContext, animate_counter, animate_progress, format_value,
    image_node, measure_text, number_node, panel_node, resolve_text_style, rich_text_node,
    rule_node, safe_number, text_node, video_node,
)

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


def _headline(scene: dict) -> str:
    value = scene.get("headline", scene.get("title", ""))
    if isinstance(value, dict):
        return " ".join(str(run.get("text", "")) for run in value.get("runs", []))
    return str(value or "")


def _subtitle(scene: dict) -> str:
    return str(scene.get("body") or scene.get("subtitle") or "")


def _runs(scene: dict, tokens: DesignTokens, ink, accent) -> list[Run] | None:
    value = scene.get("headline")
    if not isinstance(value, dict) or "runs" not in value:
        return None
    runs = []
    for item in value["runs"]:
        colour = {"white": ink, "accent": accent,
                  "muted": tokens.palette.muted}.get(
                      item.get("color", "white"), ink)
        runs.append(Run(str(item.get("text", "")),
                        float(item.get("scale", 1.0)), colour,
                        item.get("weight", "bold"),
                        bool(item.get("break_before", False)),
                        item.get("effect")))
    return runs


def _fmt(scene: dict, suffix: str = " zł",
         decimals: int = 0) -> dict:
    raw = scene.get("format")
    if isinstance(raw, dict):
        return dict(raw)
    return {"suffix": scene.get("suffix", suffix),
            "prefix": scene.get("prefix", ""),
            "decimals": scene.get("decimals", decimals),
            "thousands": " "}


def _theme(ctx: SceneContext, scene: dict) -> dict:
    palette = ctx.tokens.palette
    background = scene.get("background") or {}
    kind = background.get("kind") if isinstance(background, dict) else None
    if kind == "solid":
        base = parse_hex(background.get("color", "#101A14"))
    elif kind == "gradient":
        base = parse_hex(background.get("from", background.get("color", "#101A14")))
    elif scene.get("photo") or (isinstance(background, dict)
                                and background.get("asset")):
        # Photography is treated as a dark editorial surface unless the scene
        # explicitly opts into a light treatment. The brand's page background
        # is not the luminance of the actual footage.
        base = (14, 22, 17)
    else:
        base = palette.background
    light = relative_luminance(base) > .46
    if scene.get("theme") == "light":
        light = True
    elif scene.get("theme") == "dark":
        light = False
    photo = bool(scene.get("photo") or (isinstance(background, dict)
                                        and background.get("asset")))
    if light:
        ink = darken(base, .88) if relative_luminance(base) > .25 else (18, 30, 22)
        muted = mix(ink, base, .38)
        accent = ensure_contrast(palette.accent, base, 4.5)
        surface = palette.surface if relative_luminance(palette.surface) > .7 else (255, 255, 255)
        kicker = accent
        scrim = 0.0
    else:
        ink = (255, 255, 255)
        muted = lighten(ink, .22)
        accent = ensure_contrast(palette.accent, base, 4.5)
        surface = palette.surface
        # Accent green cannot be guaranteed against arbitrary photography.
        # A white kicker plus a real scrim keeps the label legible.
        kicker = ink if photo else accent
        scrim = .62 if photo else (.55 if ctx.tokens.backdrop != "none" else .15)
    return {"light": light, "base": base, "ink": ink, "muted": muted,
            "accent": accent, "kicker": kicker, "surface": surface,
            "scrim": scrim, "photo": photo}


def _background(ctx: SceneContext, scene: dict, theme: dict) -> dict:
    palette = ctx.tokens.palette
    config = scene.get("background")
    if not isinstance(config, dict):
        config = {}
    photo = scene.get("photo") or config.get("asset") or config.get("photo")
    if photo:
        camera = config.get("camera") or scene.get("camera") or {}
        if isinstance(camera, str):
            camera = {"direction": camera}
        return {
            "kind": "photo",
            "asset": photo,
            "video_source": scene.get("photo_source") or config.get("video_source"),
            "time": scene.get("photo_time", config.get("time", 0)),
            "camera": {
                "direction": camera.get("direction", "push-in"),
                "intensity": camera.get("intensity", ctx.tokens.motion.camera_drift),
            },
            "scrim": config.get("scrim", theme["scrim"]),
            "tint": config.get("tint"),
            "blur": config.get("blur", 0),
        }
    kind = config.get("kind", "gradient" if not theme["light"] else "solid")
    if kind == "solid":
        return {"kind": "solid", "color": config.get(
            "color", theme["base"])}
    start = config.get("from", theme["base"])
    end = config.get("to", mix(theme["base"], theme["accent"],
                              .10 if not theme["light"] else .04))
    return {"kind": "gradient", "from": start, "to": end,
            "angle": config.get("angle", 90)}


def _decor(ctx: SceneContext, scene: dict, theme: dict) -> list[Node]:
    # Editorial default: no automatically injected ornaments. Decorative
    # bars, dots, rings and floating blobs must be an explicit art-direction
    # choice, never a scene-index-dependent template flourish.
    if scene.get("decor") is not True:
        return []
    index = ctx.scene_index
    w, h = ctx.width, ctx.height
    accent = theme["accent"]
    pattern = index % 4
    nodes: list[Node] = []
    if pattern == 0:
        radius = min(w, h) * .52
        nodes.append(Node(kind="circle", role="decor-orb",
                          props={"cx": w * .94, "cy": h * .10, "r": radius,
                                 "fill": accent},
                          opacity=.055, qa_class="decor"))
    elif pattern == 1:
        nodes.append(Node(kind="rect", role="decor-rule",
                          props={"x": ctx.tokens.space("lg"), "y": h * .12,
                                 "w": ctx.tokens.px(5), "h": h * .26,
                                 "fill": accent},
                          opacity=.55, qa_class="decor"))
        nodes.append(Node(kind="circle", role="decor-dot",
                          props={"cx": w - ctx.tokens.space("lg"),
                                 "cy": h - ctx.tokens.space("xl"),
                                 "r": ctx.tokens.px(7), "fill": accent},
                          opacity=.7, qa_class="decor"))
    elif pattern == 2:
        size = min(w, h) * .70
        nodes.append(Node(kind="circle", role="decor-ring",
                          props={"cx": w * .08, "cy": h * .92, "r": size * .5,
                                 "width": ctx.tokens.px(2), "color": accent},
                          opacity=.12, qa_class="decor"))
    else:
        nodes.append(Node(kind="round", role="decor-block",
                          props={"x": -w * .06, "y": h * .78,
                                 "w": w * .34, "h": ctx.tokens.px(10),
                                 "r": ctx.tokens.px(5), "fill": accent},
                          opacity=.25, qa_class="decor"))
    return nodes


def _measure(copy: str, style: TextStyle, width: float,
             ctx: SceneContext) -> tuple[float, float]:
    return measure_text(copy, style, width, ctx.fonts)


def _text_elements(ctx: SceneContext, scene: dict, layout, theme: dict,
                   *, headline_role: str = "title",
                   align: str = "left",
                   include_kicker: bool = True,
                   include_body: bool = True,
                   body_role: str = "body",
                   rich: bool = True) -> dict[str, Node]:
    elements: dict[str, Node] = {}
    if include_kicker and scene.get("kicker"):
        style = resolve_text_style(ctx.tokens, "kicker",
                                   theme.get("kicker", theme["accent"]),
                                   align=align)
        node = text_node("kicker", str(scene["kicker"]), style,
                         layout.region("kicker"), ctx.fonts, align=align,
                         valign="bottom")
        if node:
            elements["kicker"] = node
    headline = _headline(scene)
    if headline:
        region = layout.optional("headline")
        if region:
            runs = _runs(scene, ctx.tokens, theme["ink"], theme["accent"]) if rich else None
            if runs:
                base = resolve_text_style(ctx.tokens, headline_role,
                                          theme["ink"], align=align,
                                          line_height=tokens_line(ctx),
                                          balance=False)
                elements["headline"] = rich_text_node(
                    "headline", runs, base, region, ctx.fonts,
                    align=align, valign="center")
            else:
                style = resolve_text_style(
                    ctx.tokens, headline_role, theme["ink"], align=align,
                    balance=len(headline) < 70,
                    line_height=tokens_line(ctx))
                node = text_node("headline", headline, style, region,
                                 ctx.fonts, align=align, valign="center")
                if node:
                    elements["headline"] = node
    if include_body and _subtitle(scene):
        region = layout.optional("body")
        if region:
            style = resolve_text_style(ctx.tokens, body_role, theme["muted"],
                                       align=align, line_height=1.32)
            node = text_node("body", _subtitle(scene), style, region,
                             ctx.fonts, align=align, valign="center")
            if node:
                elements["body"] = node
    return elements


def tokens_line(ctx: SceneContext) -> float:
    return ctx.tokens.typography.line_height


def _spec(role: str, weight: float, kind: str = "support",
          hint: str | None = None, order: int = 0) -> ElementSpec:
    return ElementSpec(role, weight=weight, kind=kind, hint=hint, order=order)


def _external_icon(scene: dict, key: str, cx: float, cy: float,
                   size: float, color, *, role: str | None = None) -> Node | None:
    """Resolve scene-selected licensed packs without drawing custom paths.

    Explicit icon_library activates the provider. icon_names overrides the
    finite semantic mapping; pack-specific icon_style selects a pinned variant.
    """
    library = scene.get("icon_library")
    if not library:
        return None
    from ..icon_library import DEFAULT_STYLES, SEMANTIC_ICONS

    overrides = scene.get("icon_names") or {}
    if not isinstance(overrides, dict):
        raise ValueError("icon_names must be a dictionary")
    name = str(overrides.get(key) or SEMANTIC_ICONS.get(library, SEMANTIC_ICONS["lucide"])[key])
    if library == "material_symbols" and not name.startswith("web/"):
        name = "web/" + name.replace("-", "_")
    style = scene.get("icon_style", DEFAULT_STYLES.get(library, "outline"))
    rgb = tuple(color)
    return Node(kind="icon", role=role or key, qa_class="decor",
                props={"x": cx - size / 2, "y": cy - size / 2,
                       "w": size, "h": size, "size": size,
                       "library": library, "name": name,
                       "style": style,
                       "weight": scene.get("icon_weight", 400),
                       "fill": scene.get("icon_fill", False),
                       "grade": scene.get("icon_grade", 0),
                       "optical_size": scene.get("icon_optical_size", 24),
                       "color": "#{:02X}{:02X}{:02X}".format(*rgb),
                       "stroke_width": scene.get("icon_stroke_width", 0)},
                meta={"icon_library": library, "icon_name": name})


def _extra_icons(ctx: SceneContext, scene: dict, theme: dict) -> list[Node]:
    """Place arbitrary named assets in the scene using normalized coordinates."""
    config = scene.get("icon_assets") or []
    if not isinstance(config, list):
        raise ValueError("icon_assets must be a list")
    nodes = []
    for index, item in enumerate(config):
        if not isinstance(item, dict):
            raise ValueError("Every icon_assets entry must be an object")
        library = str(item.get("library", scene.get("icon_library", "lucide")))
        name = str(item.get("name", ""))
        if library == "material_symbols" and not name.startswith("web/"):
            name = "web/" + name.replace("-", "_")
        from ..icon_library import DEFAULT_STYLES
        size = float(item.get("size", .10))
        x = float(item.get("x", .5))
        y = float(item.get("y", .5))
        if not (0.02 <= size <= 0.70 and 0 <= x <= 1 and 0 <= y <= 1):
            raise ValueError("icon_assets coordinates must be 0..1 and size .02..70")
        px = size * ctx.width
        colour_name = item.get("color", "accent")
        color = theme.get(colour_name) if isinstance(colour_name, str) else None
        if color is None:
            from ..design.color import parse_hex
            color = parse_hex(str(colour_name))
        rotation = item.get("rotation", 0)
        if isinstance(rotation, bool) or not isinstance(rotation, (int, float)) \
                or not math.isfinite(rotation) or not -35 <= rotation <= 35:
            raise ValueError("icon_assets rotation must be finite and between -35 and 35 degrees")
        rotation_motion = item.get("rotation_motion")
        if rotation_motion is not None and rotation != 0:
            raise ValueError("icon_assets cannot combine static rotation and rotation_motion")
        node = Node(kind="icon", role=f"asset-icon-{index}",
                    props={"library": library, "name": name,
                           "style": item.get("style", DEFAULT_STYLES.get(library, "outline")),
                           "weight": item.get("weight", scene.get("icon_weight", 400)),
                           "fill": item.get("fill", scene.get("icon_fill", False)),
                           "grade": item.get("grade", scene.get("icon_grade", 0)),
                           "optical_size": item.get("optical_size", scene.get("icon_optical_size", 24)),
                           "x": x * ctx.width - px / 2,
                           "y": y * ctx.height - px / 2,
                           "w": px, "h": px, "size": px,
                           "color": "#{:02X}{:02X}{:02X}".format(*color),
                           "stroke_width": item.get("stroke_width", 0)},
                    rotation=float(rotation), qa_class="decor",
                    meta={"icon_library": library, "icon_name": name})
        if rotation_motion is not None:
            from ..motionkit.editorial_rotation import rotation_track
            node.track("rotation", rotation_track(rotation_motion, ctx.duration, role="icon"))
            node.meta["editorial_rotation"] = {
                "family": rotation_motion.get("family", "tilt-settle"),
                "reason": rotation_motion.get("reason", "explicit art direction"),
            }
        nodes.append(node)
    return nodes


def _icon_collisions(icon: Node, occupied: list[Node], gap: float) -> list[str]:
    """Collision detection on static layout bounds, excluding panel backgrounds."""
    from ..core.scene_graph import boxes_overlap
    bounds = icon.base_bounds()
    if bounds is None:
        return []
    clashes = []
    for node in occupied:
        if node.kind not in ("icon", "text", "number"):
            continue
        other = node.base_bounds()
        if other is not None and boxes_overlap(bounds, other, padding=gap):
            clashes.append(node.role)
    return clashes


def _validate_icon_spacing(ctx: SceneContext, nodes: list[Node]) -> None:
    """Fail before rendering when icon glyphs collide with text or each other."""
    leaves = [n for root in nodes for n in root.flatten()
              if n.kind in ("icon", "text", "number")]
    gap = max(2.0, ctx.tokens.space("xs") * .5)
    for icon in (n for n in leaves if n.kind == "icon"):
        occupied = [n for n in leaves if n is not icon]
        clashes = _icon_collisions(icon, occupied, gap)
        if clashes:
            raise ValueError(
                f"Icon {icon.role!r} overlaps {clashes!r}; adjust spacing "
                "or decrease icon size before export")


def _finish(ctx: SceneContext, scene: dict, layout, background: dict,
            elements: dict[str, Node], specs: Iterable[ElementSpec],
            decor: list[Node] | None = None, meta: dict | None = None) -> BuiltScene:
    from ..motionkit.choreography import plan_choreography
    specs = list(specs)
    elements = {role: node for role, node in elements.items() if node is not None}
    specs = list(specs)
    roles = {spec.role for spec in specs}
    # Creative Engine's explicit, renderer-backed typography preset wins
    # over the ordinary scene-index pattern, without changing older projects.
    requested_type_motion = scene.get("typography_motion")
    if requested_type_motion:
        from ..motionkit.choreography import ElementSpec
        specs = [ElementSpec(role=spec.role, weight=spec.weight,
                             kind=spec.kind, order=spec.order,
                             hint=requested_type_motion if spec.role == "headline"
                             else spec.hint) for spec in specs]
    raw_cues = scene.get("cues") or {}
    cues = {role: value for role, value in raw_cues.items() if role in roles}
    dropped = sorted(set(raw_cues) - roles)
    plan = plan_choreography(
        specs, style=ctx.style, scene_index=ctx.scene_index,
        scene_duration=ctx.duration, tokens=ctx.tokens,
        cues=cues)
    from ..design.editorial_quality import audit_editorial_style
    plan.warnings.extend(audit_editorial_style(scene))
    if dropped:
        plan.warnings.append({
            "code": "cue_without_element",
            "roles": dropped,
            "message": "Narration cues refer to elements not present in this scene.",
        })
    for role, node in elements.items():
        entry = plan.entries.get(role)
        if entry:
            safe = layout.safe
            apply_entrance(node, entry.preset, entry.onset, entry.duration,
                           ctx.tokens, seed=ctx.seed,
                           safe_bounds=(safe.x, safe.y, safe.right, safe.bottom))
            node.meta["motion"] = entry.preset
            node.meta["onset"] = round(entry.onset, 4)
        exit_entry = plan.exits.get(role)
        if exit_entry:
            apply_exit(node, exit_entry.onset, exit_entry.duration, ctx.tokens)
    from ..motionkit.editorial_rotation import (
        apply_editorial_rotations, editorial_media_nodes)
    if scene.get("editorial_rotation"):
        plan.warnings.extend(apply_editorial_rotations(
            elements, scene["editorial_rotation"], ctx.duration))
    media_nodes = editorial_media_nodes(scene, ctx.width, ctx.height, ctx.duration)
    vlayer = scene.get("video_layer")
    if isinstance(vlayer, dict) and vlayer.get("path"):
        safe = layout.safe
        vx = float(vlayer.get("x", safe.x))
        vy = float(vlayer.get("y", safe.y + safe.h * .52))
        vw = float(vlayer.get("w", safe.w))
        vh = float(vlayer.get("h", safe.h * .38))
        media_nodes.append(video_node(
            str(vlayer.get("role", "video-layer")),
            str(vlayer["path"]),
            Rect(vx, vy, vw, vh),
            trim_start=float(vlayer.get("trim_start", 0.0)),
            trim_end=vlayer.get("trim_end"),
            crop=tuple(vlayer["crop"]) if vlayer.get("crop") else None,
            mask=str(vlayer.get("mask", "rounded")),
            radius=float(vlayer.get("radius", 18.0)),
            qa_class="decor",
        ))
    final_nodes = (decor or []) + media_nodes + list(elements.values()) + _extra_icons(
        ctx, scene, _theme(ctx, scene))
    _validate_icon_spacing(ctx, final_nodes)
    return BuiltScene(
        index=ctx.scene_index, scene=scene, context=ctx, layout=layout,
        background=background, nodes=final_nodes,
        elements=elements, choreography=plan, meta={
            "headline": _headline(scene), "body": _subtitle(scene),
            "theme": "light" if _is_light(ctx, scene) else "dark",
            **(meta or {})})


def _is_light(ctx: SceneContext, scene: dict) -> bool:
    return _theme(ctx, scene)["light"]


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


def _card_fill(theme: dict) -> tuple[int, int, int]:
    """Opaque card surface that keeps light ink readable on dark styles."""
    if theme["light"]:
        return lighten(theme["base"], .72)
    return mix(theme["base"], theme["ink"], .08)


def _panel_with_text(ctx: SceneContext, role: str, rect: Rect, theme: dict,
                     *, fill=None, accent=False) -> Node:
    return panel_node(role, rect, ctx.tokens,
                      fill=fill or (theme["accent"] if accent else _card_fill(theme)),
                      radius="lg", shadow=not theme["light"])


# --------------------------------------------------------------------- amount
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


# ------------------------------------------------------------------ breakdown
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


# --------------------------------------------------------------- announcement
def build_announcement(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    kicker = str(scene.get("kicker", "PROGRAM DOTACYJNY"))
    lines = scene.get("headline")
    if isinstance(lines, dict):
        headline_copy = _headline(scene)
        runs = _runs(scene, ctx.tokens, theme["ink"], theme["accent"])
    else:
        headline_copy = str(lines or "NABÓR\nOTWARTY")
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
    specs = [_spec("kicker", 3), _spec("headline", 10, "display"),
             _spec("visual", 5, "control", hint="pop-settle"),
             _spec("body", 4)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "calendar", "day": day,
                         "calendar_label": month})


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


# ---------------------------------------------------------------------- donut
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


# ----------------------------------------------------------------- comparison
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


# ----------------------------------------------------------------------- heat
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
                              align="center", valign="bottom"),
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


# --------------------------------------------------------------------- europe
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
                              align="center", valign="bottom"),
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


# ------------------------------------------------------------------- deadline
def build_deadline(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    kicker = str(scene.get("kicker", "NABÓR DO"))
    date = str(scene.get("date") or _headline(scene) or "1.10.2027")
    subtitle = str(scene.get("subtitle") or _subtitle(scene)
                   or "LUB DO WYCZERPANIA BUDŻETU")
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
        "timeline": Node(kind="group", role="timeline",
                         children=_timeline_graphic(
                             ctx, layout.region("timeline"),
                             scene.get("milestones"), theme),
                         qa_class="control"),
    }
    if subtitle:
        elements["body"] = text_node("body", subtitle, body_style,
                                     layout.region("body"), ctx.fonts,
                                     align="center", valign="center")
    specs = [_spec("kicker", 3), _spec("headline", 10, "display"),
             _spec("timeline", 6, "control", hint="reveal-right"),
             _spec("body", 4)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "timeline", "date": date,
                         "budget_consumption_shown": False})


def _timeline_graphic(ctx: SceneContext, region: Rect,
                      milestones, theme: dict) -> list[Node]:
    labels = milestones if isinstance(milestones, list) and milestones else [
        {"label": "START NABORU", "value": "2026"},
        {"label": "DZIŚ", "value": "—"},
        {"label": "TERMIN", "value": "1.10.2027"},
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


# -------------------------------------------------------------------- urgency
def build_urgency(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    headline = _headline(scene) or "NIE ZWLEKAJ"
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
    clock = Node(kind="group", role="visual",
                 children=[icons.clock(region.center_x, cy, size,
                                       theme["ink"]),
                           hands],
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


# ------------------------------------------------------------------------ cta
def build_cta(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    headline = _headline(scene) or "ZADZWOŃ LUB NAPISZ"
    phone = str(scene.get("phone", "CONTACT"))
    line_one = str(scene.get("line_one", "SPRAWDŹ DOTACJĘ"))
    line_two = str(scene.get("line_two", ""))
    website = str(scene.get("website", "example.com"))
    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "title", theme["ink"],
                                        align="center", balance=True)
    phone_style = TextStyle(ctx.tokens.px(72), theme["surface"], "bold",
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
    phone_node = Node(kind="text", role="phone", props={
        "x": card_region.x + ctx.tokens.space("md"),
        "y": card_region.y + card_region.h * .20,
        "w": card_region.w - ctx.tokens.space("md") * 2,
        "h": card_region.h * .34,
        "block": typeset(phone, phone_style,
                         card_region.w - ctx.tokens.space("md") * 2,
                         ctx.fonts),
        "align": "center", "color": theme["surface"],
        "size": phone_style.size, "weight": "bold",
        "tracking_offset": 0.0},
        qa_class="text", meta={"text": phone})
    tag_style = TextStyle(ctx.tokens.px(26), theme["surface"], "bold",
                          align="center", uppercase=True, tracking=1.5)
    tag = text_node("cta-tag", line_one, tag_style,
                    Rect(card_region.x + ctx.tokens.space("md"),
                         card_region.y + card_region.h * .58,
                         card_region.w - ctx.tokens.space("md") * 2,
                         card_region.h * .22), ctx.fonts,
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


# ------------------------------------------------------------------ spotlight
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
    headline_style = resolve_text_style(ctx.tokens, "hero", theme["ink"],
                                        balance=True)
    body_style = resolve_text_style(ctx.tokens, "body", theme["muted"],
                                    line_height=1.32)
    measurements = {
        "headline": _measure(_headline(scene), headline_style, width, ctx),
        "body": _measure(_subtitle(scene), body_style, width, ctx),
    }
    layout = ctx.layout.layout("spotlight", measurements)
    elements = _text_elements(ctx, scene, layout, theme,
                              headline_role="hero")
    specs = [_spec("kicker", 3), _spec("headline", 9, "display"),
             _spec("body", 4)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "spotlight"})


# ------------------------------------------------------------------ statement
def build_statement(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "display", theme["ink"],
                                        align="center", balance=True,
                                        line_height=.98)
    body_style = resolve_text_style(ctx.tokens, "subtitle", theme["muted"],
                                    align="center")
    headline = _headline(scene) or _subtitle(scene)
    body = _subtitle(scene) if _headline(scene) else ""
    measurements = {
        "headline": _measure(headline, headline_style, width, ctx),
        "body": _measure(body, body_style, width, ctx),
    }
    layout = ctx.layout.layout("statement", measurements)
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


# ------------------------------------------------------------------ checklist
def build_checklist(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    headline = _headline(scene) or "CO ZYSKUJESZ"
    items = scene.get("items") or ["Nadwyżki zostają w domu",
                                   "Ochrona przed blackoutem",
                                   "Niższe rachunki"]
    if not isinstance(items, list) or not items:
        raise ValueError("checklist items must be a nonempty list")
    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "title", theme["ink"],
                                        balance=True)
    measurements = {"headline": _measure(headline, headline_style, width, ctx)}
    layout = ctx.layout.layout("checklist", measurements)
    elements: dict[str, Node] = {
        "headline": text_node("headline", headline, headline_style,
                              layout.region("headline"), ctx.fonts,
                              valign="center")}
    specs = [_spec("headline", 8)]
    list_region = layout.region("list")
    row_h = min(ctx.tokens.px(118), list_region.h / max(1, len(items)))
    item_style = resolve_text_style(ctx.tokens, "subtitle", theme["ink"],
                                    line_height=1.2)
    for index, item in enumerate(items):
        region = Rect(list_region.x, list_region.y + index * row_h,
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


# ------------------------------------------------------------------ stat grid
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


# ------------------------------------------------------------------- data table
def build_table(ctx: SceneContext, scene: dict) -> BuiltScene:
    """Build a compact table from explicit ordered columns and stable row IDs.

    Cell values must already be formatted strings. Width weights and alignments
    are caller data; this component neither formats numbers nor drops rows.
    """
    theme = _theme(ctx, scene)
    headline = _headline(scene)
    columns = scene.get("columns")
    rows = scene.get("rows")
    if not isinstance(columns, list) or not 2 <= len(columns) <= 6:
        raise ValueError("table requires 2..6 explicit columns")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 8:
        raise ValueError("table requires 1..8 explicit rows; pagination is not implemented")

    parsed_columns = []
    seen_columns = set()
    for index, column in enumerate(columns):
        if not isinstance(column, dict):
            raise ValueError(f"table column {index} must be an object")
        key, label = column.get("id"), column.get("label")
        width = column.get("width")
        align = column.get("align")
        if not isinstance(key, str) or not key.strip() or key in seen_columns:
            raise ValueError("table column IDs must be unique non-empty strings")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"table column {key!r} requires a label")
        if (isinstance(width, bool) or not isinstance(width, (int, float))
                or not math.isfinite(width) or width <= 0):
            raise ValueError(f"table column {key!r} requires a positive width weight")
        if align not in ("left", "center", "right"):
            raise ValueError(f"table column {key!r} requires an explicit alignment")
        seen_columns.add(key)
        parsed_columns.append({"id": key, "label": label.strip(),
                               "width": float(width), "align": align})
    weight_total = sum(column["width"] for column in parsed_columns)
    if not math.isclose(weight_total, 1.0, rel_tol=0, abs_tol=1e-6):
        raise ValueError("table column width weights must sum to 1.0")

    parsed_rows = []
    seen_rows = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"table row {index} must be an object")
        row_id, values = row.get("id"), row.get("values")
        if not isinstance(row_id, str) or not row_id.strip() or row_id in seen_rows:
            raise ValueError("table row IDs must be unique non-empty strings")
        if not isinstance(values, dict) or set(values) != seen_columns:
            raise ValueError(f"table row {row_id!r} values must match all declared column IDs")
        if any(not isinstance(value, str) or not value.strip()
               for value in values.values()):
            raise ValueError(f"table row {row_id!r} cells must be explicit non-empty strings")
        seen_rows.add(row_id)
        parsed_rows.append({"id": row_id,
                            "values": {column["id"]: values[column["id"]]
                                       for column in parsed_columns}})

    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "title", theme["ink"],
                                        align="center", balance=True)
    body = str(scene.get("subtitle") or _subtitle(scene) or "")
    body_style = resolve_text_style(ctx.tokens, "body", theme["muted"],
                                    align="center")
    layout = ctx.layout.layout("data-panel", {
        "headline": _measure(headline, headline_style, width, ctx),
        "body": _measure(body, body_style, width, ctx),
    })
    table_region = layout.region("chart")
    outer_x = table_region.x + table_region.w * .02
    table_width = table_region.w * .96
    header_height = min(ctx.tokens.px(46), table_region.h * .12)
    rows_height = table_region.h - header_height - ctx.tokens.px(8)
    row_height = rows_height / len(parsed_rows)
    if row_height < ctx.tokens.px(30):
        raise ValueError("table rows do not fit safely in the available region")
    elements: dict[str, Node] = {
        "headline": text_node("headline", headline, headline_style,
                              layout.region("headline"), ctx.fonts,
                              align="center", valign="center")
    }
    table_children: list[Node] = []
    header_y = table_region.y
    table_children.append(panel_node(
        "table-header", Rect(outer_x, header_y, table_width, header_height),
        ctx.tokens, fill=theme["accent"], radius="sm", shadow=False))
    header_style = TextStyle(max(12, ctx.tokens.px(17)), theme["base"], "bold",
                             uppercase=False, line_height=1.0)
    cell_style = TextStyle(max(12, min(ctx.tokens.px(20), row_height * .52)),
                           theme["ink"], "regular", line_height=1.0)
    x = outer_x
    for column in parsed_columns:
        cell_width = table_width * column["width"]
        header = text_node(
            f"table-header-{column['id']}", column["label"], header_style,
            Rect(x + cell_width * .04, header_y, cell_width * .92, header_height),
            ctx.fonts, align=column["align"], valign="center", fit=True)
        if header:
            table_children.append(header)
        x += cell_width

    highlight_rows = {str(r) for r in (scene.get("highlight_rows") or [])}
    highlight_cells = {
        (str(pair[0]), str(pair[1]))
        for pair in (scene.get("highlight_cells") or [])
        if isinstance(pair, (list, tuple)) and len(pair) == 2
    }
    animate_from = [str(r) for r in (scene.get("animate_from_row_ids") or [])]
    prev_slot_by_id = {rid: idx for idx, rid in enumerate(animate_from)}
    cell_transitions = scene.get("cell_transitions") or {}
    cell_highlight_style = TextStyle(
        max(12, min(ctx.tokens.px(20), row_height * .52)),
        theme["accent"], "bold", line_height=1.0,
    )

    for row_index, row in enumerate(parsed_rows):
        y = header_y + header_height + ctx.tokens.px(8) + row_index * row_height
        is_row_hi = row["id"] in highlight_rows
        row_fill = (
            mix(theme["surface"], theme["accent"], .22)
            if is_row_hi else (
                theme["surface"] if row_index % 2 == 0
                else mix(theme["surface"], theme["base"], .06)
            )
        )
        row_nodes = [panel_node(
            f"table-row-bg-{row_index}", Rect(outer_x, y, table_width, row_height),
            ctx.tokens, fill=row_fill, radius="sm", shadow=False)]
        x = outer_x
        row_trans = cell_transitions.get(row["id"]) if isinstance(cell_transitions, dict) else None
        for column in parsed_columns:
            cell_width = table_width * column["width"]
            col_id = column["id"]
            is_cell_hi = is_row_hi or ((row["id"], col_id) in highlight_cells)
            style_use = cell_highlight_style if is_cell_hi else cell_style
            cell_rect = Rect(x + cell_width * .04, y, cell_width * .92, row_height)
            spec_tr = row_trans.get(col_id) if isinstance(row_trans, dict) else None
            if isinstance(spec_tr, dict) and "from" in spec_tr and "to" in spec_tr:
                fmt = {
                    "prefix": str(spec_tr.get("prefix", "")),
                    "suffix": str(spec_tr.get("suffix", "")),
                    "decimals": int(spec_tr.get("decimals", 0)),
                    "thousands": " ",
                }
                cell = number_node(
                    f"table-cell-{row_index}-{col_id}",
                    safe_number(spec_tr["to"]),
                    cell_rect,
                    ctx.tokens,
                    fmt=fmt,
                    size_role="body",
                    color=style_use.color,
                    align=column["align"],
                )
                from_val = safe_number(spec_tr["from"])
                to_val = safe_number(spec_tr["to"])
                dur = max(.4, min(1.2, ctx.duration * .45))
                cell.track("prop.value", Track([
                    Keyframe(0.0, from_val, "out-cubic"),
                    Keyframe(0.25, from_val, "out-cubic"),
                    Keyframe(0.25 + dur, to_val, "out-cubic"),
                ]))
            else:
                cell = text_node(
                    f"table-cell-{row_index}-{col_id}",
                    row["values"][col_id], style_use,
                    cell_rect,
                    ctx.fonts, align=column["align"], valign="center", fit=True)
            if cell:
                row_nodes.append(cell)
            x += cell_width
        row_group = Node(
            kind="group", role=f"table-row-{row_index}", children=row_nodes,
            qa_class="control",
            meta={"stable_row_id": row["id"], "highlighted": is_row_hi},
        )
        prev_idx = prev_slot_by_id.get(row["id"])
        if prev_idx is not None and prev_idx != row_index and 0 <= prev_idx < len(parsed_rows):
            delta_y = (prev_idx - row_index) * row_height
            settle_t = max(.35, min(1.1, ctx.duration * .45))
            row_group.track("dy", Track([
                Keyframe(0.0, delta_y, "in-out-cubic"),
                Keyframe(settle_t, 0.0, "in-out-cubic"),
                Keyframe(ctx.duration, 0.0, "linear"),
            ]))
        table_children.append(row_group)
    elements["table"] = Node(kind="group", role="table", children=table_children,
                              qa_class="control",
                              meta={"row_ids": [row["id"] for row in parsed_rows],
                                    "highlight_rows": sorted(highlight_rows)})
    if body and layout.optional("body"):
        elements["body"] = text_node("body", body, body_style,
                                      layout.region("body"), ctx.fonts,
                                      align="center", valign="center")
    specs = [_spec("headline", 7), _spec("table", 9, "control"),
             _spec("body", 3)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "table",
                         "columns": parsed_columns,
                         "row_ids": [row["id"] for row in parsed_rows],
                         "highlight_rows": sorted(highlight_rows),
                         "data_provenance": scene.get("data_provenance")})


# ----------------------------------------------------------------------- bars
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


# ------------------------------------------------------------- line/time-series
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


# ------------------------------------------------------------------ energy flow
def build_energy(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    headline = _headline(scene) or "OD ENERGII DO DOMU"
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


# ----------------------------------------------------------------------- quote
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
    mark = text_node("quote-mark", "„", mark_style,
                     Rect(ctx.layout.safe.x, ctx.layout.safe.y,
                          ctx.tokens.px(180), ctx.tokens.px(180)), ctx.fonts,
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


# --------------------------------------------------- DM-102/103 advanced charts
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


def build_product_3d(ctx: SceneContext, scene: dict) -> BuiltScene:
    """Render a true 3D perspective-projected product mesh with 3-point lighting in Studio (MD-601)."""
    from ..creative.pipeline import validate_3d_product_scene

    theme, layout, elements = _data_panel_scaffold(ctx, scene, "MODEL 3D PRODUKTU")
    spec_3d = scene.get("product_3d") or scene
    validate_3d_product_scene(spec_3d)
    chart = layout.region("chart")
    mesh_node = Node(
        kind="mesh3d",
        role="product-mesh-3d",
        props={
            "x": chart.x,
            "y": chart.y,
            "w": chart.w,
            "h": chart.h,
            "spec": dict(spec_3d),
        },
        qa_class="control",
    )
    elements["chart"] = mesh_node
    specs = [_spec("headline", 7), _spec("chart", 9, "control"), _spec("body", 3)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "product_3d", "mesh_path": spec_3d.get("mesh_path")})


# ------------------------------------------------------------------- dispatcher
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
    "table": build_table,
    "energy": build_energy,
    "quote": build_quote,
}


def build_scene(ctx: SceneContext, scene: dict) -> BuiltScene:
    kind = _scene_type(scene)
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


def _build_stack(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    has_visual = bool(scene.get("photo"))
    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "title", theme["ink"],
                                        align="center", balance=True)
    body_style = resolve_text_style(ctx.tokens, "body", theme["muted"],
                                    align="center")
    measurements = {
        "headline": _measure(_headline(scene), headline_style, width, ctx),
        "body": _measure(_subtitle(scene), body_style, width, ctx)}
    layout = ctx.layout.layout("stack-center", measurements,
                               has_visual=has_visual)
    elements = _text_elements(ctx, scene, layout, theme, align="center")
    specs = [_spec("kicker", 3), _spec("headline", 9, "display"),
             _spec("body", 4)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "stack"})


def _build_full_bleed(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "display", theme["ink"],
                                        align="center", balance=True,
                                        line_height=.94)
    body_style = resolve_text_style(ctx.tokens, "subtitle", theme["muted"],
                                    align="center")
    measurements = {
        "headline": _measure(_headline(scene), headline_style, width, ctx),
        "body": _measure(_subtitle(scene), body_style, width, ctx)}
    layout = ctx.layout.layout("full-bleed-type", measurements)
    elements = _text_elements(ctx, scene, layout, theme, align="center",
                              headline_role="display")
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, [_spec("kicker", 3),
                              _spec("headline", 10, "display"),
                              _spec("body", 4)],
                   decor=_decor(ctx, scene, theme),
                   meta={"component": "full-bleed"})


def _build_split(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, scene)
    width = ctx.layout.safe.w
    headline_style = resolve_text_style(ctx.tokens, "title", theme["ink"],
                                        balance=True)
    body_style = resolve_text_style(ctx.tokens, "body", theme["muted"],
                                    line_height=1.34)
    layout = ctx.layout.layout("split-editorial", {
        "headline": _measure(_headline(scene), headline_style, width, ctx),
        "body": _measure(_subtitle(scene), body_style, width, ctx)},
        has_visual=True)
    elements = _text_elements(ctx, scene, layout, theme, align="left")
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, [_spec("kicker", 3),
                              _spec("headline", 9, "display"),
                              _spec("body", 5)],
                   decor=_decor(ctx, scene, theme),
                   meta={"component": "split"})
