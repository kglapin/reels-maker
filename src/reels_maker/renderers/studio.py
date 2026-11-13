"""Studio render pipeline: graph -> frames -> H.264 (+ optional audio mix).

A default-on per-scene segment cache stores encoded scene parts by render
settings, scene data and referenced asset metadata. Unchanged scenes are reused
without copying their cached files; edited scenes are re-encoded independently.
"""
from __future__ import annotations

import errno
import hashlib
import json
import multiprocessing
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from time import perf_counter, time as wall_time
from typing import Callable
from fractions import Fraction

from ..audio_mix import mux_audio
from ..ffmpeg import RenderError, drain_stderr, execute, require_tool
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
    _asset_fingerprints, _publish_cache_segment, _scene_cache_key, trim_cache,
)
from .studio_output import (
    FORMAT_MATRIX_DIMENSIONS, probe_output, _verify_studio_output,
    render_master_format_matrix,
)

HW_ENCODERS = ("h264_videotoolbox", "hevc_videotoolbox", "h264_nvenc",
               "hevc_nvenc", "h264_vaapi")


def resolve_scene_supersample(scene: dict, default: int) -> int:
    """Effective supersample factor for one studio scene.

    Scenes may pin ``"supersample"`` to an integer 1..4. The default
    ``"auto"`` renders natively-rasterized full-frame scenes at 1x —
    currently ``iso-explainer``, whose film is authored at delivery
    resolution and would otherwise be upscaled only to be downscaled
    again — and every other composition at the project default.
    """
    raw = scene.get("supersample", "auto")
    if raw == "auto":
        if scene.get("composition") == "iso-explainer":
            return 1
        return default
    if isinstance(raw, bool) or not isinstance(raw, int) or not 1 <= raw <= 4:
        raise RenderError(
            f"Scene {scene.get('id', '?')}: supersample must be 'auto' "
            "or an integer 1..4")
    return raw


def encoder_options(codec: str, *, crf: int, preset: str,
                    threads: int | None = None) -> list[str]:
    """FFmpeg encoder args for software and hardware H.264/HEVC encoders.

    Hardware encoders do not accept x264 ``-preset``/``-crf``: VideoToolbox
    uses ``-q:v`` quality, NVENC uses ``-cq`` with a constant-quality rate
    control, VAAPI uses ``-qp``. Mapping keeps the caller's CRF intent.
    """
    if codec in ("h264_videotoolbox", "hevc_videotoolbox"):
        quality = max(10, min(100, round(100 - crf * 1.8)))
        return ["-c:v", codec, "-q:v", str(quality)]
    if codec in ("h264_nvenc", "hevc_nvenc"):
        return ["-c:v", codec, "-preset", "p4", "-cq", str(crf), "-b:v", "0"]
    if codec == "h264_vaapi":
        return ["-c:v", codec, "-qp", str(crf)]
    options = ["-c:v", codec, "-preset", preset, "-crf", str(crf)]
    if threads:
        options += ["-threads", str(threads)]
    return options


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


_AUDIO_CACHE_VERSION = 1


def _audio_input_signature(project: StudioProject, value: str) -> dict:
    """Content identity for one audible input file (size + mtime)."""
    try:
        stat = _asset_path(project, value).stat()
    except (OSError, RuntimeError, ValueError):
        return {"file": value, "unresolved": True}
    return {"file": value, "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def _audio_cache_key(project: StudioProject, *, voice, music,
                     sfx_tracks, duration: float) -> str:
    """Key for the mixed soundtrack: every audible input plus its config."""
    sfx = []
    for track in sfx_tracks:
        entry = dict(track)
        sfx.append({"config": entry,
                    "input": _audio_input_signature(
                        project, track.get("file") or track.get("path") or "")})
    payload = {
        "version": _AUDIO_CACHE_VERSION,
        "duration": round(float(duration), 6),
        "voice": dict(voice or {}),
        "music": dict(music or {}),
        "sfx": sfx,
        "aac": {"codec": "aac", "bitrate": "192k", "rate": 48000,
                "limiter": 0.95},
    }
    if voice and voice.get("file"):
        payload["voice_input"] = _audio_input_signature(
            project, voice["file"])
    if music and music.get("file"):
        payload["music_input"] = _audio_input_signature(
            project, music["file"])
    return _hash_payload(payload)


