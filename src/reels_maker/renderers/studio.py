"""Studio render pipeline: graph -> frames -> H.264 (+ optional audio mix)."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from time import perf_counter
from typing import Callable
from fractions import Fraction

from ..audio_mix import mux_audio
from ..ffmpeg import RenderError, require_tool
from ..spec import Project
from ..studio import PROFILES, StudioProject
from .scene import RenderOptions, SceneRenderer

CRF = {"preview": 23, "review": 20, "final": 17, "high-motion": 17}
PRESET = {"preview": "veryfast", "review": "medium", "final": "slow",
          "high-motion": "slow"}
SLUG = re.compile(r"[^a-z0-9-]+")


def _output_path(project: StudioProject, profile: str | None,
                 output: str | Path | None) -> Path:
    if output:
        return Path(output).resolve()
    suffix = profile or "custom"
    brand = project.brand or "studio"
    directory = project.root / "renders" / brand
    directory.mkdir(parents=True, exist_ok=True)
    name = SLUG.sub("-", project.name.lower()).strip("-") or "video"
    return directory / f"{name}-{suffix}.mp4"


def _audio_config(project: StudioProject):
    voice = project.audio.get("voiceover")
    music = project.audio.get("music")
    if isinstance(voice, str):
        voice = {"file": voice}
    if isinstance(music, str):
        music = {"file": music}
    voice_path = Path(voice["file"]) if voice and voice.get("file") else None
    music_path = Path(music["file"]) if music and music.get("file") else None
    if voice_path and not voice_path.is_file():
        raise RenderError(f"Voiceover file does not exist: {voice_path}")
    if music_path and not music_path.is_file():
        raise RenderError(f"Music file does not exist: {music_path}")
    sfx_tracks = list(project.audio.get("sfx") or [])
    for track in sfx_tracks:
        path = Path(track.get("file") or track.get("path") or "")
        if not path.is_file():
            raise RenderError(f"SFX file does not exist: {path}")
    return voice, music, voice_path, music_path, sfx_tracks


def _mux(project: StudioProject, silent: Path, destination: Path,
         duration: float) -> dict:
    voice, music, voice_path, music_path, sfx_tracks = _audio_config(project)
    if voice_path is None and music_path is None and not sfx_tracks:
        shutil.move(str(silent), str(destination))
        return {"audio": False}
    voice_cfg = dict(voice or {})
    music_cfg = dict(music or {})
    for cfg in (voice_cfg, music_cfg):
        cfg.pop("file", None)
    dummy = Project(
        name=project.name, width=project.width, height=project.height,
        fps=project.fps, scenes=[], music=music_cfg or None,
        branding={}, output=str(destination), brand=project.brand,
        voiceover=voice_cfg or None)
    result = mux_audio(dummy, silent, destination, music_path, voice_path,
                       duration, sfx_tracks=sfx_tracks)
    return {"audio": True, **result}


def render_studio(project: StudioProject, *, output: str | Path | None = None,
                  profile: str | None = None, supersample: int | None = None,
                  progress: Callable[[dict], None] | None = None) -> dict:
    """Render a studio project and return a JSON-friendly delivery report."""
    if profile and profile not in PROFILES:
        raise RenderError(f"Unknown export profile {profile!r}")
    effective_profile = profile or project.export.get("profile")
    if effective_profile in PROFILES and (
            PROFILES[effective_profile]["width"] != project.width
            or PROFILES[effective_profile]["height"] != project.height
            or PROFILES[effective_profile]["fps"] != project.fps):
        raise RenderError(
            "Manifest was loaded for a different profile. Reload it with "
            "--profile so tokens and stills match the delivery resolution.")
    timeline = project.timeline()
    built = project.build(timeline)
    if supersample is None:
        supersample = 2 if project.height >= 1600 else 1
    renderer = SceneRenderer(
        project.width, project.height, project.tokens, project.fonts,
        options=RenderOptions(supersample=supersample))
    destination = _output_path(project, effective_profile, output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    require_tool("ffmpeg")
    # Stage beside the final output so the final os.replace is atomic on the
    # same filesystem. A failed encode/mux never destroys a previous delivery.
    scratch = Path(tempfile.mkdtemp(prefix=".reels-studio-",
                                    dir=str(destination.parent)))
    silent = scratch / "silent.mp4"
    staged = scratch / "delivery.mp4"
    codec = project.export.get("codec", "libx264")
    crf = int(project.export.get("crf", CRF.get(effective_profile or "final", 18)))
    preset = str(project.export.get("preset", PRESET.get(effective_profile or "final",
                                                        "medium")))
    command = [
        require_tool("ffmpeg"), "-hide_banner", "-nostdin", "-y",
        "-f", "rawvideo", "-pix_fmt", "bgra",
        "-s", f"{project.width}x{project.height}", "-r", str(project.fps),
        "-i", "-", "-an", "-c:v", codec, "-preset", preset,
        "-crf", str(crf), "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(silent),
    ]
    started = perf_counter()
    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.PIPE)
        written = 0
        try:
            for scene, timing in zip(built, timeline.scenes):
                for frame in range(timing.frames):
                    time = frame / project.fps
                    image = renderer.render(scene, min(time, scene.duration))
                    try:
                        process.stdin.write(
                            image.convert("RGBA").tobytes("raw", "BGRA"))
                    except (BrokenPipeError, OSError) as exc:
                        stderr = process.stderr.read().decode("utf-8", "replace") \
                            if process.stderr else ""
                        raise RenderError(
                            f"FFmpeg stopped while writing frame {written}: "
                            f"{stderr[-2000:]}") from exc
                    written += 1
                    if progress and (written % max(1, project.fps) == 0
                                     or written == timeline.total_frames):
                        progress({"frames": written,
                                  "total": timeline.total_frames,
                                  "scene": scene.index + 1})
        finally:
            if process.stdin:
                process.stdin.close()
            stderr = process.stderr.read().decode("utf-8", "replace") \
                if process.stderr else ""
            code = process.wait()
            if process.stderr:
                process.stderr.close()
        if code:
            raise RenderError(f"FFmpeg exited {code}: {stderr[-4000:]}")
        if written != timeline.total_frames:
            raise RenderError(f"Encoded {written} of {timeline.total_frames} frames")
        audio_result = _mux(project, silent, staged, timeline.duration)
        export_quality = _verify_studio_output(staged, project, timeline)
        os.replace(staged, destination)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    elapsed = perf_counter() - started
    return {
        "schema_version": 1,
        "status": "ok",
        "ok": True,
        "output": str(destination),
        "name": project.name,
        "brand": project.brand,
        "style": project.style,
        "width": project.width,
        "height": project.height,
        "fps": project.fps,
        "frames": timeline.total_frames,
        "duration": timeline.duration,
        "profile": effective_profile or "custom",
        "supersample": supersample,
        "crf": crf,
        "codec": codec,
        "bytes": destination.stat().st_size,
        "render_seconds": round(elapsed, 2),
        "fps_rendered": round(timeline.total_frames / elapsed, 2),
        "audio": audio_result,
        "export_quality": export_quality,
        "scenes": [scene.to_dict() for scene in built],
        "warnings": [issue for scene in built
                     for issue in scene.choreography.warnings],
        "project_warnings": list(project.warnings),
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


def _verify_studio_output(path: Path, project: StudioProject,
                          timeline) -> dict:
    metadata = probe_output(path)
    expected_fps = float(project.fps)
    try:
        actual_fps = float(Fraction(str(metadata["fps"])))
    except (ValueError, ZeroDivisionError, TypeError) as exc:
        raise RenderError("Cannot verify exported FPS") from exc
    if (metadata["width"], metadata["height"]) != (project.width, project.height):
        raise RenderError("Export dimensions do not match the studio project")
    if metadata["codec"] != "h264" or metadata["pix_fmt"] != "yuv420p":
        raise RenderError("Studio export must be H.264 with yuv420p pixels")
    if abs(actual_fps - expected_fps) > .005:
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
    return {"status": "pass", **metadata,
            "expected_frames": timeline.total_frames,
            "expected_duration": timeline.duration}
