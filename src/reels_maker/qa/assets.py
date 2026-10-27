"""Assets checks for Studio QA."""
from __future__ import annotations

from pathlib import Path

from ..core.timeline import Timeline
from .models import Issue



def _asset_checks(built, project) -> list[Issue]:
    issues = []
    manager = getattr(project, "asset_manager", None)
    background = built.background
    if background.get("kind") == "photo":
        asset = Path(background.get("asset", ""))
        if not asset.is_file():
            issues.append(Issue(
                "missing_asset", "error",
                f"Background asset is missing: {asset}",
                built.index + 1, None, [],
                "Restore the media file or point the manifest at an approved asset."))
        if manager is not None:
            reviewed_path = background.get("video_source") or asset
            review = manager.reviews.get(
                _relative_asset(manager, Path(reviewed_path)), {})
            state = review.get("type", "unreviewed")
            if state == "finished_promo" and not built.scene.get("allow_prebranded"):
                issues.append(Issue(
                    "prebranded_footage", "error",
                    "A finished promo with burned-in graphics is used as a background.",
                    built.index + 1, None, [],
                    "Use clean source footage or explicitly accept the baked-in branding."))
            elif state == "unreviewed" and not built.scene.get("allow_unreviewed"):
                issues.append(Issue(
                    "asset_unreviewed", "warning",
                    "Background footage has no editorial review record.",
                    built.index + 1, None, [],
                    "Inspect actual frames and record editorial_state before publishing."))
    for root in built.nodes:
        for node in root.flatten():
            if node.kind != "video":
                continue
            raw_path = node.props.get("path")
            asset = Path(raw_path) if isinstance(raw_path, str) and raw_path else None
            if asset is None or not asset.is_file():
                issues.append(Issue(
                    "missing_asset", "error",
                    f"Video layer asset is missing: {raw_path or '<empty path>'}",
                    built.index + 1, None, [node.role],
                    "Restore the source video or select an existing reviewed asset."))
                continue
            if manager is None:
                continue
            review = manager.reviews.get(_relative_asset(manager, asset), {})
            state = review.get("type", "unreviewed")
            if state == "finished_promo" and not built.scene.get("allow_prebranded"):
                issues.append(Issue(
                    "prebranded_footage", "error",
                    f"Video layer {node.role!r} uses a finished promo with baked-in graphics.",
                    built.index + 1, None, [node.role],
                    "Use reviewed clean-source video or explicitly review its baked-in overlays."))
            elif state == "unreviewed" and not built.scene.get("allow_unreviewed"):
                issues.append(Issue(
                    "asset_unreviewed", "warning",
                    f"Video layer {node.role!r} has no editorial review record.",
                    built.index + 1, None, [node.role],
                    "Inspect the footage and record its editorial state before delivery."))
    camera_video = (built.scene.get("video")
                    if built.scene.get("camera_canvas") else None)
    if camera_video:
        asset = Path(str(camera_video))
        if not asset.is_file():
            issues.append(Issue(
                "missing_asset", "error",
                f"Camera Canvas video is missing: {asset}",
                built.index + 1, None, ["camera-canvas-video"],
                "Restore the source video or select an existing reviewed asset."))
        elif manager is not None:
            review = manager.reviews.get(_relative_asset(manager, asset), {})
            state = review.get("type", "unreviewed")
            if state == "finished_promo" and not built.scene.get("allow_prebranded"):
                issues.append(Issue(
                    "prebranded_footage", "error",
                    "Camera Canvas uses a finished promo with baked-in graphics.",
                    built.index + 1, None, ["camera-canvas-video"],
                    "Use reviewed clean-source video or explicitly review its baked-in overlays."))
            elif state == "unreviewed" and not built.scene.get("allow_unreviewed"):
                issues.append(Issue(
                    "asset_unreviewed", "warning",
                    "Camera Canvas video has no editorial review record.",
                    built.index + 1, None, ["camera-canvas-video"],
                    "Inspect the footage and record its editorial state before delivery."))
    return issues


def _relative_asset(manager, path: Path) -> str:
    try:
        return path.resolve().relative_to(manager.brand_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _asset_summary(project) -> dict:
    manager = getattr(project, "asset_manager", None)
    if manager is None:
        return {"status": "not_available"}
    return {"status": "ok", **manager.summary()}
