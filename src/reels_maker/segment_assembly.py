"""Shared FFmpeg operations for joining already encoded scene segments."""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from .ffmpeg import RenderError, execute


def join_segments(parts: Sequence[Path], destination: Path, scratch: Path,
                  *, max_frames: int | None = None) -> None:
    """Join compatible video segments with stream copy.

    Both renderer backends use this boundary. Keeping it outside either
    renderer prevents one backend from depending on another backend's private
    implementation.
    """
    manifest = scratch / "segments.txt"

    def quote_path(path: Path) -> str:
        return str(path).replace("'", "'\\''")

    manifest.write_text(
        "".join(f"file '{quote_path(path)}'\n" for path in parts),
        encoding="utf-8",
    )
    args = ["-f", "concat", "-safe", "0", "-i", str(manifest),
            "-map", "0:v:0", "-an", "-c:v", "copy"]
    if max_frames is not None:
        if isinstance(max_frames, bool) or max_frames < 1:
            raise RenderError("max_frames must be a positive frame count")
        args += ["-frames:v", str(max_frames)]
    execute(args + [str(destination)])
