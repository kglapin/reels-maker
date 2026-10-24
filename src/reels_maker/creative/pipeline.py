"""Typed, additive Creative Intent -> Motion Plan -> Render Graph boundary.

This boundary deliberately adapts to the existing Studio manifest contract; it
does not introduce a renderer or change the v1 compiler/CLI defaults. Stage
snapshots are JSON-backed so callers cannot mutate an upstream stage by
retaining references to input dictionaries.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any

from .compiler import compile_creative_spec
from .director import plan_shots
from .spec import CreativeSpecError, validate_creative_spec


def _canonical(value: Any, path: str) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise CreativeSpecError(path, "must contain JSON-compatible values") from exc


def _decode(value: str) -> Any:
    return json.loads(value)


@dataclass(frozen=True)
class CreativeIntent:
    """A validated, immutable snapshot of Creative Spec v1 input."""

    _spec_json: str
    fingerprint: str

    def __post_init__(self) -> None:
        data = _decode(self._spec_json)
        validate_creative_spec(data)
        expected = hashlib.sha256(self._spec_json.encode("utf-8")).hexdigest()
        if self.fingerprint != expected:
            raise CreativeSpecError("$", "intent fingerprint does not match snapshot")

    @property
    def name(self) -> str:
        return _decode(self._spec_json)["name"]

    @property
    def mode(self) -> str:
        return validate_creative_spec(_decode(self._spec_json))["mode"]

    @property
    def spec(self) -> dict:
        """Return a defensive copy of the validated v1 input."""
        return _decode(self._spec_json)


@dataclass(frozen=True)
class MotionDecision:
    """A renderer-capability-checked per-shot Director decision."""

    scene_id: str
    layout: str
    typography_motion: str
    _decision_json: str

    def __post_init__(self) -> None:
        data = _decode(self._decision_json)
        if (data.get("id") != self.scene_id or data.get("layout") != self.layout
                or data.get("typography_motion") != self.typography_motion):
            raise CreativeSpecError("$.motion_plan", "typed decision fields do not match payload")

    @property
    def decision(self) -> dict:
        return _decode(self._decision_json)


@dataclass(frozen=True)
class MotionPlan:
    """Deterministic, intent-bound output of the existing heuristic Director."""

    intent_fingerprint: str
    decisions: tuple[MotionDecision, ...]
    _intent_json: str

    def __post_init__(self) -> None:
        intent = CreativeIntent(self._intent_json, self.intent_fingerprint)
        expected = plan_shots(intent.spec)
        actual = [decision.decision for decision in self.decisions]
        if actual != expected:
            raise CreativeSpecError("$.motion_plan", "decisions do not match validated intent")


@dataclass(frozen=True)
class RenderScene:
    """One timed, legacy-renderer scene payload in the common graph boundary."""

    scene_id: str
    start: float
    duration: float
    _payload_json: str

    def __post_init__(self) -> None:
        if (not self.scene_id or not math.isfinite(self.start)
                or not math.isfinite(self.duration) or self.start < 0
                or self.duration <= 0 or not isinstance(_decode(self._payload_json), dict)):
            raise CreativeSpecError("$.render_graph.scenes", "invalid timed scene node")

    @property
    def payload(self) -> dict:
        return _decode(self._payload_json)


@dataclass(frozen=True)
class RenderGraph:
    """Typed timeline adapter for an existing renderer input.

    ``backend`` identifies an existing contract, not a shared rendering
    implementation: Studio and Camera Canvas remain separate renderer paths.
    """

    backend: str
    width: int
    height: int
    fps: int
    scenes: tuple[RenderScene, ...]
    _manifest_json: str
    _report_json: str

    def __post_init__(self) -> None:
        if self.backend not in ("studio_manifest_v1", "camera_canvas_manifest_v1"):
            raise CreativeSpecError("$.render_graph.backend", "unsupported renderer capability")
        if any(type(value) is not int for value in (self.width, self.height, self.fps)):
            raise CreativeSpecError("$.render_graph.video", "dimensions and fps must be integers")
        if not (180 <= self.width <= 4096 and 180 <= self.height <= 4096
                and 1 <= self.fps <= 120):
            raise CreativeSpecError("$.render_graph.video", "unsupported output dimensions or fps")
        manifest = _decode(self._manifest_json)
        if not isinstance(manifest, dict) or not isinstance(manifest.get("scenes"), list):
            raise CreativeSpecError("$.render_graph", "manifest requires a scenes array")
        if len(manifest["scenes"]) != len(self.scenes):
            raise CreativeSpecError("$.render_graph.scenes", "scene count differs from manifest")
        expected_start = 0.0
        ids = set()
        for index, scene in enumerate(self.scenes):
            if scene.scene_id in ids or not math.isclose(scene.start, expected_start,
                                                          abs_tol=1e-8):
                raise CreativeSpecError("$.render_graph.scenes", "scene ids/timing are ambiguous")
            ids.add(scene.scene_id)
            if (manifest["scenes"][index].get("id") != scene.scene_id
                    or float(manifest["scenes"][index].get("duration", -1)) != scene.duration
                    or scene.payload != manifest["scenes"][index]):
                raise CreativeSpecError("$.render_graph.scenes", "typed scene differs from manifest")
            expected_start = round(expected_start + scene.duration, 9)
        if (manifest.get("schema_version") != 1
                or manifest.get("video") != {"width": self.width, "height": self.height,
                                              "fps": self.fps}):
            raise CreativeSpecError("$.render_graph", "manifest does not match typed graph")
        report = _decode(self._report_json)
        expected_backend = f"{report.get('mode')}_manifest_v1"
        if report.get("ok") is not True or self.backend != expected_backend:
            raise CreativeSpecError("$.render_graph.report", "expected successful compile report")

    def to_renderer_input(self) -> dict:
        """Return the exact Studio manifest produced by the v1 compiler."""
        return _decode(self._manifest_json)

    @property
    def report(self) -> dict:
        return _decode(self._report_json)


def creative_intent(spec: dict) -> CreativeIntent:
    """Validate and snapshot a Creative Spec v1 document."""
    validate_creative_spec(spec)
    encoded = _canonical(spec, "$")
    return CreativeIntent(encoded, hashlib.sha256(encoded.encode("utf-8")).hexdigest())


def plan_motion(intent: CreativeIntent) -> MotionPlan:
    """Plan using only the deterministic, currently supported Director."""
    if not isinstance(intent, CreativeIntent):
        raise TypeError("plan_motion requires a validated CreativeIntent")
    decisions = tuple(
        MotionDecision(item["id"], item["layout"], item["typography_motion"],
                       _canonical(item, "$.motion_plan"))
        for item in plan_shots(intent.spec)
    )
    return MotionPlan(intent.fingerprint, decisions, intent._spec_json)


def render_graph(intent: CreativeIntent, motion_plan: MotionPlan, *,
                 source_dir: str = ".", root: str | None = None,
                 check_assets: bool = True) -> RenderGraph:
    """Convert typed stages into the existing, validated renderer contract.

    Unsupported/ambiguous render capabilities fail in the v1 validator and
    compiler. No new node kinds, transforms, media, or renderer defaults are
    inferred here.
    """
    if not isinstance(intent, CreativeIntent) or not isinstance(motion_plan, MotionPlan):
        raise TypeError("render_graph requires CreativeIntent and MotionPlan stages")
    if motion_plan.intent_fingerprint != intent.fingerprint:
        raise CreativeSpecError("$.motion_plan", "plan was derived from a different intent")
    if motion_plan._intent_json != intent._spec_json:
        raise CreativeSpecError("$.motion_plan", "plan intent snapshot mismatch")
    manifest, report = compile_creative_spec(
        intent.spec, source_dir=source_dir, root=root, check_assets=check_assets)
    expected = [decision.decision for decision in motion_plan.decisions]
    actual = plan_shots(intent.spec)
    if expected != actual:
        raise CreativeSpecError("$.motion_plan", "unsupported or inconsistent motion decisions")
    width, height, fps = (manifest["video"][key] for key in ("width", "height", "fps"))
    scenes = []
    start = 0.0
    for item in manifest["scenes"]:
        duration = float(item["duration"])
        scenes.append(RenderScene(item["id"], start, duration,
                                  _canonical(item, "$.render_graph.scenes")))
        start = round(start + duration, 9)
    return RenderGraph(f"{intent.mode}_manifest_v1", width, height, fps,
                       tuple(scenes), _canonical(manifest, "$.render_graph"),
                       _canonical(report, "$.render_graph.report"))


APPROVED_DEPTH_MODELS = frozenset({
    "depth-anything-v2-Metric-Indoor",
    "depth-anything-v2-Metric-Outdoor",
    "marigold-lcm-v1",
})


def validate_3d_product_scene(spec: dict) -> dict:
    """Validate a true 3D/Blender product camera & 3-point lighting contract (MD-601).

    Rejects planar 2D image rotations masquerading as 3D product scenes.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a dict")
    if spec.get("simulated_planar_rotation"):
        raise ValueError("Simulated planar 2D rotation cannot be advertised as a 3D product scene")
    mesh = str(spec.get("mesh_path", "")).strip()
    if not mesh.endswith((".glb", ".gltf", ".blend", ".obj", ".usd", ".usdc")):
        raise ValueError("3D product scene requires an explicit 3D asset (.glb/.gltf/.blend/.obj/.usd)")
    camera = spec.get("camera") or {}
    focal_mm = float(camera.get("focal_length_mm", 0))
    if not 18.0 <= focal_mm <= 200.0:
        raise ValueError("3D camera requires focal_length_mm between 18 and 200")
    lights = spec.get("lighting") or {}
    for rig_key in ("key_light", "fill_light", "rim_light"):
        if rig_key not in lights:
            raise ValueError(f"3D product scene requires 3-point lighting ({rig_key} missing)")
    return {
        "ok": True,
        "engine": spec.get("engine", "blender-cycles"),
        "mesh_path": mesh,
        "focal_length_mm": focal_mm,
        "lighting_rig": ["key_light", "fill_light", "rim_light"],
    }


