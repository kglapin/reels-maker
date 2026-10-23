"""Five distinct visual systems built on one shared scene engine.

The style system changes composition order, motion vocabulary, typography
proportions and transition rhythm — not the underlying renderer. A brand can
therefore switch style without forking the codebase, and every new component
becomes available to every style.
"""
from __future__ import annotations

from dataclasses import dataclass

from .tokens import MotionTokens, Spacing, TypeScale


@dataclass(frozen=True)
class StyleSystem:
    key: str
    label: str
    purpose: str
    palette: dict[str, str]
    typography: TypeScale
    spacing: Spacing
    motion: MotionTokens
    radii: dict[str, int]
    safe: dict[str, float]
    density: str
    backdrop: str
    accent_ratio: float
    uppercase_kickers: bool
    number_feature: str
    corner_style: str
    compositions: tuple[str, ...]
    motions: tuple[str, ...]
    transitions: tuple[str, ...]
    preferred_components: tuple[str, ...]


EDITORIAL = StyleSystem(
    key="editorial-premium",
    label="Editorial Premium",
    purpose="B2B, experts and finance: restrained motion, precise hierarchy.",
    palette={
        "background": "#101A14",
        "surface": "#F7F7F2",
        "ink": "#FFFFFF",
        "muted": "#C9D2CB",
        "accent": "#47A013",
    },
    typography=TypeScale(display=170, hero=120, title=78, subtitle=42,
                         body=31, caption=25, micro=20, kicker=28,
                         line_height=1.10, tracking=0.01),
    spacing=Spacing(xs=8, sm=18, md=30, lg=48, xl=76, xxl=112),
    motion=MotionTokens(enter=.54, micro=.26, stagger=.11, settle=.78,
                        hold=.62, overshoot=1.018, camera_drift=.038),
    radii={"sm": 6, "md": 14, "lg": 24, "pill": 999},
    safe={"horizontal": .082, "top": .082, "bottom": .118},
    density="airy",
    backdrop="scrim",
    accent_ratio=.08,
    uppercase_kickers=True,
    number_feature="tabular",
    corner_style="precise",
    compositions=("stack-center", "split-editorial", "hero-number",
                  "full-bleed-type", "data-panel", "statement",
                  "timeline", "cta-panel"),
    motions=("fade-up", "mask-rise", "slide-left", "tracking-in",
             "word-cascade", "pop-settle"),
    transitions=("cut", "dip", "wipe-up"),
    preferred_components=("counter", "stat", "comparison", "checklist"),
)

KINETIC = StyleSystem(
    key="kinetic-advertising",
    label="Kinetic Advertising",
    purpose="Ads, subsidies and promotions: energetic rhythm and bold numbers.",
    palette={
        "background": "#142C1E",
        "surface": "#FFFFFF",
        "ink": "#FFFFFF",
        "muted": "#D5E4D9",
        "accent": "#47A013",
    },
    typography=TypeScale(display=210, hero=150, title=96, subtitle=52,
                         body=36, caption=28, micro=22, kicker=32,
                         line_height=1.02, tracking=-0.01),
    spacing=Spacing(xs=8, sm=16, md=26, lg=42, xl=64, xxl=96),
    motion=MotionTokens(enter=.38, micro=.18, stagger=.065, settle=.66,
                        hold=.5, overshoot=1.065, camera_drift=.075),
    radii={"sm": 10, "md": 24, "lg": 40, "pill": 999},
    safe={"horizontal": .072, "top": .072, "bottom": .105},
    density="dense",
    backdrop="strong",
    accent_ratio=.16,
    uppercase_kickers=True,
    number_feature="tabular",
    corner_style="soft",
    compositions=("hero-number", "stack-center", "full-bleed-type",
                  "comparison", "data-panel", "calendar", "cta-panel",
                  "breakdown"),
    motions=("pop-settle", "mask-rise", "word-cascade", "slide-right",
             "tracking-in", "scale-focus"),
    transitions=("cut", "wipe-left", "wipe-up", "dip"),
    preferred_components=("counter", "donut", "comparison", "bars"),
)

