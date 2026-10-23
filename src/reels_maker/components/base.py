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
    style = TextStyle(**{**style.__dict__, "align": align})
    block = typeset_runs(runs, style, max(4.0, rect.w), fonts)
    while block.height > rect.h + .5 and style.size > 10:
        style = TextStyle(**{**style.__dict__, "size": int(style.size * .94)})
        block = typeset_runs(runs, style, max(4.0, rect.w), fonts)
    if block.height > rect.h + .5:
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


def apply_choreography(ctx: SceneContext, elements: dict[str, Node],
                       specs: Iterable[ElementSpec], cues: Mapping[str, float] | None
                       ) -> Choreography:
    plan = choreograph(ctx, specs, cues)
    plan.apply(elements, ctx.tokens, seed=ctx.seed)
    return plan


def safe_number(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Component value must be numeric")
    if not math.isfinite(float(value)):
        raise ValueError("Component value must be finite")
    return float(value)
