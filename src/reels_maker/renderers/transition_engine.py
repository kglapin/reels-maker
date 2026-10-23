"""Object-driven, frame-exact scene transitions for the studio renderer.

Transitions occupy the final N frames of the outgoing scene. They never add
or remove frames, and they composite real adjacent scene frames, not fades
to black. All effects use deterministic, resolution-independent geometry.
"""
from __future__ import annotations

import math
from PIL import Image, ImageDraw, ImageFilter

EFFECTS = frozenset({"color-takeover", "radial-reveal", "whip-pan", "zoom-through"})


def _ease(t: float) -> float:
    t = min(1.0, max(0.0, float(t)))
    return t * t * (3.0 - 2.0 * t)


def transition_frame(outgoing: Image.Image, incoming: Image.Image,
                     progress: float, *, effect: str = "color-takeover",
                     color: str = "#47A013", anchor: tuple[float, float] = (.5, .5),
                     direction: str = "left") -> Image.Image:
    """Blend adjacent frames via masks, geometry and camera movement.

    progress=0 returns outgoing, progress=1 returns incoming.
    """
    if effect not in EFFECTS:
        raise ValueError(f"Unknown transition: {effect}")
    if outgoing.size != incoming.size:
        raise ValueError("Transition frames must have identical dimensions")
    if len(anchor) != 2 or any(not 0 <= float(v) <= 1 for v in anchor):
        raise ValueError("Transition anchor must be normalized 0..1")
    if direction not in ("left", "right", "up", "down"):
        raise ValueError("Unsupported camera direction")
    t = _ease(progress)
    if t <= 0:
        return outgoing.copy()
    if t >= 1:
        return incoming.copy()
    w, h = outgoing.size
    a = outgoing.convert("RGB")
    b = incoming.convert("RGB")
    if effect in ("color-takeover", "radial-reveal"):
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        x, y = int(w * anchor[0]), int(h * anchor[1])
        max_radius = math.hypot(max(x, w-x), max(y, h-y))
        if effect == "radial-reveal":
            radius = max_radius * t
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=255)
            return Image.composite(b, a, mask)
        # Grow a thin line into a full-frame color plane, then reveal scene B.
        # At t=.5 the color covers the full screen; the incoming scene
        # is revealed in the second half.
        if t < .5:
            q = _ease(t * 2)
            cover = Image.new("RGB", (w, h), color)
            half_width = w * (.08 + .52 * q)
            half_height = max(2, h * (.002 + .52 * q))
            draw.rounded_rectangle((x-half_width, y-half_height,
                                    x+half_width, y+half_height),
                                   radius=min(w*.03, half_height), fill=255)
            return Image.composite(cover, a, mask)
        q = _ease((t-.5)*2)
        # Color stays as a full-screen intermediate, next scene emerges
        # through a circular mask from the same anchor.
        base = Image.new("RGB", (w, h), color)
        radius = max_radius * q
        draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=255)
        return Image.composite(b, base, mask)
    if effect == "whip-pan":
        horizontal = direction in ("left", "right")
        sign = -1 if direction in ("left", "up") else 1
        dist = w if horizontal else h
        shift = round(dist * t)
        frame = Image.new("RGB", (w, h), (0, 0, 0))
        if horizontal:
            frame.paste(a, (sign*shift, 0))
            frame.paste(b, (sign*(shift-dist), 0))
        else:
            frame.paste(a, (0, sign*shift))
            frame.paste(b, (0, sign*(shift-dist)))
        # Directional blur strengthens motion at maximum velocity.
        if .12 < t < .88:
            frame = frame.filter(ImageFilter.GaussianBlur(radius=max(0.4, min(w,h)*.004)))
        return frame
    # Zoom-through: incoming scene expands from anchor while outgoing
    # recedes; clipped to canvas with no external image references.
    scale = .3 + .7*t
    bw, bh = max(1, int(w*scale)), max(1, int(h*scale))
    foreground = b.resize((bw,bh), Image.Resampling.BICUBIC)
    frame = a.copy()
    frame.paste(foreground, (round(w*anchor[0]-bw*anchor[0]),
                             round(h*anchor[1]-bh*anchor[1])))
    return frame
