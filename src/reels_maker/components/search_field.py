"""Reusable search and prompt-field overlay with a measured typewriter reveal."""
from __future__ import annotations

import math
import unicodedata

from ..core.scene_graph import Node
from ..design.color import parse_hex
from ..layout.engine import Rect
from ..motionkit.keyframes import Keyframe, Track
from ..textkit.typesetter import TextStyle, fit_text
from .base import SceneContext
from .text_motion import typing_track


def _number(config: dict, key: str, default: float, *, low: float,
            high: float) -> float:
    raw = config.get(key, default)
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError(f"search_field.{key} must be numeric")
    value = float(raw)
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(
            f"search_field.{key} must be between {low} and {high}")
    return value


def _entrance(node: Node, *, duration: float, scale_from: float = 1.0,
              delay: float = 0.0) -> None:
    end = delay + duration
    opacity_keys = [Keyframe(0.0, 0.0, "linear")]
    scale_keys = [Keyframe(0.0, scale_from, "linear")]
    if delay > 0:
        opacity_keys.append(Keyframe(delay, 0.0, "linear"))
        scale_keys.append(Keyframe(delay, scale_from, "linear"))
    opacity_keys.append(Keyframe(end, 1.0, "out-cubic"))
    node.track("opacity", Track(opacity_keys))
    if scale_from != 1.0:
        scale_keys.append(Keyframe(end, 1.0, "out-cubic"))
        node.track("scale", Track(scale_keys))


def _cursor_positions(block, fonts, *, text_size: int) -> list[float]:
    """Return cursor x offsets after each character in a single text line."""
    if len(block.lines) != 1:
        raise ValueError("Search query must fit on one line")
    line = block.lines[0]
    positions = [0.0]
    words = line.words
    for index, word in enumerate(words):
        font = fonts.get(word.size or text_size, word.weight or "regular")
        tracking = float(word.tracking)
        for end in range(1, len(word.text) + 1):
            prefix = word.text[:end]
            width = float(font.getlength(prefix))
            width += tracking * max(0, end - 1)
            positions.append(float(word.x) + width)
        if index + 1 < len(words):
            # Whitespace is represented by the measured gap between words.
            positions.append(float(words[index + 1].x))
    return positions


def _cursor_track(positions: list[float], text: str, start: float,
                  duration: float, profile: str) -> Track:
    first = positions[0]
    return Track([Keyframe(key.time, positions[int(key.value)] - first,
                           "linear")
                  for key in typing_track(text, start, duration,
                                          profile=profile).keys])


def _blink_track(start: float, duration: float, *, blink: bool,
                 period: float = .42) -> Track:
    keys = [Keyframe(0.0, 0.0, "linear"),
            Keyframe(start, 1.0, "linear")]
    if blink:
        time = start + period
        visible = 0.0
        while time < duration:
            keys.append(Keyframe(time, visible, "linear"))
            visible = 1.0 - visible
            time += period
    return Track(keys)