def _mux(project: StudioProject, silent: Path, destination: Path,
         duration: float, *, cache_root: Path | None = None,
         music_start_offset: float = 0.0) -> dict:
    voice, music, voice_path, music_path, sfx_tracks = _audio_config(project)
    if voice_path is None and music_path is None and not sfx_tracks:
        shutil.move(str(silent), str(destination))
        return {"audio": False}
    if music_start_offset:
        # Partial renders keep the music aligned to the film timeline.
        music = dict(music or {})
        music["start"] = float(music.get("start", 0)) + music_start_offset
    mode = (music or {}).get("ducking", "off")
    flags = {"voiceover": voice_path is not None,
             "music": music_path is not None, "sfx": len(sfx_tracks),
             "ducking": mode if (voice_path and music_path) else "off",
             "sample_rate": 48000, "peak_limiter": 0.95}
    cache_file = None
    if cache_root is not None:
        key = _audio_cache_key(project, voice=voice, music=music,
                               sfx_tracks=sfx_tracks, duration=duration)
        cache_file = cache_root / "audio" / f"{key}.m4a"
        if cache_file.is_file() and cache_file.stat().st_size > 0:
            # Identical mix already encoded: remux with stream copy.
            execute(["-v", "error", "-i", str(silent), "-i", str(cache_file),
                     "-map", "0:v:0", "-map", "1:a:0", "-c", "copy",
                     "-t", f"{duration:.8f}",
                     "-movflags", "+faststart", str(destination)])
            return {"audio": True, "cached": True, **flags}
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
    if cache_file is not None:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        staged = cache_file.with_suffix(".tmp.m4a")
        execute(["-v", "error", "-i", str(destination),
                 "-map", "0:a:0", "-c", "copy", str(staged)])
        os.replace(staged, cache_file)
    return {"audio": True, "cached": False, **result}


def _encode_studio_scene(project: StudioProject, renderer, built, timing,
                         dest: Path, *, codec: str, crf: int, preset: str,
                         frames_done: int, total_frames: int,
                         progress: Callable[[dict], None] | None,
                         next_scene=None, transition: dict | None = None,
                         metrics: dict | None = None,
                         threads: int | None = None,
                         frame_start: int = 0,
                         frame_count: int | None = None,
                         pixel_format: str = "yuv420p") -> int:
    """Encode one scene's frames into a standalone stream-copyable MP4.

    ``frame_start``/``frame_count`` encode a contiguous slice of the scene
    (chunked parallel encodes); frame times stay scene-global, so chunk
    boundaries never shift the picture.
    """
    total = timing.frames
    count = total - frame_start if frame_count is None else frame_count
    if frame_start < 0 or count < 1 or frame_start + count > total:
        raise RenderError(
            f"Invalid frame range [{frame_start}, {frame_start + count}) "
            f"for a {total}-frame scene")
    command = [
        require_tool("ffmpeg"), "-hide_banner", "-nostdin", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{project.width}x{project.height}", "-r", str(project.fps),
        "-i", "-", "-an",
        *encoder_options(codec, crf=crf, preset=preset, threads=threads),
        *(["-profile:v", "high10"]
          if pixel_format.endswith("10le") and codec == "libx264" else []),
        "-pix_fmt", pixel_format, str(dest),
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
            for frame in range(frame_start, frame_start + count):
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
                        direction=transition.get("direction", "left"),
                        easing=transition.get("easing", "smooth"))
                scene_perspective = getattr(built, "scene", None)
                if isinstance(scene_perspective, dict) and scene_perspective.get("perspective"):
                    from .perspective import apply_perspective
                    image = apply_perspective(
                        image, scene_perspective, time, built.duration)
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
                                 or written == count
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
        if written != count:
            raise RenderError(f"Encoded {written} of {count} frames")
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


