"""Bind host reviews to the exact rendered files and sampled frames."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping


class RenderEvidenceError(ValueError):
    """Render evidence is absent, malformed, or not tied to actual files."""


def _sha256(path: Path) -> tuple[str, int]:
    if not path.is_file():
        raise RenderEvidenceError(f"evidence file does not exist: {path}")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    if size == 0:
        raise RenderEvidenceError(f"evidence file is empty: {path}")
    return digest.hexdigest(), size


def bind_render_evidence(render: Mapping[str, Any],
                         storyboard: Mapping[str, Any]) -> dict:
    """Return hashes/times for actual render and storyboard artifacts.

    This creates review-ready provenance only. It cannot attest that a model or
    person actually received, watched, or understood the files.
    """
    if not isinstance(render, Mapping) or not isinstance(storyboard, Mapping):
        raise RenderEvidenceError("render and storyboard reports must be objects")
    render_path = render.get("output")
    storyboard_path = storyboard.get("output")
    if not isinstance(render_path, str) or not isinstance(storyboard_path, str):
        raise RenderEvidenceError("reports must name actual render and storyboard files")
    render_sha, render_bytes = _sha256(Path(render_path).resolve())
    storyboard_sha, storyboard_bytes = _sha256(Path(storyboard_path).resolve())
    mode = storyboard.get("mode")
    if mode not in ("settled", "motion_strip"):
        raise RenderEvidenceError("unknown storyboard evidence mode")
    samples = storyboard.get("samples")
    if not isinstance(samples, list) or not samples:
        raise RenderEvidenceError("storyboard report must list sampled frames")
    normalized_samples = []
    for index, sample in enumerate(samples):
        if not isinstance(sample, Mapping):
            raise RenderEvidenceError(f"samples[{index}] must be an object")
        scene = sample.get("scene")
        phase = sample.get("phase")
        timestamp = sample.get("timestamp_seconds")
        if isinstance(scene, bool) or not isinstance(scene, int) or scene < 1:
            raise RenderEvidenceError(f"samples[{index}].scene must be positive")
        if phase not in ("entry", "settled", "exit"):
            raise RenderEvidenceError(f"samples[{index}].phase is unsupported")
        if (isinstance(timestamp, bool) or not isinstance(timestamp, (float, int))
                or not math.isfinite(float(timestamp)) or timestamp < 0):
            raise RenderEvidenceError(f"samples[{index}].timestamp_seconds is invalid")
        duration = render.get("duration")
        if (isinstance(duration, (float, int)) and not isinstance(duration, bool)
                and timestamp > duration + .001):
            raise RenderEvidenceError(f"samples[{index}] is outside the rendered video")
        normalized_samples.append({"scene": scene, "phase": phase,
                                   "timestamp_seconds": round(float(timestamp), 4)})
    if mode == "motion_strip":
        phases_by_scene: dict[int, set[str]] = {}
        for sample in normalized_samples:
            phases_by_scene.setdefault(sample["scene"], set()).add(sample["phase"])
        required = {"entry", "settled", "exit"}
        if any(not required.issubset(phases) for phases in phases_by_scene.values()):
            raise RenderEvidenceError(
                "every motion-strip scene must contain entry, settled and exit frames")
    payload = {
        "schema_version": 1,
        "render_sha256": render_sha,
        "storyboard_sha256": storyboard_sha,
        "storyboard_mode": mode,
        "samples": normalized_samples,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    evidence_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {**payload, "render_bytes": render_bytes,
            "storyboard_bytes": storyboard_bytes,
            "evidence_hash": evidence_hash,
            "sha256": evidence_hash,
            "host_observation_required": True}
