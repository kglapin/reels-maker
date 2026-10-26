"""Persistent per-scene cache keys and atomic segment publication."""
from __future__ import annotations

import errno
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from ..studio import StudioProject

STUDIO_CACHE_SCHEMA = 2


_ASSET_PATH_FIELDS = frozenset({
    "asset", "file", "image", "logo", "mesh_path", "path", "photo",
    "photo_source", "photos", "video_source",
})


def _font_signature(fonts) -> dict:
    """Cache signature for the resolved font configuration."""
    signature = {"family": fonts.family}
    for weight in ("regular", "bold"):
        path = Path(fonts.path(weight)).resolve()
        signature[weight] = [str(path), path.stat().st_mtime_ns]
    return signature


def _hash_payload(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                     default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _cache_signature(project: StudioProject, profile: str | None,
                     supersample: int, codec: str, crf: int, preset: str,
                     timeline, built, *,
                     font_signature: dict | None = None) -> str:
    """Aggregate project signature retained for reporting and diagnostics."""
    payload = {
        "width": project.width, "height": project.height, "fps": project.fps,
        "profile": profile, "codec": codec, "crf": crf, "preset": preset,
        "supersample": supersample, "style": project.style,
        "brand": project.brand, "name": project.name,
        "tokens": project.tokens.to_dict(),
        "fonts": font_signature or _font_signature(project.fonts),
        "cache_schema": STUDIO_CACHE_SCHEMA,
        "transition_engine_version": 1,
        "scenes": [
            {"scene": scene, "frames": timing.frames,
             "transition_in": item.meta.get("transition_in"),
             "transition_duration": item.meta.get("transition_duration")}
            for scene, timing, item in zip(project.scenes, timeline.scenes,
                                           built)],
    }
    return _hash_payload(payload)


def _cache_settings_signature(project: StudioProject, profile: str | None,
                              supersample: int, codec: str, crf: int,
                              preset: str, font_signature: dict) -> str:
    """Settings shared by every scene cache entry."""
    return _hash_payload({
        "cache_schema": STUDIO_CACHE_SCHEMA,
        "transition_engine_version": 1,
        "width": project.width, "height": project.height, "fps": project.fps,
        "profile": profile, "codec": codec, "crf": crf, "preset": preset,
        "supersample": supersample, "style": project.style,
        "brand": project.brand,
        "tokens": project.tokens.to_dict(),
        "fonts": font_signature,
    })


def _iter_asset_paths(value, *, path_field: bool = False):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _iter_asset_paths(
                child, path_field=key in _ASSET_PATH_FIELDS)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _iter_asset_paths(child, path_field=path_field)
    elif path_field and isinstance(value, str):
        yield value


def _asset_path(project: StudioProject, value: str) -> Path:
    if value.startswith("shared://"):
        return (project.root / "shared_media"
                / value.removeprefix("shared://")).resolve()
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    if value.startswith("brands/"):
        return (project.root / path).resolve()
    brand_root = (project.root / "brands" / project.brand
                  if project.brand else project.path.parent)
    return (brand_root / path).resolve()


def _asset_fingerprints(project: StudioProject, scene: dict, built) -> list[dict]:
    """Return cheap stat signatures for local visual assets used by a scene."""
    structures = [scene, built.background]
    for node in built.nodes:
        structures.extend(child.props for child in node.flatten())
    paths = set()
    for structure in structures:
        for value in _iter_asset_paths(structure):
            try:
                path = _asset_path(project, value)
                if path.is_file():
                    paths.add(path)
            except (OSError, RuntimeError, ValueError):
                continue
    signatures = []
    for path in sorted(paths, key=str):
        try:
            stat = path.stat()
        except OSError:
            continue
        signatures.append({
            "path": str(path),
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
        })
    return signatures


def _publish_cache_segment(part: Path, cached: Path) -> None:
    """Publish atomically even when output and cache are on different volumes."""
    try:
        os.replace(part, cached)
        return
    except OSError as exc:
        if exc.errno != errno.EXDEV:
            raise

    staged = None
    try:
        with tempfile.NamedTemporaryFile(
                prefix=f".{cached.name}.", suffix=".tmp",
                dir=str(cached.parent), delete=False) as handle:
            staged = Path(handle.name)
        shutil.copyfile(part, staged)
        os.replace(staged, cached)
        part.unlink()
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)


def _scene_cache_key(settings_signature: str, project: StudioProject,
                     index: int, scene: dict, timing, built,
                     next_scene=None) -> str:
    """Hash only the inputs that can change this encoded scene segment."""
    payload = {
        "settings": settings_signature,
        "index": index,
        "seed": getattr(built.context, "seed", index * 17 + 3),
        "scene": scene,
        "frames": timing.frames,
        "transition_in": built.meta.get("transition_in"),
        "transition_duration": built.meta.get("transition_duration"),
        "assets": _asset_fingerprints(project, scene, built),
    }
    transition_out = scene.get("transition_out")
    if transition_out and next_scene is not None:
        payload["outgoing_dependency"] = {
            "transition": transition_out,
            "index": next_scene.index,
            "scene": next_scene.scene,
            "seed": getattr(
                next_scene.context, "seed", next_scene.index * 17 + 3),
            "transition_in": next_scene.meta.get("transition_in"),
            "transition_duration": next_scene.meta.get("transition_duration"),
            "assets": _asset_fingerprints(
                project, next_scene.scene, next_scene),
        }
    return _hash_payload(payload)
