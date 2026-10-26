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


# Shared purple content zone for every standard 9:16 vertical Reel.
# Authored copy and illustrations stay inside; backgrounds and motion travel
# are handled separately.
VERTICAL_REELS_SAFE_INSETS = {
    "horizontal": .075,
    "top": .09,
    "bottom": .16,
}


def is_vertical_reels_canvas(width: int, height: int) -> bool:
    """Whether a canvas uses the standard 9:16 vertical Reels format."""
    if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
        return False
    return abs(width / height - 9 / 16) <= .01


def vertical_reels_content_polygon(width: int, height: int):
    """Return the rectangular content zone; the surrounding area is margin."""
    from ..textkit.safe_geometry import SafePolygon

    if not is_vertical_reels_canvas(width, height):
        raise ValueError("Vertical Reels safe zones require a 9:16 canvas")
    left = width * VERTICAL_REELS_SAFE_INSETS["horizontal"]
    right = width * (1.0 - VERTICAL_REELS_SAFE_INSETS["horizontal"])
    top = height * VERTICAL_REELS_SAFE_INSETS["top"]
    bottom = height * (1.0 - VERTICAL_REELS_SAFE_INSETS["bottom"])
    return SafePolygon(((left, top), (right, top), (right, bottom), (left, bottom)),
                       "vertical-reels-content")


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
    if is_vertical_reels_canvas(width, height):
        # Brand and style overrides may add breathing room, but cannot shrink
        # the shared vertical-Reels content zone.
        for key, minimum in VERTICAL_REELS_SAFE_INSETS.items():
            safe[key] = max(float(safe.get(key, minimum)), minimum)
    return DesignTokens(
        style=style, palette=palette, typography=typography, spacing=spacing,
        motion=motion, radii=radii, safe=safe,
        density=system.density, backdrop=system.backdrop,
        accent_ratio=system.accent_ratio,
        uppercase_kickers=system.uppercase_kickers,
        number_feature=system.number_feature,
        corner_style=system.corner_style,
    ).with_canvas(width, height)


PLATFORM_PROFILES: dict[str, dict[str, object]] = {
    "instagram_reels": {
        "width": 1080,
        "height": 1920,
        "aspect": "9:16",
        "safe": {"left": .075, "right": .075, "top": .08, "bottom": .14},
        "action_rail": {"x_from": .84, "y_from": .48},
    },
    "tiktok": {
        "width": 1080,
        "height": 1920,
        "aspect": "9:16",
        "safe": {"left": .075, "right": .075, "top": .09, "bottom": .16},
        "action_rail": {"x_from": .83, "y_from": .45},
    },
    "youtube_shorts": {
        "width": 1080,
        "height": 1920,
        "aspect": "9:16",
        "safe": {"left": .075, "right": .075, "top": .08, "bottom": .15},
        "action_rail": {"x_from": .84, "y_from": .50},
    },
    "linkedin_portrait": {
        "width": 1080,
        "height": 1350,
        "aspect": "4:5",
        "safe": {"left": .07, "right": .07, "top": .07, "bottom": .10},
        "action_rail": None,
    },
    "square_feed": {
        "width": 1080,
        "height": 1080,
        "aspect": "1:1",
        "safe": {"left": .075, "right": .075, "top": .075, "bottom": .09},
        "action_rail": None,
    },
    "landscape_hd": {
        "width": 1920,
        "height": 1080,
        "aspect": "16:9",
        "safe": {"left": .075, "right": .075, "top": .08, "bottom": .10},
        "action_rail": None,
    },
}


def resolve_platform_profile(name: str) -> dict[str, object]:
    """Return a validated copy of a social-platform profile (MD-403)."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Platform profile name must be a non-empty string")
    key = name.strip().lower().replace("-", "_")
    if key not in PLATFORM_PROFILES:
        raise ValueError(
            f"Unknown platform profile {name!r}; choose one of "
            + ", ".join(sorted(PLATFORM_PROFILES))
        )
    spec = PLATFORM_PROFILES[key]
    return {
        "id": key,
        "width": spec["width"],
        "height": spec["height"],
        "aspect": spec["aspect"],
        "safe": dict(spec["safe"]),
        "action_rail": dict(spec["action_rail"]) if spec["action_rail"] else None,
    }


def platform_safe_polygon(profile_name: str, width: int | None = None,
                          height: int | None = None):
    """Build a platform-specific SafePolygon accounting for UI rails (MD-203/403)."""
    from ..textkit.safe_geometry import SafePolygon

    spec = resolve_platform_profile(profile_name)
    w = int(width if width is not None else spec["width"])
    h = int(height if height is not None else spec["height"])
    if w <= 0 or h <= 0:
        raise ValueError("Canvas dimensions must be positive")
    safe = spec["safe"]
    left = w * float(safe["left"])
    right = w * (1.0 - float(safe["right"]))
    top = h * float(safe["top"])
    bottom = h * (1.0 - float(safe["bottom"]))
    rail = spec["action_rail"]
    if rail:
        rail_x = min(right, w * float(rail["x_from"]))
        rail_y = max(top, min(bottom, h * float(rail["y_from"])))
        if rail_x < right and top < rail_y < bottom:
            # 6-vertex L-polygon excluding the lower-right social UI action rail
            return SafePolygon((
                (left, top),
                (right, top),
                (right, rail_y),
                (rail_x, rail_y),
                (rail_x, bottom),
                (left, bottom),
            ), f"platform:{spec['id']}")
    return SafePolygon((
        (left, top),
        (right, top),
        (right, bottom),
        (left, bottom),
    ), f"platform:{spec['id']}")
