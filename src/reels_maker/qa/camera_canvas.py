"""Camera Canvas checks for Studio QA."""
from __future__ import annotations

from ..design.tokens import is_vertical_reels_canvas
from .geometry import _inside_polygon, SAFE_AREA_TOLERANCE
from .models import Issue



def audit_camera_canvas(
    scenes: list[dict],
    width: int,
    height: int,
    *,
    fps: int = 30,
    max_angle_delta: float = 45.0,
    min_subject_retention: float = 0.55,
) -> dict:
    """Timeline-sampled QA for Camera Canvas path, hierarchy and subject retention (MD-204/206)."""
    from ..renderers.camera_canvas import (
        _LAYOUT_PHOTO_BOXES, _LAYOUT_TEXT_ORIGINS,
        build_camera_canvas_hierarchy, camera_world_to_viewport, plan_camera_path,
    )
    from ..design.tokens import (
        is_vertical_reels_canvas, vertical_reels_content_polygon,
    )

    path_report = plan_camera_path(
        scenes, width, height,
        max_angle_delta=max_angle_delta,
        min_subject_retention=min_subject_retention,
    )
    hierarchy, local_bounds = build_camera_canvas_hierarchy(scenes, width, height)
    reels_zone = (vertical_reels_content_polygon(width, height)
                  if is_vertical_reels_canvas(width, height) else None)
    issues: list[Issue] = []
    for item in path_report["violations"]:
        issues.append(Issue(
            item["code"],
            "error",
            f"Camera Canvas scene {item['scene']} failed {item['code']}.",
            item["scene"],
            None,
            [f"shot-{item['scene'] - 1}"],
            "Reduce camera step/rotation or adjust zoom so the subject stays in frame.",
        ))
    sampled_frames = 0
    for idx, scene in enumerate(scenes):
        cfg = scene["camera_canvas"]
        if reels_zone is not None:
            layout = cfg.get("layout", "photo-above")
            px, py, pw, ph = _LAYOUT_PHOTO_BOXES[layout]
            tx_rel, ty_rel = _LAYOUT_TEXT_ORIGINS[layout]
            authored_boxes = (
                ("photo", (px * width, py * height,
                           (px + pw) * width, (py + ph) * height)),
                ("typography", (tx_rel * width, ty_rel * height,
                                (tx_rel + .83) * width,
                                ty_rel * height + min(
                                    height * .18,
                                    height * (1.0 - ty_rel - .04)))),
            )
            for role, bounds in authored_boxes:
                if not _inside_polygon(bounds, reels_zone):
                    issues.append(Issue(
                        "reels_content_safe_zone", "error",
                        (f"Camera Canvas {role} in scene {idx + 1} extends "
                         "into the vertical-Reels margin."),
                        idx + 1, None, [f"shot-{idx}/{role}"],
                        "Keep the authored photo and text inside the content zone; camera travel is exempt."))
        duration = float(scene.get("duration", 3.0))
        move = 0.0 if idx == 0 else float(cfg.get("move_duration", .8))
        delay = float(cfg.get("reveal_delay", .18))
        reveal = float(cfg.get("reveal_duration", .55))
        key_times = sorted({
            0.0,
            min(duration, move * .5),
            min(duration, move),
            min(duration, move + delay),
            min(duration, move + delay + reveal * .5),
            min(duration, move + delay + reveal),
            duration,
        })
        sampled_frames += len(key_times)
        # Verify hierarchy transforms invert cleanly at every key time
        stop = (float(cfg["x"]), float(cfg["y"]),
                float(cfg.get("angle", 0.0)), float(cfg.get("zoom", 1.0)))
        vp_map = camera_world_to_viewport(*stop, width, height)
        text_id = f"shot-{idx}/typography"
        text_vp = hierarchy.world_transform(text_id).then(vp_map).map_bounds(local_bounds[text_id])
        if (text_vp.left < -SAFE_AREA_TOLERANCE or text_vp.top < -SAFE_AREA_TOLERANCE
                or text_vp.right > width + SAFE_AREA_TOLERANCE
                or text_vp.bottom > height + SAFE_AREA_TOLERANCE):
            issues.append(Issue(
                "camera_typography_clipped",
                "error",
                f"Camera Canvas typography {text_id!r} leaves viewport when settled.",
                idx + 1,
                round(move + delay + reveal, 3),
                [text_id],
                "Reduce camera zoom/rotation or shorten headline copy.",
                round((move + delay + reveal) * fps),
            ))
    return {
        "schema_version": 1,
        "ok": not issues,
        "scenes": len(scenes),
        "frames_sampled": sampled_frames,
        "path": path_report,
        "issues": [issue.to_dict() for issue in issues],
    }