CHUNK_FRAMES = 60
_PROCESS_WORKERS_CAP = 4

# Inherited by fork()ed chunk workers; renderers are per-process, per-ss.
_PROCESS_STATE: dict = {}


def _plan_chunks(total_frames: int, chunk_frames: int, *,
                 has_transition: bool) -> list[tuple[int, int]]:
    """Split a scene into (start, count) encode chunks.

    Scenes with an outgoing transition stay whole: their tail blends the
    next scene's first frame, which chunk assembly must not slice.
    """
    if chunk_frames < 1:
        raise RenderError("chunk_frames must be a positive frame count")
    if has_transition or total_frames <= chunk_frames:
        return [(0, total_frames)]
    chunks = []
    start = 0
    while start < total_frames:
        count = min(chunk_frames, total_frames - start)
        chunks.append((start, count))
        start += count
    return chunks


def _chunk_worker_init() -> None:
    _PROCESS_STATE["renderers"] = {}


def _encode_chunk_task(task: dict) -> dict:
    """Encode one scene chunk inside a forked worker process."""
    from .canvas import collect_video_decode_metrics

    project = _PROCESS_STATE["project"]
    built = _PROCESS_STATE["built"]
    timings = _PROCESS_STATE["timings"]
    index = task["index"]
    item = built[index]
    timing = timings[index]
    renderers = _PROCESS_STATE.setdefault("renderers", {})
    renderer = renderers.get(task["ss"])
    if renderer is None:
        renderer = SceneRenderer(
            project.width, project.height, project.tokens, project.fonts,
            options=RenderOptions(supersample=task["ss"]),
            cache_scale=_PROCESS_STATE["cache_scale"])
        renderers[task["ss"]] = renderer
    transition = task.get("transition")
    next_scene = (built[index + 1]
                  if transition and index + 1 < len(built) else None)
    metrics: dict = {}
    started = perf_counter()
    with collect_video_decode_metrics() as video_metrics:
        encoded = _encode_studio_scene(
            project, renderer, item, timing, Path(task["dest"]),
            codec=task["codec"], crf=task["crf"], preset=task["preset"],
            pixel_format=task.get("pixel_format", "yuv420p"),
            frames_done=task["start"], total_frames=timing.frames,
            progress=None, next_scene=next_scene, transition=transition,
            metrics=metrics, frame_start=task["start"],
            frame_count=task["count"])
    if encoded != task["count"]:
        raise RenderError(
            f"Chunk at frame {task['start']}: encoded {encoded} of "
            f"{task['count']} frames")
    return {
        "index": index, "start": task["start"], "count": task["count"],
        "dest": task["dest"],
        "encode_seconds": perf_counter() - started,
        "frame_render_seconds": metrics.get("frame_render_seconds", 0.0),
        "frame_pipe_write_seconds": metrics.get(
            "frame_pipe_write_seconds", 0.0),
        "video_decode_seconds": video_metrics["video_decode_seconds"],
        "video_decode_calls": video_metrics["video_decode_calls"],
        "video_decoded_frames": video_metrics["video_decoded_frames"],
        "frames": metrics.get("frames_rendered", 0),
    }


