"""Object-driven, frame-exact scene transitions for the studio renderer.

Transitions occupy the final N frames of the outgoing scene. They never add
or remove frames, and they composite real adjacent scene frames, not fades
to black. All effects use deterministic, resolution-independent geometry.
"""
from __future__ import annotations

import math
from PIL import Image, ImageDraw, ImageFilter

EFFECTS = frozenset({"color-takeover", "radial-reveal", "whip-pan", "zoom-through",
                     "diagonal-wipe", "iris-close-open", "stripe-reveal",
                     "split-slide", "spin-zoom", "pixel-dissolve"})


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
    # Renderer frames are already RGB. Reuse those buffers directly;
    # transition branches only read them and build a separate output image.
    a = outgoing if outgoing.mode == "RGB" else outgoing.convert("RGB")
    b = incoming if incoming.mode == "RGB" else incoming.convert("RGB")
    if effect == "diagonal-wipe":
        mask = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(mask)
        extent = w + h
        cutoff = -h + t * (extent + h)
        d.polygon([(0, 0), (max(0, cutoff), 0),
                   (max(0, cutoff-h), h), (0, h)], fill=255)
        return Image.composite(b, a, mask)
    if effect == "stripe-reveal":
        mask = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(mask)
        stripes = 9
        for i in range(stripes):
            start = i / stripes * .33
            p = _ease((t-start)/.67)
            if p <= 0:
                continue
            y0, y1 = round(i*h/stripes), round((i+1)*h/stripes)
            extent = round(w*p)
            if i % 2:
                d.rectangle((w-extent, y0, w, y1), fill=255)
            else:
                d.rectangle((0, y0, extent, y1), fill=255)
        return Image.composite(b, a, mask)
    if effect == "split-slide":
        frame = b.copy()
        offset = round((1-t)*w/2)
        upper = a.crop((0, 0, w//2, h))
        lower = a.crop((w//2, 0, w, h))
        frame.paste(upper, (-round(t*w/2), 0))
        frame.paste(lower, (w//2+round(t*w/2), 0))
        return frame
    if effect == "iris-close-open":
        x, y = round(w*anchor[0]), round(h*anchor[1])
        radius = math.hypot(max(x,w-x), max(y,h-y))
        mask = Image.new("L", (w,h), 0)
        d = ImageDraw.Draw(mask)
        if t < .5:
            r = radius * (1-_ease(t*2))
            d.ellipse((x-r,y-r,x+r,y+r), fill=255)
            return Image.composite(a, Image.new("RGB",(w,h),color), mask)
        r = radius * _ease((t-.5)*2)
        d.ellipse((x-r,y-r,x+r,y+r), fill=255)
        return Image.composite(b, Image.new("RGB",(w,h),color), mask)
    if effect == "spin-zoom":
        # Rotated outgoing card shrinks to reveal the incoming scene.
        scale = max(.04, 1-.96*t)
        cw, ch = max(1,round(w*scale)), max(1,round(h*scale))
        card = a.resize((cw,ch), Image.Resampling.BICUBIC)
        card = card.rotate(105*t, resample=Image.Resampling.BICUBIC,
                           expand=True)
        frame = b.copy()
        frame.paste(card, (round(w*anchor[0]-card.width/2),
                           round(h*anchor[1]-card.height/2)))
        return frame
    if effect == "pixel-dissolve":
        # Deterministic ordered Bayer dither, no frame-to-frame randomness.
        bayer = ((0,8,2,10),(12,4,14,6),(3,11,1,9),(15,7,13,5))
        mask = Image.new("L",(w,h),0)
        d = ImageDraw.Draw(mask)
        block = max(8,round(min(w,h)*.022))
        threshold = t*16
        for row,y0 in enumerate(range(0,h,block)):
            for col,x0 in enumerate(range(0,w,block)):
                if bayer[row%4][col%4] < threshold:
                    d.rectangle((x0,y0,min(w,x0+block),min(h,y0+block)),fill=255)
        return Image.composite(b,a,mask)
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
