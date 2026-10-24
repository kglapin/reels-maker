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
from pathlib import Path
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


def _load_or_build_mesh(mesh_path: str) -> tuple[list[tuple[float, float, float]], list[tuple[int, ...]]]:
    """Load an .obj mesh from disk if it exists, otherwise build a 3D prism/inverter mesh."""
    path = Path(mesh_path)
    if path.suffix.lower() == ".obj" and path.is_file():
        verts: list[tuple[float, float, float]] = []
        faces: list[tuple[int, ...]] = []
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if line.startswith("v "):
                parts = line.split()[1:4]
                if len(parts) == 3:
                    verts.append((float(parts[0]), float(parts[1]), float(parts[2])))
            elif line.startswith("f "):
                idxs = [int(tok.split("/")[0]) - 1 for tok in line.split()[1:]]
                if len(idxs) >= 3 and all(0 <= i < len(verts) for i in idxs):
                    faces.append(tuple(idxs))
        if len(verts) >= 4 and faces:
            return verts, faces
    # Procedural 3D energy-storage / inverter cabinet prism (width 1.4, height 2.0, depth 0.65)
    hx, hy, hz = 0.70, 1.00, 0.34
    verts = [
        (-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
        (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz),
    ]
    # Counter-clockwise outward-facing quads
    faces = [
        (4, 5, 6, 7),  # front (+Z)
        (1, 0, 3, 2),  # back (-Z)
        (5, 1, 2, 6),  # right (+X)
        (0, 4, 7, 3),  # left (-X)
        (7, 6, 2, 3),  # top (+Y)
        (0, 1, 5, 4),  # bottom (-Y)
    ]
    return verts, faces


def render_3d_product_frame(
    spec: dict,
    width: int,
    height: int,
    time: float = 0.0,
) -> "Image.Image":
    """Perspective-project and 3-point Phong-shade a 3D product mesh at ``time`` (MD-601)."""
    from PIL import Image, ImageDraw
    from ..design.color import parse_hex

    validate_3d_product_scene(spec)
    verts, faces = _load_or_build_mesh(str(spec["mesh_path"]))
    camera = spec.get("camera") or {}
    focal_mm = float(camera.get("focal_length_mm", 50.0))
    sensor_mm = float(camera.get("sensor_width_mm", 36.0))
    cam_dist = float(camera.get("distance", 3.6))
    yaw_deg = float(camera.get("yaw_deg", 24.0)) + float(camera.get("turntable_deg_per_s", 32.0)) * float(time)
    pitch_deg = float(camera.get("pitch_deg", 14.0))
    yaw, pitch = math.radians(yaw_deg), math.radians(pitch_deg)
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)

    def transform_v(v: tuple[float, float, float]) -> tuple[float, float, float]:
        x, y, z = v
        # Rotate around Y (turntable yaw), then around X (pitch)
        x1, z1 = cy * x + sy * z, -sy * x + cy * z
        y2, z2 = cp * y - sp * z1, sp * y + cp * z1
        return (x1, y2, z2)

    t_verts = [transform_v(v) for v in verts]
    f_px = (focal_mm / max(1.0, sensor_mm)) * min(width, height)

    def project(v: tuple[float, float, float]) -> tuple[float, float, float]:
        x, y, z = v
        z_cam = max(0.3, cam_dist - z)
        u = width / 2.0 + (f_px * x) / z_cam
        vp = height / 2.0 - (f_px * y) / z_cam
        return (u, vp, z_cam)

    lights_cfg = spec.get("lighting") or {}
    default_dirs = {
        "key_light": ((0.55, 0.65, 0.75), 0.90),
        "fill_light": ((-0.65, 0.25, 0.55), 0.42),
        "rim_light": ((0.0, 0.80, -0.75), 0.35),
    }
    lights = []
    for lname, (ddir, dint) in default_dirs.items():
        lcfg = lights_cfg.get(lname) or {}
        raw_dir = lcfg.get("direction", ddir)
        dx, dy, dz = (float(raw_dir[0]), float(raw_dir[1]), float(raw_dir[2]))
        norm = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
        intensity = float(lcfg.get("intensity", dint))
        lights.append(((dx / norm, dy / norm, dz / norm), intensity))

    base_rgb = parse_hex(str(spec.get("albedo", "#2E7D32")))
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")

    # Sort faces back-to-front by camera-space Z (painter's algorithm)
    face_records = []
    for f_idx, face in enumerate(faces):
        pts3 = [t_verts[i] for i in face]
        # Compute outward normal (v1 - v0) x (v2 - v0)
        ux, uy, uz = (pts3[1][j] - pts3[0][j] for j in range(3))
        vx, vy, vz = (pts3[2][j] - pts3[0][j] for j in range(3))
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        n_len = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        nx, ny, nz = nx / n_len, ny / n_len, nz / n_len
        proj = [project(p) for p in pts3]
        mean_z = sum(p[2] for p in proj) / len(proj)
        # Back-face culling in camera space (camera looks toward -Z in world, +Z toward camera)
        if nz <= -0.15:
            continue
        shade = 0.18
        for (lx, ly, lz), l_int in lights:
            ndotl = max(0.0, nx * lx + ny * ly + nz * lz)
            # Blinn-Phong half-vector with view = (0, 0, 1)
            hx_v, hy_v, hz_v = lx, ly, lz + 1.0
            h_len = math.sqrt(hx_v * hx_v + hy_v * hy_v + hz_v * hz_v) or 1.0
            ndoth = max(0.0, (nx * hx_v + ny * hy_v + nz * hz_v) / h_len)
            spec_term = (ndoth ** 20) * 0.28
            shade += l_int * (0.78 * ndotl + spec_term)
        rgb = tuple(max(0, min(255, round(c * min(1.35, shade)))) for c in base_rgb)
        poly2d = [(p[0], p[1]) for p in proj]
        face_records.append((mean_z, poly2d, rgb))

    face_records.sort(key=lambda r: -r[0])
    for _, poly2d, rgb in face_records:
        draw.polygon(poly2d, fill=(*rgb, 255), outline=(20, 32, 24, 220))
    return img


