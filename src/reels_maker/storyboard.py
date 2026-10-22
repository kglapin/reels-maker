"""Visual QC contact sheet of *actual rendered frames*, not illustrative mockups.

Deterministic representative stills are sampled from each scene's settled
reading window, accounting for overlap frames. Human review is indispensable.
"""
from __future__ import annotations

import math
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .ffmpeg import RenderError, execute, probe
from .renderer import _frame_counts
from .spec import Project
from .transitions import transition_plan, timeline_frames


def make_storyboard(project: Project, video: Path, output: Path,
                    *, columns: int = 4, max_shots: int = 80) -> dict:
    """Review composition/contrast on real export, without re-encoding video."""
    video = Path(video).resolve()
    if not video.is_file():
        raise RenderError(f"Rendered video does not exist: {video}")
    if not 1 <= columns <= 8:
        raise RenderError("Storyboard columns must be 1..8")
    frames = _frame_counts(project)
    if len(frames) > max_shots:
        raise RenderError(f"Too many scenes for contact sheet ({max_shots} max)")
    steps = transition_plan(project, frames)
    metadata = probe(video)
    stream = next((s for s in metadata["streams"] if s["codec_type"] == "video"), {})
    if (stream.get("width") != project.width or
            stream.get("height") != project.height):
        raise RenderError("Storyboard input does not match project output dimensions")
    total = timeline_frames(frames, steps) / project.fps
    actual = float(metadata.get("format", {}).get("duration", 0))
    if abs(total - actual) > max(.12, 2 / project.fps):
        raise RenderError("Storyboard project does not match MP4 duration")

    thumb_w = 260
    thumb_h = round(thumb_w * project.height / project.width)
    # Contact sheets are for inspection, not a full-resolution proxy archive.
    if thumb_h > 490:
        thumb_h = 490
        thumb_w = max(100, round(thumb_h * project.width / project.height))
    margin, gap, label_h = 26, 18, 36
    cell_w = thumb_w + 16
    cell_h = thumb_h + label_h + 14
    rows = math.ceil(len(frames) / columns)
    canvas_w = 2 * margin + columns * cell_w + (columns - 1) * gap
    canvas_h = 2 * margin + rows * cell_h + (rows - 1) * gap
    sheet = Image.new("RGB", (canvas_w, canvas_h), "#121817")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()

    samples = []
    beginning = 0
    overlaps = [0] + [s["frames"] for s in steps]
    with tempfile.TemporaryDirectory(prefix="reels-storyboard-") as temp:
        for i, length in enumerate(frames):
            # Full-opacity interval after the incoming transition and before
            # the next one, never the muddy middle of a dissolve.
            incoming = overlaps[i]
            outgoing = overlaps[i + 1] if i + 1 < len(frames) else 0
            clean = length - incoming - outgoing
            if clean < 1:
                raise RenderError(f"Scene {i + 1} has no clean inspection frames")
            midpoint = beginning + incoming + clean // 2
            timestamp = (midpoint + .5) / project.fps
            still = Path(temp) / f"{i:03d}.png"
            execute(["-ss", f"{timestamp:.6f}", "-i", str(video),
                     "-frames:v", "1",
                     "-vf", f"scale={thumb_w}:{thumb_h}:force_original_aspect_ratio=decrease",
                     "-update", "1", str(still)])
            if not still.is_file():
                raise RenderError(f"Cannot extract frame {i + 1}")
            with Image.open(still) as original:
                tile = original.convert("RGB")
            col, row = i % columns, i // columns
            x = margin + col * (cell_w + gap)
            y = margin + row * (cell_h + gap)
            sheet.paste(tile, (x + (cell_w - tile.width) // 2, y))
            label = f"SCENE {i + 1:02d}    {timestamp:.2f}s"
            draw.text((x + 5, y + thumb_h + 10), label, fill="#ECF2ED",
                      font=font)
            samples.append({"scene": i + 1, "timestamp_seconds": round(timestamp, 3)})
            beginning += length - (overlaps[i + 1] if i + 1 < len(frames) else 0)
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, optimize=True)
    return {"output": str(output), "scenes": len(frames),
            "samples": samples, "video": str(video),
            "human_review_required": True}