def render_studio(project: StudioProject, *, output: str | Path | None = None,
                  profile: str | None = None, supersample: int | None = None,
                  cache_dir: str | Path | None = None, cache: bool = True,
                  jobs: int = 1,
                  scenes: list[int] | None = None,
                  chunk_frames: int = CHUNK_FRAMES,
                  cache_max_gb: float | None = None,
                  progress: Callable[[dict], None] | None = None) -> dict:
    """Render a studio project and return a JSON-friendly delivery report.

    Per-scene H.264 caching is enabled by default under
    .cache/reels-maker/studio. Set cache=False to disable it, or pass
    cache_dir to select a different cache directory. ``jobs`` controls
    concurrent encodes (1 = sequential, max 8); with more than one job,
    scenes are split into frame chunks and encoded in forked worker
    processes (capped at 4). The Camera Canvas renderer always stays
    sequential because it shares one world surface. ``scenes`` renders
    only the given 0-based scene indexes into an explicitly named output
    (a partial preview; it still warms the shared scene/chunk cache).
    """
    if profile and profile not in PROFILES:
        raise RenderError(f"Unknown export profile {profile!r}")
    if (isinstance(jobs, bool) or not isinstance(jobs, int)
            or jobs < 1 or jobs > 8):
        raise RenderError("jobs must be an integer between 1 and 8")
    if chunk_frames < 1:
        raise RenderError("chunk_frames must be a positive frame count")
    selected: list[int] | None = None
    if scenes is not None:
        selected = sorted(set(scenes))
        if not selected:
            raise RenderError("scenes must name at least one scene index")
        if output is None:
            raise RenderError(
                "A partial studio render (scenes=...) requires an "
                "explicit output path")
    overall_started = perf_counter()
    wall_started = wall_time()
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
    if selected is not None and selected[-1] >= len(built):
        raise RenderError(
            f"scenes index {selected[-1]} is outside the project "
            f"({len(built)} scenes)")
    selected_set = (set(selected) if selected is not None
                    else set(range(len(built))))
    view_frames = sum(timeline.scenes[i].frames for i in selected_set)
    view_duration = sum(timeline.scenes[i].duration for i in selected_set)
    music_offset = (sum(timeline.scenes[i].duration
                        for i in range(min(selected_set)))
                    if selected is not None else 0.0)
    if supersample is None:
        supersample = 2 if project.height >= 1600 else 1
    uses_camera_canvas = any("camera_canvas" in scene
                             for scene in project.scenes)
    effective_jobs = 1 if uses_camera_canvas else jobs
    # Parallel workers each build their own renderer inside the pool; the
    # shared instance is only needed for serial encodes.
    renderer = None
    if uses_camera_canvas:
        from .camera_canvas import CameraCanvasRenderer
        renderer = CameraCanvasRenderer(project)
    elif effective_jobs == 1:
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
    pixel_format = str(project.export.get("pixel_format", "yuv420p"))
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
            if index not in selected_set:
                continue
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
                "cached": cached, "key": key,
                "transition": scene.get("transition_out"),
            })

        # Each worker owns ~512MB of image caches; scale budgets down as the
        # pool grows so jobs=8 cannot pin several GB of RAM.
        worker_cache_scale = min(1.0, 4.0 / max(effective_jobs, 1))
        renderer_local = threading.local()
        progress_lock = threading.Lock()
        progress_written: dict[int, int] = {}

        serial_pool: dict[int, SceneRenderer] = {}

        def renderer_for(ss: int) -> SceneRenderer:
            """One SceneRenderer per supersample factor (per worker thread).

            Sprite and settled-frame caches are resolution-specific, so a
            renderer must never serve two factors. The shared serial
            instance stays on the hot path for the project default; camera
            canvas projects always use their dedicated renderer.
            """
            if uses_camera_canvas or (ss == supersample
                                      and renderer is not None):
                return renderer
            if effective_jobs == 1:
                pool = serial_pool
            else:
                pool = getattr(renderer_local, "renderers", None)
                if pool is None:
                    pool = renderer_local.renderers = {}
            current = pool.get(ss)
            if current is None:
                current = SceneRenderer(
                    project.width, project.height, project.tokens,
                    project.fonts,
                    options=RenderOptions(supersample=ss),
                    cache_scale=worker_cache_scale)
                pool[ss] = current
            return current

        def report_progress(update: dict, slot: int) -> None:
            # update["frames"] counts frames rendered inside this scene.
            with progress_lock:
                progress_written[slot] = int(update["frames"])
                done = sum(progress_written.values())
            if progress is not None:
                progress({"frames": done,
                          "total": view_frames,
                          "scene": update.get("scene")})

        # Warm-cache scenes encode nothing, but their frames still count
        # toward the reported total.
        for cache_index, cache_entry in timing_entries.items():
            if cache_entry.get("cache_hit"):
                report_progress({"frames": timeline.scenes[cache_index].frames,
                                 "scene": cache_entry["scene"]},
                                cache_index)

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
                    renderer_for(resolve_scene_supersample(
                        work["scene"], supersample)),
                    work["item"], timing, work["part"],
                    codec=codec, crf=crf, preset=preset,
                    pixel_format=pixel_format,
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
        chunk_stats: dict[int, dict] = {}
        process_workers = 0
        fork_context = None
        if effective_jobs > 1 and not uses_camera_canvas and work_items:
            try:
                fork_context = multiprocessing.get_context("fork")
            except ValueError:
                fork_context = None
        if fork_context is not None:
            # Process mode: scenes split into frame chunks, encoded by
            # forked workers (threads would serialize on the GIL). Chunk
            # files are cached under the scene key, so an interrupted
            # render resumes at chunk granularity.
            from concurrent.futures import ProcessPoolExecutor

            process_workers = min(effective_jobs, _PROCESS_WORKERS_CAP)
            scene_chunks: dict[int, list[dict]] = {}
            chunk_tasks: list[dict] = []
            for work in work_items:
                index = work["index"]
                timing = work["timing"]
                entries = []
                for start, count in _plan_chunks(
                        timing.frames, chunk_frames,
                        has_transition=bool(work["transition"])):
                    chunk_cache = (
                        cache_root / "chunks"
                        / f"{work['key']}-{start}-{count}.mp4"
                        if cache_root is not None and work["key"] else None)
                    dest = scratch / f"scene-{index}-chunk-{start}.mp4"
                    hit = (chunk_cache is not None
                           and chunk_cache.is_file()
                           and chunk_cache.stat().st_size > 0)
                    entry = {"start": start, "count": count,
                             "cache": chunk_cache, "hit": hit,
                             "path": chunk_cache if hit else dest}
                    if not hit:
                        chunk_tasks.append({
                            "index": index, "start": start, "count": count,
                            "dest": str(dest),
                            "ss": resolve_scene_supersample(
                                work["scene"], supersample),
                            "codec": codec, "crf": crf, "preset": preset,
                            "pixel_format": pixel_format,
                            "transition": work["transition"],
                        })
                    entries.append(entry)
                scene_chunks[index] = entries
                chunk_stats[index] = {
                    "chunks": len(entries),
                    "chunk_hits": sum(1 for e in entries if e["hit"])}
                hit_frames = sum(e["count"] for e in entries if e["hit"])
                if hit_frames and progress is not None:
                    with progress_lock:
                        progress_written[index] = hit_frames
                        progress({"frames": sum(progress_written.values()),
                                  "total": view_frames,
                                  "scene": index + 1})
            aggregated: dict[int, dict] = {
                work["index"]: {
                    "encode_seconds": 0.0, "frame_render_seconds": 0.0,
                    "frame_pipe_write_seconds": 0.0,
                    "video_decode_seconds": 0.0, "video_decode_calls": 0,
                    "video_decoded_frames": 0, "frames": 0}
                for work in work_items}
            if chunk_tasks:
                if cache_root is not None:
                    (cache_root / "chunks").mkdir(parents=True,
                                                  exist_ok=True)
                _PROCESS_STATE.clear()
                _PROCESS_STATE.update(
                    project=project, built=built,
                    timings=timeline.scenes,
                    cache_scale=worker_cache_scale)
                try:
                    with ProcessPoolExecutor(
                            max_workers=min(process_workers,
                                            len(chunk_tasks)),
                            mp_context=fork_context,
                            initializer=_chunk_worker_init) as pool:
                        futures = {pool.submit(_encode_chunk_task, task): task
                                   for task in chunk_tasks}
                        for future in as_completed(futures):
                            task = futures[future]
                            result = future.result()
                            index = result["index"]
                            agg = aggregated[index]
                            for field in ("encode_seconds",
                                          "frame_render_seconds",
                                          "frame_pipe_write_seconds",
                                          "video_decode_seconds"):
                                agg[field] += result[field]
                            for field in ("video_decode_calls",
                                          "video_decoded_frames", "frames"):
                                agg[field] += result[field]
                            entry = next(
                                e for e in scene_chunks[index]
                                if e["start"] == result["start"])
                            if entry["cache"] is not None:
                                _publish_cache_segment(
                                    Path(result["dest"]), entry["cache"])
                                entry["path"] = entry["cache"]
                            if progress is not None:
                                with progress_lock:
                                    progress_written[index] = (
                                        progress_written.get(index, 0)
                                        + result["count"])
                                    progress({
                                        "frames": sum(
                                            progress_written.values()),
                                        "total": view_frames,
                                        "scene": index + 1})
                finally:
                    _PROCESS_STATE.clear()
            for work in work_items:
                index = work["index"]
                entries = sorted(scene_chunks[index],
                                 key=lambda e: e["start"])
                if len(entries) == 1:
                    only = entries[0]
                    if only["hit"]:
                        shutil.copyfile(only["path"], work["part"])
                    elif Path(only["path"]) != work["part"]:
                        os.replace(only["path"], work["part"])
                else:
                    join_segments([e["path"] for e in entries],
                                  work["part"], scratch,
                                  max_frames=work["timing"].frames)
                result = aggregated[index]
                result["frames"] = work["timing"].frames
                results[index] = result
        elif effective_jobs > 1 and len(work_items) > 1:
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
            if index in chunk_stats:
                timing_entries[index].update(chunk_stats[index])

        parts = [part for part in parts if part is not None]
        scene_timings = [timing_entries[index]
                         for index in sorted(timing_entries)]
        scene_loop_seconds = perf_counter() - scene_loop_started
        join_started = perf_counter()
        join_segments(parts, silent, scratch, max_frames=view_frames)
        join_seconds = perf_counter() - join_started
        audio_started = perf_counter()
        audio_result = _mux(project, silent, staged, view_duration,
                            cache_root=cache_root,
                            music_start_offset=music_offset)
        audio_mux_seconds = perf_counter() - audio_started
        verify_started = perf_counter()
        # Fully warm render: every scene segment came from cache, so the
        # video frames are unchanged and the flash verdict would be
        # identical — skip the full-file decode, but say so explicitly.
        full_warm = (selected is None and cache_root is not None
                     and encodes == 0)
        from types import SimpleNamespace
        view_timeline = SimpleNamespace(total_frames=view_frames,
                                        duration=view_duration)
        export_quality = _verify_studio_output(staged, project, view_timeline,
                                               skip_flash=full_warm)
        verification_seconds = perf_counter() - verify_started
        os.replace(staged, destination)
        cache_gc = None
        if cache_root is not None and cache_max_gb:
            cache_gc = trim_cache(
                cache_root, int(cache_max_gb * 1_000_000_000),
                keep=set(parts), keep_after=wall_started)
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
        "frames": view_frames,
        "duration": view_duration,
        "partial": selected is not None,
        "scenes_rendered": [i + 1 for i in sorted(selected_set)],
        "process_workers": process_workers,
        "chunk_frames": chunk_frames,
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
        "fps_rendered": round(view_frames / elapsed, 2),
        "audio": audio_result,
        "export_quality": export_quality,
        "cache_hits": cache_hits,
        "cache_misses": encodes,
        "cache_gc": cache_gc,
        "jobs": effective_jobs,
        "cache_signature": (cache_signature[:12] if cache_signature else None),
        "icon_provenance": _icon_provenance(built),
        "scenes": [scene.to_dict() for scene in built],
        "warnings": [issue for scene in built
                     for issue in scene.choreography.warnings],
        "project_warnings": list(project.warnings),
    }
