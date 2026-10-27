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


def _smooth(p: float) -> float:
    p = max(0.0, min(1.0, p))
    return p * p * (3 - 2 * p)


def _inverse_smooth(p: float) -> float:
    low, high = 0.0, 1.0
    for _ in range(32):
        middle = (low + high) / 2
        if _smooth(middle) < p:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def _camera_track(onsets: list[float], centers: list[float],
                  pan_duration: float) -> tuple[Track, list[tuple[float, float, float, float]]]:
    keys = [Keyframe(0.0, 0.0, "linear")]
    transitions: list[tuple[float, float, float, float]] = []
    for index in range(1, len(centers)):
        # Finish the pan at the new word's release, so it is centered from
        # the moment it appears and stays centered throughout its fall.
        start = onsets[index] - pan_duration
        end = onsets[index]
        previous, current = centers[index - 1], centers[index]
        transitions.append((start, end, previous, current))
        keys.extend((Keyframe(start, previous, "linear"),
                     Keyframe(end, current, "smooth")))
    return Track(keys), transitions


def _crossing_time(camera_value: float,
                   transitions: list[tuple[float, float, float, float]]) -> float | None:
    for start, end, first, last in transitions:
        if first <= camera_value <= last and last > first:
            progress = (camera_value - first) / (last - first)
            return start + (end - start) * _inverse_smooth(progress)
    return None


def _word_opacity_track(index: int, onsets: list[float],
                        base_lefts: list[float], widths: list[float],
                        camera: Track,
                        transitions: list[tuple[float, float, float, float]],
                        viewport: Rect, scene_duration: float,
                        *, fade_in: float, edge_fade: float,
                        edge_pad: float) -> Track:
    onset = onsets[index]
    left, width = base_lefts[index], widths[index]
    right_edge = viewport.right - edge_pad
    left_edge = viewport.x + edge_pad

    def opacity(time: float) -> float:
        if time <= onset:
            return 0.0
        camera_x = float(camera.value(time))
        screen_left = left - camera_x
        screen_right = screen_left + width
        left_margin = screen_left - left_edge
        right_margin = right_edge - screen_right
        if left_margin < 0 or right_margin < 0:
            return 0.0
        edge_alpha = max(0.0, min(1.0,
                                  min(left_margin, right_margin) / edge_fade))
        entrance_alpha = max(0.0, min(1.0, (time - onset) / fade_in))
        return min(edge_alpha, entrance_alpha)

    times = {0.0, onset, min(scene_duration, onset + fade_in), scene_duration}
    # Fade only at the actual video-frame edges, keeping each trailing word
    # fully visible right up to the edge instead of fading at the UI-safe inset.
    margins = [edge_fade * part / 4 for part in range(5)]
    targets = [right_edge - (left + width) + margin for margin in margins]
    targets.extend(left - left_edge - margin for margin in margins)
    for target in targets:
        crossing = _crossing_time(target, transitions)
        if crossing is not None and onset <= crossing <= scene_duration:
            times.add(crossing)
    keys = [Keyframe(time, opacity(time), "linear")
            for time in sorted(times)]
    return Track(keys)


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
    camera, transitions = _camera_track(onsets, centers, pan_duration)
    # Authored text stays centered within the safe area; horizontal travel is
    # carried by transforms and may continue to the physical frame edges.
    base_lefts = [rect.center_x - word.width / 2 + centers[index]
                  for index, word in enumerate(line.words)]
    widths = [word.width for word in line.words]
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
            index, onsets, base_lefts, widths, camera, transitions, viewport,
            scene_duration, fade_in=.16, edge_fade=ctx_edge_fade(block),
            edge_pad=4.0))
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


def ctx_edge_fade(block: TextBlock) -> float:
    """Use only a short fade at the physical edge of the video frame."""
    return max(8.0, min(14.0, block.style.size * .25))


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
    stagger = _number(config, "stagger", 1.12, .25, 2.5)
    duration = _number(config, "duration", 1.1, .55, 2.5)
    distance_units = _number(config, "distance_units", 168.0, 24.0, 360.0)
    restitution = _number(config, "restitution", .48, .30, .68)
    pan_duration = _number(config, "pan_duration", .28, .12, .65)
    if pan_duration >= stagger:
        raise ValueError("word_drop.pan_duration must be shorter than stagger")

    width = ctx.layout.safe.w
    base_style = resolve_text_style(
        ctx.tokens, "title", theme["ink"], align="left",
        line_height=1.0, balance=False)
    base_style = replace(base_style, size=max(
        ctx.tokens.type_size("subtitle"), round(base_style.size * .80)))
    # Typeset the whole copy on one virtual line. Each individual word is
    # checked against the real safe width; the trailing sequence may travel
    # through the platform margins but fades at the actual frame boundary.
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
    if stagger < actual_settle + .025:
        raise ValueError(
            "word_drop.stagger must leave each word time to finish its rebounds")
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
                  "diminishing restitution, and is centered by a smooth "
                  "rightward camera pan."),
              "word_count": word_count,
              "restitution": restitution,
              "camera_pan_duration": pan_duration,
              "camera_follow": "latest-word-centered",
              "last_word_landing": round(last_landing, 3),
              "actual_rebound_settle": round(actual_settle, 3),
              "bounce_visible": True})
