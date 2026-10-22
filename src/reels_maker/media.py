"""Preflight assets once, before expensive video encoding."""
from dataclasses import dataclass
from pathlib import Path

from .ffmpeg import RenderError, probe, require_tool
from .paths import resolve_asset
from .spec import Project


@dataclass(frozen=True)
class Shot:
    path: Path
    start: float
    length: float
    framing: str
    title: dict


@dataclass(frozen=True)
class Inputs:
    shots: tuple[Shot, ...]
    music: Path | None
    logo: Path | None


def preflight(project: Project, root: Path) -> Inputs:
    require_tool("ffmpeg")
    require_tool("ffprobe")
    cache = {}

    def info(path):
        if path not in cache:
            cache[path] = probe(path)
        return cache[path]

    shots = []
    for index, item in enumerate(project.scenes):
        path = resolve_asset(item["file"], root)
        metadata = info(path)
        if not any(s.get("codec_type") == "video" for s in metadata.get("streams", [])):
            raise RenderError(f"Scene {index}: no video stream: {path}")
        start, length = float(item.get("start", 0)), float(item["duration"])
        try:
            source_duration = float(metadata["format"]["duration"])
        except (KeyError, ValueError, TypeError) as exc:
            raise RenderError(f"Scene {index}: missing source duration: {path}") from exc
        if start + length > source_duration + 0.05:
            raise RenderError(f"Scene {index}: segment exceeds {path.name}")
        if round(length * project.fps) < 1:
            raise RenderError(f"Scene {index}: shorter than one frame")
        shots.append(Shot(path, start, length, item.get("framing", "crop"), item.get("title", {})))

    music = resolve_asset(project.music["file"], root) if project.music else None
    if music:
        metadata = info(music)
        if not any(s.get("codec_type") == "audio" for s in metadata.get("streams", [])):
            raise RenderError(f"Music file has no audio stream: {music}")
        if float(project.music.get("start", 0)) + project.duration > float(metadata["format"]["duration"]) + 0.05:
            raise RenderError("Music segment is shorter than the requested video")

    logo = resolve_asset(project.branding["logo"], root) if project.branding.get("logo") else None
    if logo and logo.suffix.lower() != ".png":
        raise RenderError("Logo overlay requires transparent PNG; convert SVG once in advance")
    return Inputs(tuple(shots), music, logo)
