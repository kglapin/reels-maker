"""Technical media delivery gate for MP4/H.264 scene exports.

A successful ffmpeg subprocess does not prove the published video is complete.
Check the encoded stream (not just container duration) *before* atomic
publication, and return a stable machine-readable report for agents.
"""
from __future__ import annotations

from fractions import Fraction
from pathlib import Path

from .ffmpeg import RenderError, probe
from .spec import Project
from .transitions import timeline_frames, transition_plan


def _fps(stream: dict) -> float:
    rate = stream.get("avg_frame_rate") or stream.get("r_frame_rate")
    try:
        frames = Fraction(str(rate))
        if frames <= 0:
            raise ValueError("fps must be positive")
        return float(frames)
    except (ValueError, TypeError, ZeroDivisionError) as exc:
        raise RenderError(f"MP4 video stream has invalid average frame rate: {rate!r}") from exc


def expected_frame_count(project: Project) -> int:
    """Use the same cumulative quantization as the renderer."""
    from .renderer import _frame_counts  # avoid an import cycle
    frames = _frame_counts(project)
    return timeline_frames(frames, transition_plan(project, frames))


def verify_metadata(metadata: dict, project: Project, *,
                    expected_frames: int | None = None) -> dict:
    """Reject missing frames, altered resolution/FPS, codecs and audio errors."""
    streams = metadata.get("streams") or []
    videos = [s for s in streams if s.get("codec_type") == "video"]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    if len(videos) != 1:
        raise RenderError(f"MP4 must contain exactly one video stream; found {len(videos)}")
    video = videos[0]
    if (video.get("width"), video.get("height")) != (project.width, project.height):
        raise RenderError(
            "Export resolution mismatch: expected "
            f"{project.width}x{project.height}, got "
            f"{video.get('width')}x{video.get('height')}")
    if video.get("codec_name") != "h264" or video.get("pix_fmt") != "yuv420p":
        raise RenderError(
            "Export codec/pixel format mismatch: expected H.264 yuv420p")
    reported_fps = _fps(video)
    if abs(reported_fps - project.fps) > 0.005:
        raise RenderError(f"Export FPS mismatch: expected {project.fps}, got {reported_fps}")

    frames = expected_frames if expected_frames is not None else expected_frame_count(project)
    raw_count = video.get("nb_frames")
    try:
        count = int(raw_count)
    except (ValueError, TypeError) as exc:
        raise RenderError("Cannot verify exported frame count (nb_frames is missing)") from exc
    if count != frames:
        raise RenderError(
            f"Export frame count mismatch: expected {frames}, got {count}")
    ideal_duration = frames / project.fps
    video_duration = video.get("duration")
    if video_duration is None:
        raise RenderError("Cannot verify video track duration")
    try:
        track_duration = float(video_duration)
    except (TypeError, ValueError) as exc:
        raise RenderError("Invalid video track duration") from exc
    if abs(track_duration - ideal_duration) > max(.025, .55 / project.fps):
        raise RenderError("Export video track duration does not match expected frame timing")

    with_music = project.music is not None or project.voiceover is not None
    if with_music and len(audios) != 1:
        raise RenderError("Expected one audio stream but output is missing or duplicated")
    if not with_music and audios:
        raise RenderError("Unexpected audio in a silent project")
    if with_music and audios[0].get("codec_name") != "aac":
        raise RenderError("Expected AAC audio output")
    return {
        "status": "pass",
        "video_codec": "h264",
        "pixel_format": "yuv420p",
        "width": project.width,
        "height": project.height,
        "fps": project.fps,
        "frames_expected": frames,
        "frames_actual": count,
        "video_track_seconds": round(track_duration, 5),
        "audio_streams": len(audios),
    }


def verify_export(project: Project, video_file: Path) -> dict:
    file = Path(video_file)
    if not file.is_file() or file.stat().st_size < 1:
        raise RenderError(f"Export does not exist or is empty: {file}")
    return {"file": str(file.resolve()),
            **verify_metadata(probe(file), project)}
