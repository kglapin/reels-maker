"""Studio render pipeline: graph -> frames -> H.264 (+ optional audio mix).

A default-on per-scene segment cache stores encoded scene parts by render
settings, scene data and referenced asset metadata. Unchanged scenes are reused
without copying their cached files; edited scenes are re-encoded independently.
"""
from __future__ import annotations

import errno
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
STUDIO_CACHE_SCHEMA = 2


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


def _icon_provenance(scenes) -> list[dict]:
    from ..icon_library import provenance
    records: dict[tuple, dict] = {}
    seen: set[tuple] = set()
    for scene in scenes:
        pending = list(scene.nodes)
        while pending:
            node = pending.pop()
            pending.extend(node.children or [])
            if node.kind != "icon":
                continue
            props = node.props
            signature = tuple(repr(value) for value in (
                props["library"], props["name"], props.get("style", "outline"),
                props.get("weight", 400), props.get("fill", False),
                props.get("grade", 0), props.get("optical_size", 24),
            ))
            if signature in seen:
                continue
            seen.add(signature)
            record = provenance(
                str(props["library"]), str(props["name"]),
                style=str(props.get("style", "outline")),
                cache_dir=props.get("cache_dir"),
                offline=bool(props.get("offline", False)),
                weight=props.get("weight", 400),
                fill=props.get("fill", False),
                grade=props.get("grade", 0),
                optical_size=props.get("optical_size", 24),
            )
            key = (record["provider"], record["asset_id"], record["style"],
                   record["source_url"])
            records[key] = record
    return [records[key] for key in sorted(records)]


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


def _hash_payload(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                     default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _cache_signature(project: StudioProject, profile: str | None,
                     supersample: int, codec: str, crf: int, preset: str,
                     timeline, built, *,
                     font_signature: dict | None = None) -> str:
    """Aggregate project signature retained for reporting and diagnostics."""
    payload = {
        "width": project.width, "height": project.height, "fps": project.fps,
        "profile": profile, "codec": codec, "crf": crf, "preset": preset,
        "supersample": supersample, "style": project.style,
        "brand": project.brand, "name": project.name,
        "tokens": project.tokens.to_dict(),
        "fonts": font_signature or _font_signature(project.fonts),
        "cache_schema": STUDIO_CACHE_SCHEMA,
        "transition_engine_version": 1,
        "scenes": [
            {"scene": scene, "frames": timing.frames,
             "transition_in": item.meta.get("transition_in"),
             "transition_duration": item.meta.get("transition_duration")}
            for scene, timing, item in zip(project.scenes, timeline.scenes,
                                           built)],
    }
    return _hash_payload(payload)


def _cache_settings_signature(project: StudioProject, profile: str | None,
                              supersample: int, codec: str, crf: int,
                              preset: str, font_signature: dict) -> str:
    """Settings shared by every scene cache entry."""
    return _hash_payload({
        "cache_schema": STUDIO_CACHE_SCHEMA,
        "transition_engine_version": 1,
        "width": project.width, "height": project.height, "fps": project.fps,
        "profile": profile, "codec": codec, "crf": crf, "preset": preset,
        "supersample": supersample, "style": project.style,
        "brand": project.brand,
        "tokens": project.tokens.to_dict(),
        "fonts": font_signature,
    })


_ASSET_PATH_FIELDS = frozenset({
    "asset", "file", "image", "logo", "mesh_path", "path", "photo",
    "photo_source", "photos", "video_source",
})


def _iter_asset_paths(value, *, path_field: bool = False):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _iter_asset_paths(
                child, path_field=key in _ASSET_PATH_FIELDS)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _iter_asset_paths(child, path_field=path_field)
    elif path_field and isinstance(value, str):
        yield value


def _asset_path(project: StudioProject, value: str) -> Path:
    if value.startswith("shared://"):
        return (project.root / "shared_media"
                / value.removeprefix("shared://")).resolve()
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    if value.startswith("brands/"):
        return (project.root / path).resolve()
    brand_root = (project.root / "brands" / project.brand
                  if project.brand else project.path.parent)
    return (brand_root / path).resolve()


def _asset_fingerprints(project: StudioProject, scene: dict, built) -> list[dict]:
    """Return cheap stat signatures for local visual assets used by a scene."""
    structures = [scene, built.background]
    for node in built.nodes:
        structures.extend(child.props for child in node.flatten())
    paths = set()
    for structure in structures:
        for value in _iter_asset_paths(structure):
            try:
                path = _asset_path(project, value)
                if path.is_file():
                    paths.add(path)
            except (OSError, RuntimeError, ValueError):
                continue
    signatures = []
    for path in sorted(paths, key=str):
        try:
            stat = path.stat()
        except OSError:
            continue
        signatures.append({
            "path": str(path),
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
        })
    return signatures


def _publish_cache_segment(part: Path, cached: Path) -> None:
    """Publish atomically even when output and cache are on different volumes."""
    try:
        os.replace(part, cached)
        return
    except OSError as exc:
        if exc.errno != errno.EXDEV:
            raise

    staged = None
    try:
        with tempfile.NamedTemporaryFile(
                prefix=f".{cached.name}.", suffix=".tmp",
                dir=str(cached.parent), delete=False) as handle:
            staged = Path(handle.name)
        shutil.copyfile(part, staged)
        os.replace(staged, cached)
        part.unlink()
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)


