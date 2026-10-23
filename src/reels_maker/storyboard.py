"""Visual QA contact sheets from actual rendered MP4 frames.

Default: one clean, settled image per shot. Optional motion strip: entry,
settled and exit frames for each shot to inspect type staging and visual flow.
Neither mode performs aesthetic scoring or relies on synthetic stand-ins.
"""
from __future__ import annotations

import math
import tempfile
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .export_quality import verify_metadata
from .ffmpeg import RenderError, execute, probe
from .renderer import _frame_counts
from .spec import Project
from .transitions import timeline_frames, transition_plan
from .motion_timing import build_cue_schedule, scripted_text_roles


def _settled_frame(scene: dict, fps: int, scene_start: int,
                   clean_start: int, clean_end: int,
                   scene_frames: int) -> int:
    """Choose a truly settled frame using the same explicit cues as rendering."""
    choice = clean_start + (clean_end - clean_start) // 2
    motion = scene.get("motion") or {}
    if motion:
        title = scene.get("title") or {}
        roles = ["logo", "accent"] + [
            role for role, _ in scripted_text_roles(title)]
        try:
            schedule = build_cue_schedule(motion, roles, fps, scene_frames)
        except ValueError as exc:
            raise RenderError(f"Invalid storyboard motion cues: {exc}") from exc
        fully_settled = scene_start + schedule.last_settled_frame + 1
        if fully_settled >= clean_end:
            raise RenderError(
                "No fully settled motion frame before outgoing transition")
        choice = max(choice, fully_settled)
    return min(clean_end - 1, choice)


def _sample_frames(scene: dict, fps: int, beginning: int, length: int,
                   incoming: int, outgoing: int, *, motion_strip: bool) -> list[tuple[str, int]]:
    """Return deterministic frame indices inside the clean portion of a shot."""
    clean_start = beginning + incoming
    clean_end = beginning + length - outgoing
    clean = clean_end - clean_start
    if clean <= 0:
        raise RenderError("Scene does not contain any unmixed inspection frames")
    settled = _settled_frame(
        scene, fps, beginning, clean_start, clean_end, length)
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


