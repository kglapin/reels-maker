"""Reusable note-composition and text-selection motion overlay.

This is an original, generic text-entry treatment inspired by familiar mobile
editor behavior: a composed page, live caret, progressive text entry and a
range highlight with draggable-style endpoints. It does not reproduce Apple
Notes artwork, dimensions, typography or exact controls.
"""
from __future__ import annotations

import math
import unicodedata

from ..core.scene_graph import Node
from ..design.color import mix, parse_hex
from ..layout.engine import Rect
from ..motionkit.keyframes import Keyframe, Track
from ..textkit.typesetter import TextStyle, typeset
from .base import SceneContext
from .text_motion import render_units, typing_track


def _number(config: dict, key: str, default: float, low: float,
            high: float) -> float:
    value = config.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"note_editor.{key} must be numeric")
    value = float(value)
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"note_editor.{key} must be between {low} and {high}")
    return value


def _opacity_track(total: float, start: float, fade_in: float,
                   end: float | None = None) -> Track:
    fade_in = max(1 / 60, min(fade_in, max(1 / 60, total - start)))
    keys = [Keyframe(0.0, 0.0, "linear")]
    if start > 0:
        keys.append(Keyframe(start, 0.0, "linear"))
    keys.append(Keyframe(start + fade_in, 1.0, "out-cubic"))
    if end is not None and end < total:
        hold_end = max(start + fade_in, end - .12)
        if hold_end > start + fade_in:
            keys.append(Keyframe(hold_end, 1.0, "linear"))
        if end > hold_end:
            keys.append(Keyframe(end, 0.0, "in-cubic"))
    return Track(keys)


def _text_node(role: str, content: str, block, style: TextStyle,
               x: float, y: float, *, color=None) -> Node:
    width = block.width
    return Node(
        kind="text", role=role,
        props={"x": x, "y": y, "w": width, "h": block.height,
               "block": block, "align": "left",
               "color": color or style.color, "size": style.size,
               "weight": style.weight, "tracking_offset": 0.0},
        qa_class="text",
        meta={"text": content, "color": color or style.color,
              "size": style.size, "weight": style.weight,
              "bounds": (x, y, x + width, y + block.height)},
    )


def _caption_node(role: str, content: str, style: TextStyle,
                  rect: Rect, fonts) -> Node | None:
    """Small muted metadata line near the top of the sheet."""
    return _text_node(role, content, typeset(content, style, rect.w, fonts),
                      style, rect.x, rect.y, color=style.color)


_KEYBOARD_ROWS = ("QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM")
_TOOLBAR_KEYS = ("123", "return")


def _key_target(char: str) -> str:
    """Map a typed character onto the simplified generic keyboard."""
    if char == " ":
        return "space"
    if char.upper() in "".join(_KEYBOARD_ROWS):
        return char.upper()
    return "123"


def _press_track(presses: list[float]) -> Track:
    """Dip a key for every designated press time, bounded by the next press."""
    keys = [Keyframe(0.0, 1.0, "linear")]
    ordered = sorted(t for t in presses if t >= 0)
    for index, press in enumerate(ordered):
        down = press + .03
        hold = press + .09
        up = min(hold + .10, ordered[index + 1] - .02
                 if index + 1 < len(ordered) else hold + .10)
        if up <= down:
            continue
        keys.append(Keyframe(down, .92, "linear"))
        keys.append(Keyframe(min(hold, up), .92, "linear"))
        if up > min(hold, up):
            keys.append(Keyframe(up, 1.0, "out-cubic"))
    return Track(keys)


