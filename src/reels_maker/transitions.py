"""Deliberate, opt-in FFmpeg xfade transitions. Hard cut is always the default."""
from pathlib import Path

from .ffmpeg import RenderError, execute
from .spec import Project

CURATED = {
    "dissolve": "fade",
    "dip_to_black": "fadeblack",
    "motion_wipe_left": "smoothleft",
    "motion_wipe_right": "smoothright",
}


def transition_plan(project: Project, frames: list[int]) -> list[dict]:
    steps = []
    for i in range(1, len(project.scenes)):
        config = project.scenes[i].get("transition_in") or {"type": "cut"}
        kind = config.get("type", "cut")
        count = config.get("frames", 0) if kind != "cut" else 0
        if count > min(frames[i - 1], frames[i]) // 3:
            raise RenderError(f"Scene {i}: transition exceeds a third of its shot")
        steps.append({"type": kind, "frames": count})
    return steps


def timeline_frames(frames: list[int], steps: list[dict]) -> int:
    return sum(frames) - sum(step["frames"] for step in steps)


def assemble(parts: list[Path], frames: list[int], fps: int,
             steps: list[dict], destination: Path) -> None:
    """Mix explicit transitions; normal stream-copy path stays untouched."""
    if len(parts) != len(frames) or len(steps) != len(parts) - 1:
        raise RenderError("Mismatched transition graph")
    if not any(step["type"] != "cut" for step in steps):
        raise RenderError("No xfade requested")
    arguments, filters = [], []
    for i, part in enumerate(parts):
        arguments += ["-i", str(part)]
        # setpts before xfade loses constant-frame-rate metadata in FFmpeg 7.
        filters.append(f"[{i}:v]settb=AVTB,format=yuv420p[v{i}]")
    previous, total = "v0", frames[0]
    for i, step in enumerate(steps, start=1):
        result = "out" if i == len(steps) else f"m{i}"
        if step["type"] == "cut":
            filters.append(f"[{previous}][v{i}]concat=n=2:v=1:a=0[{result}]")
            total += frames[i]
        else:
            overlap = step["frames"]
            offset = (total - overlap) / fps
            seconds = overlap / fps
            mode = CURATED[step["type"]]
            filters.append(f"[{previous}][v{i}]xfade=transition={mode}:"
                           f"duration={seconds:.8f}:offset={offset:.8f}[{result}]")
            total += frames[i] - overlap
        previous = result
    execute(arguments + ["-filter_complex", ";".join(filters), "-map",
                         f"[{previous}]", "-an", "-c:v", "libx264",
                         "-preset", "veryfast", "-crf", "20",
                         "-pix_fmt", "yuv420p", "-r", str(fps),
                         "-frames:v", str(total), "-movflags", "+faststart",
                         str(destination)])
