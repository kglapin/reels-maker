"""Design tokens shared by every studio composition.

Tokens are expressed in design units for a 1080 px short side. Layout and
typography multiply them by ``min(width, height) / 1080`` so the same manifest
looks proportionally identical in 9:16, 1:1 and 16:9. Absolute platform safe
areas continue to be pixel values, exactly like the legacy renderer.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Mapping

from .color import darken, lighten, parse_hex, to_hex


@dataclass(frozen=True)
class Palette:
    background: tuple[int, int, int]
    surface: tuple[int, int, int]
    ink: tuple[int, int, int]
    muted: tuple[int, int, int]
    accent: tuple[int, int, int]
    accent_dark: tuple[int, int, int]
    accent_light: tuple[int, int, int]
    danger: tuple[int, int, int]
    positive: tuple[int, int, int]
    on_accent: tuple[int, int, int]

    def as_hex(self) -> dict[str, str]:
        return {name: to_hex(value) for name, value in self.__dict__.items()}


@dataclass(frozen=True)
class TypeScale:
    display: int = 196
    hero: int = 138
    title: int = 88
    subtitle: int = 48
    body: int = 34
    caption: int = 27
    micro: int = 21
    kicker: int = 30
    line_height: float = 1.08
    tracking: float = 0.0

    def size(self, role: str) -> int:
        if not hasattr(self, role) or role in ("line_height", "tracking"):
            raise KeyError(f"Unknown typography role: {role!r}")
        return int(getattr(self, role))


@dataclass(frozen=True)
class Spacing:
    xs: int = 8
    sm: int = 16
    md: int = 28
    lg: int = 44
    xl: int = 68
    xxl: int = 104

    def __getitem__(self, key: str) -> int:
        return int(getattr(self, key))


@dataclass(frozen=True)
class MotionTokens:
    enter: float = .46
    micro: float = .22
    stagger: float = .085
    settle: float = .72
    hold: float = .55
    exit: float = .28
    overshoot: float = 1.045
    camera_drift: float = .055


@dataclass(frozen=True)
class DesignTokens:
    style: str
    palette: Palette
    typography: TypeScale
    spacing: Spacing
    motion: MotionTokens
    radii: Mapping[str, int] = field(default_factory=lambda: {
        "sm": 10, "md": 22, "lg": 34, "pill": 999})
    stroke: Mapping[str, int] = field(default_factory=lambda: {"hair": 2, "line": 4, "bold": 8})
    safe: Mapping[str, float] = field(default_factory=lambda: {
        "horizontal": .075, "top": .075, "bottom": .11})
    scale: float = 1.0
    density: str = "balanced"
    backdrop: str = "scrim"
    accent_ratio: float = .12
    uppercase_kickers: bool = True
    number_feature: str = "tabular"
    corner_style: str = "soft"

    def px(self, value: float) -> int:
        """Scale a design-unit measurement to the active canvas."""
        return max(1, round(float(value) * self.scale))

    def type_size(self, role: str) -> int:
        return self.px(self.typography.size(role))

    def radius(self, name: str = "md") -> int:
        return self.px(self.radii[name])

    def space(self, name: str = "md") -> int:
        return self.px(self.spacing[name])

    def safe_pixels(self, width: int, height: int) -> tuple[int, int, int]:
        return (round(width * self.safe["horizontal"]),
                round(height * self.safe["top"]),
                round(height * self.safe["bottom"]))

    def with_canvas(self, width: int, height: int) -> "DesignTokens":
        scale = min(width, height) / 1080.0
        return replace(self, scale=scale)

    def to_dict(self) -> dict:
        return {
            "style": self.style,
            "scale": self.scale,
            "palette": self.palette.as_hex(),
            "typography": {
                name: self.type_size(name)
                for name in ("display", "hero", "title", "subtitle",
                             "body", "caption", "micro", "kicker")
            },
            "spacing": {name: self.space(name)
                        for name in ("xs", "sm", "md", "lg", "xl", "xxl")},
            "motion": self.motion.__dict__,
            "radii": {name: self.radius(name) for name in self.radii},
            "safe": dict(self.safe),
            "density": self.density,
            "backdrop": self.backdrop,
        }


NEUTRAL = {
    "background": "#0E1A13",
    "surface": "#FFFFFF",
    "ink": "#FFFFFF",
    "muted": "#C6D3CB",
    "accent": "#47A013",
    "danger": "#C2412D",
    "positive": "#1D7A46",
}


def make_palette(values: Mapping[str, str] | None = None,
                 *, background: str | None = None) -> Palette:
    """Resolve a brand palette into the roles used by compositions."""
    source = {**NEUTRAL, **(values or {})}
    accent = parse_hex(source.get("accent", NEUTRAL["accent"]))
    background_colour = parse_hex(background or source.get("background", NEUTRAL["background"]))
    surface = parse_hex(source.get("surface", NEUTRAL["surface"]))
    ink = parse_hex(source.get("ink", source.get("text", NEUTRAL["ink"])))
    muted_raw = source.get("muted")
    muted = parse_hex(muted_raw) if muted_raw else lighten(ink, .28)
    return Palette(
        background=background_colour,
        surface=surface,
        ink=ink,
        muted=muted,
        accent=accent,
        accent_dark=darken(accent, .28),
        accent_light=lighten(accent, .72),
        danger=parse_hex(source.get("danger", NEUTRAL["danger"])),
        positive=parse_hex(source.get("positive", NEUTRAL["positive"])),
        # White stays the safest ink on a saturated brand accent.
        on_accent=parse_hex(source.get("on_accent", "#FFFFFF")),
    )


def resolve_tokens(style: str, brand: Mapping | None = None,
                   *, width: int = 1080, height: int = 1920,
                   overrides: Mapping | None = None) -> DesignTokens:
    """Compose a style with brand colours and optional per-project overrides."""
    from .styles import STYLE_SYSTEMS

    if style not in STYLE_SYSTEMS:
        raise ValueError(f"Unknown visual style {style!r}; choose one of "
                         + ", ".join(sorted(STYLE_SYSTEMS)))
    system = STYLE_SYSTEMS[style]
    brand = brand or {}
    palette_values = brand.get("palette", brand if isinstance(brand, Mapping) else {})
    if not isinstance(palette_values, Mapping):
        raise ValueError("Brand palette must be an object of hex colours")
    palette = make_palette({**system.palette, **palette_values},
                           background=system.palette.get("background"))
    overrides = dict(overrides or {})
    typography = replace(system.typography,
                         **{key: value for key, value in overrides.items()
                            if key in TypeScale.__dataclass_fields__})
    spacing = replace(system.spacing,
                      **{key: value for key, value in overrides.items()
                         if key in Spacing.__dataclass_fields__})
    motion = replace(system.motion,
                     **{key: value for key, value in overrides.items()
                        if key in MotionTokens.__dataclass_fields__})
    radii = {**system.radii, **overrides.get("radii", {})}
    safe = {**system.safe, **overrides.get("safe", {})}
    return DesignTokens(
        style=style, palette=palette, typography=typography, spacing=spacing,
        motion=motion, radii=radii, safe=safe,
        density=system.density, backdrop=system.backdrop,
        accent_ratio=system.accent_ratio,
        uppercase_kickers=system.uppercase_kickers,
        number_feature=system.number_feature,
        corner_style=system.corner_style,
    ).with_canvas(width, height)
