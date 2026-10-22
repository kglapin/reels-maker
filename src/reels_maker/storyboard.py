"""Visual QA contact sheets from actual rendered MP4 frames.

Default: one clean, settled image per shot. Optional motion strip: entry,
settled and exit frames for each shot to inspect type staging and visual flow.
Neither mode performs aesthetic scoring or relies on synthetic stand-ins.
"""
from __future__ import annotations

import math
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .export_quality import verify_metadata
from .ffmpeg import RenderError, execute, probe
from .renderer import _frame_counts
from .spec import Project
from .transitions import timeline_frames, transition_plan


def _settled_frame(scene: dict, fps: int, scene_start: int,
                   clean_start: int, clean_end: int) -> int:
    """Prefer a fully revealed frame after the last animated text element."""
    choice = clean_start + (clean_end - clean_start) // 2
    motion = scene.get("motion") or {}
    if motion:
        title = scene.get("title") or {}
        active = sum(
            len(value.get("runs", [])) if isinstance(value, dict) else bool(value)
            for field in ("kicker", "headline", "body", "footer")
            for value in (title.get(field),)
        )
        duration = motion.get("duration_frames", max(2, round(fps * .24)))
        stagger = motion.get("stagger_frames", max(1, round(fps * .07)))
        reveal_end = scene_start + duration + stagger * max(0, active - 1)
        choice = max(choice, reveal_end + 1)
    return min(clean_end - 1, choice)


def _sample_frames(scene: dict, fps: int, beginning: int, length: int,
                   incoming: int, outgoing: int, *, motion_strip: bool) -> list[tuple[str, int]]:
    """Return deterministic frame indices inside the clean portion of a shot."""
    clean_start = beginning + incoming
    clean_end = beginning + length - outgoing
    clean = clean_end - clean_start
    if clean <= 0:
        raise RenderError("Scene does not contain any unmixed inspection frames")
    settled = _settled_frame(scene, fps, beginning, clean_start, clean_end)
    if not motion_strip:
        return [("settled", settled)]
    entry = min(clean_end - 1, clean_start + max(0, round(fps * .06)))
    # Sample before the outgoing transition, not inside it.
    exit_frame = max(clean_start, clean_end - max(1, round(fps * .08)) - 1)
    return [("entry", entry), ("settled", settled), ("exit", exit_frame)]


def make_storyboard(project: Project, video: Path, output: Path,
                    *, columns: int = 4, max_shots: int = 80,
                    motion_strip: bool = False) -> dict:
    """Review composition and actual timing frames without re-encoding video."""
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
    # Reject old exports with wrong frame rate, count or audio structure.
    verify_metadata(metadata, project, expected_frames=timeline_frames(frames, steps))

    thumb_w = 260
    thumb_h = round(thumb_w * project.height / project.width)
    if thumb_h > 490:
        thumb_h = 490
        thumb_w = max(100, round(thumb_h * project.width / project.height))
    margin, gap, label_h = 26, 18, 36
    cell_w = thumb_w + 16
    cell_h = thumb_h + label_h + 14
    entries_per_scene = 3 if motion_strip else 1
    num_cols = 3 if motion_strip else columns
    total_images = len(frames) * entries_per_scene
    rows = math.ceil(total_images / num_cols)
    canvas_w = 2 * margin + num_cols * cell_w + (num_cols - 1) * gap
    canvas_h = 2 * margin + rows * cell_h + (rows - 1) * gap
    sheet = Image.new("RGB", (canvas_w, canvas_h), "#121817")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    samples = []
    beginning = 0
    overlaps = [0] + [s["frames"] for s in steps]
    index = 0
    with tempfile.TemporaryDirectory(prefix="reels-storyboard-") as temp:
        for i, length in enumerate(frames):
            incoming = overlaps[i]
            outgoing = overlaps[i+1] if i+1 < len(frames) else 0
            targets = _sample_frames(
                project.scenes[i], project.fps, beginning, length,
                incoming, outgoing, motion_strip=motion_strip)
            for phase, frame in targets:
                timestamp = (frame + .5) / project.fps
                still = Path(temp) / f"{i:03d}-{phase}.png"
                execute(["-ss", f"{timestamp:.6f}", "-i", str(video),
                         "-frames:v", "1",
                         "-vf", f"scale={thumb_w}:{thumb_h}:force_original_aspect_ratio=decrease",
                         "-update", "1", str(still)])
                if not still.is_file():
                    raise RenderError(f"Cannot extract scene {i+1} ({phase})")
                with Image.open(still) as picture:
                    tile = picture.convert("RGB")
                col,row = index % num_cols,index // num_cols
                x = margin + col * (cell_w + gap)
                y = margin + row * (cell_h + gap)
                sheet.paste(tile, (x + (cell_w - tile.width)//2,y))
                label = f"SCENE {i+1:02d}  {phase.upper()}  {timestamp:.2f}s"
                draw.text((x+5,y+thumb_h+10),label,fill="#ECF2ED",font=font)
                samples.append({"scene":i+1,"phase":phase,
                                "timestamp_seconds":round(timestamp,3)})
                index += 1
            beginning += length - (overlaps[i+1] if i+1 < len(frames) else 0)
    output=Path(output).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    sheet.save(output,optimize=True)
    return {"output":str(output),"scenes":len(frames),
            "mode":"motion_strip" if motion_strip else "settled",
            "samples":samples,"video":str(video),
            "human_review_required":True}
