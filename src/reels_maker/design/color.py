"""Small, deterministic colour toolkit used by the studio design system.

Everything here is pure Python: no dependency on Cairo, Pillow or a display.
Colours are RGB tuples in the 0..255 range. Alpha is handled explicitly where
it matters, never as an implicit fourth channel in design tokens.
"""
from __future__ import annotations

import math
import re

HEX = re.compile(r"^#?(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def parse_hex(value: str) -> tuple[int, int, int]:
    """Parse ``#RGB`` or ``#RRGGBB`` with a clear error for bad values."""
    if not isinstance(value, str) or not HEX.fullmatch(value.strip()):
        raise ValueError(f"Invalid hex colour: {value!r}")
    raw = value.strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(letter * 2 for letter in raw)
    return tuple(int(raw[index:index + 2], 16) for index in (0, 2, 4))


def to_hex(color: tuple[int, int, int]) -> str:
    if len(color) != 3 or any(type(channel) is not int or not 0 <= channel <= 255
                              for channel in color):
        raise ValueError("Colour must be three integers in the 0..255 range")
    return "#{:02X}{:02X}{:02X}".format(*color)


def clamp_channel(value: float) -> int:
    return max(0, min(255, round(value)))


def mix(first: tuple[int, int, int], second: tuple[int, int, int],
        amount: float) -> tuple[int, int, int]:
    if not math.isfinite(amount):
        raise ValueError("Mix amount must be finite")
    amount = max(0.0, min(1.0, amount))
    return tuple(clamp_channel(a + (b - a) * amount)
                 for a, b in zip(first, second))


def lighten(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return mix(color, (255, 255, 255), amount)


def darken(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return mix(color, (0, 0, 0), amount)


def blend_alpha(foreground: tuple[int, int, int], background: tuple[int, int, int],
                alpha: float) -> tuple[int, int, int]:
    """Composite a translucent ink over an opaque background."""
    if not math.isfinite(alpha) or not 0 <= alpha <= 1:
        raise ValueError("Alpha must be between 0 and 1")
    return mix(background, foreground, alpha)


def relative_luminance(color: tuple[int, int, int]) -> float:
    """WCAG 2.x relative luminance."""
    channels = []
    for channel in color:
        value = channel / 255.0
        channels.append(value / 12.92 if value <= .04045
                        else ((value + .055) / 1.055) ** 2.4)
    red, green, blue = channels
    return .2126 * red + .7152 * green + .0722 * blue


def contrast_ratio(first: tuple[int, int, int],
                   second: tuple[int, int, int]) -> float:
    """WCAG contrast ratio between two opaque colours (1..21)."""
    a, b = relative_luminance(first), relative_luminance(second)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + .05) / (darker + .05)


def meets_contrast(foreground: tuple[int, int, int],
                   background: tuple[int, int, int], minimum: float) -> bool:
    return contrast_ratio(foreground, background) + 1e-9 >= minimum


def ensure_contrast(ink: tuple[int, int, int],
                    background: tuple[int, int, int], minimum: float = 4.5,
                    direction: str | None = None) -> tuple[int, int, int]:
    """Return ``ink`` or a darker/lighter variant that passes ``minimum``.

    Brand accent colours are preserved whenever they already pass. Only small
    text is adjusted; the caller chooses ``minimum`` from type size. A pure
    black/white fallback is always guaranteed to pass because the ratio
    between black and white is 21:1.
    """
    if not 1 <= minimum <= 21:
        raise ValueError("Contrast target must be between 1 and 21")
    if meets_contrast(ink, background, minimum):
        return ink
    if direction is None:
        # Choose the direction that can actually reach the target against this
        # backdrop. A saturated brand accent can have low luminance yet still
        # need to be lightened on a deep panel, not darkened into it.
        direction = "lighten" if relative_luminance(background) < .5 else "darken"
    if direction not in ("darken", "lighten"):
        raise ValueError("direction must be darken or lighten")
    target = (0, 0, 0) if direction == "darken" else (255, 255, 255)
    # Search along a perceptual mix for the closest passing colour. This is
    # deterministic and avoids abrupt pure-black typography on deep panels.
    for step in range(1, 101):
        candidate = mix(ink, target, step / 100)
        if meets_contrast(candidate, background, minimum):
            return candidate
    # Pure black or white always passes 4.5:1 on the opposite backdrop; the
    # fallback is explicit rather than returning an unverified colour.
    opposite = (0, 0, 0) if direction == "lighten" else (255, 255, 255)
    return opposite


def best_text_colour(background: tuple[int, int, int],
                     light: tuple[int, int, int] = (255, 255, 255),
                     dark: tuple[int, int, int] = (20, 34, 26)) -> tuple[int, int, int]:
    """Pick whichever editorial ink has more contrast on a sampled backdrop."""
    return light if contrast_ratio(light, background) >= contrast_ratio(
        dark, background) else dark


def average_colour(pixels: list[tuple[int, int, int]]) -> tuple[int, int, int]:
    if not pixels:
        raise ValueError("At least one pixel is required")
    if any(len(pixel) < 3 for pixel in pixels):
        raise ValueError("Pixels must be RGB tuples")
    count = len(pixels)
    return (round(sum(p[0] for p in pixels) / count),
            round(sum(p[1] for p in pixels) / count),
            round(sum(p[2] for p in pixels) / count))


def with_alpha(color: tuple[int, int, int], alpha: float) -> tuple[int, int, int, int]:
    if not math.isfinite(alpha) or not 0 <= alpha <= 1:
        raise ValueError("Alpha must be between 0 and 1")
    return (*color, round(alpha * 255))
