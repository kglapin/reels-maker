"""Depth-map composite validation and rendering."""
from __future__ import annotations

APPROVED_DEPTH_MODELS = frozenset({
    "depth-anything-v2-Metric-Indoor",
    "depth-anything-v2-Metric-Outdoor",
    "marigold-lcm-v1",
})

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