CINEMATIC = StyleSystem(
    key="product-cinematic",
    label="Product Cinematic",
    purpose="Products, technology and installations: photography and depth.",
    palette={
        "background": "#0A0F0C",
        "surface": "#FFFFFF",
        "ink": "#FFFFFF",
        "muted": "#CCD6CF",
        "accent": "#7CC242",
    },
    typography=TypeScale(display=156, hero=112, title=74, subtitle=40,
                         body=30, caption=24, micro=19, kicker=26,
                         line_height=1.14, tracking=.02),
    spacing=Spacing(xs=8, sm=18, md=32, lg=52, xl=80, xxl=120),
    motion=MotionTokens(enter=.72, micro=.3, stagger=.12, settle=.9,
                        hold=.7, overshoot=1.012, camera_drift=.11),
    radii={"sm": 4, "md": 10, "lg": 18, "pill": 999},
    safe={"horizontal": .075, "top": .08, "bottom": .13},
    density="airy",
    backdrop="scrim",
    accent_ratio=.1,
    uppercase_kickers=False,
    number_feature="proportional",
    corner_style="precise",
    compositions=("spotlight", "split-editorial", "full-bleed-type",
                  "statement", "hero-number", "cta-panel"),
    motions=("fade-up", "mask-rise", "slide-left", "scale-focus",
             "tracking-in", "pop-settle"),
    transitions=("cut", "dip", "wipe-up"),
    preferred_components=("spotlight", "stat", "energy-flow", "checklist"),
)

DATA = StyleSystem(
    key="data-storytelling",
    label="Data Storytelling",
    purpose="Reports, savings and comparisons: readable numbers and charts.",
    palette={
        "background": "#F2F5F0",
        "surface": "#FFFFFF",
        "ink": "#14221A",
        "muted": "#59685E",
        "accent": "#47A013",
        "on_accent": "#FFFFFF",
    },
    typography=TypeScale(display=168, hero=124, title=82, subtitle=44,
                         body=32, caption=26, micro=21, kicker=28,
                         line_height=1.12, tracking=.005),
    spacing=Spacing(xs=8, sm=16, md=28, lg=44, xl=70, xxl=104),
    motion=MotionTokens(enter=.5, micro=.22, stagger=.08, settle=.72,
                        hold=.64, overshoot=1.02, camera_drift=.03),
    radii={"sm": 8, "md": 18, "lg": 28, "pill": 999},
    safe={"horizontal": .08, "top": .08, "bottom": .115},
    density="balanced",
    backdrop="none",
    accent_ratio=.12,
    uppercase_kickers=False,
    number_feature="tabular",
    corner_style="soft",
    compositions=("data-panel", "comparison", "hero-number", "stat-grid",
                  "statement", "cta-panel"),
    motions=("fade-up", "pop-settle", "mask-rise", "word-cascade",
             "slide-left", "tracking-in"),
    transitions=("cut", "dip"),
    preferred_components=("bars", "donut", "comparison", "counter", "checklist"),
)

SOCIAL = StyleSystem(
    key="social-native",
    label="Social Native",
    purpose="Reels, Shorts and TikTok: faster cuts and short captions.",
    palette={
        "background": "#111111",
        "surface": "#FFFFFF",
        "ink": "#FFFFFF",
        "muted": "#D8D8D8",
        "accent": "#47A013",
    },
    typography=TypeScale(display=196, hero=142, title=92, subtitle=50,
                         body=38, caption=30, micro=23, kicker=32,
                         line_height=.98, tracking=-.015),
    spacing=Spacing(xs=8, sm=16, md=24, lg=38, xl=58, xxl=88),
    motion=MotionTokens(enter=.32, micro=.16, stagger=.05, settle=.58,
                        hold=.42, overshoot=1.08, camera_drift=.09),
    radii={"sm": 12, "md": 28, "lg": 44, "pill": 999},
    safe={"horizontal": .07, "top": .09, "bottom": .16},
    density="dense",
    backdrop="strong",
    accent_ratio=.18,
    uppercase_kickers=True,
    number_feature="tabular",
    corner_style="soft",
    compositions=("hero-number", "full-bleed-type", "statement",
                  "spotlight", "comparison", "cta-panel"),
    motions=("pop-settle", "word-cascade", "slide-right", "mask-rise",
             "scale-focus", "tracking-in"),
    transitions=("cut", "wipe-left", "dip"),
    preferred_components=("counter", "stat", "donut", "bars"),
)


STYLE_SYSTEMS = {system.key: system for system in (
    EDITORIAL, KINETIC, CINEMATIC, DATA, SOCIAL)}

STYLE_ALIASES = {
    "editorial": "editorial-premium",
    "premium": "editorial-premium",
    "kinetic": "kinetic-advertising",
    "advertising": "kinetic-advertising",
    "cinematic": "product-cinematic",
    "product": "product-cinematic",
    "data": "data-storytelling",
    "storytelling": "data-storytelling",
    "social": "social-native",
    "native": "social-native",
}


def canonical_style(name: str | None) -> str:
    if not name:
        return "kinetic-advertising"
    key = name.strip().lower().replace("_", "-")
    key = STYLE_ALIASES.get(key, key)
    if key not in STYLE_SYSTEMS:
        raise ValueError(f"Unknown visual style {name!r}; choose one of "
                         + ", ".join(sorted(STYLE_SYSTEMS)))
    return key
