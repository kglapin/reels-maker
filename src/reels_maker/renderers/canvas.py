"""Pillow rendering primitives for the studio scene graph.

The renderer is intentionally dependency-light: Pillow and FFmpeg only. All
geometric antialiasing is achieved by optional supersampling in the scene
renderer, while typography uses real FreeType glyphs and word-level geometry.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..design.color import mix, parse_hex
from ..design.format import format_value
from ..textkit.typesetter import FontBook, TextBlock, digits_width


@dataclass(frozen=True)
class Camera:
    zoom: float = 1.0
    x: float = 0.0
    y: float = 0.0
    blur: float = 0.0


@lru_cache(maxsize=128)
def _load(path: str, mtime: float) -> Image.Image:
    image = Image.open(path)
    image.load()
    return image.convert("RGBA")


def load_image(path: str | Path) -> Image.Image:
    path = str(Path(path).resolve())
    stat = os.stat(path)
    return _load(path, stat.st_mtime)


def cover(image: Image.Image, width: int, height: int,
          camera: Camera | None = None) -> Image.Image:
    """Cover-fit an image and apply a subtle camera transform."""
    if width < 1 or height < 1:
        raise ValueError("Target size must be positive")
    camera = camera or Camera()
    if camera.zoom <= 0:
        raise ValueError("Camera zoom must be positive")
    scale = max(width / image.width, height / image.height) * camera.zoom
    scaled = image.resize((max(1, round(image.width * scale)),
                           max(1, round(image.height * scale))),
                          Image.Resampling.LANCZOS)
    overflow_x = max(0, scaled.width - width)
    overflow_y = max(0, scaled.height - height)
    # camera.x/y are normalized -1..1 offsets within the available overflow.
    x = int(round((overflow_x / 2) * (1 + max(-1, min(1, camera.x)) * .8)))
    y = int(round((overflow_y / 2) * (1 + max(-1, min(1, camera.y)) * .8)))
    return scaled.crop((x, y, x + width, y + height))


def gradient_image(width: int, height: int, start: tuple[int, int, int],
                   end: tuple[int, int, int], angle: float = 90) -> Image.Image:
    """Linear two-stop gradient. Cache this at scene level, never per frame."""
    if width < 1 or height < 1:
        raise ValueError("Gradient size must be positive")
    if angle in (90, 270):
        if angle == 270:
            start, end = end, start
        strip = Image.new("RGB", (1, height))
        pixels = strip.load()
        for y in range(height):
            pixels[0, y] = mix(start, end, y / max(1, height - 1))
        return strip.resize((width, height))
    if angle in (0, 180):
        if angle == 0:
            start, end = end, start
        strip = Image.new("RGB", (width, 1))
        pixels = strip.load()
        for x in range(width):
            pixels[x, 0] = mix(start, end, x / max(1, width - 1))
        return strip.resize((width, height))
    # Diagonal: build per-row colour then expand horizontally.
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    span = width + height
    for y in range(height):
        for x in range(0, width, max(1, width // 64)):
            amount = (x + y) / max(1, span)
            draw.line((x, y, min(width, x + width // 64), y),
                      fill=mix(start, end, amount))
    return image


def shadow(image: Image.Image, radius: float = 18,
           opacity: float = .35) -> Image.Image:
    """Return a blurred black silhouette suitable for compositing beneath."""
    if opacity <= 0:
        return Image.new("RGBA", image.size, (0, 0, 0, 0))
    alpha = image.getchannel("A")
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    layer.putalpha(alpha.point(lambda value: int(value * opacity)))
    return layer.filter(ImageFilter.GaussianBlur(max(1, radius)))


def rounded(image: Image.Image, box: tuple[float, float, float, float],
            radius: float, fill, outline=None, width: int = 1,
            opacity: float = 1.0) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    x0, y0, x1, y1 = box
    radius = max(0.0, min(radius, (x1 - x0) / 2, (y1 - y0) / 2))
    fill_rgba = _rgba(fill, opacity)
    outline_rgba = _rgba(outline, opacity) if outline else None
    if fill_rgba is None and outline_rgba is None:
        return
    draw.rounded_rectangle((x0, y0, x1, y1), radius=radius,
                           fill=fill_rgba, outline=outline_rgba,
                           width=max(1, int(width)))


def circle(image: Image.Image, cx: float, cy: float, radius: float,
           fill=None, outline=None, width: int = 1,
           opacity: float = 1.0) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                 fill=_rgba(fill, opacity), outline=_rgba(outline, opacity),
                 width=max(1, int(width)))


def ring(image: Image.Image, cx: float, cy: float, radius: float,
         thickness: float, color, progress: float = 1.0,
         start_angle: float = -90, opacity: float = 1.0) -> None:
    if radius <= 0 or thickness <= 0:
        return
    progress = max(0.0, min(1.0, float(progress)))
    draw = ImageDraw.Draw(image, "RGBA")
    box = (cx - radius, cy - radius, cx + radius, cy + radius)
    stroke = max(1, int(round(thickness)))
    if progress >= .999:
        draw.ellipse(box, outline=_rgba(color, opacity), width=stroke)
        return
    if progress <= .001:
        return
    end = start_angle + 360 * progress
    draw.arc(box, start=start_angle, end=end, fill=_rgba(color, opacity),
             width=stroke)
    # Rounded caps make the progress ring feel designed, not clipped.
    for angle in (start_angle, end):
        radians = math.radians(angle)
        px = cx + radius * math.cos(radians)
        py = cy + radius * math.sin(radians)
        rr = stroke / 2
        draw.ellipse((px - rr, py - rr, px + rr, py + rr),
                     fill=_rgba(color, opacity))


def line(image: Image.Image, points, color, width: float = 2,
         opacity: float = 1.0, closed: bool = False, fill: bool = False) -> None:
    if not points:
        return
    draw = ImageDraw.Draw(image, "RGBA")
    colour = _rgba(color, opacity)
    if fill or closed:
        draw.polygon(points, fill=colour if fill else None,
                     outline=colour if not fill else None)
        if not fill and len(points) > 1:
            draw.line(points + ([points[0]] if closed else []),
                      fill=colour, width=max(1, int(round(width))),
                      joint="curve")
        return
    draw.line(points, fill=colour, width=max(1, int(round(width))),
              joint="curve")


def text_block(image: Image.Image, block: TextBlock, origin: tuple[float, float],
               fonts: FontBook, *, tracking_offset: float = 0.0,
               color=None, opacity: float = 1.0, scale: float = 1.0,
               skip_effects: bool = False) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    ox, oy = origin[0] * scale, origin[1] * scale
    progress = 0
    for line in block.lines:
        for word in line.words:
            if skip_effects and word.effect:
                progress += max(1, len(word.text))
                continue
            ink = color or word.color
            alpha = int(round(255 * opacity * block.style.opacity))
            if alpha <= 0:
                continue
            size = max(6, round((word.size or block.style.size) * scale))
            weight = word.weight or block.style.weight
            font = fonts.get(size, weight)
            offset = tracking_offset * progress * scale
            draw.text((ox + word.x * scale + offset,
                       oy + line.baseline * scale), word.text,
                      font=font, fill=(*ink, alpha), anchor="ls")
            progress += max(1, len(word.text))
    return


def text_block_mask(image: Image.Image, block: TextBlock,
                    origin: tuple[float, float], fonts: FontBook, *,
                    effect: str = "negative", tracking_offset: float = 0.0,
                    opacity: float = 1.0, scale: float = 1.0) -> None:
    """Draw only words carrying ``effect`` into a transparent alpha mask."""
    if effect != "negative":
        raise ValueError(f"Unsupported text mask effect {effect!r}")
    draw = ImageDraw.Draw(image, "RGBA")
    ox, oy = origin[0] * scale, origin[1] * scale
    progress = 0
    for line in block.lines:
        for word in line.words:
            if word.effect != effect:
                progress += max(1, len(word.text))
                continue
            alpha = int(round(255 * opacity * block.style.opacity))
            size = max(6, round((word.size or block.style.size) * scale))
            font = fonts.get(size, word.weight or block.style.weight)
            offset = tracking_offset * progress * scale
            draw.text((ox + word.x * scale + offset,
                       oy + line.baseline * scale), word.text,
                      font=font, fill=(255, 255, 255, alpha), anchor="ls")
            progress += max(1, len(word.text))


def number(image: Image.Image, value: float, rect: tuple[float, float, float, float],
           fonts: FontBook, *, fmt: dict | None = None,
           size: int = 120, color=(255, 255, 255), align: str = "center",
           opacity: float = 1.0, tracking_offset: float = 0.0,
           scale: float = 1.0) -> None:
    """Draw a tabular number whose width never jitters as digits change."""
    fmt = dict(fmt or {})
    text = format_value(value, fmt)
    x, y, w, h = (value * scale for value in rect)
    size = max(6, round(size * scale))
    tracking_offset = tracking_offset * scale
    font = fonts.get(size, "bold")
    width = digits_width(font, text)
    while width > w and size > 10:
        size = max(10, int(size * .94))
        font = fonts.get(size, "bold")
        width = digits_width(font, text)
    ascent, descent = font.getmetrics()
    text_height = ascent + descent
    if text_height > h:
        scale = h / text_height
        size = max(8, int(size * scale))
        font = fonts.get(size, "bold")
        ascent, descent = font.getmetrics()
        text_height = ascent + descent
    if align == "left":
        start = x
    elif align == "right":
        start = x + w - width
    else:
        start = x + (w - width) / 2
    baseline = y + (h - text_height) / 2 + ascent
    draw = ImageDraw.Draw(image, "RGBA")
    alpha = int(round(255 * opacity))
    digit_advance = max(font.getlength(str(digit)) for digit in "0123456789")
    cursor = start + tracking_offset
    for character in text:
        advance = digit_advance if character.isdigit() else font.getlength(character)
        draw.text((cursor, baseline), character, font=font,
                  fill=(*color, alpha), anchor="ls")
        cursor += advance


def tint(image: Image.Image, color: tuple[int, int, int],
         amount: float) -> Image.Image:
    if not 0 <= amount <= 1:
        raise ValueError("Tint amount must be between 0 and 1")
    if amount == 0:
        return image
    overlay = Image.new("RGBA", image.size, (*color, 255))
    return Image.blend(image.convert("RGBA"), overlay, amount)


def scrim(image: Image.Image, strength: float, *, from_bottom: bool = True,
          gamma: float = .85) -> Image.Image:
    """Per-context overlay instead of globally washing out every photograph."""
    if not 0 <= strength <= .95:
        raise ValueError("Scrim strength must be between 0 and 0.95")
    if strength <= 0:
        return image
    width, height = image.size
    gradient = Image.new("L", (1, height))
    pixels = gradient.load()
    for y in range(height):
        amount = y / max(1, height - 1)
        if not from_bottom:
            amount = 1 - amount
        pixels[0, y] = int(255 * strength * (amount ** gamma))
    mask = gradient.resize((width, height))
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    layer.putalpha(mask)
    return Image.alpha_composite(image.convert("RGBA"), layer)


def _rgba(color, opacity: float):
    if color is None:
        return None
    if isinstance(color, str):
        color = parse_hex(color)
    if len(color) == 4:
        r, g, b, a = color
        return (r, g, b, max(0, min(255, int(a * opacity))))
    r, g, b = color[:3]
    return (r, g, b, max(0, min(255, int(255 * opacity))))
