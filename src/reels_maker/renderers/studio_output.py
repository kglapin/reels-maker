"""Studio output probing, delivery verification and format matrix rendering."""
from __future__ import annotations

import subprocess
from fractions import Fraction
from pathlib import Path

from ..ffmpeg import RenderError
from ..studio import StudioProject

FORMAT_MATRIX_DIMENSIONS: dict[str, tuple[int, int]] = {
    "portrait": (360, 640),
    "square": (480, 480),
    "landscape": (640, 360),
    "portrait_hd": (1080, 1920),
    "square_hd": (1080, 1080),
    "landscape_hd": (1920, 1080),
}

def probe_output(path: Path) -> dict:
    from ..ffmpeg import probe
    info = probe(Path(path))
    videos = [stream for stream in info["streams"]
              if stream.get("codec_type") == "video"]
    audios = [stream for stream in info["streams"]
              if stream.get("codec_type") == "audio"]
    if len(videos) != 1:
        raise RenderError(f"Expected one video stream in {path}, got {len(videos)}")
    video = videos[0]
    audio = audios[0] if audios else None
    return {
        "width": int(video["width"]), "height": int(video["height"]),
        "fps": video.get("avg_frame_rate") or video.get("r_frame_rate"),
        "frames": int(video.get("nb_frames", 0)),
        "codec": video.get("codec_name"),
        "pix_fmt": video.get("pix_fmt"),
        "duration": float(info["format"].get("duration", 0)),
        "video_duration": float(video.get("duration", 0)),
        "audio_streams": len(audios),
        "audio_codec": audio.get("codec_name") if audio else None,
        "sample_rate": audio.get("sample_rate") if audio else None,
    }


def _luma_series(path: Path, *, width: int = 16,
                 height: int = 16) -> list[float]:
    """Mean luminance per frame, decoded at thumbnail size for flash checks."""
    from ..ffmpeg import require_tool
    completed = subprocess.run(
        [require_tool("ffmpeg"), "-v", "error", "-i", str(path),
         "-vf", f"scale={width}:{height},format=gray",
         "-f", "rawvideo", "-"],
        capture_output=True, check=False)
    if completed.returncode:
        raise RenderError(
            f"Cannot decode {path} for flash check: "
            f"{completed.stderr.decode('utf-8', 'replace')[-800:]}")
    data = completed.stdout
    stride = width * height
    count = len(data) // stride
    return [sum(data[i * stride:(i + 1) * stride]) / (stride * 255.0)
            for i in range(count)]


# Memoized by (path, size, mtime): repeat verifications of an unchanged
# file (studio-qa re-runs, warm renders) skip the full decode.
_FLASH_MEMO: dict[tuple[str, int, int], dict] = {}


def _flash_check(path: Path) -> dict:
    """Advisory blink detection on the encoded file.

    A hard cut produces a monotonic luminance step; a blink reverses
    direction within a frame or two. Only reversals where both deltas
    exceed the threshold count, so ordinary scene changes stay silent.
    """
    try:
        stat = path.stat()
    except OSError:
        stat = None
    memo_key = ((str(path), stat.st_size, stat.st_mtime_ns)
                if stat is not None else None)
    if memo_key is not None and memo_key in _FLASH_MEMO:
        return dict(_FLASH_MEMO[memo_key])
    luma = _luma_series(path)
    if len(luma) < 3:
        return {"status": "pass", "frames": len(luma), "blink_frames": 0,
                "max_delta": 0.0}
    threshold = 0.20
    deltas = [luma[i + 1] - luma[i] for i in range(len(luma) - 1)]
    blink_frames = sum(
        1 for i in range(1, len(deltas))
        if (deltas[i - 1] > threshold and deltas[i] < -threshold)
        or (deltas[i - 1] < -threshold and deltas[i] > threshold))
    result = {"status": "warn" if blink_frames else "pass",
              "frames": len(luma), "blink_frames": blink_frames,
              "max_delta": round(max(abs(d) for d in deltas), 4)}
    if memo_key is not None:
        _FLASH_MEMO[memo_key] = result
        while len(_FLASH_MEMO) > 64:
            _FLASH_MEMO.pop(next(iter(_FLASH_MEMO)))
    return result


