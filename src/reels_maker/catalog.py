"""Fast media discovery for terminal harnesses; metadata probing is optional."""
from __future__ import annotations

import os
from pathlib import Path

from .ffmpeg import RenderError, probe

_MEDIA = {".mp4", ".mov", ".mkv", ".webm", ".mp3", ".wav", ".m4a"}
_SKIP = {".git", ".cache", ".venv", ".tmp", "output", "render", "__pycache__", "work"}


def catalog(root: Path, *, include_metadata: bool = False, limit: int = 500) -> dict:
    """List usable source paths, highlighting missing Git LFS payloads.

    By default this performs only filesystem operations, without invoking FFprobe.
    """
    root = Path(root).resolve()
    if not root.is_dir():
        raise RenderError(f"Asset root does not exist: {root}")
    if not 1 <= limit <= 10000:
        raise RenderError("Catalog limit must be between 1 and 10000")
    items = []
    for folder, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in _SKIP and not d.startswith("."))
        for name in sorted(names):
            path = Path(folder) / name
            if path.suffix.lower() not in _MEDIA or not path.is_file():
                continue
            stats = path.stat()
            pointer = False
            if stats.st_size < 300:
                with path.open("rb") as stream:
                    pointer = stream.read(64).startswith(
                        b"version https://git-lfs.github.com/spec/v1")
            item = {
                "file": path.relative_to(root).as_posix(),
                "size_bytes": stats.st_size,
                "available": not pointer,
                "kind": "audio" if path.suffix.lower() in {".mp3", ".wav", ".m4a"} else "video",
            }
            if include_metadata and not pointer:
                try:
                    info = probe(path)
                    item["duration"] = float(info["format"]["duration"])
                    item["video"] = any(s.get("codec_type") == "video" for s in info["streams"])
                    item["audio"] = any(s.get("codec_type") == "audio" for s in info["streams"])
                except (RenderError, KeyError, TypeError, ValueError) as exc:
                    item["probe_error"] = str(exc)
            items.append(item)
            if len(items) >= limit:
                return {"root": str(root), "items": items, "truncated": True, "count": len(items)}
    return {"root": str(root), "items": items, "truncated": False, "count": len(items)}
