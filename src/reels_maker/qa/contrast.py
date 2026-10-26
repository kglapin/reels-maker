"""Contrast checks for Studio QA."""
from __future__ import annotations

from PIL import Image

from ..design.color import contrast_ratio, relative_luminance
from .models import Issue

CONTRAST_LARGE = 3.0
CONTRAST_SMALL = 4.5



def _median_colour(pixels: list[tuple[int, int, int]]) -> tuple[int, int, int]:
    if not pixels:
        return (0, 0, 0)
    pixels = sorted(pixels, key=relative_luminance)
    return pixels[len(pixels) // 2]


def _ring_pixels(image: Image.Image, box, thickness: int = 5):
    x0, y0, x1, y1 = (round(value) for value in box)
    width, height = image.size
    # Sample a ring outside the glyph box so anti-aliased text pixels do not
    # masquerade as the backdrop and depress the measured contrast.
    x0, y0 = max(0, x0 - thickness), max(0, y0 - thickness)
    x1, y1 = min(width, x1 + thickness), min(height, y1 + thickness)
    if x1 - x0 < 2 or y1 - y0 < 2:
        return []
    crop = image.crop((x0, y0, x1, y1)).convert("RGB")
    pixels = []
    cw, ch = crop.size
    data = crop.load()
    for y in range(ch):
        for x in range(cw):
            if x < thickness or y < thickness or x >= cw - thickness or y >= ch - thickness:
                pixels.append(data[x, y])
    return pixels


def _contrast(elements: list[dict], frame: Image.Image, built,
              time: float, fps: int, *, design_scale: float = 1.0) -> list[Issue]:
    issues = []
    for element in elements:
        # Transient entrance states are intentionally semi-transparent; only
        # judge contrast once the element has settled into its readable state.
        if element["opacity"] < .98:
            continue
        if element["meta"].get("negative_effect"):
            # The ink is a per-pixel inverse of the sampled image, not the
            # token color stored in the typeset block.
            continue
        colour = element["meta"].get("color")
        if not colour:
            continue
        size = float(element["meta"].get("size", 24)) / max(1e-6, design_scale)
        weight = element["meta"].get("weight", "regular")
        threshold = CONTRAST_LARGE if (size >= 32 or (size >= 24 and weight == "bold"))\
            else CONTRAST_SMALL
        pixels = _ring_pixels(frame, element["bounds"], thickness=5)
        if not pixels:
            continue
        background = _median_colour(pixels)
        ratio = contrast_ratio(tuple(colour[:3]), background)
        if ratio + 1e-6 < threshold:
            issues.append(Issue(
                "contrast_low", "error",
                (f"{element.get('path', element['role'])!r} has {ratio:.2f}:1 against the sampled "
                 f"backdrop; {threshold:.1f}:1 required at this size."),
                built.index + 1, round(time, 3),
                [element.get("path", element["role"])],
                "Use the accessible accent variant or a contextual scrim/panel.",
                round(time * fps)))
    return issues
