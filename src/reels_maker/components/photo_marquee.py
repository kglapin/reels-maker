"""Three-row looping photo marquee with central, moving light.

Each row reuses the same image sequence so one complete cycle lands on an
identical frame. The rows travel in alternating directions with subtle
sinusoidal speed variation; soft shadows track away from a point light at the
center of the canvas.
"""
from __future__ import annotations

import math

from ..core.scene_graph import Node
from ..design.color import mix
from ..layout.engine import LayoutPlan, Rect
from ..motionkit.keyframes import Keyframe, Track
from .base import SceneContext, image_node


_ROW_DIRECTIONS = (-1.0, 1.0, -1.0)
_ROW_PHASES = (0.36, 0.15, 0.66)
_SPEED_VARIATION = 0.12
_TRACK_SAMPLES = 49
_SHADOW_OPACITY = 0.70


def _paced_phase(phase: float, phase_shift: float) -> float:
    """Vary speed gently while preserving the loop endpoints and velocity."""
    wave = math.sin(2.0 * math.pi * (phase + phase_shift))
    start = math.sin(2.0 * math.pi * phase_shift)
    return phase + _SPEED_VARIATION * (wave - start) / (2.0 * math.pi)


def _row_motion_track(duration: float, cycle_width: float, direction: float,
                      phase_shift: float) -> Track:
    keys = []
    for step in range(_TRACK_SAMPLES):
        phase = step / (_TRACK_SAMPLES - 1)
        time = duration * phase
        distance = direction * cycle_width * _paced_phase(phase, phase_shift)
        keys.append(Keyframe(time, distance, "linear"))
    return Track(keys)


def _shadow_tracks(card_x: float, card_y: float, card_w: float,
                   card_h: float, canvas_w: float, canvas_h: float,
                   duration: float, cycle_width: float, direction: float,
                   phase_shift: float, shadow_reach: float) -> tuple[Track, Track]:
    dx_keys = []
    dy_keys = []
    light_x, light_y = canvas_w / 2.0, canvas_h / 2.0
    half_width, half_height = max(1.0, light_x), max(1.0, light_y)
    for step in range(_TRACK_SAMPLES):
        phase = step / (_TRACK_SAMPLES - 1)
        time = duration * phase
        row_dx = direction * cycle_width * _paced_phase(phase, phase_shift)
        object_x = card_x + card_w / 2.0 + row_dx
        object_y = card_y + card_h / 2.0
        # Normalize each axis to the canvas so horizontal movement remains
        # visible on a tall 9:16 frame, while the source stays at canvas center.
        vector_x = (object_x - light_x) / half_width
        vector_y = (object_y - light_y) / half_height
        distance = math.hypot(vector_x, vector_y)
        strength = min(1.0, distance / 0.20)
        length = max(1e-9, distance)
        dx_keys.append(Keyframe(
            time, shadow_reach * strength * vector_x / length, "linear"))
        dy_keys.append(Keyframe(
            time, shadow_reach * strength * vector_y / length, "linear"))
    return Track(dx_keys), Track(dy_keys)


