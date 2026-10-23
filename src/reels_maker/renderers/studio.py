"""Studio render pipeline: graph -> frames -> H.264 (+ optional audio mix).

An optional per-scene segment cache (opt-in ``cache_dir``) stores encoded
scene parts keyed by a signature of scene data, tokens and timings. A cache
hit streams the stored segment unchanged; scenes are re-encoded only when the
signature differs, mirroring the classic renderer's cache contract.
"""
from __future__ import annotations

import hashlib
import json
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


def _font_signature(fonts) -> dict:
    """Cache signature for the resolved font configuration."""
    signature = {"family": fonts.family}
    for weight in ("regular", "bold"):
        path = Path(fonts.path(weight)).resolve()
        signature[weight] = [str(path), path.stat().st_mtime_ns]
    return signature


def _cache_signature(project: StudioProject, profile: str | None,
                     supersample: int, codec: str, crf: int, preset: str,
                     timeline, built) -> str:
    """Deterministic signature: payload, tokens, fonts and per-scene data."""
    payload = {
        "width": project.width, "height": project.height, "fps": project.fps,
        "profile": profile, "codec": codec, "crf": crf, "preset": preset,
        "supersample": supersample, "style": project.style,
        "brand": project.brand, "name": project.name,
        "tokens": project.tokens.to_dict(),
        "fonts": _font_signature(project.fonts),
        "scenes": [
            {"scene": scene, "frames": timing.frames,
             "transition_in": item.meta.get("transition_in"),
             "transition_duration": item.meta.get("transition_duration")}
            for scene, timing, item in zip(project.scenes, timeline.scenes,
                                           built)],
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                     default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _encode_studio_scene(project: StudioProject, renderer, built, timing,
                         dest: Path, *, codec: str, crf: int, preset: str,
                         frames_done: int, total_frames: int,
                         progress: Callable[[dict], None] | None) -> int:
    """Encode one scene's frames into a standalone stream-copyable MP4."""
    command = [
        require_tool("ffmpeg"), "-hide_banner", "-nostdin", "-y",
        "-f", "rawvideo", "-pix_fmt", "bgra",
        "-s", f"{project.width}x{project.height}", "-r", str(project.fps),
        "-i", "-", "-an", "-c:v", codec, "-preset", preset,
        "-crf", str(crf), "-pix_fmt", "yuv420p", str(dest),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE)
    written = 0
    try:
        try:
            for frame in range(timing.frames):
                time = frame / project.fps
                image = renderer.render(built, min(time, built.duration))
                try:
                    process.stdin.write(
                        image.convert("RGBA").tobytes("raw", "BGRA"))
                except (BrokenPipeError, OSError) as exc:
                    stderr = process.stderr.read().decode("utf-8", "replace") \
                        if process.stderr else ""
                    raise RenderError(
                        f"FFmpeg stopped while writing frame "
                        f"{frames_done + written}: {stderr[-2000:]}") from exc
                written += 1
                if progress and (written % max(1, project.fps) == 0
                                 or frames_done + written == total_frames):
                    progress({"frames": frames_done + written,
                              "total": total_frames,
                              "scene": built.index + 1})
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
        if written != timing.frames:
            raise RenderError(f"Encoded {written} of {timing.frames} frames")
    except Exception:
        if process.poll() is None:
            process.kill()
        process.wait()
        raise
    finally:
        if process.stderr and not process.stderr.closed:
            process.stderr.close()
    return written


def render_studio(project: StudioProject, *, output: str | Path | None = None,
                  profile: str | None = None, supersample: int | None = None,
                  cache_dir: str | Path | None = None,
                  progress: Callable[[dict], None] | None = None) -> dict:
    """Render a studio project and return a JSON-friendly delivery report.

    With ``cache_dir`` the render reuses per-scene H.264 segments keyed by a
    signature of scene data, tokens, fonts and encoder settings; unchanged
    scenes stream-copy from cache instead of re-rendering frames.
    """
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
    cache_root = Path(cache_dir).resolve() if cache_dir else None
    if cache_root is not None:
        cache_root.mkdir(parents=True, exist_ok=True)
    cache_signature = _cache_signature(project, effective_profile, supersample,
                                       codec, crf, preset, timeline, built)
    started = perf_counter()
    try:
        from ..renderer import _join
        parts: list[Path] = []
        frames_done = 0
        cache_hits = 0
        encodes = 0
        for scene, timing, item in zip(project.scenes, timeline.scenes, built):
            part = scratch / f"scene-{item.index}.mp4"
            key = f"{cache_signature}-{item.index}"
            cached = cache_root / f"{key}.mp4" if cache_root else None
            if cached is not None and cached.is_file() \
                    and cached.stat().st_size > 0:
                shutil.copyfile(cached, part)
                cache_hits += 1
            else:
                encoded = _encode_studio_scene(
                    project, renderer, item, timing, scratch / "part.mp4",
                    codec=codec, crf=crf, preset=preset,
                    frames_done=frames_done,
                    total_frames=timeline.total_frames,
                    progress=progress)
                encodes += 1
                if encoded != timing.frames:  # defensive; encoder raises first
                    raise RenderError(
                        f"Scene {item.index + 1}: encoded {encoded} of "
                        f"{timing.frames} frames")
                part = scratch / "part.mp4"
                if cached is not None:
                    # Atomic publication avoids half-written cache objects.
                    os.replace(part, cached)
                    part = cached
            frames_done += timing.frames
            parts.append(part)
        _join(parts, silent, scratch)
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
        "cache_hits": cache_hits,
        "cache_misses": encodes,
        "cache_signature": (cache_signature[:12] if cache_root else None),
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
