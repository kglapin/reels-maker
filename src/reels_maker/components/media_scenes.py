"""Scene builders for the media family."""
from __future__ import annotations

from ..core.scene_graph import Node
from .base import BuiltScene, SceneContext
from .scene_support import (
    _background, _data_panel_scaffold, _decor, _finish, _spec,
)



def build_product_3d(ctx: SceneContext, scene: dict) -> BuiltScene:
    """Render a true 3D perspective-projected product mesh with 3-point lighting in Studio (MD-601)."""
    from ..creative.pipeline import validate_3d_product_scene

    theme, layout, elements = _data_panel_scaffold(ctx, scene, "MODEL 3D PRODUKTU")
    spec_3d = scene.get("product_3d") or scene
    validate_3d_product_scene(spec_3d)
    chart = layout.region("chart")
    mesh_node = Node(
        kind="mesh3d",
        role="product-mesh-3d",
        props={
            "x": chart.x,
            "y": chart.y,
            "w": chart.w,
            "h": chart.h,
            "spec": dict(spec_3d),
        },
        qa_class="control",
    )
    elements["chart"] = mesh_node
    specs = [_spec("headline", 7), _spec("chart", 9, "control"), _spec("body", 3)]
    return _finish(ctx, scene, layout, _background(ctx, scene, theme),
                   elements, specs, decor=_decor(ctx, scene, theme),
                   meta={"component": "product_3d", "mesh_path": spec_3d.get("mesh_path")})


def build_polaroid_burst(ctx: SceneContext, scene: dict) -> BuiltScene:
    from .editorial_scenes import build_statement

    config = scene.get("polaroid_burst")
    if not isinstance(config, dict):
        raise ValueError("polaroid_burst scene requires a polaroid_burst object")
    from ..motionkit.polaroid_burst import polaroid_burst_nodes

    background = scene.get("background")
    if background is None:
        background = {"kind": "solid",
                      "color": config.get("background", "#181525")}
    base_scene = {**scene, "background": background, "headline": "",
                  "title": "", "body": "", "subtitle": "", "kicker": ""}
    built = build_statement(ctx, base_scene)
    built.layout.recipe = "polaroid-burst"
    built.layout.regions.clear()
    nodes, shots = polaroid_burst_nodes(
        config, ctx.width, ctx.height, ctx.duration, ctx.fps,
        fallback_seed=ctx.seed)
    cues = ([{"role": "polaroid_shutter", "local_frame": shot.flash_frame}
             for shot in shots] if config.get("shutter_sound") else [])
    built.scene = scene
    built.nodes = nodes
    built.elements = {}
    built.meta.update({
        "component": "polaroid_burst",
        "photo_count": len(shots),
        "audio_cues": cues,
        "flash_frames": [shot.flash_frame for shot in shots],
    })
    return built