def _build_keyboard(ctx: SceneContext, config: dict, *, enter: float,
                    ink: tuple[int, int, int]) -> list[Node]:
    """Original simplified QWERTY block with per-key press dips.

    Letters map to letter keys, space to the space bar and everything else
    (punctuation, digits, symbols) to the ``123`` layout key. This keeps the
    demo recognizable without copying any vendor's exact keyboard artwork.
    """
    kb_config = config if isinstance(config, dict) else {}
    safe = ctx.layout.safe
    height = _number(kb_config, "height_ratio", .30, .18, .46) * safe.h
    fill = parse_hex(kb_config.get("fill", "#23282E"))
    key_fill = parse_hex(kb_config.get("key_fill", "#3A4148"))
    key_ink = parse_hex(kb_config.get("key_text_color", "#EDF0F3"))
    legend_size = max(9, ctx.tokens.px(17))
    container = Rect(safe.x, safe.bottom - height, safe.w, height)
    nodes = [Node(
        kind="round", role="note-keyboard",
        props={"x": container.x, "y": container.y, "w": container.w,
               "h": container.h, "r": ctx.tokens.radius("lg"),
               "fill": fill, "border": mix(fill, (0, 0, 0), .25),
               "border_width": max(1, ctx.tokens.px(1))},
        qa_class="decor", meta={"component": "note-keyboard"},
    )]
    nodes[0].track("opacity", Track([
        Keyframe(0.0, 0.0, "linear"),
        Keyframe(enter, 1.0, "out-cubic"),
    ]))

    pad = max(6.0, ctx.tokens.px(10))
    rows = [list(_KEYBOARD_ROWS[0]), list(_KEYBOARD_ROWS[1]),
            list(_KEYBOARD_ROWS[2])]
    row_gap = max(4.0, ctx.tokens.px(9))
    special = ("123", "space", "return")
    labels = {"123": "123", "space": "", "return": "return"}
    weights = {"123": 1.6, "space": 4.4, "return": 1.9}
    key_h = (container.h - 2 * pad - 3 * row_gap) / 4
    legend_style = TextStyle(legend_size, key_ink, "regular", line_height=1.0)
    presses: dict[str, list[float]] = {}
    render_times = config.get("_press_times")
    if isinstance(render_times, dict):
        for char, times in render_times.items():
            if not isinstance(times, (list, tuple)):
                continue
            target = _key_target(str(char))
            presses.setdefault(target, []).extend(
                float(t) for t in times if isinstance(t, (int, float)))

    def key_node(role: str, rect: Rect, label: str):
        radius = max(3.0, min(rect.w, rect.h) * .16)
        node = Node(
            kind="round", role=role,
            props={"x": rect.x, "y": rect.y, "w": rect.w, "h": rect.h,
                   "r": radius, "fill": key_fill},
            qa_class="decor", anchor=(rect.center_x, rect.center_y),
        )
        node.track("scale", _press_track(presses.get(role, [])))
        if label:
            legend = typeset(label, legend_style, rect.w * .92, ctx.fonts)
            if len(legend.lines) == 1 and not legend.overflow:
                nodes.append(_text_node(
                    f"{role}-legend", label, legend, legend_style,
                    rect.x + (rect.w - legend.width) / 2,
                    rect.y + (rect.h - legend.height) / 2,
                    color=key_ink))
        return node

    for row_index, row in enumerate(rows):
        y = container.y + pad + row_index * (key_h + row_gap)
        gaps = len(row) - 1
        key_w = (container.w - 2 * pad - gaps * ctx.tokens.px(4)) / len(row)
        for col_index, char in enumerate(row):
            rect = Rect(container.x + pad
                        + col_index * (key_w + ctx.tokens.px(4)), y,
                        key_w, key_h)
            nodes.append(key_node(
                f"note-key-{char}", rect, char if len(char) <= 1 else ""))
    y = container.y + pad + 3 * (key_h + row_gap)
    share_total = sum(weights.values())
    insert_gap = ctx.tokens.px(4)
    x = container.x + pad
    for name in special:
        w = (container.w - 2 * pad - 2 * insert_gap) * weights[name] / share_total
        rect = Rect(x, y, w, key_h)
        nodes.append(key_node(f"note-key-{name}", rect, labels[name]))
        x += w + insert_gap
    return nodes


def _build_toolbar(ctx: SceneContext, *, enter: float,
                   muted: tuple[int, int, int]) -> list[Node]:
    """Minimal generic top bar: back-chevron left, dots right."""
    safe = ctx.layout.safe
    bar_h = max(18.0, ctx.tokens.px(30))
    cy = safe.y + bar_h / 2
    stroke = max(1.5, ctx.tokens.px(2.5))
    chevron = Node(
        kind="path", role="note-toolbar-back",
        props={"points": [(safe.x + ctx.tokens.px(22), cy - ctx.tokens.px(9)),
                          (safe.x + ctx.tokens.px(14), cy),
                          (safe.x + ctx.tokens.px(22), cy + ctx.tokens.px(9))],
               "width": stroke, "color": muted},
        qa_class="decor",
    )
    nodes = [chevron]
    for index in range(3):
        nodes.append(Node(
            kind="circle", role=f"note-toolbar-dot-{index}",
            props={"cx": safe.right - ctx.tokens.px(14) - index * ctx.tokens.px(16),
                   "cy": cy, "r": max(1.5, ctx.tokens.px(2)), "fill": muted},
            opacity=.85, qa_class="decor",
        ))
    for child in nodes:
        child.track("opacity", Track([
            Keyframe(0.0, 0.0, "linear"),
            Keyframe(enter, 1.0, "out-cubic"),
        ]))
    return nodes


