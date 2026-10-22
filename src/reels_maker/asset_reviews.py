"""Reviewed brand-media classifications for safe editorial compositing.

Only explicitly reviewed assets are annotated; no naive image recognition or
guessed classification is treated as fact. The source can remain in the library,
but double-branding must be stopped by the strict-quality publishing gate.
"""
from __future__ import annotations

import json
from pathlib import Path

from .brand import brand_directory
from .spec import ProjectError


def load_media_reviews(slug: str, root: Path) -> dict[str, dict]:
    directory = brand_directory(slug, root)
    source = directory / "media" / "asset-reviews.json"
    if not source.is_file():
        return {}
    try:
        parsed = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ProjectError(f"Cannot read brand media reviews: {source}: {exc}") from exc
    if (not isinstance(parsed, dict) or parsed.get("schema_version") != 1
            or not isinstance(parsed.get("assets"), dict)):
        raise ProjectError(f"Invalid asset review manifest: {source}")
    for key, record in parsed["assets"].items():
        if (not isinstance(key, str) or key.startswith("/")
                or ".." in Path(key).parts or
                not isinstance(record, dict) or
                record.get("type") not in ("finished_promo", "clean_source") or
                not isinstance(record.get("burned_in"), list) or
                not all(x in ("logo", "captions", "metric")
                            for x in record["burned_in"])):
            raise ProjectError(f"Invalid asset review record: {key}")
    return parsed["assets"]
