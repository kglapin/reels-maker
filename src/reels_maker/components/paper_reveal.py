"""Reveal copy through real, chroma-keyed footage of a sheet being torn.

The builder never draws paper itself: it composites an approved frame sequence
(paper on a transparent background) over authored copy, keeping the material
behaviour, curled fibers and light gradient of the actual capture.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from ..core.scene_graph import Node
from ..textkit.typesetter import TextStyle
from .base import (
    BuiltScene, SceneContext, image_node, resolve_text_style, text_node,
)
from .scene_support import _background, _finish, _spec, _theme

_SEQUENCE_SUFFIXES = (".png", ".webp")


def sequence_frames(directory: str | Path) -> list[str]:
    """Return the frame sequence in deterministic name order."""
    root = Path(directory)
    if not root.is_dir():
        raise ValueError(f"Paper-reveal sequence directory is missing: {root}")
    frames = sorted(
        str(path) for path in root.iterdir()
        if path.is_file() and path.suffix.lower() in _SEQUENCE_SUFFIXES)
    if len(frames) < 2:
        raise ValueError(
            f"Paper-reveal sequence needs at least two frames: {root}")
    return frames


def build_paper_reveal(ctx: SceneContext, scene: dict) -> BuiltScene:
    theme = _theme(ctx, {**scene, "theme": scene.get("theme", "dark")})
    safe = ctx.layout.safe
    tear_enabled = bool(scene.get("tear", True))
    if tear_enabled and not scene.get("tear_sequence"):
        raise ValueError(
            "paper_reveal requires tear_sequence: a brand-relative directory "
            "of chroma-keyed RGBA frames")
    frames = sequence_frames(scene["tear_sequence"]) if tear_enabled else []
    headline = str(scene.get("headline", "CO JEST POD SPODEM?"))
    kicker = str(scene.get("kicker", ""))
    subtitle = str(scene.get("subtitle", ""))
    headline_color = tuple(theme["ink"])

    elements: dict[str, Node] = {}
    band_top = ctx.height * .455
    if kicker:
        elements["kicker"] = text_node(
            "kicker", kicker,
            resolve_text_style(ctx.tokens, "kicker", tuple(theme["accent"]),
                               align="center"),
            type(safe)(safe.x, band_top - 215, safe.w, 46),
            ctx.fonts, align="center", valign="center")
    logo_value = scene.get("logo")
    if logo_value:
        logo_path = Path(str(logo_value))
        if not logo_path.is_absolute() and ctx.assets is not None:
            logo_path = Path(ctx.assets.brand_root) / logo_path
        if not logo_path.is_file():
            raise ValueError(f"Paper-reveal logo does not exist: {logo_path}")
        with Image.open(logo_path) as logo_image:
            aspect = logo_image.width / max(1, logo_image.height)
        logo_h = min(safe.h * .09, ctx.tokens.px(100))
        logo_w = min(safe.w * .6, logo_h * aspect)
        elements["logo"] = image_node(
            "logo", str(logo_path),
            type(safe)(safe.center_x - logo_w / 2, band_top - 245,
                       logo_w, logo_h),
            meta={"asset_role": "brand-logo"})
    elements["headline"] = text_node(
        "headline", headline,
        TextStyle(size=ctx.tokens.type_size("display"), color=headline_color,
                  weight="bold", align="center", line_height=1.1),
        type(safe)(safe.x, band_top - 132, safe.w, 205),
        ctx.fonts, align="center", valign="center")
    if subtitle:
        elements["subtitle"] = text_node(
            "subtitle", subtitle,
            resolve_text_style(ctx.tokens, "subtitle", tuple(theme["muted"]),
                               align="center"),
            type(safe)(safe.x + 40, band_top + 112, safe.w - 80, 95),
            ctx.fonts, align="center", valign="center")

    if tear_enabled:
        tear_zoom = float(scene.get("tear_zoom", 1.14))
        tear_w = ctx.width * tear_zoom
        tear_h = ctx.height * tear_zoom
        elements["tear-footage"] = Node(
            kind="sequence", role="tear-footage",
            props={"frames": frames,
                   "fps": float(scene.get("tear_fps", 25.0)),
                   "start": float(scene.get("tear_start", .35)),
                   "speed": float(scene.get("tear_speed", .62)),
                   "hold_frame": scene.get("tear_hold_frame"),
                   "x": (ctx.width - tear_w) / 2,
                   "y": (ctx.height - tear_h) / 2,
                   "w": tear_w, "h": tear_h},
            qa_class="decor",
            meta={"asset": str(Path(scene["tear_sequence"]).name),
                  "frames": len(frames),
                  "source": scene.get("tear_source_note", "")})
        specs = []
        meta_motion = "real captured tear composited over copy"
    else:
        # Copy-led card: no paper sheet, elements enter with a slow stagger.
        specs = []
        if "logo" in elements:
            specs.append(_spec("logo", 10, "decor", hint="scale-focus"))
        specs.append(_spec("headline", 8, "display", hint="tracking-in"))
        if "subtitle" in elements:
            specs.append(_spec("subtitle", 4, "support", hint="tracking-in"))
        if kicker:
            specs.append(_spec("kicker", 3, "support", hint="fade-up"))
        meta_motion = "copy card with staggered entrance"

    layout = ctx.layout.layout("stack-center", {}, has_visual=False)
    # The copy is fully typeset from frame one; with the tear enabled it is
    # revealed purely by the sheet, otherwise it enters via choreography.
    return _finish(ctx, scene, layout,
                   _background(ctx, scene, theme),
                   elements, specs,
                   meta={"component": "paper-reveal-footage",
                         "motion": meta_motion})
