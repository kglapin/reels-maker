"""Assets checks for Studio QA."""
from __future__ import annotations

from pathlib import Path

from ..core.timeline import Timeline
from .models import Issue



def _asset_checks(built, project) -> list[Issue]:
    issues = []
    background = built.background
    if background.get("kind") == "photo":
        asset = Path(background.get("asset", ""))
        if not asset.is_file():
            issues.append(Issue(
                "missing_asset", "error",
                f"Background asset is missing: {asset}",
                built.index + 1, None, [],
                "Restore the media file or point the manifest at an approved asset."))
        manager = getattr(project, "asset_manager", None)
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