def _line_positions(line, fonts, text_size: int) -> tuple[str, list[float]]:
    """Build glyph-boundary x positions for one rendered TextBlock line."""
    content = " ".join(word.text for word in line.words)
    positions: list[float] = []
    cursor = 0
    for word_index, word in enumerate(line.words):
        font = fonts.get(word.size or text_size, word.weight or "regular")
        tracking = float(word.tracking)
        if word_index:
            # The typesetter stores word spacing in measured x coordinates.
            # A selection boundary at the space is centered in that gap.
            previous = line.words[word_index - 1]
            previous_font = fonts.get(previous.size or text_size,
                                       previous.weight or "regular")
            previous_end = previous.x + float(previous_font.getlength(previous.text))
            positions.append((previous_end + word.x) / 2)
            cursor += 1
        for count in range(len(word.text) + 1):
            if count == 0 and positions:
                # The space boundary already supplies this word's leading edge.
                continue
            positions.append(float(word.x) + float(font.getlength(word.text[:count]))
                             + tracking * max(0, count - 1))
            cursor += 1
    if not line.words:
        positions.append(0.0)
    return content, positions


def _cursor_points(block, fonts, text_size: int) -> list[tuple[float, float]]:
    """Map renderer character-progress indices to per-character caret anchors."""
    points: list[tuple[float, float]] = []
    for line_index, line in enumerate(block.lines):
        _, x_positions = _line_positions(line, fonts, text_size)
        baseline = float(line.baseline)
        if line_index == 0:
            points.append((x_positions[0] if x_positions else 0.0, baseline))
        else:
            # One progress unit represents a rendered line break.
            points.append((x_positions[0] if x_positions else 0.0, baseline))
        for x in x_positions[1:]:
            points.append((x, baseline))
    expected = len(render_units(block)) + 1
    if len(points) != expected:
        raise ValueError("Could not map note text to measured caret positions")
    return points


def _selection_segments(block, fonts, text_size: int, selected: str):
    visible_lines = [_line_positions(line, fonts, text_size)
                     for line in block.lines]
    joined = " ".join(visible for visible, _ in visible_lines)
    match_start = joined.find(selected)
    if match_start < 0:
        return []
    match_end = match_start + len(selected)
    line_offsets = []
    offset = 0
    for visible, _ in visible_lines:
        line_offsets.append(offset)
        offset += len(visible) + 1
    segments = []
    for line_index, ((visible, positions), line_offset) in enumerate(
            zip(visible_lines, line_offsets)):
        start = max(0, match_start - line_offset)
        end = min(len(visible), match_end - line_offset)
        if end <= start:
            continue
        line = block.lines[line_index]
        x0, x1 = positions[start], positions[end]
        if x1 < x0:
            x0, x1 = x1, x0
        segments.append((line_index, x0, x1, float(line.baseline),
                         float(line.ascent), float(line.height)))
    return segments


