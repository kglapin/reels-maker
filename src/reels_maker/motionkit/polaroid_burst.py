"""Deterministic fast Polaroid photo bursts with synchronized flash cues."""
from __future__ import annotations

import math
import random
from collections.abc import Mapping
from dataclasses import dataclass

from ..core.scene_graph import Node
from .keyframes import Keyframe, Track


@dataclass(frozen=True)
class PolaroidShot:
    index: int
    asset: str
    center_x: float
    center_y: float
    card_width: float
    card_height: float
    photo_x: float
    photo_y: float
    photo_width: float
    photo_height: float
    rotation: float
    start_frame: int
    flash_frame: int
    entry_frames: int
    flash_frames: int


def _number(config: Mapping, key: str, default: float,
            lower: float, upper: float) -> float:
    value = config.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"polaroid_burst.{key} must be numeric")
    value = float(value)
    if not math.isfinite(value) or not lower <= value <= upper:
        raise ValueError(
            f"polaroid_burst.{key} must be between {lower} and {upper}")
    return value


def _frame(seconds: float, fps: int) -> int:
    return max(0, round(seconds * fps))


def plan_polaroid_burst(config: Mapping, width: int, height: int,
                        duration: float, fps: int, *, fallback_seed: int = 0
                        ) -> tuple[PolaroidShot, ...]:
    """Create a repeatable, frame-quantized stack layout and photo cadence."""
    if not isinstance(config, Mapping):
        raise ValueError("polaroid_burst must be an object")
    photos = config.get("photos")
    if not isinstance(photos, list) or not 2 <= len(photos) <= 16:
        raise ValueError("polaroid_burst.photos must contain 2 to 16 image paths")
    if any(not isinstance(path, str) or not path.strip() for path in photos):
        raise ValueError("polaroid_burst.photos entries must be non-empty paths")
    if width <= 0 or height <= 0 or fps <= 0 or duration <= 0:
        raise ValueError("Polaroid burst requires a positive canvas, FPS and duration")

    first_at = _number(config, "first_at", .06, 0, duration)
    interval = _number(config, "interval", .20, .08, 1.0)
    entry_duration = _number(config, "entry_duration", .14, .05, .4)
    flash_duration = _number(config, "flash_duration", .13, .04, .3)
    flash_strength = _number(config, "flash_strength", .78, .2, .95)
    max_rotation = _number(config, "rotation_degrees", 7.0, 0, 16)
    spread_x = _number(config, "spread_x", .10, 0, .18)
    spread_y = _number(config, "spread_y", .12, 0, .18)
    width_fraction = _number(config, "card_width_fraction", .60, .25, .82)
    hold_after = _number(config, "hold_after", .35, 0, 10)
    seed = config.get("seed", fallback_seed)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("polaroid_burst.seed must be an integer")

    interval_frames = max(2, _frame(interval, fps))
    entry_frames = max(2, _frame(entry_duration, fps))
    flash_frames = max(3, _frame(flash_duration, fps))
    first_frame = _frame(first_at, fps)
    hold_frames = _frame(hold_after, fps)
    scene_frames = round(duration * fps)
    last_start = first_frame + (len(photos) - 1) * interval_frames
    if last_start + max(entry_frames, flash_frames) + hold_frames > scene_frames:
        raise ValueError(
            "polaroid_burst does not leave enough time for the full burst and hold")
    _number(config, "shutter_gain_db", -10, -48, 6)

    rng = random.Random(seed)
    card_width = min(width * width_fraction, height * .58 / 1.18)
    card_height = card_width * 1.18
    margin = max(6.0, min(width, height) * .025)
    # Account for the maximum angle and entry overshoot before randomizing the
    # center so no card can clip at any point in its entrance.
    max_scale = 1.08
    angle = math.radians(max_rotation + 3.2)
    rotated_width = max_scale * (card_width * abs(math.cos(angle))
                                 + card_height * abs(math.sin(angle)))
    rotated_height = max_scale * (card_width * abs(math.sin(angle))
                                  + card_height * abs(math.cos(angle)))
    fit = min(1.0,
              max(0.01, (width - 2 * margin) / rotated_width),
              max(0.01, (height - 2 * margin) / rotated_height))
    card_width *= fit
    card_height *= fit
    rotated_width *= fit
    rotated_height *= fit
    max_x = max(0.0, (width - rotated_width) / 2 - margin)
    max_y = max(0.0, (height - rotated_height) / 2 - margin)
    spread_x_px = min(width * spread_x, max_x)
    spread_y_px = min(height * spread_y, max_y)
    pad = card_width * .045
    photo_width = card_width - 2 * pad
    photo_height = photo_width * .96
    photo_y = -card_height / 2 + pad
    photo_x = -card_width / 2 + pad

    result = []
    flash_offset_frames = max(1, round(.02 * fps))
    if max_rotation:
        min_rotation = max_rotation * .65
        angles = [(-1 if rng.random() < .5 else 1)
                  * rng.uniform(min_rotation, max_rotation)
                  for _ in photos]
    else:
        angles = [0.0 for _ in photos]
    if max_rotation and len(angles) > 1:
        if all(angle >= 0 for angle in angles):
            angles[-1] = -abs(angles[-1])
        elif all(angle <= 0 for angle in angles):
            angles[-1] = abs(angles[-1])
    for index, (asset, target_angle) in enumerate(zip(photos, angles, strict=True)):
        start_frame = first_frame + index * interval_frames
        result.append(PolaroidShot(
            index=index,
            asset=asset,
            center_x=width / 2 + rng.uniform(-spread_x_px, spread_x_px),
            center_y=height / 2 + rng.uniform(-spread_y_px, spread_y_px),
            card_width=card_width,
            card_height=card_height,
            photo_x=photo_x,
            photo_y=photo_y,
            photo_width=photo_width,
            photo_height=photo_height,
            rotation=target_angle,
            start_frame=start_frame,
            flash_frame=start_frame + flash_offset_frames,
            entry_frames=entry_frames,
            flash_frames=flash_frames,
        ))
    return tuple(result)