def build_search_field(ctx: SceneContext, config: dict) -> list[Node]:
    """Build a safe-area search pill, staged icon, typed query and live cursor.

    The query reveal is a renderer-backed character track. Its layout is
    measured once, while each frame draws only the prefix that has arrived.
    """
    if not isinstance(config, dict):
        raise ValueError("search_field must be an object")
    query = config.get("query", "")
    placeholder = config.get("placeholder", "Szukaj")
    if not isinstance(query, str) or not isinstance(placeholder, str):
        raise ValueError("search_field.query and placeholder must be strings")
    query = " ".join(unicodedata.normalize("NFC", query).split())
    placeholder = " ".join(unicodedata.normalize("NFC", placeholder).split())
    placeholder = placeholder or "Szukaj"
    if "\n" in query or "\r" in query:
        raise ValueError("search_field.query must be a single line")

    safe = ctx.layout.safe
    width_ratio = _number(config, "width_ratio", .84, low=.40, high=1.0)
    height_units = _number(config, "height_units", 98.0, low=60.0, high=180.0)
    center_x = _number(config, "center_x", .5, low=0.0, high=1.0) * ctx.width
    center_y = _number(config, "center_y", .54, low=0.0, high=1.0) * ctx.height
    width = safe.w * width_ratio
    height = float(ctx.tokens.px(height_units))
    rect = Rect(center_x - width / 2, center_y - height / 2, width, height)
    if (rect.x < safe.x or rect.right > safe.right
            or rect.y < safe.y or rect.bottom > safe.bottom):
        raise ValueError("search_field must remain inside the scene safe area")

    fill = parse_hex(config.get("fill", "#FFFFFF"))
    ink = parse_hex(config.get("text_color", "#1B2420"))
    muted = parse_hex(config.get("muted_color", "#7B8580"))
    border = parse_hex(config.get("border_color", "#DDE3DF"))
    accent = parse_hex(config.get("cursor_color", config.get("accent", "#47A013")))
    stroke = max(1, ctx.tokens.px(1.5))
    enter = min(.32, max(.12, ctx.tokens.motion.enter * .62),
                max(.04, ctx.duration * .30))
    icon_delay = min(.18, enter * .58)
    icon_duration = min(.22, max(.04, ctx.duration * .20))

    shell = Node(
        kind="round", role="search-field",
        props={"x": rect.x, "y": rect.y, "w": rect.w, "h": rect.h,
               "r": rect.h / 2, "fill": fill, "border": border,
               "border_width": stroke},
        qa_class="decor", anchor=(center_x, center_y),
        meta={"component": "search-field", "motion": "soft-settle"},
    )
    _entrance(shell, duration=enter, scale_from=.965)

    nodes = [shell]
    icon_enabled = config.get("icon", True)
    if not isinstance(icon_enabled, bool):
        raise ValueError("search_field.icon must be boolean")
    if icon_enabled:
        icon_cx = rect.x + rect.h * .34
        icon_cy = center_y - rect.h * .035
        radius = rect.h * .145
        ring = Node(
            kind="ring", role="search-icon-ring",
            props={"cx": icon_cx, "cy": icon_cy, "r": radius,
                   "width": max(1.5, rect.h * .025), "color": muted},
            qa_class="decor", anchor=(icon_cx, icon_cy),
        )
        _entrance(ring, duration=icon_duration, scale_from=.78,
                  delay=icon_delay)
        handle = Node(
            kind="line", role="search-icon-handle",
            props={"x1": icon_cx + radius * .69,
                   "y1": icon_cy + radius * .69,
                   "x2": icon_cx + radius * 1.48,
                   "y2": icon_cy + radius * 1.48,
                   "width": max(1.5, rect.h * .025), "color": muted},
            qa_class="decor",
        )
        _entrance(handle, duration=min(.18, max(.04, ctx.duration * .18)),
                  delay=icon_delay + .035)
        nodes.extend((ring, handle))

    text_x = rect.x + rect.h * (.70 if icon_enabled else .28)
    text_width = rect.right - text_x - rect.h * .22
    text_size = min(ctx.tokens.type_size("body"), max(10, round(rect.h * .34)))
    base_style = TextStyle(
        size=text_size, color=ink, weight="regular", line_height=1.0,
        tracking=0.0, align="left",
    )
    content = query or placeholder
    style = TextStyle(**{**base_style.__dict__, "color": ink if query else muted})
    block, style = fit_text(content, style, text_width, rect.h * .62,
                            ctx.fonts, min_scale=.52)
    if len(block.lines) != 1:
        raise ValueError("search_field text must fit on one line")
    text_y = center_y - block.height / 2
    text_node = Node(
        kind="text", role="search-query",
        props={"x": text_x, "y": text_y, "w": text_width, "h": block.height,
               "block": block, "align": "left", "color": style.color,
               "size": style.size, "weight": style.weight,
               "tracking_offset": 0.0},
        qa_class="text",
        meta={"text": content, "color": style.color, "size": style.size,
              "weight": style.weight, "bounds": (text_x, text_y,
              text_x + block.width, text_y + block.height)},
    )
    typing_start = min(
        _number(config, "typing_start", min(.38, ctx.duration * .16),
                low=0.0, high=ctx.duration),
        max(0.0, ctx.duration - 1 / ctx.fps),
    )
    if query:
        remaining = max(.04, ctx.duration - typing_start)
        default_typing = min(
            remaining, min(1.05, max(.18, remaining * .62)))
        typing_duration = _number(
            config, "typing_duration", default_typing, low=.04,
            high=remaining,
        )
        typing_duration = min(typing_duration, remaining)
        typing_profile = config.get("typing_profile", "human")
        text_node.track("prop.character_progress", typing_track(
            query, typing_start, typing_duration, profile=typing_profile))
    else:
        typing_duration = 0.0
        typing_profile = "steady"
    nodes.append(text_node)

    focus_enabled = config.get("focus_outline", True)
    if not isinstance(focus_enabled, bool):
        raise ValueError("search_field.focus_outline must be boolean")
    if query and focus_enabled:
        focus_start = min(typing_start + .10, max(0.0, ctx.duration - 2 / ctx.fps))
        focus_settle = min(typing_start + typing_duration + .18,
                           ctx.duration - 1 / ctx.fps)
        focus = Node(
            kind="round", role="search-focus-outline",
            props={"x": rect.x, "y": rect.y, "w": rect.w, "h": rect.h,
                   "r": rect.h / 2, "fill": None,
                   "border": accent, "border_width": max(stroke, ctx.tokens.px(2))},
            opacity=0.0, qa_class="decor",
        )
        focus_keys = [Keyframe(0.0, 0.0, "linear")]
        if typing_start > 0:
            focus_keys.append(Keyframe(typing_start, 0.0, "linear"))
        if focus_start > (focus_keys[-1].time + 1e-7):
            focus_keys.append(Keyframe(focus_start, .72, "out-cubic"))
        if focus_settle > (focus_keys[-1].time + 1e-7):
            focus_keys.append(Keyframe(focus_settle, .25, "out-cubic"))
        focus.track("opacity", Track(focus_keys))
        nodes.append(focus)

    cursor_setting = config.get("cursor", True)
    if not isinstance(cursor_setting, bool):
        raise ValueError("search_field.cursor must be boolean")
    if query and cursor_setting:
        positions = _cursor_positions(block, ctx.fonts, text_size=style.size)
        if len(positions) != len(query) + 1:
            raise ValueError("Could not map the measured search query to glyphs")
        cursor_width = max(2, ctx.tokens.px(3))
        cursor_height = max(8, min(round(style.size * 1.05), round(rect.h * .52)))
        cursor_x = text_x + positions[0]
        cursor_y = center_y - cursor_height / 2
        cursor = Node(
            kind="round", role="search-cursor",
            props={"x": cursor_x, "y": cursor_y, "w": cursor_width,
                   "h": cursor_height, "r": cursor_width / 2,
                   "fill": accent},
            qa_class="decor", anchor=(cursor_x, center_y),
        )
        cursor.track("dx", _cursor_track(positions, query, typing_start,
                                          typing_duration, typing_profile))
        blink_period = _number(config, "blink_period", .42,
                               low=.18, high=1.2)
        cursor.track("opacity", _blink_track(
            min(ctx.duration, typing_start + typing_duration), ctx.duration,
            blink=cursor_setting, period=blink_period))
        nodes.append(cursor)

    return nodes


def build_search_canvas(ctx: SceneContext, scene: dict):
    """Create a copy-free canvas dedicated to an animated search field."""
    from .scene_support import _background, _decor, _finish, _theme

    if not isinstance(scene.get("search_field"), dict):
        raise ValueError("search_canvas requires a search_field object")
    theme = _theme(ctx, scene)
    layout = ctx.layout.layout("statement", {})
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   {}, [], decor=_decor(ctx, scene, theme),
                   meta={"component": "search_canvas"})


__all__ = ["build_search_canvas", "build_search_field"]