def build_note_editor(ctx: SceneContext, config: dict) -> list[Node]:
    if not isinstance(config, dict):
        raise ValueError("note_editor must be an object")
    title = config.get("title", "")
    body = config.get("text", "")
    if not isinstance(title, str) or not isinstance(body, str):
        raise ValueError("note_editor.title and note_editor.text must be strings")
    title = unicodedata.normalize("NFC", title).strip()
    body = unicodedata.normalize("NFC", body).strip()
    if not title and not body:
        raise ValueError("note_editor requires a title or body")
    if len(body) > 900:
        raise ValueError("note_editor.text cannot exceed 900 characters")

    safe = ctx.layout.safe
    width_ratio = _number(config, "width_ratio", .88, .45, 1.0)
    height_ratio = _number(config, "height_ratio", .70, .28, .9)
    center_x = _number(config, "center_x", .5, 0.0, 1.0) * ctx.width
    center_y = _number(config, "center_y", .5, 0.0, 1.0) * ctx.height
    page = Rect(center_x - safe.w * width_ratio / 2,
                center_y - safe.h * height_ratio / 2,
                safe.w * width_ratio, safe.h * height_ratio)
    if (page.x < safe.x or page.right > safe.right
            or page.y < safe.y or page.bottom > safe.bottom):
        raise ValueError("note_editor page must remain inside the scene safe area")

    page_fill = parse_hex(config.get("page_color", "#FAFAF5"))
    ink = parse_hex(config.get("text_color", "#21261F"))
    caption_ink = mix(ink, page_fill, .26)
    accent = parse_hex(config.get("selection_color", "#3478F6"))
    pad = max(12.0, ctx.tokens.px(36))
    content_x = page.x + pad
    content_w = page.w - 2 * pad
    page_node = Node(
        kind="round", role="note-page",
        props={"x": page.x, "y": page.y, "w": page.w, "h": page.h,
               "r": ctx.tokens.radius("lg"), "fill": page_fill,
               "border": tuple(round(channel * .88) for channel in page_fill),
               "border_width": max(1, ctx.tokens.px(1)), "shadow": True},
        qa_class="decor", anchor=(center_x, center_y),
        meta={"component": "note-editor"},
    )
    enter = min(.30, max(.12, ctx.tokens.motion.enter * .58),
                max(.04, ctx.duration * .2))
    page_node.track("opacity", Track([
        Keyframe(0.0, 0.0, "linear"),
        Keyframe(enter, 1.0, "out-cubic"),
    ]))
    page_node.track("scale", Track([
        Keyframe(0.0, .985, "linear"),
        Keyframe(enter, 1.0, "out-cubic"),
    ]))
    nodes = [page_node]

    caption = str(config.get("caption", "")).strip()
    if caption:
        caption_style = TextStyle(
            max(10, ctx.tokens.px(20)),
            caption_ink, "regular", line_height=1.0)
        caption_node = _caption_node(
            "note-caption", unicodedata.normalize("NFC", caption),
            caption_style,
            Rect(content_x, page.y + pad * .52, content_w,
                 max(14.0, ctx.tokens.px(28))),
            ctx.fonts)
        if caption_node:
            nodes.append(caption_node)
            caption_advance = caption_node.props["h"] + ctx.tokens.px(14)
        else:
            caption_advance = 0.0
    else:
        caption_advance = 0.0

    title_size = int(config.get("title_size", ctx.tokens.type_size("title")))
    body_size = int(config.get("body_size", ctx.tokens.type_size("body")))
    if (isinstance(config.get("title_size", title_size), bool)
            or not isinstance(config.get("title_size", title_size), int)
            or not 12 <= title_size <= 180):
        raise ValueError("note_editor.title_size must be an integer in 12..180")
    if (isinstance(config.get("body_size", body_size), bool)
            or not isinstance(config.get("body_size", body_size), int)
            or not 10 <= body_size <= 120):
        raise ValueError("note_editor.body_size must be an integer in 10..120")

    title_y = page.y + pad + caption_advance
    title_style = TextStyle(title_size, ink, "bold", line_height=1.10)
    title_block = None
    body_default_start = min(.5, ctx.duration * .12)
    if title:
        title_block = typeset(title, title_style, content_w, ctx.fonts)
        if title_block.overflow:
            raise ValueError("note_editor.title does not fit the page width")
        title_node = _text_node("note-title", title, title_block,
                                title_style, content_x, title_y)
        title_start = min(enter + .10, max(0.0, ctx.duration - 2 / ctx.fps))
        title_remaining = max(1 / ctx.fps, ctx.duration - title_start)
        title_duration = min(title_remaining,
                             _number(config, "title_duration",
                                     min(.85, max(.18, len(render_units(title_block)) * .025)),
                                     min(1 / ctx.fps, title_remaining),
                                     title_remaining))
        title_node.track("prop.character_progress", typing_track(
            render_units(title_block), title_start, title_duration,
            profile=config.get("typing_profile", "human")))
        body_default_start = min(
            ctx.duration * .42,
            title_start + title_duration + .20)
        nodes.append(title_node)

    body_y = (title_y + (title_block.height if title_block else 0.0)
              + (ctx.tokens.px(24) if title else 0.0))
    body_h = page.bottom - pad - body_y
    body_style = TextStyle(body_size, ink, "regular", line_height=1.34)
    body_block = None
    if body:
        body_block = typeset(body, body_style, content_w, ctx.fonts)
        if body_block.overflow or body_block.height > body_h:
            raise ValueError("note_editor.text exceeds the visible page; shorten it or enlarge the page")

        raw_start = _number(config, "typing_start", body_default_start,
                            0.0, ctx.duration)
        typing_start = min(raw_start, max(0.0, ctx.duration - 1 / ctx.fps))
        remaining = max(1 / ctx.fps, ctx.duration - typing_start)
        typing_duration = _number(
            config, "typing_duration", min(remaining, max(.35, remaining * .58)),
            min(1 / ctx.fps, remaining), remaining)
        profile = config.get("typing_profile", "human")
        units = render_units(body_block)

        selection = config.get("selection")
        selection_start = None
        selection_end = None
        segments = []
        if selection is not None:
            if not isinstance(selection, dict) or not isinstance(selection.get("text"), str):
                raise ValueError("note_editor.selection requires a text string")
            selected_text = unicodedata.normalize("NFC", selection["text"])
            if not selected_text:
                raise ValueError("note_editor.selection.text cannot be empty")
            segments = _selection_segments(body_block, ctx.fonts, body_size,
                                           selected_text)
            if not segments:
                raise ValueError("note_editor.selection.text must appear wholly on one rendered line")
            selection_start = _number(
                selection, "start", typing_start + typing_duration + .18,
                0.0, ctx.duration)
            selection_end = min(ctx.duration, selection_start + _number(
                selection, "duration", min(.9, max(.12, ctx.duration * .18)),
                .08, max(.08, ctx.duration)))

        for index, (line_index, x0, x1, baseline, ascent, line_height) in enumerate(segments):
            sel_y = body_y + baseline - ascent
            sel_h = max(2.0, min(line_height, body_size * 1.35))
            rect_width = max(1.0, x1 - x0)
            highlight = Node(
                kind="round", role=f"note-selection-{index}",
                props={"x": content_x + x0, "y": sel_y,
                       "w": rect_width, "h": sel_h,
                       "r": max(2.0, body_size * .10),
                       "fill": accent},
                opacity=.0, qa_class="decor",
            )
            highlight.track("opacity", _opacity_track(
                ctx.duration, selection_start,
                min(.22, max(.05, ctx.duration * .035)), selection_end))
            highlight.track("prop.w", Track([
                Keyframe(0.0, 0.0, "linear"),
                Keyframe(selection_start, 0.0, "linear"),
                Keyframe(min(selection_start + .24, selection_end),
                         rect_width, "out-cubic"),
            ]))
            nodes.append(highlight)

        body_node = _text_node("note-body", body, body_block,
                               body_style, content_x, body_y)
        body_node.track("prop.character_progress", typing_track(
            units, typing_start, typing_duration, profile=profile))
        nodes.append(body_node)

        caret_enabled = config.get("caret", True)
        if not isinstance(caret_enabled, bool):
            raise ValueError("note_editor.caret must be boolean")
        if caret_enabled:
            points = _cursor_points(body_block, ctx.fonts, body_size)
            first_x, first_baseline = points[0]
            caret_w = max(2.0, ctx.tokens.px(2.5))
            caret_h = max(10.0, body_size * .94)
            caret_y = body_y + first_baseline - caret_h * .84
            caret = Node(
                kind="round", role="note-caret",
                props={"x": content_x + first_x, "y": caret_y,
                       "w": caret_w, "h": caret_h,
                       "r": caret_w / 2, "fill": accent},
                qa_class="decor",
            )
            dx_keys = [Keyframe(typing_start, 0.0, "linear")]
            dy_keys = [Keyframe(typing_start, 0.0, "linear")]
            denominator = max(1, len(points) - 1)
            for point_index, (x, baseline) in enumerate(points[1:], start=1):
                time = typing_start + typing_duration * point_index / denominator
                dx_keys.append(Keyframe(time, x - first_x, "linear"))
                dy_keys.append(Keyframe(time, baseline - first_baseline, "linear"))
            caret.track("dx", Track(dx_keys))
            caret.track("dy", Track(dy_keys))
            blink_start = min(ctx.duration, typing_start + typing_duration)
            opacity_keys = [Keyframe(0.0, 0.0, "linear"),
                            Keyframe(typing_start, 1.0, "linear"),
                            Keyframe(blink_start, 1.0, "linear")]
            if selection_start is not None:
                opacity_keys.append(Keyframe(selection_start, 0.0, "linear"))
            else:
                time, visible = blink_start + .38, 0.0
                while time < ctx.duration:
                    opacity_keys.append(Keyframe(time, visible, "linear"))
                    visible = 1.0 - visible
                    time += .38
            caret.track("opacity", Track(opacity_keys))
            nodes.append(caret)

        if selection is not None:
            for handle_index, segment in enumerate((segments[0], segments[-1])):
                _, x0, x1, baseline, ascent, line_height = segment
                at_start = handle_index == 0
                anchor_x = content_x + (x0 if at_start else x1)
                base_y = body_y + baseline - ascent
                handle_r = max(4.0, ctx.tokens.px(6))
                stem_h = max(6.0, ctx.tokens.px(11))
                stem_y = base_y - stem_h if at_start else base_y + line_height
                stem = Node(
                    kind="line", role=f"note-selection-stem-{handle_index}",
                    props={"x1": anchor_x, "y1": base_y,
                           "x2": anchor_x, "y2": stem_y,
                           "width": max(1.5, ctx.tokens.px(2)),
                           "color": accent},
                    opacity=0.0, qa_class="decor")
                dot = Node(
                    kind="circle", role=f"note-selection-handle-{handle_index}",
                    props={"cx": anchor_x, "cy": stem_y,
                           "r": handle_r, "fill": accent},
                    opacity=0.0, qa_class="decor")
                for handle_node in (stem, dot):
                    handle_node.track("opacity", _opacity_track(
                        ctx.duration, selection_start + .12,
                        min(.16, max(.04, ctx.duration * .025)), selection_end))
                nodes.extend((stem, dot))

        keyboard_cfg = config.get("keyboard")
        if keyboard_cfg not in (None, False):
            if keyboard_cfg is not True and not isinstance(keyboard_cfg, dict):
                raise ValueError("note_editor.keyboard must be true or an object")
            press_times: dict[str, list[float]] = {}
            track = body_node.tracks["prop.character_progress"]
            unit_index = 0
            units_with_spaces: list[str] = []
            for word_index, line in enumerate(body_block.lines):
                for word_in_line, word in enumerate(line.words):
                    if word_in_line:
                        units_with_spaces.append(" ")
                    units_with_spaces.extend(word.text)
            for key in track.keys:
                count = int(key.value + 1e-6)
                while unit_index < count and unit_index < len(units_with_spaces):
                    press_times.setdefault(_key_target(
                        units_with_spaces[unit_index]), []).append(key.time)
                    unit_index += 1
            keyboard_nodes = _build_keyboard(
                ctx, True if keyboard_cfg is True else keyboard_cfg,
                enter=enter, ink=ink)
            for node in keyboard_nodes:
                if node.kind == "round" and node.role.startswith("note-key-"):
                    target = node.role.removeprefix("note-key-")
                    node.track("scale", _press_track(
                        press_times.get(target, [])))
            nodes.extend(keyboard_nodes)
        if config.get("toolbar", True) is True:
            nodes.extend(_build_toolbar(
                ctx, enter=enter, muted=caption_ink))

    # Reject any accidental role collisions before StudioProject merges layers.
    roles = [node.role for node in nodes]
    if len(roles) != len(set(roles)):
        raise ValueError("note_editor generated duplicate node roles")
    return nodes


def build_note_canvas(ctx: SceneContext, scene: dict):
    """Create a copy-free canvas scene for the note-editor interaction layer."""
    from .scene_support import _background, _decor, _finish, _theme

    if not isinstance(scene.get("note_editor"), dict):
        raise ValueError("note_canvas requires a note_editor object")
    theme = _theme(ctx, scene)
    layout = ctx.layout.layout("statement", {})
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   {}, [], decor=_decor(ctx, scene, theme),
                   meta={"component": "note_canvas"})


__all__ = ["build_note_canvas", "build_note_editor"]
