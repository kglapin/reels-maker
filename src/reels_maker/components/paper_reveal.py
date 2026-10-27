"""Reveal copy through real, chroma-keyed footage of a sheet being torn.

The builder never draws paper itself: it composites an approved frame sequence
(paper on a transparent background) over authored copy, keeping the material
behaviour, curled fibers and light gradient of the actual capture.
"""
from __future__ import annotations

from pathlib import Path

from ..core.scene_graph import Node
from ..motionkit.keyframes import Keyframe, Track
from ..textkit.typesetter import TextStyle
from .base import BuiltScene, SceneContext, resolve_text_style, text_node
from .scene_support import _background, _finish, _theme

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
    if not scene.get("tear_sequence"):
        raise ValueError(
            "paper_reveal requires tear_sequence: a brand-relative directory "
            "of chroma-keyed RGBA frames")
    frames = sequence_frames(scene["tear_sequence"])
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
            type(safe)(safe.x, band_top - 165, safe.w, 40),
            ctx.fonts, align="center", valign="center")
    elements["headline"] = text_node(
        "headline", headline,
        TextStyle(size=ctx.tokens.type_size("display"), color=headline_color,
                  weight="bold", align="center", line_height=1.0),
        type(safe)(safe.x, band_top - 110, safe.w, 185),
        ctx.fonts, align="center", valign="center")
    if subtitle:
        elements["subtitle"] = text_node(
            "subtitle", subtitle,
            resolve_text_style(ctx.tokens, "subtitle", tuple(theme["muted"]),
                               align="center"),
            type(safe)(safe.x + 40, band_top + 95, safe.w - 80, 95),
            ctx.fonts, align="center", valign="center")

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

    layout = ctx.layout.layout("stack-center", {}, has_visual=False)
    # A slow rise behind the sheet gives the reveal life without animating the
    # copy into view on top of the tear itself. The copy also stays invisible
    # while the sheet still covers it, so contrast QA never scores hidden text.
    for copy_node in ("kicker", "headline", "subtitle"):
        if copy_node in elements:
            elements[copy_node].track("dy", Track([
                Keyframe(.15, 26.0, "smooth"),
                Keyframe(1.35, 0.0, "smooth")]))
            elements[copy_node].track("opacity", Track([
                Keyframe(0.0, 0.0, "smooth"),
                Keyframe(float(scene.get("copy_in", 1.45)), 0.0, "smooth"),
                Keyframe(float(scene.get("copy_settled", 2.45)), 1.0, "smooth")]))
    return _finish(ctx, scene, layout,
                   _background(ctx, scene, theme),
                   elements, [],
                   meta={"component": "paper-reveal-footage",
                         "motion": "real captured tear composited over copy"})
