"""Word-level kinetic typography scene builders."""
from __future__ import annotations

import math
from dataclasses import replace

from ..core.scene_graph import Node
from ..layout.engine import Rect
from ..motionkit.keyframes import Keyframe, Track
from ..textkit.models import Line, TextBlock
from ..textkit.typesetter import fit_text
from .base import resolve_text_style
from .model import BuiltScene, SceneContext
from .scene_support import _background, _finish, _headline, _theme


def _number(config: dict, key: str, default: float, low: float,
            high: float) -> float:
    value = config.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"word_drop.{key} must be a number")
    value = float(value)
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"word_drop.{key} must be between {low:g} and {high:g}")
    return value


def _word_nodes(block: TextBlock, rect: Rect, *, onset: float,
                stagger: float, duration: float, drop_distance: float,
                bounce_distance: float) -> list[Node]:
    """Split one measured headline into aligned, independently animated words."""
    if len(block.lines) != 1:
        raise ValueError("gravity_words requires a single-line headline")
    line = block.lines[0]
    if len(line.words) < 2:
        raise ValueError("gravity_words requires at least two words")

    line_y = rect.y + (rect.h - block.height) / 2
    fade_end_offset = min(duration * .30, .22)
    children: list[Node] = []
    for index, word in enumerate(line.words):
        word_onset = onset + index * stagger
        word_fall_end = word_onset + duration * .58
        word_bounce_end = word_onset + duration * .80
        word_landing = word_onset + duration
        local_word = replace(word, x=0.0)
        word_line = Line((local_word,), word.width, line.ascent, line.descent,
                         line.baseline, line.height)
        word_block = TextBlock((word_line,), word.width, float(line.height),
                               block.style, word.text)
        x = rect.x + word.x
        child_y = line_y
        node = Node(
            kind="text",
            role=f"headline-word-{index + 1}",
            props={"x": x, "y": child_y, "w": word.width,
                   "h": float(line.height), "block": word_block,
                   "align": "left", "color": word.color,
                   "size": word.size, "weight": word.weight,
                   "tracking_offset": 0.0},
            qa_class="text",
            meta={"text": word.text,
                  "bounds": (x, child_y, x + word.width,
                             child_y + line.height),
                  "motion_family": "gravity-word-drop",
                  "word_index": index},
        )
        node.track("opacity", Track([
            Keyframe(word_onset, 0.0, "linear"),
            Keyframe(word_onset + fade_end_offset, 1.0, "out-cubic"),
        ]))
        # Accelerate into the baseline, lose about half the impact speed on
        # the rebound, then return on a smooth, damped arc. The easing on each
        # destination keyframe controls the segment leading into it.
        node.track("dy", Track([
            Keyframe(word_onset, -drop_distance, "linear"),
            Keyframe(word_fall_end, 0.0, "in-cubic"),
            Keyframe(word_bounce_end, -bounce_distance, "out-cubic"),
            Keyframe(word_landing, 0.0, "in-out-cubic"),
        ]))
        children.append(node)

    # Keep linting tools and scene inspection aware of the schedule.
    group = Node(kind="group", role="headline", children=children,
                 qa_class="text",
                 meta={"component": "gravity_words",
                       "word_count": len(children),
                       "drop_duration": duration,
                       "last_landing": onset + (len(children) - 1) * stagger
                       + duration})
    return [group]


def build_gravity_words(ctx: SceneContext, scene: dict) -> BuiltScene:
    """Build a short text-only scene where words fall, rebound and settle."""
    theme = _theme(ctx, scene)
    text = " ".join(_headline(scene).split())
    if not text:
        raise ValueError("gravity_words requires a non-empty headline")

    width = ctx.layout.safe.w
    base_style = resolve_text_style(
        ctx.tokens, "title", theme["ink"], align="center",
        line_height=1.0, balance=False)
    block, style = fit_text(
        text, base_style, width, ctx.tokens.px(180),
        ctx.fonts, min_scale=.58)
    if len(block.lines) != 1:
        raise ValueError(
            "gravity_words headline must fit on one line; shorten the copy")
    if style.size < ctx.tokens.type_size("subtitle"):
        raise ValueError(
            "gravity_words headline would be too small; shorten the copy")
    if len(block.lines[0].words) < 2:
        raise ValueError("gravity_words requires at least two words")

    config = scene.get("word_drop") or {}
    if not isinstance(config, dict):
        raise ValueError("word_drop must be an object")
    start = _number(config, "start", .24, 0.0, 8.0)
    stagger = _number(config, "stagger", .24, .06, 1.2)
    duration = _number(config, "duration", .84, .45, 1.8)
    distance_units = _number(config, "distance_units", 168.0, 24.0, 360.0)
    bounce_units = _number(config, "bounce_units", 30.0, 6.0, 72.0)
    bounce_ratio = bounce_units / distance_units
    if not .10 <= bounce_ratio <= .20:
        raise ValueError(
            "word_drop.bounce_units must be 10%–20% of distance_units "
            "for a visible, controlled rebound")

    word_count = len(block.lines[0].words)
    last_landing = start + (word_count - 1) * stagger + duration
    if ctx.duration - last_landing < max(.55, ctx.tokens.motion.hold):
        raise ValueError(
            "gravity_words needs a readable hold after the final word lands; "
            "extend the scene or shorten the phrase")

    measured = {"headline": (width, block.height)}
    layout = ctx.layout.layout("statement", measured)
    headline_rect = layout.region("headline")
    distance_px = ctx.tokens.px(distance_units)
    bounce_px = ctx.tokens.px(bounce_units)
    line_y = headline_rect.y + (headline_rect.h - block.height) / 2
    if line_y - distance_px < layout.safe.y:
        raise ValueError(
            "gravity_words fall starts above the safe content area; "
            "reduce distance_units or move the composition")

    headline = _word_nodes(
        block, headline_rect, onset=start, stagger=stagger,
        duration=duration, drop_distance=distance_px,
        bounce_distance=bounce_px)[0]
    line = block.lines[0]
    floor_y = line_y + line.height + ctx.tokens.px(8)
    floor_left = max(layout.safe.x,
                     headline_rect.x + line.words[0].x - ctx.tokens.px(18))
    floor_right = min(layout.safe.right,
                      headline_rect.x + line.words[-1].x
                      + line.words[-1].width + ctx.tokens.px(18))
    floor = Node(
        kind="line", role="gravity-floor",
        props={"x1": floor_left, "y1": floor_y,
               "x2": floor_right,
               "y2": floor_y, "color": theme["accent"],
               "width": max(1, ctx.tokens.px(2)), "cap": "round"},
        opacity=.30, qa_class="decor",
        meta={"purpose": "visible landing baseline"})

    return _finish(
        ctx, scene, layout, _background(ctx, scene, theme),
        {"headline": headline}, [], decor=[floor],
        meta={"component": "gravity_words",
              "typography_family": "gravity-word-drop",
              "animation_intent": (
                  "Words arrive sequentially, accelerate into a shared baseline, "
                  "rebound once, and settle for reading."),
              "word_count": word_count,
              "last_word_landing": round(last_landing, 3),
              "bounce_visible": True})
