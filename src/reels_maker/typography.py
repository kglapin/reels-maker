"""Editorial mixed-size headline layout: explicit emphasis, no arbitrary HTML."""
from __future__ import annotations
import re
from dataclasses import dataclass
from PIL import ImageDraw
from .ffmpeg import RenderError

@dataclass(frozen=True)
class RichLayout:
    parts: list[tuple[str, object, str, int, int]]
    height: int
    lines: int


def layout_runs(draw: ImageDraw.ImageDraw, runs: list[dict], font_loader,
                base_size: int, max_width: int, accent: str) -> RichLayout:
    """Wrap words across styled runs, preserving typography within each line."""
    lines: list[tuple[list, int]] = []
    current: list = []
    x = 0.0
    height = max(13, round(base_size * 1.23))
    def flush():
        nonlocal current, x, height
        if current:
            lines.append((current, height))
        current, x = [], 0.0
        height = max(13, round(base_size * 1.23))

    for item in runs:
        if item.get("break_before"):
            flush()
        size = max(9, round(base_size * item.get("scale", 1.0)))
        face = font_loader(size, item.get("weight", "bold") == "bold")
        palette = {"white": "#FFFFFF", "accent": accent,
                   "muted": "#D6E5DD"}
        ink = palette[item.get("color", "white")]
        for token in re.findall(r"\S+|\s+", item["text"].replace("\n", " ")):
            if token.isspace() and not current:
                continue
            text_width = float(draw.textlength(token, font=face))
            if text_width > max_width:
                raise RenderError(f"Headline word too wide: {token.strip()!r}")
            if current and x + text_width > max_width and not token.isspace():
                flush()
            if token.isspace() and x + text_width > max_width:
                flush()
                continue
            current.append((token, face, ink, round(x)))
            x += text_width
            height = max(height, round(size * 1.24))
    flush()
    if not lines:
        raise RenderError("Rich headline cannot be empty")
    y = 0
    placed = []
    for pieces, line_height in lines:
        for token, face, ink, px in pieces:
            if not token.isspace():
                placed.append((token, face, ink, px, y))
        y += line_height
    return RichLayout(parts=placed, height=y, lines=len(lines))