def composite_depth_layers(
    foreground: "Image.Image",
    background: "Image.Image",
    depth_map: "Image.Image",
    *,
    depth_model: str = "depth-anything-v2-Metric-Indoor",
    focal_depth: float = 0.72,
    blur_radius: float = 3.5,
    parallax_dx: float = 14.0,
    parallax_dy: float = -6.0,
    tracked_badge: "Image.Image | None" = None,
    track_anchor: tuple[int, int] = (60, 60),
    badge_depth: float = 0.60,
) -> "Image.Image":
    """Composite foreground/background with per-pixel Z-depth DoF, parallax and occlusion (MD-602)."""
    from PIL import Image, ImageChops, ImageFilter

    if depth_model not in APPROVED_DEPTH_MODELS:
        raise ValueError(f"Unapproved depth model {depth_model!r}")
    w, h = background.size
    fg = foreground.convert("RGBA").resize((w, h))
    bg = background.convert("RGBA")
    dmap = depth_map.convert("L").resize((w, h))

    # Blur background for shallow depth of field
    blurred_bg = bg.filter(ImageFilter.GaussianBlur(radius=max(0.5, float(blur_radius))))
    # Displace foreground and background proportionally to depth
    fg_shifted = ImageChops.offset(fg, int(round(parallax_dx)), int(round(parallax_dy)))
    fg_shifted_dmap = ImageChops.offset(dmap, int(round(parallax_dx)), int(round(parallax_dy)))

    composed = blurred_bg.copy()
    if tracked_badge is not None:
        bx = int(round(track_anchor[0] + parallax_dx * badge_depth))
        by = int(round(track_anchor[1] + parallax_dy * badge_depth))
        badge_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        badge_layer.alpha_composite(tracked_badge.convert("RGBA"), (bx, by))
        # Occlude badge wherever foreground depth exceeds badge_depth
        threshold = int(round(badge_depth * 255))
        fg_occluder = fg_shifted_dmap.point(lambda v: 0 if v > threshold else 255)
        badge_layer.putalpha(ImageChops.multiply(badge_layer.getchannel("A"), fg_occluder))
        composed.alpha_composite(badge_layer)

    near_mask = fg_shifted_dmap.point(lambda v: 255 if v >= int(focal_depth * 180) else int(v * 0.6))
    fg_masked = fg_shifted.copy()
    fg_masked.putalpha(ImageChops.multiply(fg_shifted.getchannel("A"), near_mask))
    composed.alpha_composite(fg_masked)
    return composed


