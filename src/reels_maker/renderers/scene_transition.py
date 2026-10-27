"""In-scene entry transition effects, separated from node rasterization."""
from __future__ import annotations

from PIL import Image, ImageDraw

from ..motionkit.easing import ease


def apply_scene_transition(image: Image.Image, name: str | dict, time: float,
                           duration: float, accent: tuple[int, int, int]) -> None:
    if duration <= 0:
        return
    raw_progress = min(1.0, max(0.0, time / duration))
    easing = "smooth"
    if isinstance(name, dict):
        easing = str(name.get("easing", "smooth"))
        name = name.get("type", "cut")
    if easing not in ("linear", "smooth", "out-cubic", "in-out-cubic"):
        raise ValueError(
            "Transition easing must be linear, smooth, out-cubic or "
            "in-out-cubic")
    progress = ease(easing, raw_progress)
    if progress >= 1:
        return
    blend = .94
    if name == "cut" or not name:
        return
    if name == "dip":
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        alpha = int(255 * (1 - progress))
        ImageDraw.Draw(overlay).rectangle(
            (0, 0, image.width, image.height), fill=(5, 10, 7, alpha))
        image.alpha_composite(overlay)
        return
    if name not in ("wipe-left", "wipe-right", "wipe-up", "wipe-down"):
        raise ValueError(f"Unknown transition {name!r}")
    panel = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(panel)
    if name in ("wipe-left", "wipe-right"):
        width = image.width
        offset = width * progress
        if name == "wipe-left":
            box = (offset, 0, width, image.height)
        else:
            box = (0, 0, width - offset, image.height)
    else:
        height = image.height
        offset = height * progress
        if name == "wipe-up":
            box = (0, offset, image.width, image.height)
        else:
            box = (0, 0, image.width, height - offset)
    draw.rectangle(box, fill=(*accent, int(255 * blend)))
    # A thin bright edge gives the wipe a deliberate cut, not a glitch.
    edge = max(2, round(image.width * .004))
    if name == "wipe-left":
        draw.rectangle((box[0] - edge, 0, box[0], image.height),
                       fill=(255, 255, 255, 210))
    elif name == "wipe-right":
        draw.rectangle((box[2], 0, box[2] + edge, image.height),
                       fill=(255, 255, 255, 210))
    elif name == "wipe-up":
        draw.rectangle((0, box[1] - edge, image.width, box[1]),
                       fill=(255, 255, 255, 210))
    else:
        draw.rectangle((0, box[3], image.width, box[3] + edge),
                       fill=(255, 255, 255, 210))
    image.alpha_composite(panel)