def build_photo_marquee(ctx: SceneContext, scene: dict):
    from .scenes import _background, _finish, _theme

    config = scene.get("carousel") or {}
    items = config.get("items") or []
    if not isinstance(items, list) or not 3 <= len(items) <= 12:
        raise ValueError("photo-marquee requires between 3 and 12 image items")
    if any(not isinstance(item, dict) or not item.get("image")
           for item in items):
        raise ValueError("every photo-marquee item requires an image path")
    if ctx.duration <= 0 or not math.isfinite(ctx.duration):
        raise ValueError("photo-marquee duration must be finite and positive")

    # A landscape card reads clearly across all three bands while the equal
    # geometry keeps the composition calm and lets the motion carry the scene.
    card_w = min(ctx.width * 0.60, ctx.height * 0.43)
    card_h = min(ctx.height * 0.34, card_w * 0.94)
    if card_w <= 0 or card_h <= 0:
        raise ValueError("photo-marquee requires a positive canvas")
    gap = max(12.0, card_w * 0.07)
    stride = card_w + gap
    count = len(items)
    cycle_width = stride * count
    copies = 2
    radius = ctx.tokens.radius("md")
    shadow_blur = card_w * 0.16
    shadow_reach = card_w * 0.105
    row_centers = (ctx.height * 0.13, ctx.height * 0.50,
                   ctx.height * 0.87)
    rows = []

    for row_index, (direction, phase_shift, center_y) in enumerate(
            zip(_ROW_DIRECTIONS, _ROW_PHASES, row_centers)):
        row_y = center_y - card_h / 2.0
        start_x = (
            -cycle_width - phase_shift * cycle_width
            if direction > 0
            else -cycle_width + phase_shift * cycle_width
        )
        cards = []
        for card_index in range(count * copies):
            item_index = card_index % count
            image_path = str(items[item_index]["image"])
            card_x = start_x + card_index * stride
            rect = Rect(card_x, row_y, card_w, card_h)
            shadow = Node(
                kind="round",
                role=f"marquee-shadow-r{row_index}-c{card_index}",
                props={
                    "x": rect.x, "y": rect.y, "w": rect.w, "h": rect.h,
                    "r": radius, "fill": (18, 24, 28), "border": None,
                    "border_width": 0, "shadow": True,
                    "shadow_blur": shadow_blur,
                    "shadow_opacity": _SHADOW_OPACITY,
                    "shadow_dx": 0.0, "shadow_dy": 0.0,
                },
                qa_class="decor",
                meta={"marquee_row": row_index, "light_source": "canvas_center"},
            )
            shadow_dx, shadow_dy = _shadow_tracks(
                card_x, row_y, card_w, card_h, ctx.width, ctx.height,
                ctx.duration, cycle_width, direction, phase_shift,
                shadow_reach)
            shadow.track("prop.shadow_dx", shadow_dx)
            shadow.track("prop.shadow_dy", shadow_dy)

            photo = image_node(
                f"marquee-photo-r{row_index}-c{card_index}",
                image_path, rect, qa_class="decor",
                meta={"marquee_row": row_index, "image_index": item_index})
            photo.props["radius"] = radius
            cards.append(Node(
                kind="group",
                role=f"marquee-card-r{row_index}-c{card_index}",
                children=[shadow, photo], qa_class="decor",
                meta={"marquee_row": row_index, "image_index": item_index},
            ))

        row = Node(
            kind="group", role=f"marquee-row-{row_index}",
            children=cards, qa_class="decor",
            meta={
                "row": row_index,
                "direction": "left" if direction < 0 else "right",
                "cycle_width": cycle_width,
            },
        )
        row.track("dx", _row_motion_track(
            ctx.duration, cycle_width, direction, phase_shift))
        rows.append(row)

    full_frame = Rect(0.0, 0.0, float(ctx.width), float(ctx.height))
    layout = LayoutPlan(
        "photo-marquee", Rect(0, 0, ctx.width, ctx.height), ctx.layout.safe,
        {"visual": full_frame})
    theme = _theme(ctx, scene)
    # Creative Specs require a headline field, but this image-led treatment
    # intentionally keeps the frame free of copy.
    finish_scene = {
        **scene, "kicker": None, "headline": None,
        "subtitle": None, "body": None,
    }
    background = _background(ctx, scene, theme)
    if background.get("kind") != "photo":
        # A light surface keeps the borderless cards and their broad shadows
        # legible even when the selected type system uses a dark canvas.
        background = {
            "kind": "gradient",
            "from": theme["surface"],
            "to": mix(theme["surface"], theme["muted"], .12),
            "angle": 90,
        }
    return _finish(
        ctx, finish_scene, layout, background, {},
        [], decor=rows,
        meta={
            "component": "photo-marquee",
            "marquee_rows": 3,
            "row_directions": ["left", "right", "left"],
            "cards_per_row": count * copies,
            "card_size": [round(card_w, 2), round(card_h, 2)],
            "edge_rows_cropped": True,
            "shadow_light_source": "canvas_center",
            "shadow_blur": round(shadow_blur, 2),
            "motion_system": "looping-three-row-photo-marquee",
            "motion_profile": "sinusoidal-speed-modulation",
        },
    )
