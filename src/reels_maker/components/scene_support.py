"""Shared scene-graph construction helpers.

This module sits below the scene registry and scene-family builders. Keep it
independent of ``components.scenes`` so chart builders and editorial builders
can share layout, theme, typography and finishing behavior without a reverse
module dependency.
"""
from __future__ import annotations

import math
from typing import Iterable

from ..core.scene_graph import Node
from ..design.color import (
    darken, ensure_contrast, lighten, mix, parse_hex, relative_luminance,
)
from ..design.tokens import DesignTokens
from ..layout.engine import Rect
from ..motionkit.choreography import ElementSpec
from ..motionkit.presets import apply_entrance, apply_exit
from ..textkit.typesetter import Run, TextStyle
from .base import (
    BuiltScene, SceneContext, measure_text, resolve_text_style,
    panel_node, rich_text_node, text_node, video_node,
)

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
