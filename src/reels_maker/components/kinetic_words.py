"""Word-level kinetic typography with ballistic rebounds and camera follow."""
from __future__ import annotations

import math
import random
from dataclasses import replace

from ..core.scene_graph import Node
from ..layout.engine import Rect
from ..motionkit.keyframes import Keyframe, Track
from ..textkit.models import Line, TextBlock
from ..textkit.typesetter import typeset
from .base import resolve_text_style
from .model import BuiltScene, SceneContext
from .scene_support import (
    _background, _external_icon, _finish, _headline, _theme,
)


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
        # Finish the pan at the new item's release, so it is centered from
        # the moment it appears and stays centered throughout its fall.
        start = onsets[index] - pan_duration
        end = onsets[index]
        previous, current = centers[index - 1], centers[index]
        keys.extend((Keyframe(start, previous, "linear"),
                     Keyframe(end, current, "smooth")))
    return Track(keys)


def _item_opacity_track(onset: float, scene_duration: float,
                        *, fade_in: float) -> Track:
    """Fade a sequence item in once, then let the viewport clip its exit."""
    return Track([
        Keyframe(0.0, 0.0, "linear"),
        Keyframe(onset, 0.0, "linear"),
        Keyframe(onset + fade_in, 1.0, "out-cubic"),
        Keyframe(scene_duration, 1.0, "linear"),
    ])


def _icon_insertions(config: dict, word_count: int, seed: int
                     ) -> tuple[list[tuple[int, str]], dict]:
    """Choose repeatable word gaps for optional icon-as-word events."""
    icons = config.get("icons", {})
    if icons is None:
        icons = {}
    if not isinstance(icons, dict):
        raise ValueError("word_drop.icons must be an object")
    count = icons.get("count", 0)
    if isinstance(count, bool) or not isinstance(count, int):
        raise ValueError("word_drop.icons.count must be an integer")
    if not 0 <= count < word_count:
        raise ValueError("word_drop.icons.count must be between 0 and word count - 1")
    if count == 0:
        return [], {}

    names = icons.get("names")
    if (not isinstance(names, list) or len(names) != count
            or any(not isinstance(name, str) or not name.strip() for name in names)):
        raise ValueError(
            "word_drop.icons.names must contain one non-empty icon name per icon")
    library = icons.get("library", "lucide")
    from ..icon_library import DEFAULT_STYLES, STYLES, VERSIONS, _identity
    if not isinstance(library, str) or library not in VERSIONS:
        raise ValueError(f"Unsupported word_drop icon library: {library!r}")
    style = icons.get("style", DEFAULT_STYLES[library])
    if not isinstance(style, str) or style not in STYLES[library]:
        raise ValueError(f"Unsupported {library} icon style: {style!r}")
    try:
        for name in names:
            _identity(library, name, style)
    except ValueError as exc:
        raise ValueError(f"Invalid word_drop icon name: {exc}") from exc
    size_ratio = icons.get("size_ratio", .82)
    if isinstance(size_ratio, bool) or not isinstance(size_ratio, (int, float)):
        raise ValueError("word_drop.icons.size_ratio must be a number")
    size_ratio = float(size_ratio)
    if not math.isfinite(size_ratio) or not .35 <= size_ratio <= 1.25:
        raise ValueError("word_drop.icons.size_ratio must be between 0.35 and 1.25")
    from ..design.color import parse_hex
    try:
        rgb = parse_hex(icons.get("color", "#FFFFFF"))
    except (TypeError, ValueError) as exc:
        raise ValueError("word_drop.icons.color must be a hex color") from exc

    gaps = random.Random(seed).sample(range(word_count - 1), count)
    insertions = sorted(zip(gaps, names))
    return insertions, {
        "library": library,
        "style": style,
        "size_ratio": size_ratio,
        "color": rgb,
    }


