"""3D product mesh validation and frame rendering."""
from __future__ import annotations

import math
from pathlib import Path

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
