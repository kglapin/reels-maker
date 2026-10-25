"""Animated photo-card carousel composition for the Studio scene graph.

Cards move through a looping ring: the active photo grows into the center while
the previous and next photos recede to the sides. All motion is ordinary
scene-graph keyframes, so rendering and geometry QA sample the same animation.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

from ..core.scene_graph import Node
from ..layout.engine import LayoutPlan, Rect
from ..motionkit.keyframes import Keyframe, Track
from .base import SceneContext, image_node, panel_node, resolve_text_style, text_node


def _slot(index: int, page: int, count: int) -> int:
    return (index - page + count // 2) % count - count // 2


@lru_cache(maxsize=128)
def _card_jitter(index: int, count: int) -> tuple[float, float, float, float]:
    """Return stable, visible per-card offsets for a natural layout."""
    rng = random.Random(f"photo-carousel:{count}:{index}")
    horizontal = rng.uniform(-1.0, 1.0)
    vertical = rng.uniform(-1.0, 1.0)
    angle = rng.uniform(-1.0, 1.0)

    def visible_offset(value: float, minimum: float, maximum: float) -> float:
        sign = -1.0 if value < 0 else 1.0
        return sign * (minimum + abs(value) * (maximum - minimum))

    return (visible_offset(horizontal, 16.0, 26.0),
            visible_offset(vertical, 14.0, 22.0),
            visible_offset(angle, 6.0, 9.0),
            rng.uniform(-.05, .05))


def _state(index: int, page: int, count: int, spacing: float) -> dict[str, float]:
    slot = _slot(index, page, count)
    distance = abs(slot)
    base_scale = {0: 1.0, 1: .42, 2: .30, 3: .22}.get(distance, .16)
    opacity = {0: 1.0, 1: .84, 2: .56, 3: .38}.get(distance, .28)
    blur = {0: 0.0, 1: 3.0, 2: 6.5, 3: 9.0}.get(distance, 12.0)
    jitter_x, jitter_y, jitter_rotation, jitter_scale = _card_jitter(
        index, count)
    spread = 1.0 if distance else 0.0
    angle = float(slot) * 1.2 + jitter_rotation
    rotation = (
        math.copysign(min(12.5, max(6.5, abs(angle))),
                      angle or jitter_rotation)
        if distance else 0.0)
    return {
        "slot": float(slot),
        "dx": float(slot) * spacing + jitter_x * spread,
        "dy": float(distance * 7) + jitter_y * spread,
        "scale": base_scale * (1.0 + jitter_scale * spread),
        "opacity": opacity,
        "blur": blur,
        "rotation": rotation,
        "z_index": float(20 - distance),
    }


def _transition_schedule(duration: float, advance: float, count: int):
    """Return irregular, sinusoidally paced card advances.

    The average interval remains `advance`, while each complete orbit subtly
    speeds up and slows down over a cycle.
    """
    schedule = []
    time = 0.0
    step = 0
    while time < duration:
        interval = advance * (
            1.0 + .22 * math.sin(2 * math.pi * (step % count) / count))
        move = min(.72, interval * .56)
        schedule.append((step, time, min(duration, time + move)))
        time += interval
        step += 1
    return schedule


def _motion_track(index: int, count: int, spacing: float,
                  duration: float, advance: float, prop: str) -> Track:
    def value_for_page(page: int) -> float:
        return _state(index, page % count, count, spacing)[prop]

    # Only opacity needs a wrap fade; detect it for this card rather than for
    # the ring's first card (which may not be the card crossing the edge).
    keys: list[Keyframe] = []

    def add(time: float, value: float) -> None:
        key = Keyframe(max(0.0, min(duration, time)), float(value), "linear")
        if keys and abs(keys[-1].time - key.time) < 1e-7:
            keys[-1] = key
        else:
            keys.append(key)

    add(0.0, value_for_page(0))
    for step, start, end in _transition_schedule(duration, advance, count):
        page = step % count
        before = _state(index, page, count, spacing)
        after = _state(index, (page + 1) % count, count, spacing)
        wraps = abs(int(before["slot"]) - int(after["slot"])) > 1
        for sample in range(17):
            phase = sample / 16
            eased = .5 - .5 * math.cos(math.pi * phase)
            value = before[prop] + (after[prop] - before[prop]) * eased
            if prop == "opacity" and wraps:
                value *= abs(math.cos(math.pi * phase)) ** 1.5
            add(start + (end - start) * phase, value)
    return Track(keys)


def _indicator_track(index: int, count: int, duration: float,
                     advance: float, prop: str) -> Track:
    def value(page: int) -> float:
        active = index == page % count
        return (1.35 if active else 1.0) if prop == "scale" else (
            1.0 if active else .28)

    keys: list[Keyframe] = []

    def add(time: float, amount: float) -> None:
        key = Keyframe(max(0.0, min(duration, time)), amount, "linear")
        if keys and abs(keys[-1].time - key.time) < 1e-7:
            keys[-1] = key
        else:
            keys.append(key)

    add(0.0, value(0))
    for step, start, end in _transition_schedule(duration, advance, count):
        first, second = value(step), value(step + 1)
        for sample in range(17):
            phase = sample / 16
            eased = .5 - .5 * math.cos(math.pi * phase)
            add(start + (end - start) * phase,
                first + (second - first) * eased)
    return Track(keys)


def _photo_box_track(source: Track, prop: str, card: Rect,
                     pad: float) -> Track:
    """Keep a uniform inset that becomes slimmer as a card recedes."""
    anchor_x = card.x + card.w / 2
    anchor_y = card.y + card.h / 2

    def resized(scale: float) -> float:
        frame_w, frame_h = card.w * scale, card.h * scale
        inset = pad * max(0.0, scale) ** 1.5
        if prop == "x":
            return anchor_x - frame_w / 2 + inset
        if prop == "y":
            return anchor_y - frame_h / 2 + inset
        if prop == "w":
            return frame_w - 2 * inset
        if prop == "h":
            return frame_h - 2 * inset
        raise ValueError(f"Unsupported photo geometry property {prop!r}")

    return Track([
        Keyframe(key.time, resized(float(key.value)), key.easing, key.params)
        for key in source.keys
    ])


def _scaled_box_track(source: Track, prop: str, base: float,
                       anchor: float | None = None) -> Track:
    """Resize a card primitive around the shared card center."""
    def resized(scale: float) -> float:
        if prop in ("x", "y"):
            if anchor is None:
                raise ValueError("Position tracks require a card anchor")
            return anchor + (base - anchor) * scale
        return base * scale

    return Track([
        Keyframe(key.time, resized(float(key.value)), key.easing, key.params)
        for key in source.keys
    ])


def _card(ctx: SceneContext, image: str, index: int,
          rect: Rect) -> Node:
    frame = panel_node(
        f"carousel-frame-{index}", rect, ctx.tokens,
        fill=(255, 255, 255), radius="lg", shadow=True,
        qa_class="decor")
    pad = ctx.tokens.space("sm")
    photo_rect = Rect(rect.x + pad, rect.y + pad,
                      rect.w - 2 * pad, rect.h - 2 * pad)
    photo = image_node(f"carousel-photo-{index}", image, photo_rect,
                       qa_class="decor")
    photo.props["radius"] = ctx.tokens.radius("md")
    return Node(
        kind="group", role=f"carousel-card-{index}",
        children=[frame, photo], qa_class="decor",
        meta={"carousel_item": index, "image": image})

def build_photo_carousel(ctx: SceneContext, scene: dict):
    from .scenes import _background, _finish, _spec, _theme

    config = scene.get("carousel") or {}
    items = config.get("items") or []
    if not isinstance(items, list) or not 3 <= len(items) <= 12:
        raise ValueError("photo-carousel requires between 3 and 12 image items")
    advance = float(config.get("advance_seconds", 1.6))
    if not math.isfinite(advance) or not .8 <= advance <= 4.0:
        raise ValueError("carousel.advance_seconds must be in [0.8, 4.0]")
    safe = ctx.layout.safe
    kicker_rect = Rect(safe.x, safe.y + 8, safe.w, max(22, ctx.tokens.type_size("kicker") * 1.45))
    headline_rect = Rect(safe.x, kicker_rect.bottom + 5, safe.w, safe.h * .155)
    body_rect = Rect(safe.x + safe.w * .04, headline_rect.bottom + 2,
                     safe.w * .92, safe.h * .09)
    cards_y = safe.y + safe.h * .615
    card_w = min(safe.w * .58, safe.h * .37)
    card_h = min(safe.h * .50, card_w * 1.38)
    center = Rect((ctx.width - card_w) / 2, cards_y - card_h / 2,
                  card_w, card_h)
    side_scale = .44
    clear_gap = max(ctx.tokens.px(24), card_w * .12)
    rotation_buffer = card_h * math.sin(math.radians(12.5)) * .5
    spacing = card_w * (1.0 + side_scale) / 2 + clear_gap + rotation_buffer
    dot_y = min(ctx.height - ctx.tokens.space("xl"),
                safe.bottom - ctx.tokens.space("sm"))
    dot_r = max(3.5, ctx.tokens.px(6))

    layout = LayoutPlan(
        "photo-carousel", Rect(0, 0, ctx.width, ctx.height), safe,
        {"kicker": kicker_rect, "headline": headline_rect,
         "body": body_rect, "visual": Rect(
             safe.x, center.y, safe.w, card_h)})
    theme = _theme(ctx, scene)
    elements = {}
    if scene.get("kicker"):
        style = resolve_text_style(ctx.tokens, "kicker", theme["kicker"],
                                   align="center")
        node = text_node("kicker", str(scene["kicker"]), style,
                         kicker_rect, ctx.fonts, align="center",
                         valign="center")
        if node is not None:
            elements["kicker"] = node
    if scene.get("headline"):
        style = resolve_text_style(ctx.tokens, "title", theme["ink"],
                                   align="center", balance=True,
                                   line_height=1.08, max_lines=2)
        node = text_node("headline", str(scene["headline"]), style,
                         headline_rect, ctx.fonts, align="center",
                         valign="center")
        if node is not None:
            elements["headline"] = node
    if scene.get("subtitle") or scene.get("body"):
        copy = str(scene.get("subtitle") or scene.get("body") or "")
        style = resolve_text_style(ctx.tokens, "subtitle", theme["muted"],
                                   align="center", line_height=1.24,
                                   max_lines=2)
        node = text_node("body", copy, style, body_rect, ctx.fonts,
                         align="center", valign="center")
        if node is not None:
            elements["body"] = node

    nodes = []
    count = len(items)
    for index, item in enumerate(items):
        if not isinstance(item, dict) or not item.get("image"):
            raise ValueError(f"carousel.items[{index}] requires an image")
        image = str(item["image"])
        card = _card(ctx, image, index, center)
        # Resize photo and frame geometry directly around the shared card
        # center. The outer slot remains a pure translation, so scaling cannot
        # compress the carousel spacing.
        scale_track = _motion_track(
            index, count, spacing, ctx.duration, advance, "scale")
        anchor_x = center.x + center.w / 2
        anchor_y = center.y + center.h / 2
        card_pad = ctx.tokens.space("sm")
        rotation_track = _motion_track(
            index, count, spacing, ctx.duration, advance, "rotation")
        for part in card.children:
            # Rotate the image and frame separately around one shared center
            # so the visible tilt stays aligned through every renderer path.
            part.anchor = (anchor_x, anchor_y)
            part.track("rotation", rotation_track)
            if part.kind == "text":
                part.track("scale", scale_track)
                continue
            for prop in ("x", "y", "w", "h"):
                if prop not in part.props:
                    continue
                if part.kind == "image":
                    track = _photo_box_track(
                        scale_track, prop, center, card_pad)
                else:
                    anchor = anchor_x if prop == "x" else (
                        anchor_y if prop == "y" else None)
                    track = _scaled_box_track(
                        scale_track, prop, float(part.props[prop]), anchor)
                part.track(f"prop.{prop}", track)
            for prop in ("r", "radius", "border_width"):
                if prop in part.props:
                    part.track(
                        f"prop.{prop}",
                        _scaled_box_track(
                            scale_track, "size",
                            float(part.props[prop])))
        card.track("opacity", _motion_track(index, count, spacing, ctx.duration,
                                            advance, "opacity"))
        card.children[1].track(
            "prop.blur", _motion_track(index, count, spacing, ctx.duration,
                                       advance, "blur"))

        # Keep the slot translation outside the card's scale/rotation layer.
        # Shrinking a card then cannot pull its center back toward the middle.
        slot = Node(kind="group", role=f"carousel-slot-{index}",
                    children=[card], qa_class="decor",
                    meta={"carousel_item": index})
        slot.track("dx", _motion_track(index, count, spacing, ctx.duration,
                                       advance, "dx"))
        slot.track("dy", _motion_track(index, count, spacing, ctx.duration,
                                       advance, "dy"))
        slot.track("prop.z_index", _motion_track(
            index, count, spacing, ctx.duration, advance, "z_index"))
        nodes.append(slot)

    indicator_gap = dot_r * 3.2
    start_x = ctx.width / 2 - indicator_gap * (count - 1) / 2
    for index in range(count):
        dot = Node(
            kind="circle", role=f"carousel-indicator-{index}",
            props={"cx": start_x + indicator_gap * index,
                   "cy": dot_y, "r": dot_r,
                   "fill": theme["accent"]},
            opacity=.28, qa_class="decor")
        dot.track("opacity", _indicator_track(
            index, count, ctx.duration, advance, "opacity"))
        dot.track("scale", _indicator_track(
            index, count, ctx.duration, advance, "scale"))
        nodes.append(dot)

    return _finish(
        ctx, scene, layout, _background(ctx, scene, theme), elements,
        [_spec("kicker", 3), _spec("headline", 10, "display"),
         _spec("body", 4)],
        decor=nodes, meta={"component": "photo-carousel",
                           "carousel_items": count,
                           "advance_seconds": advance,
                           "motion_system": "looping-photo-card-ring"})