def polaroid_burst_nodes(config: Mapping, width: int, height: int,
                         duration: float, fps: int, *, fallback_seed: int = 0
                         ) -> tuple[list[Node], tuple[PolaroidShot, ...]]:
    """Build layered paper/photo groups and white flashes from one shot plan."""
    shots = plan_polaroid_burst(config, width, height, duration, fps,
                                fallback_seed=fallback_seed)
    nodes: list[Node] = []
    for shot in shots:
        cx, cy = shot.center_x, shot.center_y
        left, top = cx - shot.card_width / 2, cy - shot.card_height / 2
        paper = Node(
            kind="round", role=f"polaroid-paper-{shot.index + 1}",
            props={"x": left, "y": top, "w": shot.card_width,
                   "h": shot.card_height, "r": max(3.0, shot.card_width * .006),
                   "fill": (255, 254, 249), "border": (231, 228, 220),
                   "border_width": max(1.0, shot.card_width * .0012),
                   "shadow": True, "shadow_blur": 18,
                   "shadow_opacity": .24, "shadow_dy": 14},
            qa_class="visual")
        photo = Node(
            kind="image", role=f"polaroid-photo-{shot.index + 1}",
            props={"path": shot.asset,
                   "x": cx + shot.photo_x, "y": cy + shot.photo_y,
                   "w": shot.photo_width, "h": shot.photo_height},
            qa_class="visual", meta={"asset_role": "polaroid-photo"})
        group = Node(
            kind="group", role=f"polaroid-card-{shot.index + 1}",
            children=[paper, photo], opacity=0.0,
            anchor=(cx, cy), rotation=shot.rotation,
            qa_class="visual", meta={
                "photo_index": shot.index,
                "rotation_degrees": round(shot.rotation, 3),
                "start_frame": shot.start_frame,
                "motion": "flash-pop-and-stack",
            })
        at = shot.start_frame / fps
        end = (shot.start_frame + shot.entry_frames) / fps
        opacity_keys = [Keyframe(0.0, 0.0, "linear")]
        if shot.start_frame:
            opacity_keys.append(Keyframe(at, 0.0, "linear"))
        opacity_keys.append(Keyframe(min(end, at + 2 / fps), 1.0,
                                     "out-cubic"))
        group.track("opacity", Track(opacity_keys))
        scale_keys = [Keyframe(0.0, .84, "linear")]
        if shot.start_frame:
            scale_keys.append(Keyframe(at, .84, "linear"))
        scale_keys.extend([
            Keyframe(at + max(1, shot.entry_frames - 1) / fps, 1.045,
                     "back"),
            Keyframe(end, 1.0, "out-cubic"),
        ])
        group.track("scale", Track(scale_keys))
        direction = -1.0 if shot.rotation > 0 else 1.0
        initial_rotation = shot.rotation + direction * rng_jitter(
            shot.index, config.get("seed", fallback_seed))
        rotation_keys = [Keyframe(0.0, initial_rotation, "linear")]
        dy_keys = [Keyframe(0.0, 22 * direction, "linear")]
        if shot.start_frame:
            rotation_keys.append(Keyframe(at, initial_rotation, "linear"))
            dy_keys.append(Keyframe(at, 22 * direction, "linear"))
        rotation_keys.append(Keyframe(end, shot.rotation, "out-cubic"))
        dy_keys.append(Keyframe(end, 0.0, "out-cubic"))
        group.track("rotation", Track(rotation_keys))
        group.track("dy", Track(dy_keys))
        nodes.append(group)

    strength = _number(config, "flash_strength", .78, .2, .95)
    for shot in shots:
        flash_start_frame = max(shot.start_frame, shot.flash_frame - 1)
        flash_start = flash_start_frame / fps
        flash_end_frame = shot.start_frame + shot.flash_frames
        flash_end = flash_end_frame / fps
        fall_frame = min(shot.flash_frame + max(1, round(.06 * fps)),
                         flash_end_frame - 1)
        keys = [Keyframe(0.0, 0.0, "linear")]
        if flash_start_frame:
            keys.append(Keyframe(flash_start, 0.0, "linear"))
        keys.extend([
            Keyframe(shot.flash_frame / fps, strength, "out-cubic"),
            Keyframe(fall_frame / fps, strength * .36, "in-cubic"),
            Keyframe(flash_end, 0.0, "out-cubic"),
        ])
        flash = Node(
            kind="rect", role=f"polaroid-flash-{shot.index + 1}",
            props={"x": 0, "y": 0, "w": width, "h": height,
                   "fill": (255, 255, 255)},
            opacity=0.0, qa_class="decor",
            meta={"flash_frame": shot.flash_frame,
                  "shutter_frame": shot.start_frame})
        flash.track("opacity", Track(keys))
        nodes.append(flash)
    return nodes, shots


def rng_jitter(index: int, seed: int) -> float:
    """Small deterministic settling angle independent of photo placement."""
    return random.Random(seed + index * 7919 + 11).uniform(1.2, 3.2)
