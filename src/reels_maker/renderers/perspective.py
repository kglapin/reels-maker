"""Opt-in scene-level perspective camera for Studio renders.

A scene may declare ``"perspective"`` with ``yaw``/``pitch`` angles (degrees),
``zoom`` and a timeline envelope. The finished frame is warped through a true
homography (plane rotation about the view axis) so text and panels keep their
internal geometry while the whole composition is seen under an angle.
"""
from __future__ import annotations

import math
from typing import Mapping

from PIL import Image

from ..motionkit.easing import ease as motion_ease

MAXANGLE = 30.0


def _num(value, field: str, lo: float, hi: float) -> float:
    if isinstance(value, bool):
        raise ValueError(f"perspective.{field} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"perspective.{field} must be numeric") from None
    if not math.isfinite(result) or not lo <= result <= hi:
        raise ValueError(f"perspective.{field} must be between {lo} and {hi}")
    return result


def perspective_spec(scene: Mapping) -> dict | None:
    spec = scene.get("perspective")
    if spec is None:
        return None
    if not isinstance(spec, Mapping):
        raise ValueError("perspective must be an object")
    path_raw = spec.get("path")
    path = None
    if path_raw is not None:
        if not isinstance(path_raw, list) or len(path_raw) < 2:
            raise ValueError("perspective.path must be a list of at least 2 keys")
        path = []
        for index, key in enumerate(path_raw):
            if not isinstance(key, Mapping):
                raise ValueError("perspective.path entries must be objects")
            t = _num(key.get("t", 0.0), "path t", 0.0, 300.0)
            path.append({
                "t": t,
                "yaw": _num(key.get("yaw", 0.0), "path yaw", -MAXANGLE, MAXANGLE),
                "pitch": _num(key.get("pitch", 0.0), "path pitch", -MAXANGLE, MAXANGLE),
                "zoom": _num(key.get("zoom", 1.0), "path zoom", 0.55, 1.6),
                "pan_x": _num(key.get("pan_x", 0.0), "path pan_x", -0.35, 0.35),
                "pan_y": _num(key.get("pan_y", 0.0), "path pan_y", -0.35, 0.35),
            })
        path.sort(key=lambda item: item["t"])
        for prev, nxt in zip(path, path[1:]):
            if nxt["t"] <= prev["t"]:
                raise ValueError("perspective.path times must be strictly increasing")
    mode = str(spec.get("mode", "settle"))
    if mode not in ("settle", "drift", "push"):
        raise ValueError(f"Unknown perspective mode: {mode}")
    return {
        "yaw": _num(spec.get("yaw", 0.0), "yaw", -MAXANGLE, MAXANGLE),
        "pitch": _num(spec.get("pitch", 0.0), "pitch", -MAXANGLE, MAXANGLE),
        "zoom": _num(spec.get("zoom", 1.0), "zoom", 0.55, 1.6),
        "pan_x": _num(spec.get("pan_x", 0.0), "pan_x", -0.35, 0.35),
        "pan_y": _num(spec.get("pan_y", 0.0), "pan_y", -0.35, 0.35),
        "duration": _num(spec.get("duration", 1.4), "duration", .1, 30.0),
        "delay": _num(spec.get("delay", 0.0), "delay", 0.0, 30.0),
        "easing": str(spec.get("easing", "out-cubic")),
        "mode": mode,
        "path": path,
    }


def _pose_at(spec: dict, time: float) -> tuple[float, float, float, float, float]:
    """Return (yaw, pitch, zoom, pan_x, pan_y) at scene-local time."""
    path = spec.get("path")
    if path:
        if time <= path[0]["t"]:
            first = path[0]
            return (first["yaw"], first["pitch"], first["zoom"],
                    first["pan_x"], first["pan_y"])
        if time >= path[-1]["t"]:
            last = path[-1]
            return (last["yaw"], last["pitch"], last["zoom"],
                    last["pan_x"], last["pan_y"])
        for prev, nxt in zip(path, path[1:]):
            if prev["t"] <= time <= nxt["t"]:
                span = nxt["t"] - prev["t"]
                u = (time - prev["t"]) / span if span > 0 else 1.0
                k = u * u * (3.0 - 2.0 * u)  # smoothstep: flat velocity at keys
                return tuple(prev[channel] + (nxt[channel] - prev[channel]) * k
                             for channel in ("yaw", "pitch", "zoom",
                                             "pan_x", "pan_y"))
    yaw, pitch, zoom = spec["yaw"], spec["pitch"], spec["zoom"]
    pan_x, pan_y = spec["pan_x"], spec["pan_y"]
    if spec["mode"] == "drift":
        t = min(1.0, max(0.0, time / max(.001, spec["duration"])))
        # Sine sweep: zero velocity at both ends and at the apex, so the
        # camera eases through the angle instead of snapping at the turn.
        sway = math.sin(math.pi * t)
        return (yaw * sway, pitch * sway,
                1.0 + (zoom - 1.0) * sway, pan_x * sway, pan_y * sway)
    local = time - spec["delay"]
    if local <= 0:
        if spec["mode"] == "push":
            return 0.0, 0.0, 1.0, 0.0, 0.0
        return yaw, pitch, zoom, pan_x, pan_y
    k = motion_ease(spec["easing"], min(1.0, local / spec["duration"]))
    if spec["mode"] == "push":
        return yaw * k, pitch * k, 1.0 + (zoom - 1.0) * k, pan_x * k, pan_y * k
    return (yaw * (1 - k), pitch * (1 - k), 1.0 + (zoom - 1.0) * (1 - k),
            pan_x * (1 - k), pan_y * (1 - k))


def _coeffs(width: int, height: int, yaw_deg: float, pitch_deg: float,
            zoom: float, pan_x: float = 0.0,
            pan_y: float = 0.0) -> list[float] | None:
    """PIL PERSPECTIVE coefficients mapping output px -> input px.

    The scene plane is rotated by yaw (about vertical) and pitch (about
    horizontal) around its center; the camera sits at distance ``d`` half-
    heights away. ``zoom`` magnifies about the center before projection.
    """
    if (abs(yaw_deg) < 1e-4 and abs(pitch_deg) < 1e-4
            and abs(zoom - 1.0) < 1e-4 and abs(pan_x) < 1e-4
            and abs(pan_y) < 1e-4):
        return None
    w, h = float(width), float(height)
    cx, cy = w / 2.0 + pan_x * w, h / 2.0 + pan_y * h
    s = h / 2.0                      # world units: half the frame height
    d = 2.6                           # camera distance in world units
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    cyw, syw = math.cos(yaw), math.sin(yaw)
    cip, sip = math.cos(pitch), math.sin(pitch)

    def project(ox: float, oy: float):
        # output pixel -> world coords on the view plane
        X = (ox - cx) / s
        Y = (oy - cy) / s
        # rotate plane: first pitch about X, then yaw about Y
        y1 = Y * cip
        z1 = Y * sip
        x2 = X * cyw + z1 * syw
        y2 = y1
        z2 = -X * syw + z1 * cyw
        # camera at (0,0,d) looking at origin; f = d
        den = d - z2
        u = d * x2 / den
        v = d * y2 / den
        u *= zoom
        v *= zoom
        return cx + s * u, cy + s * v, den

    # Build the 3x3 homogeneous matrix rows (Nx, Ny, D) as affine functions
    # of output (ox, oy, 1) by sampling three basis points.
    rows = []
    for nx, ny in ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)):
        px, py, dn = project(nx, ny)
        # recover homogeneous numerator values: px = Nx/D -> Nx = px*D
        rows.append((px * dn, py * dn, dn))
    # columns per row: [const, d/dox, d/doy] for Nx, Ny, D
    m = [[rows[0][i], rows[1][i] - rows[0][i], rows[2][i] - rows[0][i]]
         for i in range(3)]
    d0 = m[2][0]
    if abs(d0) < 1e-9:
        return None
    # PIL: X = (a*x + b*y + c) / (g*x + h*y + 1)
    a, b, c = m[0][1] / d0, m[0][2] / d0, m[0][0] / d0
    dd, e, f = m[1][1] / d0, m[1][2] / d0, m[1][0] / d0
    g, hh = m[2][1] / d0, m[2][2] / d0
    return [a, b, c, dd, e, f, g, hh]


def apply_perspective(image: Image.Image, scene: Mapping,
                      time: float, duration: float) -> Image.Image:
    """Warp one rendered frame; returns the input untouched when inactive."""
    spec = perspective_spec(scene)
    if spec is None or spec["duration"] <= 0:
        return image
    yaw, pitch, zoom, pan_x, pan_y = _pose_at(spec, time)
    if (abs(yaw) < 1e-3 and abs(pitch) < 1e-3 and abs(zoom - 1.0) < 1e-3
            and abs(pan_x) < 1e-3 and abs(pan_y) < 1e-3):
        return image
    w, h = image.size
    coeffs = _coeffs(w, h, yaw, pitch, zoom, pan_x, pan_y)
    if coeffs is None:
        return image
    return image.transform((w, h), Image.Transform.PERSPECTIVE,
                           coeffs, resample=Image.Resampling.BICUBIC)
