"""Word-level kinetic typography with ballistic rebounds and camera follow."""
from __future__ import annotations

import math
from dataclasses import replace

from ..core.scene_graph import Node
from ..layout.engine import Rect
from ..motionkit.keyframes import Keyframe, Track
from ..textkit.models import Line, TextBlock
from ..textkit.typesetter import typeset
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


def _ballistic_track(onset: float, distance: float, target_settle: float,
                     restitution: float, min_rebound: float) -> tuple[Track, float]:
    """Model a fall from rest, then several exact gravity/restitution arcs."""
    fall_time = target_settle * (1 - restitution) / (1 + restitution)
    gravity = 2 * distance / (fall_time * fall_time)
    first_impact = onset + fall_time
    keys = [Keyframe(onset, -distance, "linear"),
            Keyframe(first_impact, 0.0, "in-quad")]
    impact = first_impact
    next_fall_time = fall_time

    # Each rebound starts with a lower vertical velocity. out-quad describes
    # the upward arc losing speed under gravity; in-quad describes the exact
    # accelerated return from the apex to the floor.
    while True:
        up_time = restitution * next_fall_time
        apex_height = .5 * gravity * up_time * up_time
        if apex_height <= min_rebound:
            break
        apex = impact + up_time
        impact = apex + up_time
        keys.extend((Keyframe(apex, -apex_height, "out-quad"),
                     Keyframe(impact, 0.0, "in-quad")))
        next_fall_time = up_time
    return Track(keys), impact - onset


def _camera_track(onsets: list[float], centers: list[float],
                  pan_duration: float) -> Track:
    keys = [Keyframe(0.0, 0.0, "linear")]
    for index in range(1, len(centers)):
        # Finish the pan at the new word's release, so it is centered from
        # the moment it appears and stays centered throughout its fall.
        start = onsets[index] - pan_duration
        end = onsets[index]
        previous, current = centers[index - 1], centers[index]
        keys.extend((Keyframe(start, previous, "linear"),
                     Keyframe(end, current, "smooth")))
    return Track(keys)


def _word_opacity_track(onset: float, scene_duration: float,
                        *, fade_in: float) -> Track:
    """Fade a word in once, then let the viewport clip its exit."""
    return Track([
        Keyframe(0.0, 0.0, "linear"),
        Keyframe(onset, 0.0, "linear"),
        Keyframe(onset + fade_in, 1.0, "out-cubic"),
        Keyframe(scene_duration, 1.0, "linear"),
    ])


