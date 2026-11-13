"""``iso-explainer`` scene: a procedural isometric world inside the Studio graph.

The scene owns a single time-dependent ``iso-world`` node sampled at the
scene-local time plus the manifest ``t0`` film offset, so a 110 s educational
arc is sliced into Studio scenes (one per narration beat) while the world
clock stays continuous across cuts. Copy, pills and charts are typeset by
the iso engine at fixed editorial positions; the Studio graph carries the
node for caching, QA bounds and storyboard sampling.
"""
from __future__ import annotations

from pathlib import Path

from ..core.scene_graph import Node
from .base import BuiltScene
from .model import SceneContext
from .scene_support import _background, _finish, _spec, _theme


def _resolve_logo(scene: dict, ctx: SceneContext, key: str = "logo",
                default: str = "assets/logo.png") -> str | None:
    logo = scene.get(key, default)
    if not logo:
        return None
    if isinstance(logo, (list, tuple)):
        out = []
        for item in logo:
            one = _resolve_logo({**scene, key: item}, ctx, key, default=None)
            if one:
                out.append(one)
        return out or None
    candidate = Path(str(logo))
    if candidate.is_absolute():
        return str(candidate) if candidate.is_file() else None
    roots: list[Path] = []
    assets = getattr(ctx, "assets", None)
    brand_root = getattr(assets, "brand_root", None)
    if brand_root:
        roots.append(Path(brand_root))
    roots.append(Path.cwd() / "brands" / str(scene.get("brand") or "asta-energy"))
    for root in roots:
        resolved = root / candidate
        if resolved.is_file():
            return str(resolved)
    return None


def build_iso_explainer(ctx: SceneContext, scene: dict) -> BuiltScene:
    from ..iso import FILM_DURATION

    duration = float(scene.get("duration", 7.0))
    t0 = float(scene.get("t0", 0.0))
    if t0 < 0 or t0 + duration > FILM_DURATION + 1e-6:
        raise ValueError(
            f"iso-explainer window [{t0}, {t0 + duration}] exceeds film {FILM_DURATION}s")
    base = tuple(int(v) for v in ctx.tokens.palette.background)
    palette = {"bg": base}
    palette.update(dict(scene.get("palette") or {}))
    copy = scene.get("copy")
    spec = {
        "t0": t0,
        "palette": palette,
        "font": scene.get("font"),
        "photo": _resolve_logo(scene, ctx, key="photo",
                               default="assets/photo.png"),
        "logo": _resolve_logo(scene, ctx),
        "snow": float(scene.get("snow", 1.0)),
        "film": str(scene.get("film") or "odszranianie"),
        "copy": dict(copy) if isinstance(copy, dict) else None,
        "prop": scene.get("prop"),
        "camera": dict(scene.get("camera") or {}),
        "zoom": dict(scene.get("zoom") or {}),
        "title_size": scene.get("title_size"),
        "stage": str(scene.get("stage") or "plinth"),
        "labels": [dict(lb) if isinstance(lb, dict) else lb
                   for lb in (scene.get("labels") or [])],
    }
    node = Node(
        kind="iso-world",
        role="world-backdrop",
        # No playback_time here: SceneGraph.sample() injects the scene-local
        # time every frame (same mechanism as video/mesh3d). A fixed value
        # would freeze the world on its first frame.
        props={"x": 0, "y": 0, "w": ctx.width, "h": ctx.height, "spec": spec},
        qa_class="decor",
        meta={"component": "iso-explainer", "t0": t0, "background": True,
              "asset_role": "background"},
    )
    theme = _theme(ctx, scene)
    layout = ctx.layout.layout("statement", {})
    base = tuple(int(v) for v in ctx.tokens.palette.background)
    background = {"kind": "solid",
                  "color": "#%02x%02x%02x" % base}
    elements = {"world": node}
    specs = [_spec("world", 9, "control", hint="none")]
    built = _finish(ctx, scene, layout, background, elements, specs,
                    decor=[], meta={"component": "iso-explainer", "t0": t0})
    # The world clock is continuous across beats and scenes join by hard cut,
    # so the backdrop must never fade out at a scene boundary.
    built.choreography.exits.pop("world", None)
    node.tracks.pop("opacity", None)
    node.opacity = 1.0
    return built
