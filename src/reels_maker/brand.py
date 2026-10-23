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


def init_brand(slug: str, *, name: str, accent: str, root: Path,
               force: bool = False) -> dict:
    """Scaffold a new brand directory (MD-10 enablement).

    The scaffold is generated, not invented content: the accent colour is the
    one explicitly provided by the caller and neutral supporting colors are
    labeled as placeholders for the brandbook flow. The owner still supplies
    licensed fonts, a logo with cleared rights and reviewed media before
    delivery. An existing brand directory is never overwritten without
    ``force``.
    """
    directory = brand_directory(slug, root)
    if directory.exists() and not force:
        raise ProjectError(
            f"Brand directory already exists: {directory} "
            "(use --force to replace it)")
    if not isinstance(name, str) or not name.strip():
        raise ProjectError("Brand name must be nonempty")
    accent = str(accent).strip()
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", accent):
        raise ProjectError(
            f"Accent must be a hex colour like #47A013, got {accent!r}")
    directory = Path(directory)
    if force:
        import shutil
        shutil.rmtree(directory, ignore_errors=True)
    for sub in ("projects", "media/footage", "media/audio",
                "media/assets", "licensing"):
        (directory / sub).mkdir(parents=True, exist_ok=True)
    config = {
        "id": slug,
        "name": name.strip(),
        # Scaffold neutral placeholders; the brandbook review flow replaces
        # them once the owner supplies verified identity assets.
        "identity": {
            "palette": {
                "primary": accent,
                "background": "#FFFFFF",
                "text": "#101416",
                "neutral": "#5A6368",
            },
        },
        "branding": {"accent": accent, "logo": False},
        "version": 1,
        "scaffold": {
            "status": "placeholder identity — verify fonts, logo rights and "
                      "claims before any delivery",
            "created": "2026-10-23",
        },
    }
    (directory / "brand.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    (directory / "BRAND.md").write_text(
        f"# {name.strip()}\n\n"
        "Scaffolded brand directory. Before any delivery:\n\n"
        "1. Confirm the palette with the owner (background/text/neutral are "
        "placeholders around the supplied accent).\n"
        "2. Add licensed fonts under `media/fonts/` and register them in "
        "`brand.json` identity.\n"
        "3. Only add media with documented rights in `licensing/` "
        "(source + license + review date).\n"
        "4. Keep project manifests under `projects/`; brand paths are "
        "relative to this directory.\n",
        encoding="utf-8")
    (directory / "licensing" / "README.txt").write_text(
        "Log every external source here: title, author, URL, license "
        "(SPDX/name), and the date the owner verified it. An asset without "
        "documented rights must not be listed in media/asset-library.json.\n",
        encoding="utf-8")
    return {
        "brand": slug,
        "directory": str(directory),
        "scaffolded": ["brand.json", "BRAND.md",
                       "projects/", "media/", "licensing/"],
        "warnings": [
            "Placeholder identity: replace neutral palette entries and add "
            "licensed fonts before delivery",
            "No media is shipped with the scaffold; rights must be documented "
            "in licensing/ first",
        ],
    }


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
