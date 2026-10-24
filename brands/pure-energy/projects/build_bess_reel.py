#!/usr/bin/env python3
"""Build the Pure Energy BESS reels in the channel's own house style.

Style source: @PureEnergyPolska Shorts + professional reference edits
(grayscale/texture edit grammar supplied by the owner):
  - crumpled cream-paper canvas (procedural texture, static — no beat pulsing)
  - persistent white logo pill top-left
  - kinetic word-by-word captions in Baloo 2, purple/amber/ink on paper,
    white + solar orange on footage and dark scenes
  - scrapbook photo cards: slight rotation, white frame, soft shadow
  - translucent deep-purple caption bands over full-bleed photography
  - diagram accents: thin rings, orbiting dots, corner ticks, chart strokes
  - cuts and entrances land on measured percussion onsets of the supplied
    audioera-stylish-trailer-percussion track

Usage (repo root):
    .venv/bin/python brands/pure-energy/projects/build_bess_reel.py \
        [--render] [--qa] [--output PATH]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from reels_maker.components.base import (  # noqa: E402
    BuiltScene, SceneContext, image_node, panel_node)
from reels_maker.components import scenes as _scenes  # noqa: E402
from reels_maker.core.scene_graph import Node  # noqa: E402
from reels_maker.design.color import parse_hex  # noqa: E402
from reels_maker.layout.engine import LayoutPlan  # noqa: E402
from reels_maker.motionkit.choreography import (  # noqa: E402
    Choreography, EntranceTiming)
from reels_maker.motionkit.keyframes import (  # noqa: E402
    Keyframe, Track, opacity_track, scale_track, value_track)
from reels_maker.motionkit.presets import (  # noqa: E402
    number_track, progress_track)
from reels_maker.studio import load_studio  # noqa: E402
from reels_maker.textkit.typesetter import TextStyle, typeset  # noqa: E402

# ------------------------------------------------------------------ palette
# Channel-sampled palette. #FF9600 fails the 3:1 large-text contrast floor on
# cream paper, so paper scenes use amber #C96A00 for display accents while the
# pure solar orange stays on dark/photo surfaces (where it measures 6.4:1+).
C = {
    "orange": parse_hex("#FF9600"),
    "amber": parse_hex("#C96A00"),
    "amber_dark": parse_hex("#9A5700"),
    "purple": parse_hex("#2E2064"),
    "purple2": parse_hex("#433384"),
    "ink": parse_hex("#181525"),
    "body": parse_hex("#3B3748"),
    "muted": parse_hex("#6F6A80"),
    "line": parse_hex("#E6E0F2"),
    "cream": parse_hex("#FFF9F1"),
    "soft": parse_hex("#F7F5FB"),
    "white": parse_hex("#FFFFFF"),
}
# Words carried on a fill chip: fill -> readable word colour.
CHIP_TEXT = {"orange": "ink", "amber": "white", "purple": "white",
             "purple2": "white", "cream": "purple", "white": "purple",
             "soft": "purple", "ink": "white"}

BRAND = Path(__file__).resolve().parents[1]
MANIFEST = Path(__file__).with_suffix(".json").with_name(
    "pure-energy-bess-reels.json")
MUSIC = BRAND / "media/audio/audioera-stylish-trailer-percussion-622881.mp3"

# Percussion grid measured from the supplied track (librosa onset_strength +
# manual check of the strong hits). Scene boundaries sit on these times.
BEATS = [0.53, 1.28, 3.28, 5.29, 6.48, 7.29, 9.38, 11.29, 13.38, 15.29,
         17.65, 19.29, 21.29, 23.38, 25.29, 27.38, 29.29, 33.29, 37.29,
         41.29, 45.38, 49.38, 53.29]


def _rgb(value):
    if isinstance(value, str):
        key = value.lstrip("#")
        return C[key] if key in C else parse_hex(value)
    return tuple(value)


def _pop(node: Node, onset: float, *, scale=.78, dy=20.0, dur=.30) -> Node:
    """Percussive word-pop: opacity + scale overshoot + small rise."""
    node.track("opacity", opacity_track(onset, .10))
    node.track("scale", scale_track(onset, dur, start=scale, easing="back"))
    node.track("dy", Track([
        Keyframe(max(0.0, onset), dy, "out-cubic"),
        Keyframe(onset + dur * .9, 0.0, "out-cubic")]))
    return node


def _rise(node: Node, onset: float, *, dur=.44, dy=34.0) -> Node:
    """Mask-rise caption entrance (calmer than the pop)."""
    node.reveal = {"direction": "up", "progress": 0.0}
    node.track("reveal", value_track(onset, dur, 0.0, 1.0,
                                     easing="out-quart"))
    node.track("dy", Track([
        Keyframe(max(0.0, onset), dy, "out-quart"),
        Keyframe(onset + dur, 0.0, "out-quart")]))
    return node


def _fade(node: Node, onset: float, *, dur=.34) -> Node:
    node.track("opacity", opacity_track(onset, dur))
    return node


def _drop(node: Node, onset: float, *, dur=.55, dy=130.0,
          spin: float = 0.0) -> Node:
    """Scrapbook drop: card falls in and settles onto the paper."""
    node.track("opacity", opacity_track(onset, .16))
    node.track("dy", Track([
        Keyframe(max(0.0, onset), dy, "out-cubic"),
        Keyframe(onset + dur, 0.0, "out-cubic")]))
    if spin and node.rotation is not None:
        base = node.rotation
        node.track("rotation", Track([
            Keyframe(max(0.0, onset), base + spin, "out-cubic"),
            Keyframe(onset + dur, base, "out-cubic")]))
    return node


def _word_block(word: str, style: TextStyle, fonts) -> tuple[object, float, float]:
    block = typeset(word, style, 100_000.0, fonts)
    return block, block.width, block.height


def _word_node(role: str, word: str, style: TextStyle, x: float, y: float,
               fonts, *, qa_class="text") -> Node:
    block, w, h = _word_block(word, style, fonts)
    return Node(
        kind="text", role=role,
        props={"x": x, "y": y, "w": w, "h": h, "block": block,
               "align": "left", "color": style.color, "size": style.size,
               "weight": style.weight, "tracking_offset": 0.0},
        qa_class=qa_class,
        meta={"text": word, "color": style.color, "size": style.size,
              "weight": style.weight,
              "bounds": (x, y, x + w, y + h)})


def _track_in(node: Node, onset: float, *, dur=.55, spread=34.0) -> Node:
    """Letter-spacing settles from wide to normal (editorial tracking-in)."""
    node.props["tracking_offset"] = spread
    node.track("prop.tracking_offset",
               value_track(onset, dur, spread, 0.0, easing="out-expo"))
    node.track("opacity", opacity_track(onset, .18))
    return node


def _chars(ctx: SceneContext, spec: dict, role: str,
           elements: dict, entries: dict, nodes: list) -> None:
    """Per-character cascade for hero lines (advanced kinetic type)."""
    text = str(spec["text"]).strip()
    size = int(spec.get("size", 96))
    colour = _rgb(spec.get("color", "purple"))
    y = float(spec.get("y", .5)) * ctx.height
    onset = float(spec.get("onset", 0.0))
    stagger = float(spec.get("stagger", .035))
    style = TextStyle(size=size, color=colour, weight="bold",
                      line_height=1.0,
                      tracking=float(spec.get("tracking", 0.0)),
                      uppercase=bool(spec.get("uppercase", True)))
    # measure whole line for centring
    block, total, line_h = _word_block(text.replace(" ", " "), style,
                                       ctx.fonts)
    space_w = size * .3
    total += space_w * (text.count(" "))
    x = (float(spec.get("x", .5)) * ctx.width - total / 2
         if spec.get("align", "center") == "center"
         else float(spec.get("x", .10)) * ctx.width)
    safe = ctx.layout.safe
    if total > safe.w:  # shrink like _words does
        scale = safe.w / total * .96
        size = int(size * scale)
        style = TextStyle(size=size, color=colour, weight="bold",
                          line_height=1.0, tracking=style.tracking,
                          uppercase=style.uppercase)
        block, total, line_h = _word_block(text.replace(" ", " "),
                                           style, ctx.fonts)
        total += size * .3 * (text.count(" "))
        x = (float(spec.get("x", .5)) * ctx.width - total / 2
             if spec.get("align", "center") == "center" else x)
    x = max(x, safe.x)
    cursor = x
    index = 0
    for ch in text:
        if ch == " ":
            cursor += size * .3
            continue
        ch_block, cw, ch_h = _word_block(ch, style, ctx.fonts)
        ch_role = f"{role}-c{index}"
        node = Node(
            kind="text", role=ch_role,
            props={"x": cursor, "y": y, "w": cw, "h": ch_h,
                   "block": ch_block, "align": "left", "color": colour,
                   "size": size, "weight": "bold", "tracking_offset": 0.0},
            qa_class="text",
            meta={"text": ch, "color": colour, "size": size,
                  "bounds": (cursor, y, cursor + cw, y + ch_h)})
        _pop(node, onset + index * stagger, scale=.5, dy=26.0, dur=.26)
        nodes.append(node)
        elements[ch_role] = node
        entries[ch_role] = EntranceTiming(ch_role, onset + index * stagger,
                                          .26, "pop-settle", True)
        cursor += cw
        index += 1


def _swap(ctx: SceneContext, spec: dict, role: str,
          elements: dict, entries: dict, nodes: list) -> None:
    """Strike-through word replacement: old claim struck out, benefit pops in."""
    size = int(spec.get("size", 118))
    y = float(spec.get("y", .5)) * ctx.height
    onset = float(spec.get("onset", 0.0))
    swap_at = float(spec.get("swap_at", onset + 1.2))
    safe = ctx.layout.safe
    for tag, text, color_key, when in (
            ("a", spec["text1"], spec.get("color1", "purple"), onset),
            ("b", spec["text2"], spec.get("color2", "amber"), swap_at + .12)):
        style = TextStyle(size=size, color=_rgb(color_key), weight="bold",
                          line_height=1.0, uppercase=True)
        block, w, h = _word_block(str(text), style, ctx.fonts)
        while w > safe.w and size > 12:
            size = int(size * safe.w / w * .96)
            style = TextStyle(size=size, color=_rgb(color_key),
                              weight="bold", line_height=1.0,
                              uppercase=True)
            block, w, h = _word_block(str(text), style, ctx.fonts)
        x = float(spec.get("x", .5)) * ctx.width - w / 2
        node = Node(
            kind="text", role=f"{role}-{tag}",
            props={"x": x, "y": y, "w": w, "h": h, "block": block,
                   "align": "left", "color": _rgb(color_key), "size": size,
                   "weight": "bold", "tracking_offset": 0.0},
            qa_class="text",
            meta={"text": str(text), "color": _rgb(color_key),
                  "size": size, "bounds": (x, y, x + w, y + h)})
        if tag == "a":
            _pop(node, when)
            node.track("opacity", Track([
                Keyframe(0.0, 0.0, "linear"),
                Keyframe(when + .3, 1.0, "linear"),
                Keyframe(swap_at, 1.0, "linear"),
                Keyframe(swap_at + .3, .22, "linear")]))
            strike = Node(
                kind="rect", role=f"{role}-strike",
                props={"x": x - size * .06, "y": y + h * .52,
                       "w": w + size * .12, "h": max(4.0, size * .08),
                       "fill": _rgb(spec.get("strike_color", "orange"))},
                qa_class="decor", meta={})
            strike.reveal = {"direction": "right", "progress": 0.0}
            strike.track("reveal", value_track(swap_at, .28, 0.0, 1.0,
                                               easing="out-cubic"))
            strike.track("opacity", Track([
                Keyframe(0.0, 0.0, "linear"),
                Keyframe(swap_at, 0.0, "linear"),
                Keyframe(swap_at + .28, 1.0, "linear"),
                Keyframe(swap_at + .42, 1.0, "linear"),
                Keyframe(swap_at + .72, 0.0, "linear")]))
            nodes.append(strike)
            elements[f"{role}-strike"] = strike
            entries[f"{role}-strike"] = EntranceTiming(
                f"{role}-strike", swap_at, .28, "reveal-right", True)
        else:
            _pop(node, when, scale=.6, dy=0.0, dur=.3)
        nodes.append(node)
        elements[f"{role}-{tag}"] = node
        entries[f"{role}-{tag}"] = EntranceTiming(
            f"{role}-{tag}", when, .3, "pop-settle", True)


def _words(ctx: SceneContext, spec: dict, role: str,
           elements: dict, entries: dict, nodes: list) -> None:
    """Kinetic word-by-word caption line (channel signature)."""
    if spec.get("mode") == "chars":
        _chars(ctx, spec, role, elements, entries, nodes)
        return
    text = str(spec["text"]).strip()
    size = int(spec.get("size", 96))
    colors = spec.get("colors") or [spec.get("color", "purple")]
    if isinstance(colors, str):
        colors = [colors]
    y = float(spec.get("y", .5)) * ctx.height
    onset = float(spec.get("onset", 0.0))
    stagger = float(spec.get("stagger", .30))
    preset = spec.get("preset", "pop")
    tracking = float(spec.get("tracking", 0.0))
    chips = {int(k): v for k, v in (spec.get("chips") or {}).items()}
    words = [w for w in text.split() if w]
    space = size * float(spec.get("space", .24))

    # measure every word first so the line can be centred before placement
    safe = ctx.layout.safe
    fits_safe = None
    for _attempt in range(3):
        measured = []
        for index, word in enumerate(words):
            colour = _rgb(colors[min(index, len(colors) - 1)])
            style = TextStyle(size=size, color=colour, weight="bold",
                              line_height=1.0, tracking=tracking,
                              uppercase=bool(spec.get("uppercase", True)))
            block, w, h = _word_block(word, style, ctx.fonts)
            measured.append((word, style, w, h))
        space = size * float(spec.get("space", .24))
        total = sum(m[2] for m in measured) + space * (len(measured) - 1)
        if total <= safe.w:
            fits_safe = measured
            break
        size = max(12, int(size * safe.w / total * .96))
    measured = fits_safe or measured
    total = min(total, safe.w)
    align = spec.get("align", "center")
    if align == "center":
        x = float(spec.get("x", .5)) * ctx.width - total / 2
    elif align == "right":
        x = float(spec.get("x", .86)) * ctx.width - total
    else:
        x = float(spec.get("x", .10)) * ctx.width
    x = max(x, safe.x)

    for index, (word, style, w, h) in enumerate(measured):
        w_onset = onset + index * stagger
        w_role = f"{role}-w{index}"
        chip_fill = chips.get(index)
        if chip_fill:
            pad_x, pad_y = size * .22, size * .16
            chip = Node(
                kind="round", role=f"{w_role}-chip",
                props={"x": x - pad_x, "y": y + h * .06 - pad_y,
                       "w": w + pad_x * 2, "h": h + pad_y * 1.6,
                       "r": size * .24, "fill": _rgb(chip_fill)},
                qa_class="decor", meta={})
            chip.reveal = {"direction": "right", "progress": 0.0}
            chip.track("reveal", value_track(w_onset, .30, 0.0, 1.0,
                                             easing="in-out-quart"))
            nodes.append(chip)
            elements[f"{w_role}-chip"] = chip
            entries[f"{w_role}-chip"] = EntranceTiming(
                f"{w_role}-chip", w_onset, .30, "reveal-right", True)
            style = TextStyle(size=size,
                              color=_rgb(CHIP_TEXT.get(chip_fill, "white")),
                              weight="bold", line_height=1.0,
                              tracking=tracking,
                              uppercase=bool(spec.get("uppercase", True)))
        node = _word_node(w_role, word, style, x, y, ctx.fonts)
        if preset == "rise":
            _rise(node, w_onset)
        elif preset == "fade":
            _fade(node, w_onset)
        else:
            _pop(node, w_onset)
        nodes.append(node)
        elements[w_role] = node
        entries[w_role] = EntranceTiming(
            w_role, w_onset, .34, "pop-settle" if preset == "pop" else preset,
            True)
        x += w + space


def _bigtext(ctx: SceneContext, spec: dict, role: str,
             elements: dict, entries: dict, nodes: list) -> None:
    """One oversized literal string (e.g. '11,9' keeps the Polish comma)."""
    size = int(spec.get("size", 220))
    colour = _rgb(spec.get("color", "purple"))
    style = TextStyle(size=size, color=colour, weight="bold",
                      line_height=1.0,
                      tracking=float(spec.get("tracking", 0.0)),
                      uppercase=bool(spec.get("uppercase", True)))
    block, w, h = _word_block(str(spec["text"]), style, ctx.fonts)
    safe_w = ctx.layout.safe.w
    while w > safe_w and size > 12:
        size = int(size * safe_w / w * .96)
        style = TextStyle(size=size, color=colour, weight="bold",
                          line_height=1.0,
                          tracking=float(spec.get("tracking", 0.0)),
                          uppercase=bool(spec.get("uppercase", True)))
        block, w, h = _word_block(str(spec["text"]), style, ctx.fonts)
    align = spec.get("align", "center")
    if align == "center":
        x = float(spec.get("x", .5)) * ctx.width - w / 2
    else:
        x = float(spec.get("x", .10)) * ctx.width
    y = float(spec.get("y", .4)) * ctx.height
    node = Node(
        kind="text", role=role,
        props={"x": x, "y": y, "w": w, "h": h, "block": block,
               "align": "left", "color": colour, "size": size,
               "weight": "bold", "tracking_offset": 0.0},
        qa_class="text",
        meta={"text": str(spec["text"]), "color": colour, "size": size,
              "weight": "bold", "bounds": (x, y, x + w, y + h)})
    onset = float(spec.get("onset", 0.0))
    preset = spec.get("preset", "pop")
    (_rise if preset == "rise" else _pop)(node, onset)
    nodes.append(node)
    elements[role] = node
    entries[role] = EntranceTiming(role, onset, .4, "pop-settle", True)


def _count(ctx: SceneContext, spec: dict, role: str,
           elements: dict, entries: dict, nodes: list) -> None:
    """Animated metric counter rendered like the giant hero numbers."""
    size = int(spec.get("size", 300))
    colour = _rgb(spec.get("color", "amber"))
    rect_h = size * 1.18
    x = float(spec.get("x", .5)) * ctx.width
    y = float(spec.get("y", .4)) * ctx.height
    node = Node(
        kind="number", role=role,
        props={"x": x - ctx.width * .30, "y": y, "w": ctx.width * .6,
               "h": rect_h, "value": 0.0,
               "format": dict(spec.get("format") or {"suffix": "%"}),
               "size": size, "weight": "bold",
               "align": spec.get("align", "center"), "color": colour,
               "tracking_offset": 0.0},
        qa_class="text",
        meta={"text": str(spec.get("value", "")), "color": colour,
              "size": size, "weight": "bold",
              "bounds": (x - ctx.width * .30, y,
                         x + ctx.width * .30, y + rect_h)})
    onset = float(spec.get("onset", 0.0))
    dur = float(spec.get("dur", .9))
    node.track("prop.value",
               number_track(float(spec["value"]), onset, dur,
                            easing="out-cubic"))
    node.track("opacity", opacity_track(onset, .14))
    node.track("scale", scale_track(onset, .4, start=.7, easing="back"))
    nodes.append(node)
    elements[role] = node
    entries[role] = EntranceTiming(role, onset, .4, "pop-settle", True)


def _photo(ctx: SceneContext, spec: dict, role: str,
           elements: dict, entries: dict, nodes: list) -> None:
    """Scrapbook photo card: white frame + shadow + slight tilt."""
    x, y, w, h = (float(v) for v in spec["rect"])
    X, Y, W, H = (x * ctx.width, y * ctx.height,
                  w * ctx.width, h * ctx.height)
    rotation = float(spec.get("rotation", 0.0))
    framed = spec.get("frame", "card") == "card"
    children = []
    pad = float(spec.get("pad", 16))
    if framed:
        frame = Node(
            kind="round", role=f"{role}-frame",
            props={"x": X - pad, "y": Y - pad, "w": W + pad * 2,
                   "h": H + pad * 2, "r": float(spec.get("radius", 14)) + pad,
                   "fill": C["white"], "shadow": True},
            qa_class="decor", meta={})
        children.append(frame)
    img = image_node(
        f"{role}-img", str(BRAND / spec["src"]),
        _rect(X, Y, W, H), meta={})
    img.props["radius"] = float(spec.get("radius", 14))
    if spec.get("pan_x") or spec.get("pan_y"):
        img.props["pan_x"] = float(spec.get("pan_x", 0))
        img.props["pan_y"] = float(spec.get("pan_y", 0))
    if spec.get("zoom"):
        img.props["zoom"] = float(spec["zoom"])
    children.append(img)
    group = Node(kind="group", role=role, children=children,
                 rotation=rotation,
                 anchor=(X + W / 2, Y + H / 2),
                 qa_class="decor", meta={})
    onset = float(spec.get("onset", 0.0))
    preset = spec.get("preset", "drop")
    if preset == "drop":
        _drop(group, onset, spin=float(spec.get("spin", 4.0)))
    elif preset == "rise":
        _rise(group, onset, dur=.5)
    else:
        _fade(group, onset)
    nodes.append(group)
    elements[role] = group
    entries[role] = EntranceTiming(role, onset, .55, "rise", True)


def _rect(x, y, w, h):
    from reels_maker.layout.engine import Rect
    return Rect(x, y, w, h)


def _band(ctx: SceneContext, spec: dict, role: str,
          elements: dict, entries: dict, nodes: list) -> None:
    """Translucent caption band (the channel's purple strip on footage)."""
    x, y, w, h = (float(v) for v in spec["rect"])
    node = Node(
        kind="rect", role=role,
        props={"x": x * ctx.width, "y": y * ctx.height,
               "w": w * ctx.width, "h": h * ctx.height,
               "fill": _rgb(spec.get("fill", "purple"))},
        opacity=float(spec.get("opacity", .85)),
        qa_class="decor", meta={})
    onset = float(spec.get("onset", 0.0))
    direction = spec.get("direction", "right")
    node.reveal = {"direction": direction, "progress": 0.0}
    node.track("reveal", value_track(onset, float(spec.get("dur", .5)),
                                     0.0, 1.0, easing="in-out-quart"))
    nodes.append(node)
    elements[role] = node
    entries[role] = EntranceTiming(role, onset, .5, "reveal-right", True)


def _panel(ctx: SceneContext, spec: dict, role: str,
           elements: dict, entries: dict, nodes: list) -> None:
    x, y, w, h = (float(v) for v in spec["rect"])
    node = panel_node(
        role, _rect(x * ctx.width, y * ctx.height,
                    w * ctx.width, h * ctx.height),
        ctx.tokens, fill=_rgb(spec.get("fill", "white")),
        radius=spec.get("radius", "lg"),
        opacity=float(spec.get("opacity", 1.0)),
        border=_rgb(spec["border"]) if spec.get("border") else None,
        shadow=bool(spec.get("shadow", False)))
    if spec.get("r") is not None:
        node.props["r"] = float(spec["r"])
    onset = float(spec.get("onset", 0.0))
    preset = spec.get("preset", "fade")
    if preset == "reveal":
        node.reveal = {"direction": spec.get("direction", "right"),
                       "progress": 0.0}
        node.track("reveal", value_track(onset, .5, 0.0, 1.0,
                                         easing="in-out-quart"))
    elif preset == "pop":
        _pop(node, onset)
    elif preset == "drop":
        _drop(node, onset)
    else:
        _fade(node, onset)
    nodes.append(node)
    elements[role] = node
    entries[role] = EntranceTiming(role, onset, .4, "fade-up", True)


def _image(ctx: SceneContext, spec: dict, role: str,
           elements: dict, entries: dict, nodes: list) -> None:
    x, y, w, h = (float(v) for v in spec["rect"])
    node = image_node(role, str(BRAND / spec["src"]),
                      _rect(x * ctx.width, y * ctx.height,
                            w * ctx.width, h * ctx.height))
    if spec.get("radius"):
        node.props["radius"] = float(spec["radius"])
    onset = float(spec.get("onset", 0.0))
    preset = spec.get("preset", "pop")
    (_pop if preset == "pop" else _fade)(node, onset)
    nodes.append(node)
    elements[role] = node
    entries[role] = EntranceTiming(role, onset, .4, "pop-settle", True)


def _pill(ctx: SceneContext, spec: dict, role: str,
          elements: dict, entries: dict, nodes: list) -> None:
    """Persistent white logo pill, channel position top-left."""
    scale = float(spec.get("scale", 1.0))
    w, h = 250 * scale, 92 * scale
    x = float(spec.get("x", .07)) * ctx.width
    y = float(spec.get("y", .075)) * ctx.height
    back = Node(
        kind="round", role=f"{role}-bg",
        props={"x": x, "y": y, "w": w, "h": h, "r": h * .32,
               "fill": C["white"], "shadow": True},
        qa_class="decor", meta={})
    # logo asset is 1.8:1 including its padding; keep that ratio so the
    # cover-fit never crops the mark.
    lh = h * .70
    lw = lh * 1.8
    logo = image_node(f"{role}-img", str(BRAND / "assets/logo-light-bg.png"),
                      _rect(x + (w - lw) / 2, y + (h - lh) / 2, lw, lh))
    group = Node(kind="group", role=role, children=[back, logo],
                 qa_class="control", meta={})
    onset = float(spec.get("onset", 0.0))
    if onset > 0:
        _pop(group, onset, scale=.7, dy=18.0, dur=.4)
    nodes.append(group)
    elements[role] = group
    entries[role] = EntranceTiming(role, onset, .4, "pop-settle", True)


def _ring(ctx: SceneContext, spec: dict, role: str,
          elements: dict, entries: dict, nodes: list) -> None:
    cx = float(spec.get("cx", .5)) * ctx.width
    cy = float(spec.get("cy", .4)) * ctx.height
    r = float(spec.get("r", .28)) * ctx.width
    progress = float(spec.get("to", 1.0))
    node = Node(
        kind="ring", role=role,
        props={"cx": cx, "cy": cy, "r": r,
               "width": float(spec.get("width", 7)),
               "color": _rgb(spec.get("color", "purple2")),
               "progress": 0.0,
               "start_angle": float(spec.get("start_angle", -90))},
        qa_class="decor", meta={})
    onset = float(spec.get("onset", 0.0))
    node.track("prop.progress",
               value_track(onset, float(spec.get("dur", .8)),
                           0.0, progress, easing="out-cubic"))
    node.track("opacity", opacity_track(onset, .12))
    track = spec.get("track")
    if track:
        halo = Node(
            kind="ring", role=f"{role}-track",
            props={"cx": cx, "cy": cy, "r": r,
                   "width": float(spec.get("width", 7)),
                   "color": _rgb(track), "progress": 1.0,
                   "start_angle": -90},
            opacity=float(spec.get("track_opacity", .18)),
            qa_class="decor", meta={})
        nodes.append(halo)
        elements[f"{role}-track"] = halo
    nodes.append(node)
    elements[role] = node
    entries[role] = EntranceTiming(role, onset, .8, "scale-focus", True)
    for index, dot in enumerate(spec.get("dots") or []):
        angle = math.radians(float(dot["angle"]))
        d_role = f"{role}-dot{index}"
        d = Node(
            kind="circle", role=d_role,
            props={"cx": cx + math.cos(angle) * r,
                   "cy": cy + math.sin(angle) * r,
                   "r": float(dot.get("r", 11)),
                   "fill": _rgb(dot.get("color", "amber"))},
            qa_class="decor", meta={})
        _pop(d, float(dot.get("onset", onset + .5)), scale=.4, dy=0)
        nodes.append(d)
        elements[d_role] = d
        entries[d_role] = EntranceTiming(d_role, float(dot.get("onset", 0)),
                                         .3, "pop-settle", True)


def _path(ctx: SceneContext, spec: dict, role: str,
          elements: dict, entries: dict, nodes: list) -> None:
    points = [(float(p[0]) * ctx.width, float(p[1]) * ctx.height)
              for p in spec["points"]]
    node = Node(
        kind="path", role=role,
        props={"points": points, "color": _rgb(spec.get("color", "purple")),
               "width": float(spec.get("width", 5)),
               "progress": 0.0,
               "closed": bool(spec.get("closed", False)),
               "fill": bool(spec.get("fill", False))},
        opacity=float(spec.get("opacity", 1.0)),
        qa_class="decor", meta={})
    onset = float(spec.get("onset", 0.0))
    dur = float(spec.get("dur", .7))
    node.track("prop.progress",
               progress_track(onset, dur, easing="out-cubic"))
    node.track("opacity", Track([
        Keyframe(0.0, 0.0, "linear"),
        Keyframe(max(0.0, onset), 0.0, "linear"),
        Keyframe(onset + .10, float(spec.get("opacity", 1.0)), "linear")]))
    nodes.append(node)
    elements[role] = node
    entries[role] = EntranceTiming(role, onset, dur, "reveal-right", True)


def _sweep(ctx: SceneContext, spec: dict, role: str,
           elements: dict, entries: dict, nodes: list) -> None:
    """Light-beam sweep: translucent wedge glides across the frame."""
    w = float(spec.get("width", .24)) * ctx.width
    node = Node(
        kind="rect", role=role,
        props={"x": -w * 1.5, "y": -ctx.height * .25,
               "w": w, "h": ctx.height * 1.5,
               "fill": _rgb(spec.get("fill", "white"))},
        rotation=float(spec.get("angle", 18)),
        anchor=(0.0, 0.0), opacity=0.0, qa_class="decor", meta={})
    onset = float(spec.get("onset", 0.0))
    dur = float(spec.get("dur", .55))
    node.track("dx", Track([
        Keyframe(0.0, 0.0, "linear"),
        Keyframe(max(0.0, onset), 0.0, "linear"),
        Keyframe(onset + dur, ctx.width * 1.7, "out-cubic")]))
    node.track("opacity", Track([
        Keyframe(0.0, 0.0, "linear"),
        Keyframe(max(0.0, onset), 0.0, "linear"),
        Keyframe(onset + dur * .25, float(spec.get("opacity", .10)),
                 "out-cubic"),
        Keyframe(onset + dur, 0.0, "linear")]))
    nodes.append(node)
    elements[role] = node
    entries[role] = EntranceTiming(role, onset, dur, "slide-left", True)


def _ticks(ctx: SceneContext, spec: dict, role: str,
           elements: dict, entries: dict, nodes: list) -> None:
    """Technical corner ticks around a rect (diagram accent from refs)."""
    x, y, w, h = (float(v) for v in spec["rect"])
    X, Y, W2, H2 = (x * ctx.width, y * ctx.height,
                    w * ctx.width, h * ctx.height)
    size = float(spec.get("size", .05)) * ctx.width
    th = float(spec.get("thickness", 5))
    colour = _rgb(spec.get("color", "purple"))
    corners = [
        [(X, Y + size), (X, Y), (X + size, Y)],
        [(X + W2 - size, Y), (X + W2, Y), (X + W2, Y + size)],
        [(X, Y + H2 - size), (X, Y + H2), (X + size, Y + H2)],
        [(X + W2 - size, Y + H2), (X + W2, Y + H2), (X + W2, Y + H2 - size)],
    ]
    onset = float(spec.get("onset", 0.0))
    stagger = float(spec.get("stagger", .12))
    for index, pts in enumerate(corners):
        tick = Node(kind="path", role=f"{role}-t{index}",
                    props={"points": pts, "color": colour, "width": th,
                           "progress": 0.0},
                    qa_class="decor", meta={})
        tick.track("prop.progress",
                   progress_track(onset + index * stagger, .28,
                                  easing="out-cubic"))
        tick.track("opacity", opacity_track(onset + index * stagger, .1))
        nodes.append(tick)
        elements[f"{role}-t{index}"] = tick
        entries[f"{role}-t{index}"] = EntranceTiming(
            f"{role}-t{index}", onset + index * stagger, .28,
            "fade-up", True)


def _tag(ctx: SceneContext, spec: dict, role: str,
         elements: dict, entries: dict, nodes: list) -> None:
    """Numbered paper tag (step rows on the CTA-adjacent scene)."""
    x, y, w, h = (float(v) for v in spec["rect"])
    X, Y, W2, H2 = (x * ctx.width, y * ctx.height,
                    w * ctx.width, h * ctx.height)
    onset = float(spec.get("onset", 0.0))
    card = panel_node(f"{role}-card", _rect(X, Y, W2, H2), ctx.tokens,
                      fill=C["white"], radius="lg", shadow=True)
    num_style = TextStyle(size=int(spec.get("num_size", 58)),
                          color=_rgb(spec.get("num_color", "amber")),
                          weight="bold", line_height=1.0)
    label_style = TextStyle(size=int(spec.get("text_size", 44)),
                            color=_rgb(spec.get("text_color", "purple")),
                            weight="bold", line_height=1.0,
                            uppercase=True)
    num_block, nw, nh = _word_block(str(spec.get("num", "")), num_style,
                                  ctx.fonts)
    num = Node(kind="text", role=f"{role}-num",
               props={"x": X + H2 * .42, "y": Y + (H2 - nh) / 2,
                      "w": nw, "h": nh, "block": num_block,
                      "align": "left", "color": num_style.color,
                      "size": num_style.size, "weight": "bold",
                      "tracking_offset": 0.0},
               qa_class="text",
               meta={"text": str(spec.get("num")), "color": num_style.color,
                     "size": num_style.size,
                     "bounds": (X + H2 * .42, Y + (H2 - nh) / 2,
                                X + H2 * .42 + nw, Y + (H2 + nh) / 2)})
    label_block, lw, lh = _word_block(str(spec["text"]), label_style,
                                      ctx.fonts)
    label = Node(kind="text", role=f"{role}-label",
                 props={"x": X + H2 * .42 + nw + W2 * .05,
                        "y": Y + (H2 - lh) / 2,
                        "w": lw, "h": lh, "block": label_block,
                        "align": "left", "color": label_style.color,
                        "size": label_style.size, "weight": "bold",
                        "tracking_offset": 0.0},
                 qa_class="text",
                 meta={"text": str(spec["text"]), "color": label_style.color,
                       "size": label_style.size,
                       "bounds": (X + H2 * .42 + nw + W2 * .05,
                                  Y + (H2 - lh) / 2,
                                  X + H2 * .42 + nw + W2 * .05 + lw,
                                  Y + (H2 + lh) / 2)})
    group = Node(kind="group", role=role, children=[card, num, label],
                 qa_class="control", meta={})
    _pop(group, onset, scale=.9, dy=44.0, dur=.4)
    nodes.append(group)
    elements[role] = group
    entries[role] = EntranceTiming(role, onset, .4, "pop-settle", True)


_KINDS = {
    "pill": _pill, "words": _words, "bigtext": _bigtext, "count": _count,
    "photo": _photo, "band": _band, "panel": _panel, "image": _image,
    "ring": _ring, "path": _path, "sweep": _sweep, "ticks": _ticks,
    "tag": _tag, "swap": _swap,
}


def build_pe_editorial(ctx: SceneContext, scene: dict) -> BuiltScene:
    elements: dict[str, Node] = {}
    entries: dict[str, EntranceTiming] = {}
    nodes: list[Node] = []
    for index, spec in enumerate(scene.get("elements") or []):
        kind = str(spec.get("kind", ""))
        if kind not in _KINDS:
            raise ValueError(f"pe_editorial: unknown element kind {kind!r}")
        _KINDS[kind](ctx, spec, spec.get("role", f"{kind}-{index}"),
                     elements, entries, nodes)
    layout = LayoutPlan(recipe="pe-editorial", canvas=ctx.layout.canvas,
                        safe=ctx.layout.safe, regions={})
    background = dict(scene.get("background") or {"kind": "solid",
                                                "color": "#FFF9F1"})
    choreography = Choreography(entries=entries,
                                scene_index=ctx.scene_index)
    return BuiltScene(
        index=ctx.scene_index, scene=scene, context=ctx, layout=layout,
        background=background, nodes=nodes, elements=elements,
        choreography=choreography,
        meta={"type": "pe_editorial",
              "headline": str(scene.get("name", "")),
              "theme": str(scene.get("theme", "light"))})


_scenes.BUILDERS["pe_editorial"] = build_pe_editorial


def _paper(path: str) -> dict:
    return {"kind": "photo", "asset": path, "scrim": 0.0,
            "camera": {"direction": "push-in", "intensity": 0.0}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--qa", action="store_true")
    parser.add_argument("--manifest", default=str(MANIFEST))
    parser.add_argument("--supersample", type=int, default=None)
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--output",
                        default=str(ROOT / "renders/pure-energy/"
                                    "pure-energy-bess-reels.mp4"))
    args = parser.parse_args()

    project = load_studio(args.manifest, root=ROOT)
    # Display weight for this reel: Baloo 2 ExtraBold (regular stays Medium).
    project.fonts.bold = str(BRAND / "fonts/Baloo2-ExtraBold.ttf")
    if not MUSIC.is_file():
        raise SystemExit(f"Missing music track: {MUSIC}")
    project.audio = {"music": {"file": str(MUSIC), "volume": .92,
                               "fade_out": 1.4}}

    if args.qa or not args.render:
        from reels_maker.qa.report import audit, contact_sheet, write_report
        from reels_maker.renderers.scene import RenderOptions, SceneRenderer
        timeline = project.timeline()
        built = project.build(timeline)
        renderer = SceneRenderer(project.width, project.height,
                                 project.tokens, project.fonts,
                                 options=RenderOptions(supersample=1))
        report = audit(project, built, timeline, renderer=renderer,
                       samples_per_scene=3, strict=True)
        out_dir = (ROOT / "renders/pure-energy/qa" / project.name)
        out_dir.mkdir(parents=True, exist_ok=True)
        written = write_report(report, out_dir)
        sheet = contact_sheet(report, built, renderer, timeline,
                              out_dir / "qa-contact-sheet.png")
        print(json.dumps({"ok": report["ok"],
                          "report": written["report"],
                          "contact_sheet": str(sheet),
                          "errors": report.get("errors", 0),
                          "warnings": report.get("warnings", 0)},
                         indent=1))
        if not report["ok"]:
            return 2

    if args.render:
        from reels_maker.renderers.studio import render_studio
        result = render_studio(project, output=args.output,
                               supersample=args.supersample,
                               cache_dir=args.cache_dir,
                               progress=lambda p: print(
                                   f"\r{p['frames']}/{p['total']} "
                                   f"scene {p['scene']}", end="", flush=True))
        print()
        print(json.dumps({k: result[k] for k in
                          ("output", "duration", "frames", "fps", "codec",
                           "export_quality", "audio")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