def _scene_cache_key(settings_signature: str, project: StudioProject,
                     index: int, scene: dict, timing, built,
                     next_scene=None) -> str:
    """Hash only the inputs that can change this encoded scene segment."""
    payload = {
        "settings": settings_signature,
        "index": index,
        "seed": getattr(built.context, "seed", index * 17 + 3),
        "scene": scene,
        "frames": timing.frames,
        "transition_in": built.meta.get("transition_in"),
        "transition_duration": built.meta.get("transition_duration"),
        "assets": _asset_fingerprints(project, scene, built),
    }
    transition_out = scene.get("transition_out")
    if transition_out and next_scene is not None:
        payload["outgoing_dependency"] = {
            "transition": transition_out,
            "index": next_scene.index,
            "scene": next_scene.scene,
            "seed": getattr(
                next_scene.context, "seed", next_scene.index * 17 + 3),
            "transition_in": next_scene.meta.get("transition_in"),
            "transition_duration": next_scene.meta.get("transition_duration"),
            "assets": _asset_fingerprints(
                project, next_scene.scene, next_scene),
        }
    return _hash_payload(payload)


def _encode_studio_scene(project: StudioProject, renderer, built, timing,
                         dest: Path, *, codec: str, crf: int, preset: str,
                         frames_done: int, total_frames: int,
                         progress: Callable[[dict], None] | None,
                         next_scene=None, transition: dict | None = None,
                         metrics: dict | None = None) -> int:
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
    render_seconds = 0.0
    frame_write_seconds = 0.0
    transition_renderer = None
    transition_frames = 0
    transition_start = timing.frames
    incoming_frame = None
    if next_scene is not None and transition is not None:
        from .transition_engine import transition_frame
        transition_renderer = transition_frame
        transition_frames = max(2, round(
            float(transition.get("duration", .55)) * project.fps))
        transition_frames = min(transition_frames, timing.frames)
        transition_start = timing.frames - transition_frames
    try:
        try:
            for frame in range(timing.frames):
                time = frame / project.fps
                render_started = perf_counter()
                image = renderer.render(built, min(time, built.duration))
                if transition_renderer is not None and frame >= transition_start:
                    progress_t = ((frame - transition_start)
                                  / max(1, transition_frames - 1))
                    # Scene B starts from the same frame throughout this
                    # transition, so render it once and reuse its pixels.
                    if incoming_frame is None:
                        incoming_frame = renderer.render(next_scene, 0.0)
                    image = transition_renderer(
                        image, incoming_frame, progress_t,
                        effect=transition.get("type", "color-takeover"),
                        color=transition.get("color", "#47A013"),
                        anchor=tuple(transition.get("anchor", (.5, .5))),
                        direction=transition.get("direction", "left"))
                render_seconds += perf_counter() - render_started
                write_started = perf_counter()
                try:
                    process.stdin.write(
                        image.convert("RGBA").tobytes("raw", "BGRA"))
                except (BrokenPipeError, OSError) as exc:
                    stderr = process.stderr.read().decode("utf-8", "replace") \
                        if process.stderr else ""
                    raise RenderError(
                        f"FFmpeg stopped while writing frame "
                        f"{frames_done + written}: {stderr[-2000:]}") from exc
                frame_write_seconds += perf_counter() - write_started
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
    if metrics is not None:
        metrics["frame_render_seconds"] = render_seconds
        metrics["frame_pipe_write_seconds"] = frame_write_seconds
        metrics["frames_rendered"] = written
    return written


