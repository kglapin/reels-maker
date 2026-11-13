"""Shared scene-graph construction helpers.

This module sits below the scene registry and scene-family builders. Keep it
independent of ``components.scenes`` so chart builders and editorial builders
can share layout, theme, typography and finishing behavior without a reverse
module dependency.
"""
from __future__ import annotations

import copy
import math
from typing import Iterable

from ..core.scene_graph import Node
from ..design.color import lighten, mix, parse_hex
from ..design.tokens import DesignTokens
from ..layout.engine import Rect
from ..motionkit.choreography import ElementSpec
from ..motionkit.easing import EASINGS
from ..motionkit.presets import (
    apply_entrance, apply_exit, canonical_preset, number_track,
)
from ..textkit.typesetter import Run, TextStyle
from .base import (
    BuiltScene, SceneContext, image_node, measure_text,
    number_node, resolve_text_style, panel_node, rich_text_node, text_node,
    video_node,
)
from .scene_theme import (
    background_for_scene as _background,
    is_light_scene as _is_light,
    theme_for_scene as _theme,
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


def _reposition_kicker(ctx: SceneContext, scene: dict, layout) -> None:
    """Honour an explicit ``kicker_position`` for this scene.

    The spotlight-style recipes seat the kicker at the top of the safe
    rectangle, detached from the copy block. ``kicker_position:
    "above-headline"`` moves the kicker region directly above the measured
    headline block with one ``md`` gap — the kicker-to-headline spacing the
    stack recipes already use. When the pair would leave the safe area the
    recipe position is kept, so the layout contract still holds.
    """
    position = scene.get("kicker_position", "")
    if not position:
        return
    if position != "above-headline":
        raise ValueError(
            f"Unsupported kicker_position {position!r}; "
            "expected 'above-headline'")
    headline = layout.optional("headline")
    if headline is None:
        return
    kicker_h = ctx.tokens.type_size("kicker") * 1.4
    top = headline.y - ctx.tokens.space("md") - kicker_h
    if top < layout.safe.y - 1:
        return
    layout.regions["kicker"] = Rect(headline.x, top, headline.w, kicker_h)
    layout.notes.append("kicker placed above headline")


def _text_elements(ctx: SceneContext, scene: dict, layout, theme: dict,
                   *, headline_role: str = "title",
                   align: str = "left",
                   include_kicker: bool = True,
                   include_body: bool = True,
                   body_role: str = "body",
                   rich: bool = True) -> dict[str, Node]:
    elements: dict[str, Node] = {}
    if include_kicker and scene.get("kicker"):
        _reposition_kicker(ctx, scene, layout)
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


def _stroke_icon_children(scene: dict, library: str, name: str, style: str,
                          weight: int, fill: bool, grade: int,
                          optical_size: int, *, cx: float, cy: float,
                          size: float, color, role: str,
                          cue_key: str, draw_cfg: dict | None) -> list[Node] | None:
    """Trace a stroke icon SVG into ``path`` children that draw on stroke by
    stroke. Returns ``None`` for filled packs or untraceable SVGs so callers
    can fall back to the raster icon.
    """
    from ..icon_strokes import trace_icon
    from ..motionkit.keyframes import Track

    try:
        traced = trace_icon(
            library, name, style=style, weight=weight, fill=fill,
            grade=grade, optical_size=optical_size,
            cache_dir=scene.get("icon_cache_dir"),
            offline=bool(scene.get("icon_offline", False)))
    except Exception:
        return None
    if traced is None or not traced.strokes:
        return None
    box = traced.view_box
    box_w = box[2] - box[0]
    box_h = box[3] - box[1]
    if box_w <= 0 or box_h <= 0 or size <= 0:
        return None
    scale_x = size / box_w
    scale_y = size / box_h
    scale = (scale_x + scale_y) / 2
    origin_x = cx - size / 2 - box[0] * scale_x
    origin_y = cy - size / 2 - box[1] * scale_y
    cfg = draw_cfg if isinstance(draw_cfg, dict) else {}
    cues = scene.get("cues") or {}
    cue = cues.get(cue_key, cues.get(role))
    base = float(cfg.get("delay", cue if isinstance(cue, (int, float)) else 0.0))
    duration = float(cfg.get("duration", 0.55))
    stagger = float(cfg.get("stagger", 0.09))
    count = len(traced.strokes)
    if count > 1:
        stagger = min(stagger, max(0.02, duration * 0.6 / (count - 1)))
    children = []
    for index, stroke in enumerate(traced.strokes):
        start = base + index * stagger
        node = Node(
            kind="path", role=f"{role}-stroke-{index}", qa_class="decor",
            props={
                "points": [(origin_x + px * scale_x,
                            origin_y + py * scale_y)
                           for px, py in stroke.points],
                "color": color,
                "width": max(1.0, stroke.width * scale),
                "closed": stroke.closed,
                "progress": 0.0,
            },
            meta={"icon_library": library, "icon_name": name,
                  "stroke_draw": True, "stroke_index": index})
        node.track("prop.progress", Track.from_pairs(
            [(start, 0.0), (start + duration, 1.0)], easing="linear"))
        children.append(node)
    return children


def _external_icon(scene: dict, key: str, cx: float, cy: float,
                   size: float, color, *, role: str | None = None) -> Node | None:
    """Resolve scene-selected licensed packs without drawing custom paths.

    Explicit icon_library activates the provider. icon_names overrides the
    finite semantic mapping; pack-specific icon_style selects a pinned variant.
    ``icon_draw`` traces stroke packs (e.g. Lucide) into polylines that draw
    on progressively; filled packs fall back to the raster icon.
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
    icon_role = role or key
    if scene.get("icon_draw"):
        strokes = _stroke_icon_children(
            scene, str(library), name, str(style),
            int(scene.get("icon_weight", 400)),
            bool(scene.get("icon_fill", False)),
            int(scene.get("icon_grade", 0)),
            int(scene.get("icon_optical_size", 24)),
            cx=cx, cy=cy, size=size, color=color,
            role=icon_role, cue_key=key,
            draw_cfg=scene.get("icon_draw"))
        if strokes:
            return Node(kind="group", role=icon_role, qa_class="decor",
                        children=strokes,
                        meta={"icon_library": library, "icon_name": name,
                              "stroke_draw": True})
    rgb = tuple(color)
    return Node(kind="icon", role=icon_role, qa_class="decor",
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
        role = f"asset-icon-{index}"
        if item.get("draw"):
            draw_cfg = item.get("draw")
            strokes = _stroke_icon_children(
                scene, library, name,
                str(item.get("style", DEFAULT_STYLES.get(library, "outline"))),
                int(item.get("weight", scene.get("icon_weight", 400))),
                bool(item.get("fill", scene.get("icon_fill", False))),
                int(item.get("grade", scene.get("icon_grade", 0))),
                int(item.get("optical_size", scene.get("icon_optical_size", 24))),
                cx=x * ctx.width, cy=y * ctx.height, size=px, color=color,
                role=role, cue_key=role,
                draw_cfg=draw_cfg if isinstance(draw_cfg, dict) else {})
            if strokes:
                node = Node(kind="group", role=role, qa_class="decor",
                            children=strokes, rotation=float(rotation),
                            meta={"icon_library": library, "icon_name": name,
                                  "stroke_draw": True})
                nodes.append(node)
                continue
        node = Node(kind="icon", role=role,
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
        enter = item.get("enter")
        if enter is not None:
            if not isinstance(enter, dict):
                raise ValueError(f"icon_assets[{index}] enter must be an object")
            delay = _overlay_number(enter.get("delay", 0), "enter delay", 0, 60)
            duration = _overlay_number(enter.get("duration", .5),
                                       "enter duration", .05, 3)
            preset = canonical_preset(enter.get("style") or "fade-up")
            apply_entrance(node, preset, delay, duration, ctx.tokens)
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


def overlay_nodes(ctx: SceneContext, scene: dict) -> dict[str, tuple[Node, str]]:
    """Build manifest-driven animated image overlays.

    Each ``overlays`` entry places a raster asset in normalized canvas
    coordinates and animates it through the renderer's standard property
    tracks (slide/scale/fade/reveal/rotation), exactly like text elements:

    ``{"asset": str, "x": 0..1, "y": 0..1, "w": 0.02..1, "h": 0.02..1,
    "entrance": preset (default "fade-up"),
    "anchor": [ax, ay] normalized pivot (default center),
    "travel": entrance slide distance in canvas-width units (default preset),
    "scale_from": entrance start scale (default preset),
    "easing": entrance easing curve name (default preset),
    "rotation": editorial rotation spec (optional),
    "path": [{"t", "x", "y", "easing"?}] absolute normalized top-left
        positions over scene time (optional),
    "appear": {"at", "duration"} opacity fade-in on top of entrance
        (pair with entrance "none"),
    "press": {"at", "depth", "duration"} quick scale dip for a click
        beat (optional),
    "ripple": {"at", "cx", "cy", "radius", "color", "duration", "width"}
        expanding ring emitted as a sibling node (optional),
    "exit": {"style": "fade"|"burn", "at", "duration", "seed"} motivated
        outro; "burn" disintegrates the asset through a seeded noise
        front (optional)}``

    Roles are ``overlay-0``, ``overlay-1``, ... and accept ``cues`` onsets.
    Author overlay assets at the rect's aspect ratio; the media renderer
    cover-fits the asset into the rect.

    ``path`` positions are absolute normalized canvas coordinates of the
    overlay's top-left corner; the first keyframe defines where the object
    starts, so authored ``x``/``y`` act as the reference for ``dx``/``dy``
    offsets and as the pivot for scale/rotation. A ``path`` overlay cannot
    combine with an entrance preset that translates on x/y (``fade-up``,
    ``rise``, ``slide-*``, ``mask-rise``, ``pop-settle``, ``word-cascade``,
    ``anticipate-pop``); use ``none``, ``fade``-free opacity entrances or
    ``scale-focus``/``tracking-in`` instead. ``press`` merges into the
    ``scale`` track, so avoid scale-based entrances on the same overlay or
    expect a clear keyframe-conflict error.
    """
    items = scene.get("overlays")
    if items is None:
        return {}
    if not isinstance(items, list):
        raise ValueError("overlays must be a list")
    built: dict[str, tuple[Node, str]] = {}
    for index, item in enumerate(items):
        where = f"overlays[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{where} must be an object")
        asset = item.get("asset")
        if not isinstance(asset, str) or not asset:
            raise ValueError(f"{where} requires an asset path")
        x = _overlay_number(item.get("x"), "x", 0, 1)
        y = _overlay_number(item.get("y"), "y", 0, 1)
        w = _overlay_number(item.get("w"), "w", .02, 1)
        h = _overlay_number(item.get("h"), "h", .02, 1)
        if x + w > 1.001 or y + h > 1.001:
            raise ValueError(f"{where} rectangle must fit within canvas")
        entrance = canonical_preset(item.get("entrance") or "fade-up")
        anchor = item.get("anchor", [.5, .5])
        if (not isinstance(anchor, (list, tuple)) or len(anchor) != 2):
            raise ValueError(f"{where} anchor must be an [ax, ay] pair")
        ax = _overlay_number(anchor[0], "anchor ax", 0, 1)
        ay = _overlay_number(anchor[1], "anchor ay", 0, 1)
        role = f"overlay-{index}"
        rect = Rect(x * ctx.width, y * ctx.height,
                    w * ctx.width, h * ctx.height)
        node = image_node(role, str(asset), rect, qa_class="visual",
                          meta={"asset_role": "overlay"})
        node.anchor = (rect.x + rect.w * ax, rect.y + rect.h * ay)
        if item.get("travel") is not None:
            travel = _overlay_number(item.get("travel"), "travel", 0, .5)
            # Entrance distances live in design px; normalize so the travel
            # covers the same canvas fraction at every export profile.
            node.meta["entrance_distance"] = (
                travel * ctx.width / ctx.tokens.scale)
        if item.get("scale_from") is not None:
            node.meta["entrance_scale_from"] = _overlay_number(
                item.get("scale_from"), "scale_from", .05, 3.0)
        if item.get("easing") is not None:
            easing = item.get("easing")
            if not isinstance(easing, str) or easing not in EASINGS:
                raise ValueError(
                    f"overlays: unknown easing {easing!r}")
            node.meta["entrance_easing"] = easing
        rotation = item.get("rotation")
        if rotation is not None:
            from ..motionkit.editorial_rotation import rotation_track
            node.track("rotation", rotation_track(rotation, ctx.duration,
                                                 role="overlay"))
            node.meta["editorial_rotation"] = {
                "family": rotation.get("family", "tilt-settle")
                if isinstance(rotation, dict) else "tilt-settle",
                "reason": "explicit art direction",
            }
        fx = {key: item[key] for key in _OVERLAY_FX_KEYS if key in item}
        if fx:
            node.meta["overlay_fx"] = fx
        built[role] = (node, entrance)
    return built


_OVERLAY_FX_KEYS = ("path", "appear", "press", "ripple", "exit")


def _merge_keys(node: Node, name: str, keys: list) -> None:
    """Merge extra keyframes into an existing or new property track."""
    from ..motionkit.keyframes import Track
    existing = node.tracks.get(name)
    combined = list(existing.keys) if existing else []
    combined.extend(keys)
    try:
        node.track(name, Track(combined))
    except ValueError as exc:
        raise ValueError(
            f"{node.role}: {name} keys conflict ({exc})") from exc


def _fx_time(spec: dict, where: str, field: str, default: float,
             ctx: SceneContext, *, upper: float | None = None) -> float:
    limit = ctx.duration if upper is None else upper
    return _overlay_number(spec.get(field, default),
                           f"{where} {field}", 0.0, limit)


def _overlay_appear(node: Node, spec, ctx: SceneContext) -> None:
    if spec is None:
        return
    if not isinstance(spec, dict):
        raise ValueError(f"{node.role} appear must be an object")
    at = _fx_time(spec, node.role, "at", 0.0, ctx)
    duration = _fx_time(spec, node.role, "duration", 0.3, ctx, upper=3.0)
    if duration <= 0:
        raise ValueError(f"{node.role} appear duration must be positive")
    if at + duration > ctx.duration + 1e-6:
        raise ValueError(f"{node.role} appear extends past scene end")
    from ..motionkit.keyframes import Keyframe
    _merge_keys(node, "opacity", [
        Keyframe(0.0, 0.0, "linear"),
        Keyframe(at, 0.0, "out-cubic"),
        Keyframe(at + duration, 1.0, "out-cubic"),
    ])


def _overlay_path(node: Node, spec, item: dict, ctx: SceneContext) -> None:
    if spec is None:
        return
    if not isinstance(spec, list) or not spec:
        raise ValueError(f"{node.role} path must be a nonempty list")
    if "dx" in node.tracks or "dy" in node.tracks:
        raise ValueError(
            f"{node.role} path conflicts with a translating entrance; "
            "use entrance 'none' or an opacity-only preset")
    from ..motionkit.easing import EASINGS
    from ..motionkit.keyframes import Keyframe, Track
    w = float(item["w"])
    h = float(item["h"])
    x0 = float(item["x"])
    y0 = float(item["y"])
    dx_keys: list = []
    dy_keys: list = []
    previous = -1.0
    for index, key in enumerate(spec):
        where = f"{node.role} path[{index}]"
        if not isinstance(key, dict):
            raise ValueError(f"{where} must be an object")
        t = _overlay_number(key.get("t"), f"{where} t", 0.0, ctx.duration)
        if t <= previous:
            raise ValueError(f"{where} times must strictly increase")
        previous = t
        x = _overlay_number(key.get("x"), f"{where} x", 0.0, 1.0)
        y = _overlay_number(key.get("y"), f"{where} y", 0.0, 1.0)
        if x + w > 1.001 or y + h > 1.001:
            raise ValueError(f"{where} position must keep the overlay inside the canvas")
        easing = str(key.get("easing", "in-out-cubic"))
        if easing not in EASINGS:
            raise ValueError(f"{where} unknown easing {easing!r}")
        dx_keys.append(Keyframe(t, (x - x0) * ctx.width, easing))
        dy_keys.append(Keyframe(t, (y - y0) * ctx.height, easing))
    node.track("dx", Track(dx_keys))
    node.track("dy", Track(dy_keys))


def _overlay_press(node: Node, spec, ctx: SceneContext) -> None:
    if spec is None:
        return
    if not isinstance(spec, dict):
        raise ValueError(f"{node.role} press must be an object")
    at = _fx_time(spec, node.role, "at", 0.0, ctx)
    duration = _fx_time(spec, node.role, "duration", 0.18, ctx, upper=1.0)
    if duration <= 0:
        raise ValueError(f"{node.role} press duration must be positive")
    if at + duration > ctx.duration + 1e-6:
        raise ValueError(f"{node.role} press extends past scene end")
    depth = _overlay_number(spec.get("depth", 0.06),
                            f"{node.role} press depth", 0.01, 0.3)
    from ..motionkit.keyframes import Keyframe
    down = at + duration * 0.45
    _merge_keys(node, "scale", [
        Keyframe(at, 1.0, "in-quad"),
        Keyframe(down, 1.0 - depth, "in-quad"),
        Keyframe(at + duration, 1.0, "back"),
    ])


def _overlay_exit(node: Node, spec, ctx: SceneContext) -> None:
    if spec is None:
        return
    if not isinstance(spec, dict):
        raise ValueError(f"{node.role} exit must be an object")
    style = str(spec.get("style", "fade"))
    if style not in ("fade", "burn", "tear"):
        raise ValueError(
            f"{node.role} exit style must be 'fade', 'burn' or 'tear'")
    at = _fx_time(spec, node.role, "at", max(0.0, ctx.duration - 0.6), ctx)
    duration = _fx_time(spec, node.role, "duration", 0.6, ctx, upper=5.0)
    if duration <= 0:
        raise ValueError(f"{node.role} exit duration must be positive")
    if at + duration > ctx.duration + 1e-6:
        raise ValueError(f"{node.role} exit extends past scene end")
    if style == "fade":
        from ..motionkit.presets import apply_exit
        apply_exit(node, at, duration, ctx.tokens)
        return
    import zlib
    from ..motionkit.keyframes import Keyframe, Track
    end = at + duration
    _merge_keys(node, "opacity", [
        Keyframe(max(at, end - 0.12), 1.0, "linear"),
        Keyframe(end, 0.0, "linear"),
    ])
    if style == "tear":
        node.track("prop.tear_progress", Track([
            Keyframe(at, 0.0, "linear"),
            Keyframe(end, 1.0, "in-quad"),
        ]))
        seed = spec.get("seed", 0)
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError(f"{node.role} exit seed must be an integer")
        node.meta["tear_seed"] = (
            zlib.crc32(node.role.encode("utf-8")) + seed) & 0xFFFFFFFF
        return
    node.track("prop.burn_progress", Track([
        Keyframe(at, 0.0, "linear"),
        Keyframe(end, 1.0, "linear"),
    ]))
    seed = spec.get("seed", 0)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError(f"{node.role} exit seed must be an integer")
    node.meta["burn_seed"] = (
        zlib.crc32(node.role.encode("utf-8")) + seed) & 0xFFFFFFFF


def _overlay_ripple(spec, ctx: SceneContext, owner_role: str) -> Node | None:
    if spec is None:
        return None
    if not isinstance(spec, dict):
        raise ValueError(f"{owner_role} ripple must be an object")
    role = f"{owner_role}-ripple"
    at = _fx_time(spec, role, "at", 0.0, ctx)
    duration = _fx_time(spec, role, "duration",
                        0.6, ctx, upper=2.0)
    if duration <= 0:
        raise ValueError(f"{role} duration must be positive")
    if at + duration > ctx.duration + 1e-6:
        raise ValueError(f"{role} extends past scene end")
    cx = _overlay_number(spec.get("cx"), f"{role} cx", 0.0, 1.0)
    cy = _overlay_number(spec.get("cy"), f"{role} cy", 0.0, 1.0)
    radius = _overlay_number(spec.get("radius"), f"{role} radius",
                             0.01, 0.5)
    width = _overlay_number(spec.get("width", 3.0), f"{role} width",
                            0.5, 24.0)
    color = spec.get("color", ctx.palette.accent)
    if isinstance(color, str):
        from ..design.color import parse_hex
        color = parse_hex(color)
    elif (not isinstance(color, (list, tuple)) or len(color) != 3
          or any(isinstance(v, bool) or not isinstance(v, (int, float))
                 or not 0 <= v <= 255 for v in color)):
        raise ValueError(f"{role} color must be #rrggbb or an [r, g, b] triple")
    color = tuple(int(round(float(v))) for v in color)
    from ..motionkit.keyframes import Keyframe, Track
    r0 = radius * 0.15 * ctx.width
    r1 = radius * ctx.width
    fade_in = min(0.07, duration * 0.25)
    fade_out = duration * 0.4
    node = Node(
        kind="ring", role=role, qa_class="decor",
        props={"cx": cx * ctx.width, "cy": cy * ctx.height,
               "r": r0, "width": width, "color": color,
               "progress": 1.0, "start_angle": -90.0})
    node.track("prop.r", Track([
        Keyframe(at, r0, "out-cubic"),
        Keyframe(at + duration, r1, "out-cubic"),
    ]))
    node.track("opacity", Track([
        Keyframe(at, 0.0, "out-quad"),
        Keyframe(at + fade_in, 0.85, "out-quad"),
        Keyframe(at + duration - fade_out, 0.85, "in-quad"),
        Keyframe(at + duration, 0.0, "in-quad"),
    ]))
    return node


def _apply_overlay_dynamics(elements: dict[str, Node], scene: dict,
                            ctx: SceneContext) -> list[Node]:
    """Attach authored path/press/exit tracks after entrance choreography.

    Runs post-``apply_entrance`` so merges see the final track set and
    conflicts surface as explicit errors instead of silent overwrites.
    Returns sibling nodes (click ripples) drawn above the overlays.
    """
    items = scene.get("overlays") or []
    extra: list[Node] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        role = f"overlay-{index}"
        node = elements.get(role)
        if node is None:
            continue
        fx = node.meta.get("overlay_fx")
        if not fx:
            continue
        _overlay_appear(node, fx.get("appear"), ctx)
        _overlay_path(node, fx.get("path"), item, ctx)
        _overlay_press(node, fx.get("press"), ctx)
        _overlay_exit(node, fx.get("exit"), ctx)
        ripple = _overlay_ripple(fx.get("ripple"), ctx, role)
        if ripple is not None:
            extra.append(ripple)
    return extra


_WORD_ALT_HINTS = ("slide-left", "mask-rise", "pop-settle",
                   "word-cascade", "fade-up")


def _split_text_lines(elements: dict[str, Node], specs: list[ElementSpec],
                      wanted: set[str] | None,
                      mode: str = "lines") -> tuple[dict[str, Node],
                                                     list[ElementSpec]]:
    """Explode multi-line text blocks into per-line or per-word nodes.

    Each rendered ``Line``/``Word`` keeps its absolute baseline, so a fragment
    ``TextBlock`` drawn at the fragment origin reproduces the exact same
    pixels as the unsplit block — only the choreography changes: every
    fragment becomes its own element with its own entrance.
    """
    from dataclasses import replace as _replace
    from ..textkit.models import Line, TextBlock
    split_roles: dict[str, tuple[Node, TextBlock]] = {}
    for role, node in elements.items():
        block = node.props.get("block") if node.kind == "text" else None
        if wanted is not None and role not in wanted:
            continue
        if not isinstance(block, TextBlock):
            continue
        word_count = sum(len(line.words) for line in block.lines)
        fragmented = (word_count > 1 if mode == "words"
                      else len(block.lines) > 1)
        if fragmented:
            split_roles[role] = (node, block)
    if not split_roles:
        return elements, specs
    new_elements: dict[str, Node] = {}
    for role, node in elements.items():
        if role not in split_roles:
            new_elements[role] = node
            continue
        original, block = split_roles[role]
        ox = float(original.props.get("x", 0.0))
        oy = float(original.props.get("y", 0.0))
        fragments = []
        for line_index, line in enumerate(block.lines):
            row_top = line.baseline - line.ascent
            if mode == "words":
                for word in line.words:
                    tight_word = _replace(word, x=0.0)
                    tight = Line(words=(tight_word,), width=word.width,
                                 ascent=line.ascent, descent=line.descent,
                                 baseline=line.ascent, height=line.height)
                    fragments.append((tight, word.text, word.width,
                                      word.x, row_top, line.height,
                                      line_index))
            else:
                xs = [word.x for word in line.words]
                xe = [word.x + word.width for word in line.words]
                min_x = min(xs)
                shifted = tuple(_replace(word, x=word.x - min_x)
                                for word in line.words)
                tight = Line(words=shifted, width=line.width,
                             ascent=line.ascent, descent=line.descent,
                             baseline=line.ascent, height=line.height)
                text = " ".join(word.text for word in line.words)
                fragments.append((tight, text, max(xe) - min_x,
                                  min_x, row_top, line.height, line_index))
        for index, (tight, text, width, rel_x, row_top, line_h,
                    line_index) in enumerate(fragments):
            single = TextBlock(
                lines=(tight,), width=width, height=line_h,
                style=block.style, text=text,
                overflow=False, truncated=False,
                run_count=block.run_count)
            child = copy.copy(original)
            child.role = f"{role}-{index}"
            child.props = {**original.props,
                           "x": ox + rel_x, "y": oy + row_top,
                           "w": width, "h": line_h, "block": single}
            child.meta = {**original.meta, "text": text,
                          "bounds": (ox + rel_x, oy + row_top,
                                     ox + rel_x + width,
                                     oy + row_top + line_h),
                          "split_from": role, "split_line": line_index}
            child.anchor = None
            # copy.copy shares the tracks dict; each fragment must own its
            # entrance/exit tracks or the last applied spec wins for all.
            child.tracks = dict(original.tracks)
            child.children = list(original.children)
            if mode == "words":
                # Word fragments fade in place: any vertical travel leaves
                # same-line words at different heights mid-stagger, so the
                # baseline looks broken and then snaps into alignment.
                child.meta["entrance_distance"] = 0.0
                child.meta["entrance_duration_scale"] = 1.7
            new_elements[child.role] = child
    new_specs: list[ElementSpec] = []
    for spec in specs:
        if spec.role not in split_roles:
            new_specs.append(spec)
            continue
        block = split_roles[spec.role][1]
        if mode == "words":
            count = sum(len(line.words) for line in block.lines)
        else:
            count = len(block.lines)
        default_hint = (spec.hint if spec.hint else
                        ("word-cascade" if spec.kind == "display"
                         else "fade-up") if mode == "words" else spec.hint)
        word_alts = tuple(h for h in _WORD_ALT_HINTS if h != default_hint)
        for index in range(count):
            hint = default_hint
            if mode == "words" and index % 2 == 1 and word_alts:
                hint = word_alts[(index // 2) % len(word_alts)]
            new_specs.append(ElementSpec(
                role=f"{spec.role}-{index}",
                weight=max(0.0, spec.weight - index * (.15 if mode == "words" else .45)),
                kind=spec.kind,
                hint=hint,
                order=spec.order))
    return new_elements, new_specs


def _overlay_number(value, field: str, lower: float, upper: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"overlays: {field} must be numeric")
    result = float(value)
    if not math.isfinite(result) or not lower <= result <= upper:
        raise ValueError(f"overlays: {field} must be between {lower} and {upper}")
    return result


def _counter_finite(value, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"counters: {field} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"counters: {field} must be finite")
    return result


def counter_nodes(ctx: SceneContext, scene: dict) -> list[Node]:
    """Manifest-driven animated number readouts.

    Each ``counters`` entry places a ``number`` primitive in normalized
    canvas coordinates and animates its value through ``prop.value``:

    ``{"x", "y", "w", "h", "value", "format"?, "size_role"?, "color"?,
    "align"?, "rotation"?, "count": {"at", "duration", "from", "easing"?},
    "appear": {"at", "duration"}?, "exit"?}`` — ``exit`` reuses the
    overlay exit spec (``fade``/``burn``/``tear``) so a readout can leave
    together with the surface it annotates; ``rotation`` tilts the readout
    in degrees around its own center (e.g. to match a tilted card).

    ``value`` is the final readout, ``count.from`` the start value and
    ``count.at``/``count.duration`` the scene-local count window. ``appear``
    fades the readout in (defaults to the count onset); without it the
    number would be visible at its ``from`` value before counting.
    """
    items = scene.get("counters")
    if items is None:
        return []
    if not isinstance(items, list):
        raise ValueError("counters must be a list")
    from ..motionkit.keyframes import Keyframe, Track
    nodes: list[Node] = []
    for index, item in enumerate(items):
        where = f"counters[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{where} must be an object")
        x = _overlay_number(item.get("x"), f"{where} x", 0, 1)
        y = _overlay_number(item.get("y"), f"{where} y", 0, 1)
        w = _overlay_number(item.get("w"), f"{where} w", .02, 1)
        h = _overlay_number(item.get("h"), f"{where} h", .02, 1)
        if x + w > 1.001 or y + h > 1.001:
            raise ValueError(f"{where} rectangle must fit within canvas")
        target = _counter_finite(item.get("value"), f"{where} value")
        count = item.get("count")
        if not isinstance(count, dict):
            raise ValueError(f"{where} requires a count object")
        onset = _fx_time(count, where, "at", 0.0, ctx)
        duration = _fx_time(count, where, "duration", 1.0, ctx, upper=10.0)
        if duration <= 0:
            raise ValueError(f"{where} count duration must be positive")
        if onset + duration > ctx.duration + 1e-6:
            raise ValueError(f"{where} count extends past scene end")
        start = _counter_finite(count.get("from", 0.0), f"{where} from")
        easing = count.get("easing", "out-cubic")
        if easing not in EASINGS:
            raise ValueError(f"{where} unknown easing {easing!r}")
        fmt = item.get("format")
        if fmt is not None and not isinstance(fmt, dict):
            raise ValueError(f"{where} format must be an object")
        color_raw = item.get("color")
        color = (parse_hex(str(color_raw))[:3]
                 if color_raw is not None else ctx.tokens.palette.accent)
        align = str(item.get("align", "center"))
        if align not in ("left", "center", "right"):
            raise ValueError(f"{where} align must be left, center or right")
        rotation = item.get("rotation")
        if rotation is not None:
            rotation = _counter_finite(rotation, f"{where} rotation")
            if abs(rotation) > 45.0:
                raise ValueError(f"{where} rotation must be within ±45°")
        size_role = str(item.get("size_role", "title"))
        rect = Rect(x * ctx.width, y * ctx.height,
                    w * ctx.width, h * ctx.height)
        node = number_node(f"counter-{index}", target, rect, ctx.tokens,
                           fmt=fmt, size_role=size_role, color=color,
                           align=align, qa_class="text",
                           meta={"asset_role": "counter"})
        if rotation is not None:
            node.rotation = rotation
        node.opacity = 0.0
        node.track("prop.value", number_track(
            target, onset, duration, start=start, easing=easing))
        appear = item.get("appear")
        if appear is not None and not isinstance(appear, dict):
            raise ValueError(f"{where} appear must be an object")
        appear = appear or {}
        a_at = _fx_time(appear, where, "at", onset, ctx)
        a_dur = _fx_time(appear, where, "duration",
                         min(0.35, duration), ctx, upper=3.0)
        if a_dur <= 0:
            raise ValueError(f"{where} appear duration must be positive")
        if a_at + a_dur > ctx.duration + 1e-6:
            raise ValueError(f"{where} appear extends past scene end")
        node.track("opacity", Track([
            Keyframe(0.0, 0.0, "linear"),
            Keyframe(a_at, 0.0, "linear"),
            Keyframe(a_at + a_dur, 1.0, "out-cubic"),
        ]))
        exit_spec = item.get("exit")
        if exit_spec is not None:
            if not isinstance(exit_spec, dict):
                raise ValueError(f"{where} exit must be an object")
            _overlay_exit(node, exit_spec, ctx)
        nodes.append(node)
    return nodes


def _finish(ctx: SceneContext, scene: dict, layout, background: dict,
            elements: dict[str, Node], specs: Iterable[ElementSpec],
            decor: list[Node] | None = None, meta: dict | None = None) -> BuiltScene:
    from ..motionkit.choreography import plan_choreography
    specs = list(specs)
    elements = {role: node for role, node in elements.items() if node is not None}
    for role, (node, entrance) in overlay_nodes(ctx, scene).items():
        elements[role] = node
        specs.append(_spec(role, 5, "decor", hint=entrance, order=len(specs)))
    split = scene.get("split_lines")
    if split:
        mode = "words" if split == "words" else "lines"
        wanted = (None if split is True or split == "words" else
                  {str(role) for role in split}
                  if isinstance(split, list) else set())
        elements, specs = _split_text_lines(elements, specs, wanted,
                                            mode=mode)
    roles = {spec.role for spec in specs}
    # Creative Engine's explicit, renderer-backed typography preset wins
    # over the ordinary scene-index pattern, without changing older projects.
    requested_type_motion = scene.get("typography_motion")
    if requested_type_motion:
        from ..motionkit.choreography import ElementSpec
        from ..motionkit.presets import select_text_mechanism
        resolved_motion = select_text_mechanism(str(requested_type_motion))
        specs = [ElementSpec(role=spec.role, weight=spec.weight,
                             kind=spec.kind, order=spec.order,
                             hint=(resolved_motion
                                   if spec.role == "headline"
                                   or spec.role.startswith("headline-")
                                   else spec.hint)) for spec in specs]
    preset_overrides = scene.get("entrance_presets")
    if preset_overrides is not None:
        if not isinstance(preset_overrides, dict):
            raise ValueError("entrance_presets must be an object")
        from dataclasses import replace
        known = {spec.role for spec in specs}
        unknown = sorted(set(preset_overrides) - known)
        if unknown:
            raise ValueError("entrance_presets refer to unknown elements: "
                             + ", ".join(unknown))
        specs = [replace(spec, hint=canonical_preset(
                    str(preset_overrides[spec.role])))
                 if spec.role in preset_overrides else spec
                 for spec in specs]
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
                           distance=node.meta.get("entrance_distance"),
                           scale_from=node.meta.get("entrance_scale_from"),
                           easing=node.meta.get("entrance_easing"),
                           safe_bounds=(safe.x, safe.y, safe.right, safe.bottom))
            node.meta["motion"] = entry.preset
            node.meta["onset"] = round(entry.onset, 4)
        exit_entry = plan.exits.get(role)
        if exit_entry:
            apply_exit(node, exit_entry.onset, exit_entry.duration, ctx.tokens)
    typing_cfg = scene.get("typing")
    if typing_cfg:
        from .text_motion import render_units, typing_track
        for role, tspec in typing_cfg.items():
            node = elements.get(role)
            block = node.props.get("block") if node is not None else None
            if node is None or block is None:
                plan.warnings.append({
                    "code": "typing_missing_block", "role": role,
                    "message": ("Typing effect needs a text element with a "
                                "typeset block; the cue was skipped.")})
                continue
            entry = plan.entries.get(role)
            if isinstance(tspec, dict):
                start = float(tspec.get(
                    "start", entry.onset if entry else 0.0))
                duration = float(tspec.get("duration", 1.6))
                profile = str(tspec.get("profile", "human"))
            else:
                start = entry.onset if entry else 0.0
                duration = float(tspec)
                profile = "human"
            node.track("prop.character_progress",
                       typing_track(render_units(block), start, duration,
                                    profile=profile))
    overlay_fx_nodes = _apply_overlay_dynamics(elements, scene, ctx)
    counter_nodes_ = counter_nodes(ctx, scene)
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
    final_nodes = (decor or []) + media_nodes + list(elements.values()) \
        + overlay_fx_nodes + counter_nodes_ + _extra_icons(
            ctx, scene, _theme(ctx, scene))
    _validate_icon_spacing(ctx, final_nodes)
    return BuiltScene(
        index=ctx.scene_index, scene=scene, context=ctx, layout=layout,
        background=background, nodes=final_nodes,
        elements=elements, choreography=plan, meta={
            "headline": _headline(scene), "body": _subtitle(scene),
            "theme": "light" if _is_light(ctx, scene) else "dark",
            **(meta or {})})


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