def validate_depth_composite(spec: dict) -> dict:
    """Validate depth-map / object-tracking compositing against the approved model allowlist (MD-602)."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a dict")
    model = str(spec.get("depth_model", "")).strip()
    if model not in APPROVED_DEPTH_MODELS:
        raise ValueError(
            f"Unapproved depth/tracking model {model!r}; allowed: "
            + ", ".join(sorted(APPROVED_DEPTH_MODELS))
        )
    if not spec.get("depth_map_sha256") or not spec.get("occlusion_mask"):
        raise ValueError("Depth composite requires depth_map_sha256 and occlusion_mask")
    return {
        "ok": True,
        "depth_model": model,
        "depth_map_sha256": str(spec["depth_map_sha256"]),
        "relighting_enabled": bool(spec.get("relighting", False)),
    }


def export_scene_graph_inspector(built_scenes: list) -> dict:
    """Export a GUI-ready scene graph and editable motion-path SVG/JSON payload (MD-603)."""
    scenes_out = []
    for built in built_scenes:
        nodes_out = []
        for root in built.nodes:
            for node in root.flatten():
                tracks_out = {
                    t_name: [
                        {"time": round(float(k.time), 4), "value": round(float(k.value), 4), "easing": k.easing}
                        for k in track.keys
                    ]
                    for t_name, track in node.tracks.items()
                }
                svg_path = None
                if "dx" in node.tracks or "dy" in node.tracks:
                    times = sorted({
                        0.0,
                        *(float(k.time) for t in node.tracks.values() for k in t.keys),
                        float(built.duration),
                    })
                    pts = [
                        (
                            round(float(node.tracks["dx"].value(t)) if "dx" in node.tracks else 0.0, 2),
                            round(float(node.tracks["dy"].value(t)) if "dy" in node.tracks else 0.0, 2),
                        )
                        for t in times
                    ]
                    svg_path = "M " + " L ".join(f"{x},{y}" for x, y in pts)
                nodes_out.append({
                    "role": node.role,
                    "kind": node.kind,
                    "bounds": node.world_bounds(),
                    "tracks": tracks_out,
                    "motion_path_svg": svg_path,
                })
        scenes_out.append({
            "scene_index": built.index + 1,
            "duration": float(built.duration),
            "recipe": built.layout.recipe,
            "node_count": len(nodes_out),
            "nodes": nodes_out,
        })
    return {"schema_version": 1, "scenes": scenes_out}


def build_review_portal_bundle(
    project_name: str,
    *,
    renders: dict[str, str],
    comments: list[dict],
    release_version: str,
) -> dict:
    """Build a collaboration/approval portal manifest with comparison slider pairs and shot comments (MD-604)."""
    if not str(project_name or "").strip() or not renders:
        raise ValueError("project_name and non-empty renders are required")
    validated_comments = []
    for idx, c in enumerate(comments):
        if not isinstance(c, dict) or "shot" not in c or not str(c.get("text", "")).strip():
            raise ValueError(f"comment {idx} requires shot index and non-empty text")
        validated_comments.append({
            "shot": int(c["shot"]),
            "timecode_s": round(float(c.get("timecode_s", 0.0)), 3),
            "author": str(c.get("author", "reviewer")),
            "text": str(c["text"]).strip(),
            "resolved": bool(c.get("resolved", False)),
        })
    keys = sorted(renders)
    comparison_slider = (
        {"left_variant": keys[0], "right_variant": keys[1],
         "left_path": renders[keys[0]], "right_path": renders[keys[1]]}
        if len(keys) >= 2 else None
    )
    return {
        "schema_version": 1,
        "project": project_name.strip(),
        "release_version": str(release_version).strip(),
        "renders": dict(renders),
        "comparison_slider": comparison_slider,
        "shot_comments": validated_comments,
        "approval_state": "ready_for_signoff" if all(c["resolved"] for c in validated_comments) else "changes_requested",
    }


def plan_render_farm_batch(
    jobs: list[dict],
    *,
    gpu_hourly_cost_usd: float = 0.65,
    cpu_hourly_cost_usd: float = 0.12,
    budget_usd: float = 5.0,
) -> dict:
    """Schedule batch renders across GPU/CPU workers with cost estimation and brand-cache grouping (MD-605)."""
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("jobs must be a non-empty list")
    if budget_usd <= 0:
        raise ValueError("budget_usd must be positive")
    # Group jobs by (brand, style) to maximize warm per-scene segment cache hits
    ordered = sorted(jobs, key=lambda j: (str(j.get("brand", "")), str(j.get("style", "")), str(j.get("id", ""))))
    scheduled = []
    total_cost = 0.0
    seen_groups: set[tuple[str, str]] = set()
    for job in ordered:
        jid = str(job.get("id", ""))
        dur = float(job.get("duration_s", 15.0))
        use_gpu = bool(job.get("gpu_preferred", dur >= 20.0))
        group = (str(job.get("brand", "")), str(job.get("style", "")))
        warm_cache = group in seen_groups
        seen_groups.add(group)
        est_seconds = (dur * 0.45 if use_gpu else dur * 1.4) * (0.45 if warm_cache else 1.0)
        rate = gpu_hourly_cost_usd if use_gpu else cpu_hourly_cost_usd
        cost = (est_seconds / 3600.0) * rate
        total_cost += cost
        scheduled.append({
            "job_id": jid,
            "worker_tier": "gpu" if use_gpu else "cpu",
            "warm_brand_cache": warm_cache,
            "estimated_seconds": round(est_seconds, 2),
            "estimated_cost_usd": round(cost, 5),
        })
    if total_cost > budget_usd:
        raise ValueError(f"Batch estimated cost ${total_cost:.4f} exceeds budget ${budget_usd:.2f}")
    return {
        "ok": True,
        "job_count": len(scheduled),
        "total_estimated_cost_usd": round(total_cost, 5),
        "budget_usd": float(budget_usd),
        "schedule": scheduled,
    }


__all__ = ["CreativeIntent", "MotionDecision", "MotionPlan", "RenderScene",
           "RenderGraph", "creative_intent", "plan_motion", "render_graph",
           "validate_3d_product_scene", "validate_depth_composite",
           "export_scene_graph_inspector", "build_review_portal_bundle",
           "plan_render_farm_batch"]
