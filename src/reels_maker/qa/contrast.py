"""Contrast checks for Studio QA."""
from __future__ import annotations

from PIL import Image, ImageStat

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


def _ring_coverage(built, time: float, box, role: str | None = None,
                   thickness: int = 5) -> float:
    """Share of the contrast-sampling ring hidden by an opaque frame sequence.

    A captured overlay (for example, real torn paper) can legitimately cover
    copy before it is revealed. Reading the alpha of the exact sequence frame
    drawn above the element keeps contrast honest: nothing is scored against a
    sheet that is still in front of the text.
    """
    x0, y0, x1, y1 = (float(value) for value in box)
    x0, y0 = x0 - thickness, y0 - thickness
    x1, y1 = x1 + thickness, y1 + thickness
    if x1 - x0 < 1 or y1 - y0 < 1:
        return 0.0
    from ..renderers.scene import sequence_frame_path

    sampler = getattr(built, "at", None)
    if sampler is None:
        # Lightweight QA harnesses without a scene graph cannot hide anything.
        return 0.0
    nodes = sampler(time)
    element_order = next((index for index, node in enumerate(nodes)
                          if node.role == role), None)
    if element_order is None:
        return 0.0
    covered_pixels = 0.0
    total_area = (x1 - x0) * (y1 - y0)
    for index, node in enumerate(nodes):
        if index <= element_order:
            continue
        if node.kind != "sequence" or node.opacity < .98:
            continue
        props = node.props
        path = sequence_frame_path(props, time)
        if path is None or not path.is_file():
            continue
        nx, ny = float(props["x"]) + node.dx, float(props["y"]) + node.dy
        nw, nh = float(props["w"]), float(props["h"])
        ix0, iy0 = max(x0, nx), max(y0, ny)
        ix1, iy1 = min(x1, nx + nw), min(y1, ny + nh)
        if ix1 <= ix0 or iy1 <= iy0:
            continue
        with Image.open(path) as handle:
            alpha = handle.convert("RGBA").getchannel("A")
        sw, sh = alpha.size
        scale = max(nw / sw, nh / sh)
        offset_x = (nw - sw * scale) / 2
        offset_y = (nh - sh * scale) / 2
        sx0 = int(max(0, ((ix0 - nx) - offset_x) / scale))
        sx1 = int(min(sw, max(sx0 + 1, ((ix1 - nx) - offset_x) / scale)))
        sy0 = int(max(0, ((iy0 - ny) - offset_y) / scale))
        sy1 = int(min(sh, max(sy0 + 1, ((iy1 - ny) - offset_y) / scale)))
        if sx1 <= sx0 or sy1 <= sy0:
            continue
        window = alpha.crop((sx0, sy0, sx1, sy1))
        mean_alpha = ImageStat.Stat(window).mean[0] / 255
        covered_pixels += (ix1 - ix0) * (iy1 - iy0) * mean_alpha
    return min(1.0, covered_pixels / total_area)


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
        if _ring_coverage(built, time, element["bounds"],
                          element.get("role")) > .55:
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
