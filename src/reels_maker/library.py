"""Reviewed asset library (MD-05): explicit license metadata or it fails.

Every library entry must carry explicit source, license, resolution, topics
and editorial-state metadata. Missing data is a hard error, never a fallback:
the engine must not guess rights or review status for media it is asked to
deliver. Lottie/dotLottie entries are rejected outright because animated
vector playback is not implemented yet.
"""
from __future__ import annotations

import json
from pathlib import Path

from .spec import ProjectError

ALLOWED_KINDS = {"product", "icon", "graphic", "footage", "audio"}
ALLOWED_STATES = {"reviewed", "quarantine"}
SCHEMA_VERSION = 1
_MIN_LONG_EDGE = 720


class LibraryError(ProjectError):
    """Raised when a library manifest is missing explicit metadata."""


def _entry_error(entry: dict, index: int, field: str, reason: str):
    label = entry.get("id", f"entry[{index}]")
    return LibraryError(
        f"Library entry {label!r} (#{index + 1}): {field} {reason}")


def check_library(path: str | Path) -> dict:
    """Validate an asset-library manifest and return a JSON-friendly report."""
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LibraryError(f"Cannot read library manifest {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise LibraryError(f"Library manifest {path} must be a JSON object")
    if raw.get("schema_version") != SCHEMA_VERSION:
        raise LibraryError(
            f"Library manifest {path}: schema_version must be "
            f"{SCHEMA_VERSION}, got {raw.get('schema_version')!r}")
    entries = raw.get("entries")
    if not isinstance(entries, list) or not entries:
        raise LibraryError(
            f"Library manifest {path} must list at least one entry under "
            "'entries'")

    # Manifest entry paths are relative to the brand directory (the parent of
    # the media/ folder that stores the manifest), matching brand manifests.
    brand_dir = path.parent.parent
    base = brand_dir  # explicit alias for readability below
    seen_ids: set[str] = set()
    seen_files: dict[str, str] = {}
    warnings: list[str] = []
    reviewed = 0
    quarantine = 0
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise LibraryError(
                f"Library entry #{index + 1} must be a JSON object")
        for field in ("id", "kind", "file", "source", "license",
                      "license_url", "resolution", "topics",
                      "editorial_state", "review"):
            if field not in entry or entry[field] in (None, ""):
                raise _entry_error(entry, index, field,
                                   "is required — the engine does not invent "
                                   "asset metadata")
        entry_id = str(entry["id"])
        if entry_id in seen_ids:
            raise _entry_error(entry, index, "id", f"duplicates {entry_id!r}")
        seen_ids.add(entry_id)
        kind = str(entry["kind"])
        if kind in ("lottie", "dotlottie"):
            raise _entry_error(
                entry, index, "kind",
                "Lottie/dotLottie playback is not implemented; do not list "
                "animated-vector assets until support lands")
        if kind not in ALLOWED_KINDS:
            raise _entry_error(
                entry, index, "kind",
                f"must be one of {sorted(ALLOWED_KINDS)}, got {kind!r}")
        state = str(entry["editorial_state"])
        if state not in ALLOWED_STATES:
            raise _entry_error(
                entry, index, "editorial_state",
                f"must be {sorted(ALLOWED_STATES)} (an unreviewed file is "
                f"'quarantine', never silently usable), got {state!r}")
        review = entry["review"]
        if not isinstance(review, dict) or not review.get("by") \
                or not review.get("date"):
            raise _entry_error(
                entry, index, "review",
                "must contain {'by': name, 'date': YYYY-MM-DD}; a human must "
                "have actually seen the asset")
        resolution = entry["resolution"]
        if (not isinstance(resolution, (list, tuple)) or len(resolution) != 2
                or not all(isinstance(v, int) and v > 0 for v in resolution)):
            raise _entry_error(
                entry, index, "resolution",
                "must be [width, height] in positive pixels")
        topics = entry["topics"]
        if (not isinstance(topics, list) or not topics
                or not all(isinstance(t, str) and t for t in topics)):
            raise _entry_error(
                entry, index, "topics",
                "must be a non-empty list of strings")
        file_path = base / str(entry["file"])
        if not file_path.is_file():
            raise _entry_error(
                entry, index, "file", f"does not exist on disk: {file_path}")
        file_key = str(Path(entry["file"]))
        if file_key in seen_files:
            raise _entry_error(
                entry, index, "file",
                f"duplicates {seen_files[file_key]!r} (avoid duplicate shots)")
        seen_files[file_key] = entry_id
        if state == "reviewed":
            reviewed += 1
        else:
            quarantine += 1
            warnings.append(
                f"{entry_id!r} is quarantined and excluded from delivery "
                "until reviewed")
        if max(resolution) < _MIN_LONG_EDGE:
            warnings.append(
                f"{entry_id!r} resolution {tuple(resolution)} is below "
                f"{_MIN_LONG_EDGE}px on the long edge; verify it on a phone "
                "before delivery")
    return {
        "manifest": str(path),
        "entries": len(entries),
        "reviewed": reviewed,
        "quarantine": quarantine,
        "warnings": warnings,
        "ok": True,
    }