def _word_nodes(block: TextBlock, rect: Rect, *, onset: float,
                stagger: float, settle_window: float, drop_distance: float,
                restitution: float, min_rebound: float, pan_duration: float,
                viewport: Rect,
                scene_duration: float) -> tuple[Node, float]:
    """Split a measured long line into words and follow each landing."""
    if len(block.lines) != 1:
        raise ValueError("gravity_words requires a single measured line")
    line = block.lines[0]
    if len(line.words) < 2:
        raise ValueError("gravity_words requires at least two words")

    line_y = rect.y + (rect.h - block.height) / 2
    first_center = line.words[0].x + line.words[0].width / 2
    centers = [word.x + word.width / 2 - first_center
               for word in line.words]
    onsets = [onset + index * stagger for index in range(len(line.words))]
    camera = _camera_track(onsets, centers, pan_duration)
    # Authored text stays centered within the safe area; horizontal travel is
    # carried by transforms and clipped only by the physical frame edges.
    children: list[Node] = []
    actual_settle = 0.0

    for index, word in enumerate(line.words):
        word_fall, word_settle = _ballistic_track(
            onsets[index], drop_distance, settle_window,
            restitution, min_rebound)
        actual_settle = max(actual_settle, word_settle)
        local_word = word.__class__(
            word.text, 0.0, word.width, word.font_path, word.font_index,
            word.color, word.run, word.tracking, word.size, word.weight,
            word.effect)
        word_line = Line((local_word,), word.width, line.ascent, line.descent,
                         line.baseline, line.height)
        word_block = TextBlock((word_line,), word.width, float(line.height),
                               block.style, word.text)
        left = rect.center_x - word.width / 2
        node = Node(
            kind="text",
            role=f"headline-word-{index + 1}",
            props={"x": left, "y": line_y, "w": word.width,
                   "h": float(line.height), "block": word_block,
                   "align": "left", "color": word.color,
                   "size": word.size, "weight": word.weight,
                   "tracking_offset": 0.0},
            clip=viewport.bbox,
            qa_class="text",
            meta={"text": word.text,
                  "motion_family": "ballistic-gravity-word-drop",
                  "word_index": index,
                  "camera_follow": "latest-word",
                  "allow_horizontal_edge_travel": True},
        )
        node.track("dy", word_fall)
        node.track("dx", Track([
            Keyframe(key.time,
                     centers[index] - float(camera.value(key.time)),
                     key.easing)
            for key in camera.keys
        ]))
        node.track("opacity", _word_opacity_track(
            onsets[index], scene_duration, fade_in=.16))
        children.append(node)

    group = Node(kind="group", role="headline", children=children,
                 qa_class="text",
                 meta={"component": "gravity_words",
                       "word_count": len(children),
                       "camera_follow": "latest-word-centered",
                       "drop_model": "constant-gravity-with-restitution",
                       "restitution": restitution,
                       "rebound_count": max(
                           0, (len(children[0].tracks["dy"].keys) - 2) // 2)
                       if children else 0,
                       "last_landing": round(onset + (len(children) - 1)
                                             * stagger + actual_settle, 3)})
    return group, actual_settle


def build_gravity_words(ctx: SceneContext, scene: dict) -> BuiltScene:
    """Build a ballistic word sequence that pans to center each new word."""
    theme = _theme(ctx, scene)
    text = " ".join(_headline(scene).split())
    if not text:
        raise ValueError("gravity_words requires non-empty copy")

    config = scene.get("word_drop") or {}
    if not isinstance(config, dict):
        raise ValueError("word_drop must be an object")
    start = _number(config, "start", .24, 0.0, 8.0)
    stagger = _number(config, "stagger", .5, .25, 2.5)
    duration = _number(config, "duration", 1.1, .55, 2.5)
    distance_units = _number(config, "distance_units", 168.0, 24.0, 360.0)
    restitution = _number(config, "restitution", .48, .30, .68)
    pan_duration = _number(config, "pan_duration", .11, .08, .65)
    if pan_duration >= stagger:
        raise ValueError("word_drop.pan_duration must be shorter than stagger")

    width = ctx.layout.safe.w
    base_style = resolve_text_style(
        ctx.tokens, "title", theme["ink"], align="left",
        line_height=1.0, balance=False)
    base_style = replace(base_style, size=max(
        ctx.tokens.type_size("subtitle"), round(base_style.size * .80)))
    # Typeset the whole copy on one virtual line. Each individual word is
    # checked against the real safe width; the viewport clips only the portions
    # that have actually moved beyond the physical frame edge.
    block = typeset(text, base_style, 1_000_000.0, ctx.fonts)
    if len(block.lines) != 1 or len(block.lines[0].words) < 2:
        raise ValueError("gravity_words needs at least two words")
    widest = max(word.width for word in block.lines[0].words)
    if widest > width - 16:
        raise ValueError("Every gravity_words token must fit the safe width")

    layout = ctx.layout.layout("statement", {
        "headline": (width, block.height),
    })
    headline_rect = layout.region("headline")
    distance_px = ctx.tokens.px(distance_units)
    line_y = headline_rect.y + (headline_rect.h - block.height) / 2
    if line_y - distance_px < layout.safe.y:
        raise ValueError(
            "gravity_words fall starts above the safe content area; "
            "reduce distance_units or adjust the composition")

    settle_track, actual_settle = _ballistic_track(
        start, distance_px, duration, restitution,
        max(1.0, ctx.tokens.px(1.5)))
    del settle_track
    word_count = len(block.lines[0].words)
    last_landing = start + (word_count - 1) * stagger + actual_settle
    if ctx.duration - last_landing < max(.8, ctx.tokens.motion.hold):
        raise ValueError(
            "gravity_words needs a readable hold after the final word lands; "
            "extend the scene or shorten the copy")

    headline, actual_settle = _word_nodes(
        block, headline_rect, onset=start, stagger=stagger,
        settle_window=duration, drop_distance=distance_px,
        restitution=restitution,
        min_rebound=max(1.0, ctx.tokens.px(1.5)),
        pan_duration=pan_duration,
        viewport=Rect(0, 0, ctx.width, ctx.height),
        scene_duration=ctx.duration)

    return _finish(
        ctx, scene, layout, _background(ctx, scene, theme),
        {"headline": headline}, [],
        meta={"component": "gravity_words",
              "typography_family": "ballistic-word-drop-camera-follow",
              "animation_intent": (
                  "Each word falls under constant gravity, rebounds with "
                  "diminishing restitution; a speech-paced rightward camera "
                  "pan centers each new word as older words continue past the "
                  "clipped frame edge."),
              "word_count": word_count,
              "restitution": restitution,
              "camera_pan_duration": pan_duration,
              "word_interval": stagger,
              "camera_follow": "latest-word-centered",
              "last_word_landing": round(last_landing, 3),
              "actual_rebound_settle": round(actual_settle, 3),
              "bounce_visible": True})