def render_studio(project: StudioProject, *, output: str | Path | None = None,
                  profile: str | None = None, supersample: int | None = None,
                  cache_dir: str | Path | None = None, cache: bool = True,
                  progress: Callable[[dict], None] | None = None) -> dict:
    """Render a studio project and return a JSON-friendly delivery report.

    Per-scene H.264 caching is enabled by default under
    .cache/reels-maker/studio. Set cache=False to disable it, or pass
    cache_dir to select a different cache directory.
    """
    if profile and profile not in PROFILES:
        raise RenderError(f"Unknown export profile {profile!r}")
    overall_started = perf_counter()
    effective_profile = profile or project.export.get("profile")
    if effective_profile in PROFILES and (
            PROFILES[effective_profile]["width"] != project.width
            or PROFILES[effective_profile]["height"] != project.height
            or PROFILES[effective_profile]["fps"] != project.fps):
        raise RenderError(
            "Manifest was loaded for a different profile. Reload it with "
            "--profile so tokens and stills match the delivery resolution.")
    build_started = perf_counter()
    timeline = project.timeline()
    built = project.build(timeline)
    build_seconds = perf_counter() - build_started
    if supersample is None:
        supersample = 2 if project.height >= 1600 else 1
    if any("camera_canvas" in scene for scene in project.scenes):
        from .camera_canvas import CameraCanvasRenderer
        renderer = CameraCanvasRenderer(project)
    else:
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
    cache_root = None
    cache_signature = None
    settings_signature = None
    cache_setup_started = perf_counter()
    if cache:
        cache_root = (
            Path(cache_dir).resolve() if cache_dir is not None else
            (project.root / ".cache" / "reels-maker" / "studio").resolve())
        cache_root.mkdir(parents=True, exist_ok=True)
        font_signature = _font_signature(project.fonts)
        cache_signature = _cache_signature(
            project, effective_profile, supersample, codec, crf, preset,
            timeline, built, font_signature=font_signature)
        settings_signature = _cache_settings_signature(
            project, effective_profile, supersample, codec, crf, preset,
            font_signature)
    cache_setup_seconds = perf_counter() - cache_setup_started
    started = perf_counter()
    try:
        from ..renderer import _join
        parts: list[Path] = []
        frames_done = 0
        cache_hits = 0
        encodes = 0
        scene_encoding_seconds = 0.0
        frame_render_seconds = 0.0
        frame_pipe_write_seconds = 0.0
        video_decode_seconds = 0.0
        video_decode_calls = 0
        video_decoded_frames = 0
        scene_timings = []
        scene_loop_started = perf_counter()
        for index, (scene, timing, item) in enumerate(
                zip(project.scenes, timeline.scenes, built)):
            scene_started = perf_counter()
            part = scratch / f"scene-{item.index}.mp4"
            next_scene = built[index + 1] if index + 1 < len(built) else None
            key = (_scene_cache_key(
                settings_signature, project, index, scene, timing, item,
                next_scene=next_scene) if cache_root is not None else None)
            cached = cache_root / f"{key}.mp4" if cache_root is not None else None
            if cached is not None and cached.is_file() \
                    and cached.stat().st_size > 0:
                # The concat demuxer reads cache objects directly; no full-file
                # copy is needed on a warm render.
                part = cached
                cache_hits += 1
                scene_timings.append({
                    "scene": item.index + 1, "cache_hit": True,
                    "elapsed_seconds": round(perf_counter() - scene_started, 4),
                })
            else:
                scene_metrics = {}
                from .canvas import collect_video_decode_metrics
                encode_started = perf_counter()
                with collect_video_decode_metrics() as video_metrics:
                    encoded = _encode_studio_scene(
                        project, renderer, item, timing, part,
                        codec=codec, crf=crf, preset=preset,
                        frames_done=frames_done,
                        total_frames=timeline.total_frames,
                        progress=progress,
                        next_scene=next_scene,
                        transition=scene.get("transition_out"),
                        metrics=scene_metrics)
                encode_seconds = perf_counter() - encode_started
                scene_encoding_seconds += encode_seconds
                frame_render_seconds += scene_metrics.get(
                    "frame_render_seconds", 0.0)
                frame_pipe_write_seconds += scene_metrics.get(
                    "frame_pipe_write_seconds", 0.0)
                video_decode_seconds += video_metrics["video_decode_seconds"]
                video_decode_calls += video_metrics["video_decode_calls"]
                video_decoded_frames += video_metrics["video_decoded_frames"]
                encodes += 1
                if encoded != timing.frames:  # defensive; encoder raises first
                    raise RenderError(
                        f"Scene {item.index + 1}: encoded {encoded} of "
                        f"{timing.frames} frames")
                if cached is not None:
                    # Atomic publication avoids half-written cache objects.
                    _publish_cache_segment(part, cached)
                    part = cached
                scene_timings.append({
                    "scene": item.index + 1, "cache_hit": False,
                    "elapsed_seconds": round(perf_counter() - scene_started, 4),
                    "encode_seconds": round(encode_seconds, 4),
                    "frame_render_seconds": round(
                        scene_metrics.get("frame_render_seconds", 0.0), 4),
                    "video_decode_calls": video_metrics["video_decode_calls"],
                    "video_decoded_frames": video_metrics["video_decoded_frames"],
                    "video_decode_seconds": round(
                        video_metrics["video_decode_seconds"], 4),
                    "frames": scene_metrics.get("frames_rendered", 0),
                })
            frames_done += timing.frames
            parts.append(part)
        scene_loop_seconds = perf_counter() - scene_loop_started
        join_started = perf_counter()
        _join(parts, silent, scratch, max_frames=timeline.total_frames)
        join_seconds = perf_counter() - join_started
        audio_started = perf_counter()
        audio_result = _mux(project, silent, staged, timeline.duration)
        audio_mux_seconds = perf_counter() - audio_started
        verify_started = perf_counter()
        export_quality = _verify_studio_output(staged, project, timeline)
        verification_seconds = perf_counter() - verify_started
        os.replace(staged, destination)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    elapsed = perf_counter() - started
    total_elapsed = perf_counter() - overall_started
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
        "timings_seconds": {
            "scene_build": round(build_seconds, 4),
            "cache_setup": round(cache_setup_seconds, 4),
            "scene_encoding": round(scene_encoding_seconds, 4),
            "scene_loop": round(scene_loop_seconds, 4),
            "frame_render": round(frame_render_seconds, 4),
            "frame_pipe_write": round(frame_pipe_write_seconds, 4),
            "video_decode": round(video_decode_seconds, 4),
            "video_decode_calls": video_decode_calls,
            "video_decoded_frames": video_decoded_frames,
            "concat": round(join_seconds, 4),
            "audio_mux": round(audio_mux_seconds, 4),
            "verification": round(verification_seconds, 4),
            "render_pipeline": round(elapsed, 4),
            "total": round(total_elapsed, 4),
        },
        "scene_timings": scene_timings,
        "fps_rendered": round(timeline.total_frames / elapsed, 2),
        "audio": audio_result,
        "export_quality": export_quality,
        "cache_hits": cache_hits,
        "cache_misses": encodes,
        "cache_signature": (cache_signature[:12] if cache_signature else None),
        "icon_provenance": _icon_provenance(built),
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
    return {"status": "pass", **metadata,
            "expected_frames": timeline.total_frames,
            "expected_duration": timeline.duration}


FORMAT_MATRIX_DIMENSIONS: dict[str, tuple[int, int]] = {
    "portrait": (360, 640),
    "square": (480, 480),
    "landscape": (640, 360),
    "portrait_hd": (1080, 1920),
    "square_hd": (1080, 1080),
    "landscape_hd": (1920, 1080),
}


def render_master_format_matrix(
    project: StudioProject,
    output_dir: str | Path,
    *,
    formats: tuple[str, ...] = ("portrait", "square", "landscape"),
    supersample: int = 1,
) -> dict:
    """Render and verify a Studio project across portrait/square/landscape formats (MD-405)."""
    from dataclasses import replace
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
