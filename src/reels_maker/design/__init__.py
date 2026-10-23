"""Shared design system: tokens, palettes, colour science and style systems."""
from .color import (
    average_colour, best_text_colour, blend_alpha, contrast_ratio, darken,
    ensure_contrast, lighten, meets_contrast, mix, parse_hex, relative_luminance,
    to_hex, with_alpha,
)
from .styles import STYLE_SYSTEMS, StyleSystem, canonical_style
from .tokens import (
    DesignTokens, MotionTokens, Palette, Spacing, TypeScale, make_palette,
    resolve_tokens,
)

__all__ = [
    "STYLE_SYSTEMS", "StyleSystem", "canonical_style", "DesignTokens",
    "MotionTokens", "Palette", "Spacing", "TypeScale", "make_palette",
    "resolve_tokens", "average_colour", "best_text_colour", "blend_alpha",
    "contrast_ratio", "darken", "ensure_contrast", "lighten", "meets_contrast",
    "mix", "parse_hex", "relative_luminance", "to_hex", "with_alpha",
]
