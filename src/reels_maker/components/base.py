"""Shared component primitives: scene context, measured text and panels."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping

from ..core.scene_graph import Node
from ..design.format import format_value
from ..design.tokens import DesignTokens
from ..layout.engine import LayoutEngine, LayoutPlan, Rect
from ..motionkit.choreography import Choreography, ElementSpec, plan_choreography
from ..motionkit.keyframes import Keyframe, Track
from ..motionkit.presets import number_track, progress_track
from ..textkit.typesetter import (
    FontBook, Run, TextBlock, TextStyle, fit_text, typeset, typeset_runs,
)


@dataclass
class SceneContext:
    width: int
    height: int
    fps: int
    duration: float
    tokens: DesignTokens
    style: str
    fonts: FontBook
    scene_index: int = 0
    seed: int = 0
    assets: object | None = None
    scene: dict = field(default_factory=dict)

    @property
    def layout(self) -> LayoutEngine:
        return LayoutEngine(self.width, self.height, self.tokens)

    @property
    def palette(self):
        return self.tokens.palette


@dataclass
class BuiltScene:
    index: int
    scene: dict
    context: SceneContext
    layout: LayoutPlan
    background: dict
    nodes: list[Node]
    elements: dict[str, Node]
    choreography: Choreography
    meta: dict = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return self.context.duration

    @property
    def fps(self) -> int:
        return self.context.fps

    def at(self, time: float) -> list[Node]:
        return [node.sample(time) for node in self.nodes]

    def element(self, role: str) -> Node:
        if role not in self.elements:
            raise KeyError(f"Scene {self.index + 1} has no element {role!r}")
        return self.elements[role]

    def to_dict(self) -> dict:
        return {
            "scene": self.index + 1,
            "type": self.scene.get("type", self.scene.get("composition", "custom")),
            "composition": self.layout.recipe,
            "duration": round(self.duration, 4),
            "background": self.background.get("kind", "solid"),
            "layout": self.layout.describe(),
            "choreography": self.choreography.to_dict(),
            **self.meta,
        }


def resolve_text_style(tokens: DesignTokens, role: str,
                       color: tuple[int, int, int] | None = None,
                       *, weight: str | None = None,
                       align: str = "left", line_height: float | None = None,
                       tracking: float | None = None,
                       uppercase: bool | None = None,
                       max_lines: int | None = None,
                       balance: bool = False) -> TextStyle:
    if role not in ("display", "hero", "title", "subtitle", "body",
                    "caption", "micro", "kicker"):
        raise ValueError(f"Unknown typography role {role!r}")
    weight = weight or ("bold" if role not in ("body", "caption", "micro") else "regular")
    size = tokens.type_size(role)
    scale = tokens.typography.line_height
    return TextStyle(
        size=size,
        color=color or (tokens.palette.ink if role != "kicker" else tokens.palette.accent),
        weight=weight,
        line_height=line_height if line_height is not None else scale,
        tracking=tokens.px(tracking if tracking is not None else
                           (tokens.typography.tracking * size)),
        align=align,
        uppercase=(tokens.uppercase_kickers if uppercase is None
                   and role == "kicker" else bool(uppercase)),
        max_lines=max_lines,
        balance=balance,
    )


def text_node(role: str, text: str, style: TextStyle, rect: Rect,
              fonts: FontBook, *, align: str | None = None,
              valign: str = "top", fit: bool = True,
              qa_class: str = "text", meta: Mapping | None = None) -> Node | None:
    """Measure and place one copy block inside a layout region."""
    copy = (text or "").strip()
    if not copy:
        return None
    style = TextStyle(**{**style.__dict__, "align": align or style.align})
    max_width = max(4.0, rect.w)
    if fit:
        block, style = fit_text(copy, style, max_width, rect.h, fonts)
    else:
        block = typeset(copy, style, max_width, fonts)
        if block.height > rect.h + .5 or block.overflow:
            raise ValueError(f"Text block {copy[:32]!r} exceeds its region")
    if valign == "top":
        y = rect.y
    elif valign == "center":
        y = rect.center_y - block.height / 2
    elif valign == "bottom":
        y = rect.bottom - block.height
    else:
        raise ValueError("valign must be top, center or bottom")
    if style.align == "center":
        text_x = rect.x + (rect.w - block.width) / 2
    elif style.align == "right":
        text_x = rect.right - block.width
    else:
        text_x = rect.x
    node = Node(
        kind="text", role=role,
        props={"x": rect.x, "y": y, "w": rect.w, "h": block.height,
               "block": block, "align": style.align,
               "color": style.color, "size": style.size,
               "weight": style.weight, "tracking_offset": 0.0},
        qa_class=qa_class,
        meta={"text": copy, "color": style.color, "size": style.size,
              "weight": style.weight,
              "bounds": (text_x, y, text_x + block.width, y + block.height),
              **dict(meta or {})})
    return node


def rich_text_node(role: str, runs: Iterable[Run], style: TextStyle,
                   rect: Rect, fonts: FontBook, *, align: str = "left",
                   valign: str = "center", qa_class: str = "text",
                   meta: Mapping | None = None) -> Node:
    runs = list(runs)
    style = TextStyle(**{**style.__dict__, "align": align})
    block = typeset_runs(runs, style, max(4.0, rect.w), fonts)
    # Rich run scales and per-word tracking can make ink exceed the column even
    # when the total line box fits vertically. Shrink to satisfy both hard
    # dimensions instead of leaving a headline that Studio QA must later reject.
    while (block.height > rect.h + .5 or block.overflow) and style.size > 10:
        style = TextStyle(**{**style.__dict__, "size": int(style.size * .94)})
        block = typeset_runs(runs, style, max(4.0, rect.w), fonts)
    if block.height > rect.h + .5 or block.overflow:
        raise ValueError("Rich headline exceeds its region; shorten the copy")
    if valign == "top":
        y = rect.y
    elif valign == "center":
        y = rect.center_y - block.height / 2
    else:
        y = rect.bottom - block.height
    return Node(
        kind="text", role=role,
        props={"x": rect.x, "y": y, "w": rect.w, "h": block.height,
               "block": block, "align": align, "rich": True,
               "color": None, "size": style.size,
               "weight": style.weight, "tracking_offset": 0.0},
        qa_class=qa_class,
        meta={"text": " ".join(run.text for run in runs),
              "color": style.color, "size": style.size,
              "weight": style.weight,
              "negative_effect": any(run.effect == "negative" for run in runs),
              "negative_words": [run.text.strip() for run in runs
                                 if run.effect == "negative"],
              "bounds": (rect.x, y, rect.x + block.width, y + block.height),
              **dict(meta or {})})


def number_node(role: str, value: float, rect: Rect, tokens: DesignTokens,
                *, fmt: Mapping | None = None, size_role: str = "hero",
                color: tuple[int, int, int] | None = None,
                align: str = "center", qa_class: str = "text",
                meta: Mapping | None = None) -> Node:
    fmt = dict(fmt or {})
    baseline = format_value(value, fmt)
    node = Node(
        kind="number", role=role,
        props={"x": rect.x, "y": rect.y, "w": rect.w, "h": rect.h,
               "value": float(value), "format": fmt,
               "size": tokens.type_size(size_role),
               "weight": "bold", "align": align,
               "color": color or tokens.palette.accent,
               "tracking_offset": 0.0, "baseline_text": baseline},
        qa_class=qa_class,
        meta={"text": baseline, "color": color or tokens.palette.accent,
              "size": tokens.type_size(size_role), "weight": "bold",
              "bounds": (rect.x, rect.y, rect.right, rect.bottom),
              **dict(meta or {})})
    return node


def panel_node(role: str, rect: Rect, tokens: DesignTokens,
               *, fill: tuple[int, int, int] | None = None,
               radius: str = "md", opacity: float = 1.0,
               border: tuple[int, int, int] | None = None,
               shadow: bool = False, qa_class: str = "decor") -> Node:
    return Node(
        kind="round", role=role,
        props={"x": rect.x, "y": rect.y, "w": rect.w, "h": rect.h,
               "r": tokens.radius(radius),
               "fill": fill or tokens.palette.surface,
               "border": border, "border_width": tokens.stroke["hair"],
               "shadow": shadow},
        opacity=opacity, qa_class=qa_class, meta={})


def image_node(role: str, path: str, rect: Rect, *,
               qa_class: str = "decor", meta: Mapping | None = None) -> Node:
    """Place a raster asset into a measured region, preserving its aspect fill."""
    return Node(
        kind="image", role=role,
        props={"path": str(path), "x": rect.x, "y": rect.y,
               "w": rect.w, "h": rect.h},
        qa_class=qa_class, meta=dict(meta or {}))


def video_node(
    role: str,
    path: str,
    rect: Rect,
    *,
    trim_start: float = 0.0,
    trim_end: float | None = None,
    crop: tuple[float, float, float, float] | None = None,
    mask: str = "rounded",
    radius: float = 18.0,
    qa_class: str = "control",
    meta: Mapping | None = None,
) -> Node:
    """Place a native video layer with explicit trim, crop and shape mask (MD-304)."""
    if trim_start < 0:
        raise ValueError("trim_start must be non-negative")
    if trim_end is not None and trim_end <= trim_start:
        raise ValueError("trim_end must exceed trim_start")
    if crop is not None:
        if len(crop) != 4 or not (0.0 <= crop[0] < crop[2] <= 1.0 and 0.0 <= crop[1] < crop[3] <= 1.0):
            raise ValueError("crop must be normalized (x0, y0, x1, y1) in 0..1")
    if mask not in ("rect", "rounded", "circle", "pill"):
        raise ValueError(f"Unsupported video mask {mask!r}")
    return Node(
        kind="video",
        role=role,
        props={
            "path": str(path),
            "x": rect.x,
            "y": rect.y,
            "w": rect.w,
            "h": rect.h,
            "trim_start": float(trim_start),
            "trim_end": float(trim_end) if trim_end is not None else None,
            "crop": tuple(float(v) for v in crop) if crop is not None else None,
            "mask": mask,
            "radius": float(radius),
        },
        qa_class=qa_class,
        meta=dict(meta or {}),
    )


def rule_node(role: str, x: float, y: float, width: float, tokens: DesignTokens,
              *, color: tuple[int, int, int] | None = None,
              thickness: int | None = None) -> Node:
    return Node(kind="rect", role=role,
                props={"x": x, "y": y, "w": width,
                       "h": thickness or tokens.stroke["line"],
                       "fill": color or tokens.palette.accent})


def measure_text(text: str, style: TextStyle, width: float,
                 fonts: FontBook) -> tuple[float, float]:
    """Measure copy, shrinking an overlong unbreakable word to fit the column."""
    if not text or not text.strip():
        return (0.0, 0.0)
    current = style
    block = typeset(text, current, max(4.0, width), fonts)
    while block.overflow and current.size > 6:
        current = TextStyle(**{**current.__dict__,
                               "size": max(6, int(current.size * .94))})
        block = typeset(text, current, max(4.0, width), fonts)
    return (block.width, block.height)


def choreograph(ctx: SceneContext, elements: Iterable[ElementSpec],
                cues: Mapping[str, float] | None = None) -> Choreography:
    return plan_choreography(
        elements, style=ctx.style, scene_index=ctx.scene_index,
        scene_duration=ctx.duration, tokens=ctx.tokens,
        cues=cues or (ctx.scene.get("cues") or {}))


def animate_counter(node: Node, target: float, onset: float,
                    duration: float, *, easing: str = "out-cubic") -> Node:
    node.track("prop.value", number_track(target, onset, duration,
                                           easing=easing))
    return node


def animate_progress(node: Node, onset: float, duration: float,
                     *, easing: str = "out-cubic") -> Node:
    node.track("prop.progress", progress_track(onset, duration, easing=easing))
    return node


def animate_icon_state(primary: Node, secondary: Node, *,
                       switch_time: float, duration: float = 0.32,
                       role: str = "icon-state") -> Node:
    """Cross-fade and scale-settle between two icon states at ``switch_time`` (MD-303)."""
    if switch_time < 0 or duration <= 0:
        raise ValueError("switch_time must be >= 0 and duration > 0")
    end = switch_time + duration
    primary.track("opacity", Track([
        Keyframe(0.0, 1.0, "out-cubic"),
        Keyframe(switch_time, 1.0, "out-cubic"),
        Keyframe(end, 0.0, "out-cubic"),
    ]))
    primary.track("scale", Track([
        Keyframe(0.0, 1.0, "out-cubic"),
        Keyframe(switch_time, 1.0, "out-cubic"),
        Keyframe(end, 0.86, "out-cubic"),
    ]))
    secondary.track("opacity", Track([
        Keyframe(0.0, 0.0, "out-cubic"),
        Keyframe(switch_time, 0.0, "out-cubic"),
        Keyframe(end, 1.0, "out-cubic"),
    ]))
    secondary.track("scale", Track([
        Keyframe(0.0, 0.86, "out-cubic"),
        Keyframe(switch_time, 0.86, "out-cubic"),
        Keyframe(end, 1.0, "back"),
    ]))
    return Node(
        kind="group",
        role=role,
        children=[primary, secondary],
        qa_class="control",
        meta={"switch_time": round(switch_time, 4), "duration": round(duration, 4)},
    )


def parallax_25d_group(
    planes: list[tuple[Node, float]],
    *,
    travel_dx: float = 28.0,
    travel_dy: float = -14.0,
    duration: float = 3.0,
    role: str = "parallax-25d",
) -> Node:
    """Build a multi-plane 2.5D parallax group with depth-weighted motion tracks (MD-501).

    Each entry in ``planes`` is ``(node, depth)`` with ``depth`` in ``0.0..1.0``
    (0 = far background, 1 = near foreground).
    """
    if not planes:
        raise ValueError("parallax_25d_group requires at least one (node, depth) plane")
    if duration <= 0:
        raise ValueError("duration must be positive")
    children: list[Node] = []
    for node, depth in planes:
        z = float(depth)
        if not 0.0 <= z <= 1.0:
            raise ValueError("parallax depth must be between 0.0 and 1.0")
        weight = 0.20 + 0.80 * z
        dx_end = float(travel_dx) * weight
        dy_end = float(travel_dy) * weight
        scale_end = 1.0 + 0.04 * (0.5 + 0.5 * z)
        node.track("dx", Track([
            Keyframe(0.0, 0.0, "smooth"),
            Keyframe(duration, dx_end, "smooth"),
        ]))
        node.track("dy", Track([
            Keyframe(0.0, 0.0, "smooth"),
            Keyframe(duration, dy_end, "smooth"),
        ]))
        node.track("scale", Track([
            Keyframe(0.0, 1.0, "smooth"),
            Keyframe(duration, scale_end, "smooth"),
        ]))
        node.meta["parallax_depth"] = round(z, 3)
        children.append(node)
    return Node(
        kind="group",
        role=role,
        children=children,
        qa_class="control",
        meta={"plane_count": len(children), "component": "parallax_25d"},
    )


def character_accent_group(
    text: str,
    style: TextStyle,
    rect: Rect,
    fonts: FontBook,
    *,
    onset: float = 0.08,
    stagger: float = 0.035,
    tilt_deg: float = -8.0,
    role: str = "char-accent",
) -> Node:
    """Build per-character staggered kinetic accent nodes with bounded tilt (MD-502)."""
    clean = str(text or "").strip()
    if not clean:
        raise ValueError("character_accent_group requires non-empty text")
    if not -25.0 <= tilt_deg <= 25.0:
        raise ValueError("tilt_deg must stay within [-25, 25] degrees")
    font = fonts.get(style.size, style.weight)
    advances = [max(4.0, float(font.getlength(ch))) for ch in clean]
    total_w = sum(advances)
    cursor_x = rect.x + max(0.0, (rect.w - total_w) / 2.0)
    children: list[Node] = []
    for idx, (ch, adv) in enumerate(zip(clean, advances)):
        if ch.isspace():
            cursor_x += adv
            continue
        char_rect = Rect(cursor_x, rect.y, max(adv + 4.0, 12.0), rect.h)
        cnode = text_node(
            f"{role}-ch-{idx}", ch, style, char_rect, fonts,
            align="left", valign="center",
        )
        if cnode is not None:
            t0 = onset + idx * stagger
            t1 = t0 + 0.32
            cnode.track("opacity", Track([
                Keyframe(0.0, 0.0 if t0 > 0 else 1.0, "out-cubic"),
                Keyframe(t0, 0.0, "out-cubic"),
                Keyframe(t1, 1.0, "out-cubic"),
            ]))
            cnode.track("dy", Track([
                Keyframe(0.0, 18.0, "out-quart"),
                Keyframe(t0, 18.0, "out-quart"),
                Keyframe(t1, 0.0, "out-quart"),
            ]))
            cnode.track("rotation", Track([
                Keyframe(0.0, float(tilt_deg), "out-cubic"),
                Keyframe(t0, float(tilt_deg), "out-cubic"),
                Keyframe(t1, 0.0, "out-cubic"),
            ]))
            children.append(cnode)
        cursor_x += adv
    return Node(
        kind="group",
        role=role,
        children=children,
        qa_class="text",
        meta={"text": clean, "character_count": len(children)},
    )


def animate_along_path(
    node: Node,
    waypoints: list[tuple[float, float]],
    *,
    onset: float = 0.0,
    duration: float = 1.0,
    easing: str = "in-out-cubic",
) -> Node:
    """Animate a node's dx/dy offsets along a sequence of (dx, dy) waypoints (MD-503)."""
    if len(waypoints) < 2:
        raise ValueError("animate_along_path requires at least two waypoints")
    if onset < 0 or duration <= 0:
        raise ValueError("onset must be >= 0 and duration > 0")
    step = duration / (len(waypoints) - 1)
    dx_keys = [
        Keyframe(round(onset + idx * step, 4), float(pt[0]), easing)
        for idx, pt in enumerate(waypoints)
    ]
    dy_keys = [
        Keyframe(round(onset + idx * step, 4), float(pt[1]), easing)
        for idx, pt in enumerate(waypoints)
    ]
    node.track("dx", Track(dx_keys))
    node.track("dy", Track(dy_keys))
    return node


def apply_choreography(ctx: SceneContext, elements: dict[str, Node],
                       specs: Iterable[ElementSpec], cues: Mapping[str, float] | None
                       ) -> Choreography:
    plan = choreograph(ctx, specs, cues)
    safe = ctx.layout.safe
    plan.apply(elements, ctx.tokens, seed=ctx.seed,
               safe_bounds=(safe.x, safe.y, safe.right, safe.bottom))
    return plan


def safe_number(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Component value must be numeric")
    if not math.isfinite(float(value)):
        raise ValueError("Component value must be finite")
    return float(value)
