"""Fast, reproducible video rendering with cached scene encodes.

Each scene is encoded independently and cached by source identity + settings.
Previously encoded scenes are concatenated using stream copy; only changed
scenes are encoded on subsequent runs.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .cards import draw_card
from .ffmpeg import RenderError, execute, probe
from .media import preflight as inspect_media
from .paths import ROOT
from .spec import Project

CACHE_SCHEMA = 2
SUPPORTED_ENCODER = "libx264"


def _scene_key(source: Path, scene: dict, project: Project,
               branding_files: list[Path]) -> str:
    def fingerprint(p: Path) -> tuple[str, int, int]:
        st = p.stat()
        # Stat-based signatures avoid hashing large video inputs on every render.
        return str(p.resolve()), st.st_size, st.st_mtime_ns

    signature = {
        "schema": CACHE_SCHEMA,
        "source": fingerprint(source),
        "branding_files": [fingerprint(p) for p in branding_files],
        "scene": scene,
        "branding": project.branding,
        "video": [project.width, project.height, project.fps],
        "encoder": SUPPORTED_ENCODER,
        "preset": "veryfast",
        "crf": 20,
    }
    raw = json.dumps(signature, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def preflight(project: Project, root: Path = ROOT) -> dict:
    """Check each unique source once and resolve brand assets before rendering."""
    inputs = inspect_media(project, Path(root).resolve())
    fonts = []
    for field in ("font_regular", "font_bold"):
        if project.branding.get(field):
            path = Path(project.branding[field])
            if not path.is_file():
                raise RenderError(f"Missing branding font: {path}")
            fonts.append(path)
    return {
        "sources": [shot.path for shot in inputs.shots],
        "music": inputs.music,
        "logo": inputs.logo,
        "branding_files": ([inputs.logo] if inputs.logo else []) + fonts,
    }


def _encode_scene(source: Path, scene: dict, project: Project,
                  logo: Path | None, dest: Path, scratch: Path) -> None:
    w, h, fps = project.width, project.height, project.fps
    crop = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},setsar=1")
    pad = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
           f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1")
    vf = crop if scene.get("framing", "crop") == "crop" else pad
    vf += f",fps={fps},format=yuv420p"
    card = scratch / "card.png"
    show_card = draw_card(project, scene.get("title") or {}, logo, card)
    args = ["-ss", str(scene.get("start", 0)), "-i", str(source)]
    if show_card:
        args += ["-loop", "1", "-framerate", str(fps), "-i", str(card)]
        args += ["-filter_complex",
                 f"[0:v]{vf}[base];[1:v]format=rgba[txt];"
                 "[base][txt]overlay=0:0:shortest=1:format=auto,"
                 "format=yuv420p[v]", "-map", "[v]"]
    else:
        args += ["-vf", vf, "-map", "0:v:0"]
    args += ["-t", str(scene["duration"]), "-an", "-c:v", SUPPORTED_ENCODER,
             "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", str(dest)]
    execute(args)


def _join(parts: list[Path], destination: Path, scratch: Path) -> None:
    # FFmpeg concat demuxer: stream-copy when segments have identical video settings.
    manifest = scratch / "segments.txt"
    def quote_path(p: Path) -> str:
        return str(p).replace("'", "'\\''")
    manifest.write_text("".join(f"file '{quote_path(p)}'\n" for p in parts))
    execute(["-f", "concat", "-safe", "0", "-i", str(manifest),
             "-map", "0:v:0", "-an", "-c:v", "copy", str(destination)])


def render(project: Project, *, root: Path = ROOT,
           output: Path | None = None, cache_dir: Path | None = None,
           cache: bool = True, jobs: int = 2) -> dict:
    """Produce an H.264 MP4. Returns machine-readable details for agents."""
    root = Path(root).resolve()
    inputs = preflight(project, root)
    dest = (Path(output) if output is not None else root / project.output).resolve()
    if dest.suffix.lower() != ".mp4":
        raise RenderError("Output must be an .mp4 file")
    dest.parent.mkdir(parents=True, exist_ok=True)
    cache_root = (Path(cache_dir) if cache_dir else root / ".cache" / "reels-maker").resolve()
    cache_root.mkdir(parents=True, exist_ok=True)

    if isinstance(jobs, bool) or not isinstance(jobs, int) or jobs < 1 or jobs > 8:
        raise RenderError("jobs must be an integer between 1 and 8")
    with tempfile.TemporaryDirectory(prefix="reels-", dir=dest.parent) as work:
        scratch = Path(work)
        parts = [None] * len(project.scenes)
        pending = {}
        hits = 0
        for i, (source, scene) in enumerate(zip(inputs["sources"], project.scenes)):
            key = _scene_key(source, scene, project, inputs["branding_files"])
            cached = cache_root / f"{key}.mp4"
            if cache and cached.is_file() and cached.stat().st_size > 0:
                parts[i] = cached
                hits += 1
                continue
            if key not in pending:
                scratch_scene = scratch / f"scene-{i}"
                scratch_scene.mkdir()
                pending[key] = (source, scene, scratch_scene, cached, [])
            pending[key][-1].append(i)

        def encode_task(task):
            source, scene, scene_dir, cached, indices = task
            part = scene_dir / "scene.mp4"
            _encode_scene(source, scene, project, inputs["logo"], part, scene_dir)
            return part, cached, indices

        # Independent scenes encode concurrently. Duplicate shots are encoded once.
        with ThreadPoolExecutor(max_workers=min(jobs, max(1, len(pending)))) as pool:
            futures = [pool.submit(encode_task, item) for item in pending.values()]
            for future in as_completed(futures):
                part, cached, indices = future.result()
                if cache:
                    # Atomic publication avoids half-written cache objects.
                    os.replace(part, cached)
                    part = cached
                for i in indices:
                    parts[i] = part
        encoded = len(pending)
        hits = len(parts) - encoded
        silent = scratch / "silent.mp4"
        _join(parts, silent, scratch)
        final = scratch / "final.mp4"
        if inputs["music"]:
            music = project.music
            volume = float(music.get("volume", 1.0))
            fade = float(music.get("fade_out", 0))
            audio_filter = (f"[1:a]atrim=duration={project.duration:.4f},"
                            f"asetpts=PTS-STARTPTS,volume={volume:.4f}")
            if fade > 0:
                audio_filter += (f",afade=t=out:st={project.duration-fade:.4f}:"
                                 f"d={fade:.4f}")
            audio_filter += "[aout]"
            execute(["-i", str(silent), "-ss", str(music.get("start", 0)),
                     "-i", str(inputs["music"]), "-filter_complex", audio_filter,
                     "-map", "0:v:0", "-map", "[aout]",
                     "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                     "-t", str(project.duration), "-movflags", "+faststart",
                     str(final)])
        else:
            shutil.copyfile(silent, final)
        metadata = probe(final)
        video = next((s for s in metadata["streams"] if s["codec_type"] == "video"), {})
        if video.get("width") != project.width or video.get("height") != project.height:
            raise RenderError("Export dimension verification failed")
        if not final.stat().st_size:
            raise RenderError("Empty output video")
        # Atomic final delivery; errors never overwrite an existing successful render.
        os.replace(final, dest)
    return {
        "ok": True,
        "output": str(dest),
        "duration_requested": project.duration,
        "duration_actual": float(metadata.get("format", {}).get("duration", 0)),
        "duration": float(metadata.get("format", {}).get("duration", 0)),
        "status": "ok",
        "schema_version": 1,
        "cache_misses": encoded,
        "workers": jobs,
        "audio": bool(inputs["music"]),
        "width": project.width,
        "height": project.height,
        "fps": project.fps,
        "scenes_total": len(parts),
        "scenes_encoded": encoded,
        "cache_hits": hits,
        "size_bytes": dest.stat().st_size,
    }