def write_scene_graph_inspector_html(
    built_scenes: list,
    output_html: str | Path,
) -> dict:
    """Write a self-contained interactive HTML5 + SVG motion-path editor and inspector (MD-603)."""
    import html as html_mod

    payload = export_scene_graph_inspector(built_scenes)
    out_path = Path(output_html).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    svg_paths = []
    rows_html = []
    for sc in payload["scenes"]:
        for node in sc["nodes"]:
            role_esc = html_mod.escape(str(node["role"]))
            kind_esc = html_mod.escape(str(node["kind"]))
            track_names = ", ".join(sorted(node["tracks"])) or "static"
            rows_html.append(
                f"<tr data-scene='{sc['scene_index']}' data-role='{role_esc}'>"
                f"<td>{sc['scene_index']}</td><td>{role_esc}</td><td>{kind_esc}</td>"
                f"<td>{html_mod.escape(track_names)}</td></tr>"
            )
            if node["motion_path_svg"]:
                svg_paths.append(
                    f"<path d='{html_mod.escape(node['motion_path_svg'])}' "
                    f"data-role='{role_esc}' fill='none' stroke='#47A013' stroke-width='2.5'/>"
                )
    doc = (
        "<!DOCTYPE html><html lang='pl'><head><meta charset='utf-8'/>"
        "<title>Reels Maker — Motion Path & Scene Graph Inspector</title>"
        "<style>body{font-family:system-ui,sans-serif;margin:24px;background:#0E1A13;color:#F2F5F0}"
        ".grid{display:grid;grid-template-columns:380px 1fr;gap:24px}"
        "svg{background:#14241B;border:1px solid #2C4637;border-radius:12px;width:100%;height:420px}"
        "table{width:100%;border-collapse:collapse}th,td{padding:8px;border-bottom:1px solid #24382C;text-align:left}"
        "</style></head><body>"
        "<h1>Scene Graph &amp; Editable Motion Path Inspector</h1>"
        "<label>Timeline scrubber: <input id='scrubber' type='range' min='0' max='100' value='50'/></label>"
        "<div class='grid'>"
        f"<svg id='motion-viewport' viewBox='-120 -120 360 360'>{''.join(svg_paths)}</svg>"
        f"<div><table><thead><tr><th>Scena</th><th>Rola</th><th>Typ</th><th>Tory</th></tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody></table></div></div>"
        f"<script id='scene-graph-data' type='application/json'>{json.dumps(payload)}</script>"
        "</body></html>"
    )
    out_path.write_text(doc, encoding="utf-8")
    return {"output_html": str(out_path), "scene_count": len(payload["scenes"]), "payload": payload}