def make_studio_storyboard(project, video: Path, output: Path, *,
                           columns: int = 4,
                           motion_strip: bool = False) -> dict:
    """Inspect actual studio MP4 frames with frame-accurate scene offsets."""
    video = Path(video).resolve()
    if not video.is_file():
        raise RenderError(f"Rendered video does not exist: {video}")
    if not 1 <= columns <= 8:
        raise RenderError("Storyboard columns must be 1..8")
    timeline = project.timeline()
    metadata = probe(video)
    streams = metadata.get("streams") or []
    videos = [stream for stream in streams
              if stream.get("codec_type") == "video"]
    audios = [stream for stream in streams
              if stream.get("codec_type") == "audio"]
    if len(videos) != 1:
        raise RenderError(f"Studio MP4 must have one video stream, found {len(videos)}")
    stream = videos[0]
    expected = (project.width, project.height)
    actual = (int(stream.get("width", 0)), int(stream.get("height", 0)))
    if actual != expected:
        raise RenderError(f"Studio storyboard size mismatch: expected {expected}, got {actual}")
    if stream.get("codec_name") != "h264" or stream.get("pix_fmt") != "yuv420p":
        raise RenderError("Studio storyboard requires H.264 yuv420p video")
    try:
        frame_rate = float(Fraction(str(stream.get("avg_frame_rate")
                                     or stream.get("r_frame_rate"))))
        frame_count = int(stream["nb_frames"])
    except (KeyError, ValueError, ZeroDivisionError) as exc:
        raise RenderError("Studio MP4 lacks verifiable FPS/frame metadata") from exc
    if abs(frame_rate - project.fps) > .005:
        raise RenderError(f"Studio storyboard FPS mismatch: expected {project.fps}, got {frame_rate}")
    if frame_count != timeline.total_frames:
        raise RenderError(
            f"Studio MP4 has {frame_count} frames; expected {timeline.total_frames}")
    try:
        video_duration = float(stream["duration"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RenderError("Studio MP4 lacks verifiable video duration") from exc
    if abs(video_duration - timeline.duration) > max(.025, .55 / project.fps):
        raise RenderError("Studio MP4 duration does not match its frame timeline")
    expects_audio = bool(project.audio.get("music")
                         or project.audio.get("voiceover")
                         or project.audio.get("sfx"))
    if expects_audio and (len(audios) != 1 or audios[0].get("codec_name") != "aac"):
        raise RenderError("Studio MP4 is missing its expected AAC audio stream")
    if not expects_audio and audios:
        raise RenderError("Studio manifest is silent but MP4 contains audio")

    thumb_w = 260
    thumb_h = round(thumb_w * project.height / project.width)
    if thumb_h > 490:
        thumb_h = 490
        thumb_w = max(100, round(thumb_h * project.width / project.height))
    margin, gap, label_h = 24, 16, 34
    num_cols = 3 if motion_strip else columns
    targets: list[tuple[int, str, float]] = []
    for scene, timing in zip(project.build(timeline), timeline.scenes):
        incoming = float(scene.meta.get("transition_duration", .30)) \
            if scene.meta.get("transition_in") not in (None, "cut") else 0.0
        duration = timing.frames / timeline.fps
        local_entry = min(max(.06, incoming + .04), max(.06, duration * .25))
        local_settled = min(max(local_entry, duration * .55), duration - .04)
        local_exit = max(local_settled, duration - .08)
        if motion_strip:
            samples = (("entry", local_entry), ("settled", local_settled),
                       ("exit", local_exit))
        else:
            samples = (("settled", local_settled),)
        for phase, local in samples:
            frame = min(timing.frames - 1, max(0, round(local * timeline.fps)))
            global_time = (timing.start_frame + frame + .5) / timeline.fps
            targets.append((timing.index, phase, global_time))

    rows = math.ceil(len(targets) / num_cols)
    cell_w, cell_h = thumb_w + 16, thumb_h + label_h
    canvas_w = 2 * margin + num_cols * cell_w + (num_cols - 1) * gap
    canvas_h = 2 * margin + rows * cell_h + (rows - 1) * gap
    sheet = Image.new("RGB", (canvas_w, canvas_h), "#121817")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    samples_report = []
    with tempfile.TemporaryDirectory(prefix="reels-studio-storyboard-") as temp:
        for index, (scene_index, phase, timestamp) in enumerate(targets):
            still = Path(temp) / f"{index:03d}.png"
            execute(["-ss", f"{timestamp:.6f}", "-i", str(video),
                     "-frames:v", "1",
                     "-vf", f"scale={thumb_w}:{thumb_h}:force_original_aspect_ratio=decrease",
                     "-update", "1", str(still)])
            if not still.is_file():
                raise RenderError(f"Cannot extract scene {scene_index + 1} ({phase})")
            with Image.open(still) as picture:
                tile = picture.convert("RGB")
            column, row = index % num_cols, index // num_cols
            x = margin + column * (cell_w + gap)
            y = margin + row * (cell_h + gap)
            sheet.paste(tile, (x + (cell_w - tile.width) // 2, y))
            draw.text((x + 4, y + thumb_h + 8),
                      f"SCENE {scene_index + 1:02d}  {phase.upper()}  {timestamp:.2f}s",
                      fill="#ECF2ED", font=font)
            samples_report.append({"scene": scene_index + 1, "phase": phase,
                                  "timestamp_seconds": round(timestamp, 3)})
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, optimize=True)
    return {"output": str(output), "scenes": len(timeline.scenes),
            "mode": "motion_strip" if motion_strip else "settled",
            "samples": samples_report, "video": str(video),
            "frames_verified": frame_count,
            "human_review_required": True}