def _sequence_nodes(block: TextBlock, rect: Rect, *, onset: float,
                    stagger: float, settle_window: float,
                    drop_distance: float, restitution: float,
                    min_rebound: float, pan_duration: float,
                    viewport: Rect, scene_duration: float,
                    icon_insertions: list[tuple[int, str]],
                    icon_config: dict, scene: dict
                    ) -> tuple[Node, float, float, int]:
    """Animate words and inserted icons as equal beats in one sequence."""
    if len(block.lines) != 1:
        raise ValueError("gravity_words requires a single measured line")
    line = block.lines[0]
    if len(line.words) < 2:
        raise ValueError("gravity_words requires at least two words")

    line_y = rect.y + (rect.h - block.height) / 2
    first_center = line.words[0].x + line.words[0].width / 2
    insertion_by_gap = dict(icon_insertions)
    icon_size = float(block.style.size) * icon_config.get("size_ratio", .82)
    items: list[dict] = []
    cursor = line.words[0].x
    for word_index, word in enumerate(line.words):
        items.append({"kind": "text", "word": word, "x": cursor})
        cursor += word.width
        if word_index < len(line.words) - 1:
            gap = max(0.0, line.words[word_index + 1].x
                      - (word.x + word.width))
            if word_index in insertion_by_gap:
                side_gap = max(6.0, gap / 2)
                cursor += side_gap
                items.append({"kind": "icon", "name": insertion_by_gap[word_index],
                              "x": cursor, "size": icon_size})
                cursor += icon_size + side_gap
            else:
                cursor += gap

    centers = [
        item["x"] + (item["word"].width if item["kind"] == "text"
                      else item["size"]) / 2 - first_center
        for item in items
    ]
    onsets = [onset + index * stagger for index in range(len(items))]
    camera = _camera_track(onsets, centers, pan_duration)
    # Authored text stays centered within the safe area; horizontal travel is
    # carried by transforms and clipped only by the physical frame edges.
    children: list[Node] = []
    actual_settle = 0.0

    for index, item in enumerate(items):
        word_fall, word_settle = _ballistic_track(
            onsets[index], drop_distance, settle_window,
            restitution, min_rebound)
        actual_settle = max(actual_settle, word_settle)
        if item["kind"] == "icon":
            icon_scene = {
                **scene,
                "icon_library": icon_config["library"],
                "icon_style": icon_config["style"],
                "icon_names": {"sequence-icon": item["name"]},
            }
            node = _external_icon(
                icon_scene, "sequence-icon", rect.center_x,
                line_y + block.height / 2, icon_size,
                icon_config["color"], role=f"sequence-icon-{index + 1}")
            if node is None:
                raise ValueError("gravity_words could not resolve its icon library")
            node.clip = viewport.bbox
            node.qa_class = "text"
            node.meta.update({
                "motion_family": "ballistic-gravity-word-drop",
                "sequence_index": index,
                "icon_as_word": True,
                "camera_follow": "latest-sequence-item",
                "allow_horizontal_edge_travel": True,
            })
            node.track("dy", word_fall)
            node.track("dx", Track([
                Keyframe(key.time,
                         centers[index] - float(camera.value(key.time)),
                         key.easing)
                for key in camera.keys
            ]))
            node.track("opacity", _item_opacity_track(
                onsets[index], scene_duration, fade_in=.16))
            children.append(node)
            continue

        word = item["word"]
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
            role=f"headline-word-{sum(1 for item in items[:index + 1] if item['kind'] == 'text')}",
            props={"x": left, "y": line_y, "w": word.width,
                   "h": float(line.height), "block": word_block,
                   "align": "left", "color": word.color,
                   "size": word.size, "weight": word.weight,
                   "tracking_offset": 0.0},
            clip=viewport.bbox,
            qa_class="text",
            meta={"text": word.text,
                  "motion_family": "ballistic-gravity-word-drop",
                  "word_index": sum(1 for previous in items[:index + 1]
                                    if previous["kind"] == "text") - 1,
                  "sequence_index": index,
                  "camera_follow": "latest-sequence-item",
                  "allow_horizontal_edge_travel": True},
        )
        node.track("dy", word_fall)
        node.track("dx", Track([
            Keyframe(key.time,
                     centers[index] - float(camera.value(key.time)),
                     key.easing)
            for key in camera.keys
        ]))
        node.track("opacity", _item_opacity_track(
            onsets[index], scene_duration, fade_in=.16))
        children.append(node)

    icon_count = len(icon_insertions)
    word_count = len(line.words)
    group = Node(kind="group", role="headline", children=children,
                 qa_class="text",
                 meta={"component": "gravity_words",
                       "word_count": word_count,
                       "icon_count": icon_count,
                       "sequence_count": len(items),
                       "camera_follow": "latest-sequence-item-centered",
                       "drop_model": "constant-gravity-with-restitution",
                       "restitution": restitution,
                       "rebound_count": max(
                           0, (len(children[0].tracks["dy"].keys) - 2) // 2)
                       if children else 0,
                       "last_landing": round(onset + (len(items) - 1)
                                             * stagger + actual_settle, 3)})
    last_landing = onset + (len(items) - 1) * stagger + actual_settle
    return group, actual_settle, last_landing, icon_count


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
    icon_insertions, icon_config = _icon_insertions(config, word_count, ctx.seed)
    item_count = word_count + len(icon_insertions)
    last_landing = start + (item_count - 1) * stagger + actual_settle
    if ctx.duration - last_landing < max(.8, ctx.tokens.motion.hold):
        raise ValueError(
            "gravity_words needs a readable hold after the final word lands; "
            "extend the scene or shorten the copy")

    headline, actual_settle, last_landing, icon_count = _sequence_nodes(
        block, headline_rect, onset=start, stagger=stagger,
        settle_window=duration, drop_distance=distance_px,
        restitution=restitution,
        min_rebound=max(1.0, ctx.tokens.px(1.5)),
        pan_duration=pan_duration,
        viewport=Rect(0, 0, ctx.width, ctx.height),
        scene_duration=ctx.duration,
        icon_insertions=icon_insertions, icon_config=icon_config,
        scene=scene)

    return _finish(
        ctx, scene, layout, _background(ctx, scene, theme),
        {"headline": headline}, [],
        meta={"component": "gravity_words",
              "typography_family": "ballistic-word-drop-camera-follow",
              "animation_intent": (
                  "Each word or inserted icon falls under constant gravity, "
                  "rebounds with diminishing restitution; a speech-paced "
                  "rightward camera pan centers each new sequence item as "
                  "older items continue past the clipped frame edge."),
              "word_count": word_count,
              "icon_count": icon_count,
              "sequence_count": item_count,
              "restitution": restitution,
              "camera_pan_duration": pan_duration,
              "word_interval": stagger,
              "camera_follow": "latest-sequence-item-centered",
              "last_word_landing": round(last_landing, 3),
              "actual_rebound_settle": round(actual_settle, 3),
              "bounce_visible": True})