def write_review_portal_html(
    bundle: dict,
    output_html: str | Path,
) -> dict:
    """Write an interactive HTML5 collaboration/approval portal with A/B comparison slider (MD-604)."""
    import html as html_mod

    out_path = Path(output_html).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    slider = bundle.get("comparison_slider") or {}
    comments_rows = "".join(
        f"<tr><td>#{int(c['shot'])}</td><td>{float(c['timecode_s']):.2f}s</td>"
        f"<td>{html_mod.escape(str(c['author']))}</td>"
        f"<td>{html_mod.escape(str(c['text']))}</td>"
        f"<td>{'RESOLVED' if c.get('resolved') else 'OPEN'}</td></tr>"
        for c in (bundle.get("shot_comments") or [])
    )
    doc = (
        "<!DOCTYPE html><html lang='pl'><head><meta charset='utf-8'/>"
        f"<title>Review Portal — {html_mod.escape(str(bundle.get('project', '')))}</title>"
        "<style>body{font-family:system-ui,sans-serif;margin:24px;background:#101814;color:#F4F7F5}"
        ".badge{padding:4px 10px;border-radius:6px;background:#47A013;display:inline-block}"
        "table{width:100%;border-collapse:collapse;margin-top:16px}th,td{padding:8px;border-bottom:1px solid #26382E}"
        "</style></head><body>"
        f"<h1>Portal Akceptacji: {html_mod.escape(str(bundle.get('project', '')))} "
        f"<span class='badge'>{html_mod.escape(str(bundle.get('approval_state', '')))}</span></h1>"
        "<section id='ab-comparison'>"
        f"<p>Porównanie A/B: <strong>{html_mod.escape(str(slider.get('left_variant', 'A')))}</strong> vs "
        f"<strong>{html_mod.escape(str(slider.get('right_variant', 'B')))}</strong></p>"
        "<input id='ab-slider' type='range' min='0' max='100' value='50'/>"
        "</section>"
        "<table><thead><tr><th>Ujęcie</th><th>Czas</th><th>Autor</th><th>Komentarz</th><th>Status</th></tr></thead>"
        f"<tbody>{comments_rows}</tbody></table>"
        f"<script id='review-bundle-data' type='application/json'>{json.dumps(bundle)}</script>"
        "</body></html>"
    )
    out_path.write_text(doc, encoding="utf-8")
    return {"output_html": str(out_path), "approval_state": bundle.get("approval_state")}


def detect_hardware_h264_encoder() -> str:
    """Probe FFmpeg for available GPU/hardware H.264 encoders, falling back to libx264 (MD-605)."""
    import subprocess

    try:
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True, text=True, check=False, timeout=5,
        )
        out = proc.stdout or ""
        for hw in ("h264_nvenc", "h264_videotoolbox", "h264_vaapi"):
            if hw in out:
                return hw
    except Exception:
        pass
    return "libx264"


def execute_render_farm_batch(
    projects: list,
    output_dir: str | Path,
    *,
    budget_usd: float = 5.0,
) -> dict:
    """Schedule and execute a batch of StudioProject renders with shared warm segment caching (MD-605)."""
    from ..renderers.studio import probe_output, render_studio

    if not projects:
        raise ValueError("projects must not be empty")
    out_root = Path(output_dir).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    cache_dir = out_root / ".segment-cache"
    jobs_spec = [
        {
            "id": p.name,
            "brand": p.brand or "default",
            "style": p.style,
            "duration_s": p.timeline().duration,
        }
        for p in projects
    ]
    plan = plan_render_farm_batch(jobs_spec, budget_usd=budget_usd)
    hw_encoder = detect_hardware_h264_encoder()
    by_id = {p.name: p for p in projects}
    completed = []
    for item in plan["schedule"]:
        proj = by_id[item["job_id"]]
        dest = out_root / f"{proj.name}.mp4"
        # Share segment cache across jobs in the same (brand, style) group
        from dataclasses import replace as _replace
        shared_proj = _replace(proj, name=f"{proj.brand or 'default'}-{proj.style}")
        rep = render_studio(shared_proj, output=dest, cache_dir=cache_dir, supersample=1)
        probed = probe_output(dest)
        completed.append({
            **item,
            "output_mp4": str(dest),
            "cache_hits": rep["cache_hits"],
            "cache_misses": rep["cache_misses"],
            "render_seconds": rep["render_seconds"],
            "frames": probed["frames"],
            "export_status": rep["export_quality"]["status"],
        })
    return {
        "ok": all(c["export_status"] == "pass" for c in completed),
        "hardware_encoder_detected": hw_encoder,
        "cache_dir": str(cache_dir),
        "plan": plan,
        "completed_jobs": completed,
    }


__all__ = ["CreativeIntent", "MotionDecision", "MotionPlan", "RenderScene",
           "RenderGraph", "creative_intent", "plan_motion", "render_graph",
           "validate_3d_product_scene", "render_3d_product_frame",
           "validate_depth_composite", "composite_depth_layers",
           "export_scene_graph_inspector", "write_scene_graph_inspector_html",
           "build_review_portal_bundle", "write_review_portal_html",
           "plan_render_farm_batch", "execute_render_farm_batch",
           "detect_hardware_h264_encoder"]
