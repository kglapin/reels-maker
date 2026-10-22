"""Baseline-aligned mixed-size editorial typography.

Titles use explicit semantic runs, actual glyph metrics, and a shared
typographic baseline. Enlarged words no longer appear to float above smaller
words; lines are wrapped at word boundaries and sized from real font metrics.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from PIL import ImageDraw

from .ffmpeg import RenderError


@dataclass(frozen=True)
class RichLayout:
    # text, PIL face, ink, x, baseline y, source-run index
    parts: list[tuple[str, object, str, int, int, int]]
    height: int
    lines: int


def layout_runs(draw: ImageDraw.ImageDraw, runs: list[dict], font_loader,
                base_size: int, max_width: int, accent: str) -> RichLayout:
    """Measure and line-break a headline with a shared baseline per line."""
    if max_width < 1:
        raise RenderError("Headline has no horizontal layout space")
    # Per-line pieces hold text, font, ink, x and run identity.
    pending: list[tuple[str, object, str, int, int]] = []
    rows: list[list] = []
    x = 0.0

    def flush() -> None:
        nonlocal pending, x
        if pending:
            rows.append(pending)
        pending = []
        x = 0.0

    for run_index, item in enumerate(runs):
        if item.get("break_before"):
            flush()
        size = max(9, round(base_size * item.get("scale", 1.0)))
        font = font_loader(size, item.get("weight", "bold") == "bold")
        ink = {
            "white": "#FFFFFF",
            "accent": accent,
            "muted": "#D6E5DD",
        }[item.get("color", "white")]
        # Whitespace remains attached to text until the next word; leading
        # whitespace after an explicit break is intentionally discarded.
        for token in re.findall(r"\S+|\s+", item["text"].replace("\n", " ")):
            if token.isspace() and not pending:
                continue
            advance = float(draw.textlength(token, font=font))
            if advance > max_width and not token.isspace():
                raise RenderError(f"Headline word too wide: {token.strip()!r}")
            if x + advance > max_width:
                if token.isspace():
                    flush()
                    continue
                if pending:
                    flush()
                else:
                    raise RenderError("Headline word exceeds width")
            pending.append((token, font, ink, round(x), run_index))
            x += advance
    flush()
    if not rows:
        raise RenderError("Rich headline cannot be empty")

    placed: list[tuple[str, object, str, int, int, int]] = []
    y = 0
    for row in rows:
        metrics = [piece[1].getmetrics() for piece in row]
        asc = max(pair[0] for pair in metrics)
        desc = max(pair[1] for pair in metrics)
        # Text belongs to the same baseline regardless of font size.
        baseline = y + asc
        for token, face, ink, px, run_index in row:
            if not token.isspace():
                placed.append((token, face, ink, px, baseline, run_index))
        line_height = max(
            asc + desc + max(1, round(base_size * .12)),
            round(base_size * 1.2))
        y += line_height
    return RichLayout(parts=placed, height=y, lines=len(rows))
