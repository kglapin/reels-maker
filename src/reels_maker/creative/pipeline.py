"""Compatibility facade for typed creative pipeline and advanced tools."""
from __future__ import annotations

from .pipeline_core import (
    _canonical, _decode, CreativeIntent, MotionDecision, MotionPlan,
    RenderScene, RenderGraph, creative_intent, plan_motion, render_graph,
)
from .pipeline_product import (
    validate_3d_product_scene, _load_or_build_mesh, render_3d_product_frame,
)
from .pipeline_depth import (
    APPROVED_DEPTH_MODELS, validate_depth_composite, composite_depth_layers,
)
from .pipeline_inspector import (
    export_scene_graph_inspector, write_scene_graph_inspector_html,
)
from .pipeline_review import build_review_portal_bundle, write_review_portal_html
from .pipeline_farm import (
    plan_render_farm_batch, detect_hardware_h264_encoder, execute_render_farm_batch,
)

__all__ = ["CreativeIntent", "MotionDecision", "MotionPlan", "RenderScene",
           "RenderGraph", "creative_intent", "plan_motion", "render_graph",
           "validate_3d_product_scene", "render_3d_product_frame",
           "validate_depth_composite", "composite_depth_layers",
           "export_scene_graph_inspector", "write_scene_graph_inspector_html",
           "build_review_portal_bundle", "write_review_portal_html",
           "plan_render_farm_batch", "execute_render_farm_batch",
           "detect_hardware_h264_encoder"]