def _verify_studio_output(path: Path, project: StudioProject,
                          timeline, *, skip_flash: bool = False) -> dict:
    metadata = probe_output(path)
    expected_fps = float(project.fps)
    try:
        actual_fps = float(Fraction(str(metadata["fps"])))
    except (ValueError, ZeroDivisionError, TypeError) as exc:
        raise RenderError("Cannot verify exported FPS") from exc
    if (metadata["width"], metadata["height"]) != (project.width, project.height):
        raise RenderError("Export dimensions do not match the studio project")
    if (metadata["codec"] != "h264"
            or metadata["pix_fmt"] not in ("yuv420p", "yuv420p10le")):
        raise RenderError("Studio export must be H.264 with yuv420p pixels")
    if abs(actual_fps - expected_fps) > .02:
        raise RenderError(f"Export FPS mismatch: expected {expected_fps}, got {actual_fps}")
    if metadata["frames"] != timeline.total_frames:
        raise RenderError(
            f"Export frame count mismatch: expected {timeline.total_frames}, "
            f"got {metadata['frames']}")
    if abs(metadata["video_duration"] - timeline.duration) > max(
            .025, .55 / project.fps):
        raise RenderError("Video track duration does not match the quantized timeline")
    expects_audio = bool(project.audio.get("music")
                         or project.audio.get("voiceover")
                         or project.audio.get("sfx"))
    if expects_audio and (metadata["audio_streams"] != 1
                          or metadata["audio_codec"] != "aac"):
        raise RenderError("Expected exactly one AAC soundtrack")
    if not expects_audio and metadata["audio_streams"]:
        raise RenderError("Silent studio project unexpectedly contains audio")
    if skip_flash:
        flash: dict = {"status": "skipped_warm", "frames": 0,
                       "blink_frames": 0, "max_delta": 0.0,
                       "note": "All scene segments served from cache; video "
                               "frames unchanged since the last verification."}
    else:
        flash = _flash_check(path)
    return {"status": "pass", **metadata,
            "flash_check": flash,
            "expected_frames": timeline.total_frames,
            "expected_duration": timeline.duration}


def render_master_format_matrix(
    project: StudioProject,
    output_dir: str | Path,
    *,
    formats: tuple[str, ...] = ("portrait", "square", "landscape"),
    supersample: int = 1,
) -> dict:
    """Render and verify a Studio project across portrait/square/landscape formats (MD-405)."""
    from dataclasses import replace
    from .studio import render_studio
    from ..qa.report import audit

    out_root = Path(output_dir).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    if not formats:
        raise RenderError("formats must not be empty")
    deliveries: dict[str, dict] = {}
    all_ok = True
    for fmt_name in formats:
        if fmt_name not in FORMAT_MATRIX_DIMENSIONS:
            raise RenderError(f"Unknown matrix format {fmt_name!r}")
        w, h = FORMAT_MATRIX_DIMENSIONS[fmt_name]
        scaled_tokens = project.tokens.with_canvas(w, h)
        variant_project = replace(
            project,
            width=w,
            height=h,
            tokens=scaled_tokens,
            export={**project.export, "profile": None, "preset": "ultrafast", "crf": 26},
        )
        timeline = variant_project.timeline()
        built = variant_project.build(timeline)
        qa = audit(variant_project, built, timeline, samples_per_scene=4)
        mp4_path = out_root / f"{project.name}-{fmt_name}.mp4"
        render_report = render_studio(
            variant_project, output=mp4_path, supersample=supersample
        )
        deliveries[fmt_name] = {
            "width": w,
            "height": h,
            "output": str(mp4_path),
            "qa_ok": qa["ok"],
            "qa_errors": qa["summary"]["errors"],
            "export_quality": render_report["export_quality"],
        }
        if not qa["ok"] or render_report["export_quality"]["status"] != "pass":
            all_ok = False
    return {
        "schema_version": 1,
        "ok": all_ok,
        "formats": list(formats),
        "deliveries": deliveries,
    }
