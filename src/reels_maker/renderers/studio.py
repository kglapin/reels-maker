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
from ..ffmpeg import RenderError, drain_stderr, require_tool
from ..spec import Project
from ..studio import PROFILES, StudioProject
from .scene import RenderOptions, SceneRenderer

CRF = {"preview": 23, "review": 20, "final": 17, "high-motion": 17}
PRESET = {"preview": "veryfast", "review": "medium", "final": "slow",
          "high-motion": "slow"}
SLUG = re.compile(r"[^a-z0-9-]+")

from .studio_cache import (
    STUDIO_CACHE_SCHEMA, _font_signature, _hash_payload, _cache_signature,
    _cache_settings_signature, _iter_asset_paths, _asset_path, _ASSET_PATH_FIELDS,
    _asset_fingerprints, _publish_cache_segment, _scene_cache_key,
)
from .studio_output import (
    FORMAT_MATRIX_DIMENSIONS, probe_output, _verify_studio_output,
    render_master_format_matrix,
)

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


def _encode_studio_scene(project: StudioProject, renderer, built, timing,
                         dest: Path, *, codec: str, crf: int, preset: str,
                         frames_done: int, total_frames: int,
                         progress: Callable[[dict], None] | None,
                         next_scene=None, transition: dict | None = None,
                         metrics: dict | None = None) -> int:
    """Encode one scene's frames into a standalone stream-copyable MP4."""
    command = [
        require_tool("ffmpeg"), "-hide_banner", "-nostdin", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{project.width}x{project.height}", "-r", str(project.fps),
        "-i", "-", "-an", "-c:v", codec, "-preset", preset,
        "-crf", str(crf), "-pix_fmt", "yuv420p", str(dest),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE)
    stderr_text = drain_stderr(process)
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
                    raw_frame = (
                        image.tobytes("raw", "RGB")
                        if image.mode == "RGB"
                        else image.convert("RGB").tobytes("raw", "RGB")
                    )
                    process.stdin.write(raw_frame)
                except (BrokenPipeError, OSError) as exc:
                    if process.poll() is None:
                        process.kill()
                    process.wait()
                    raise RenderError(
                        f"FFmpeg stopped while writing frame "
                        f"{frames_done + written}: "
                        f"{stderr_text()[-2000:]}") from exc
                frame_write_seconds += perf_counter() - write_started
                written += 1
                if progress and (written % max(1, project.fps) == 0
                                 or written == timing.frames
                                 or frames_done + written == total_frames):
                    progress({"frames": frames_done + written,
                              "total": total_frames,
                              "scene": built.index + 1})
        finally:
            if process.stdin:
                try:
                    process.stdin.close()
                except OSError:
                    pass
            code = process.wait()
            stderr = stderr_text()
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
                  jobs: int = 1,
                  progress: Callable[[dict], None] | None = None) -> dict:
    """Render a studio project and return a JSON-friendly delivery report.

    Per-scene H.264 caching is enabled by default under
    .cache/reels-maker/studio. Set cache=False to disable it, or pass
    cache_dir to select a different cache directory. ``jobs`` controls
    concurrent scene encodes (1 = sequential, max 8); the Camera Canvas
    renderer always stays sequential because it shares one world surface.
    """
    if profile and profile not in PROFILES:
        raise RenderError(f"Unknown export profile {profile!r}")
    if (isinstance(jobs, bool) or not isinstance(jobs, int)
            or jobs < 1 or jobs > 8):
        raise RenderError("jobs must be an integer between 1 and 8")
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
    uses_camera_canvas = any("camera_canvas" in scene
                             for scene in project.scenes)
    if uses_camera_canvas:
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
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        from ..segment_assembly import join_segments
        parts: list[Path | None] = [None] * len(built)
        cache_hits = 0
        encodes = 0
        scene_encoding_seconds = 0.0
        frame_render_seconds = 0.0
        frame_pipe_write_seconds = 0.0
        video_decode_seconds = 0.0
        video_decode_calls = 0
        video_decoded_frames = 0
        timing_entries: dict[int, dict] = {}
        scene_loop_started = perf_counter()

        work_items = []
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
                parts[index] = cached
                cache_hits += 1
                timing_entries[index] = {
                    "scene": item.index + 1, "cache_hit": True,
                    "elapsed_seconds": round(
                        perf_counter() - scene_started, 4),
                }
                continue
            work_items.append({
                "index": index, "scene": scene, "timing": timing,
                "item": item, "next_scene": next_scene, "part": part,
                "cached": cached,
                "transition": scene.get("transition_out"),
            })

        effective_jobs = 1 if uses_camera_canvas else jobs
        renderer_local = threading.local()
        progress_lock = threading.Lock()
        progress_written: dict[int, int] = {}

        def worker_renderer():
            """One SceneRenderer per worker thread; its caches are not
            thread-safe and settled-sample memoization is per scene."""
            current = getattr(renderer_local, "renderer", None)
            if current is None:
                current = SceneRenderer(
                    project.width, project.height, project.tokens,
                    project.fonts,
                    options=RenderOptions(supersample=supersample))
                renderer_local.renderer = current
            return current

        def report_progress(update: dict, slot: int) -> None:
            # update["frames"] counts frames rendered inside this scene.
            with progress_lock:
                progress_written[slot] = int(update["frames"])
                done = sum(progress_written.values())
            if progress is not None:
                progress({"frames": done,
                          "total": timeline.total_frames,
                          "scene": update.get("scene")})

        def encode_work(work: dict) -> dict:
            from .canvas import collect_video_decode_metrics
            slot = work["index"]
            timing = work["timing"]
            scene_metrics: dict = {}
            encode_started = perf_counter()
            slot_progress = (lambda update: report_progress(update, slot)
                             if progress is not None else None)
            with collect_video_decode_metrics() as video_metrics:
                encoded = _encode_studio_scene(
                    project,
                    worker_renderer() if effective_jobs > 1 else renderer,
                    work["item"], timing, work["part"],
                    codec=codec, crf=crf, preset=preset,
                    frames_done=0,
                    total_frames=timeline.total_frames,
                    progress=slot_progress,
                    next_scene=work["next_scene"],
                    transition=work["transition"],
                    metrics=scene_metrics)
            encode_seconds = perf_counter() - encode_started
            if encoded != timing.frames:  # defensive; encoder raises first
                raise RenderError(
                    f"Scene {work['item'].index + 1}: encoded {encoded} of "
                    f"{timing.frames} frames")
            return {
                "encode_seconds": encode_seconds,
                "frame_render_seconds": scene_metrics.get(
                    "frame_render_seconds", 0.0),
                "frame_pipe_write_seconds": scene_metrics.get(
                    "frame_pipe_write_seconds", 0.0),
                "video_decode_seconds": video_metrics[
                    "video_decode_seconds"],
                "video_decode_calls": video_metrics["video_decode_calls"],
                "video_decoded_frames": video_metrics[
                    "video_decoded_frames"],
                "frames": scene_metrics.get("frames_rendered", 0),
            }

        results: dict[int, dict] = {}
        if effective_jobs > 1 and len(work_items) > 1:
            with ThreadPoolExecutor(
                    max_workers=min(effective_jobs, len(work_items))) as pool:
                futures = {pool.submit(encode_work, work): work
                           for work in work_items}
                for future in as_completed(futures):
                    work = futures[future]
                    results[work["index"]] = future.result()
        else:
            for work in work_items:
                results[work["index"]] = encode_work(work)

        work_by_index = {work["index"]: work for work in work_items}
        for index in sorted(results):
            work = work_by_index[index]
            result = results[index]
            scene_started = perf_counter()
            part = work["part"]
            if work["cached"] is not None:
                # Atomic publication avoids half-written cache objects.
                _publish_cache_segment(part, work["cached"])
                part = work["cached"]
            parts[index] = part
            encodes += 1
            scene_encoding_seconds += result["encode_seconds"]
            frame_render_seconds += result["frame_render_seconds"]
            frame_pipe_write_seconds += result["frame_pipe_write_seconds"]
            video_decode_seconds += result["video_decode_seconds"]
            video_decode_calls += result["video_decode_calls"]
            video_decoded_frames += result["video_decoded_frames"]
            timing_entries[index] = {
                "scene": work["item"].index + 1, "cache_hit": False,
                "elapsed_seconds": round(
                    perf_counter() - scene_started, 4),
                "encode_seconds": round(result["encode_seconds"], 4),
                "frame_render_seconds": round(
                    result["frame_render_seconds"], 4),
                "video_decode_calls": result["video_decode_calls"],
                "video_decoded_frames": result["video_decoded_frames"],
                "video_decode_seconds": round(
                    result["video_decode_seconds"], 4),
                "frames": result["frames"],
            }

        parts = [part for part in parts if part is not None]
        scene_timings = [timing_entries[index]
                         for index in sorted(timing_entries)]
        scene_loop_seconds = perf_counter() - scene_loop_started
        join_started = perf_counter()
        join_segments(parts, silent, scratch, max_frames=timeline.total_frames)
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
        "jobs": 1 if uses_camera_canvas else jobs,
        "cache_signature": (cache_signature[:12] if cache_signature else None),
        "icon_provenance": _icon_provenance(built),
        "scenes": [scene.to_dict() for scene in built],
        "warnings": [issue for scene in built
                     for issue in scene.choreography.warnings],
        "project_warnings": list(project.warnings),
    }
