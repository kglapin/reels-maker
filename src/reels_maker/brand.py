"""Resolve immutable brand presets for consistent, brand-scoped video projects.

The renderer receives ordinary repository-relative media paths after this step.
This keeps the rendering pipeline independent from brand folder conventions.
"""
from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path

from .spec import Project, ProjectError

SLUG = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


def brand_directory(slug: str, root: Path) -> Path:
    if not isinstance(slug, str) or not SLUG.fullmatch(slug):
        raise ProjectError("Brand must be a lowercase slug (letters, digits, hyphens)")
    return Path(root).resolve() / "brands" / slug


def _scoped_path(slug: str, value: str) -> str:
    """Map a logical brand path to a safe repository-relative path."""
    if not isinstance(value, str) or not value.strip():
        raise ProjectError(f"Brand {slug}: asset path must be nonempty")
    # Intentionally disallow cross-brand access and absolute paths. Avoid
    # auto-discovery or arbitrary filesystem paths in agent-authored manifests.
    if "\\" in value or ":" in value or value.startswith("/"):
        raise ProjectError(f"Brand {slug}: use slash-separated brand-local paths: {value}")
    path = Path(value)
    if any(part in (".", "..") for part in path.parts):
        raise ProjectError(f"Brand {slug}: relative parent paths are disallowed: {value}")
    return (Path("brands") / slug / path).as_posix()


def apply_brand(project: Project, root: Path) -> Project:
    """Hydrate brand defaults exactly once, allowing project-specific overrides."""
    if not project.brand:
        return project
    directory = brand_directory(project.brand, root)
    config_path = directory / "brand.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ProjectError(f"Cannot load brand configuration {config_path}: {exc}") from exc
    if not isinstance(config, dict) or config.get("id") != project.brand:
        raise ProjectError(f"Brand manifest must declare id={project.brand!r}")
    defaults = config.get("branding", {})
    if not isinstance(defaults, dict):
        raise ProjectError("Brand defaults must contain a branding object")
    identity = config.get("identity", {})
    if not isinstance(identity, dict):
        raise ProjectError("identity must be an object")
    typography = identity.get("typography", {})
    if not isinstance(typography, dict):
        raise ProjectError("identity typography must be an object")
    # Safe areas depend on the target video and platform, not on the brand.
    # Projects can still supply explicit branding.safe_areas overrides.
    brand_style = {"font_family": typography.get("primary", "DejaVu Sans")}
    # Brand-wide defaults cascade into the project; per-project overrides win.
    branding = {**brand_style, **defaults, **project.branding}
    if branding.get("logo"):
        branding["logo"] = _scoped_path(project.brand, branding["logo"])
    scenes = [{**scene, "file": _scoped_path(project.brand, scene["file"])}
              for scene in project.scenes]
    music = ({**project.music, "file": _scoped_path(project.brand, project.music["file"])}
             if project.music else None)
    voiceover = ({**project.voiceover,
                  "file": _scoped_path(project.brand, project.voiceover["file"])}
                 if project.voiceover else None)
    # Remove brand identifier after expansion so later code never prefixes twice.
    return replace(project, scenes=scenes, music=music, voiceover=voiceover,
                   branding=branding, brand=None)
