"""Content-addressed shot cache, FFmpeg rendering, and atomic export."""
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from .cards import draw_card
from .ffmpeg import RenderError, duration, execute, probe
from .media import preflight
from .spec import Project

PIPELINE_VERSION = 1


def _fingerprint(path: Path | None):
    if path is None:
        return None
    stat = path.stat()
    return [str(path.resolve()), stat.st_size, stat.st_mtime_ns]


def _shot_key(project: Project, shot, logo: Path | None) -> str:
    payload = {
        "version": PIPELINE_VERSION,
        "source": _fingerprint(shot.path),
        "logo": _fingerprint(logo),
        "start": shot.start,
        "duration": shot.length,
        "framing": shot.framing,
        "title": shot.title,
        "branding": project.branding,
        "video": [project.width, project.height, project.fps],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _framing(project: Project, mode: str) -> str:
    w, h, fps = project.width, project.height, project.fps
    if mode == "crop":
        return (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                f"crop={w}:{h},setsar=1,fps={fps},format=yuv420p")
    if mode == "pad":
        return (f"split[bg0][fg0];[bg0]scale={w}:{h}:force_original_aspect_ratio=increase,"
                f"crop={w}:{h},boxblur=20:2,eq=brightness=-0.1[bg];"
                f"[fg0]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={fps},format=yuv420p")
    raise RenderError(f"Unsupported framing mode: {mode}")


def _encode_scene(project: Project, shot, logo: Path | None, dest: Path, scratch: Path):
    frame_count = round(shot.length * project.fps)
    card = scratch / "overlay.png"
    has_card = draw_card(project, shot.title, logo, card)
    command = ["-ss", f"{shot.start:.6f}", "-i", str(shot.path)]
    if has_card:
        command += ["-loop", "1", "-framerate", str(project.fps), "-i", str(card)]
        graph = (f"[0:v:0]{_framing(project, shot.framing)}[base];"
                 "[1:v:0]format=rgba[card];"
                 "[base][card]overlay=0:0:shortest=1,format=yuv420p[out]")
        command += ["-filter_complex", graph, "-map", "[out]"]
    elif shot.framing == "crop":
        command += ["-vf", _framing(project, "crop"), "-map", "0:v:0"]
    else:
        command += ["-filter_complex", f"[0:v:0]{_framing(project, 'pad')}[out]", "-map", "[out]"]
    execute(command + ["-frames:v", str(frame_count), "-an", "-c:v", "libx264",
                       "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                       "-movflags", "+faststart", str(dest)])


def _check_output(project: Project, target: Path) -> dict:
    info = probe(target)
    video = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    audio = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
    if len(video) != 1 or video[0].get("codec_name") != "h264":
        raise RenderError("Output requires exactly one H.264 video stream")
    if (video[0].get("width"), video[0].get("height")) != (project.width, project.height):
        raise RenderError("Output dimensions do not match project")
    if bool(audio) != bool(project.music) or (audio and audio[0].get("codec_name") != "aac"):
        raise RenderError("Unexpected audio streams or audio codec")
    actual = duration(target)
    tolerance = len(project.scenes) / (2 * project.fps) + 0.15
    if abs(actual - project.duration) > tolerance:
        raise RenderError(f"Unexpected duration {actual:.3f}s instead of {project.duration:.3f}s")
    return {"output": str(target), "duration": actual, "resolution": [project.width, project.height],
            "fps": project.fps, "scenes": len(project.scenes), "audio": bool(audio)}


def render(project: Project, *, root: Path, output: Path | None = None,
           cache_dir: Path | None = None, use_cache: bool = True) -> dict:
    """Validate then generate MP4, reusing unchanged H.264 clips between runs."""
    root = Path(root).resolve()
    inputs = preflight(project, root)
    if output is None:
        rel = Path(project.output)
        if rel.is_absolute() or ".." in rel.parts:
            raise RenderError("Manifest output must be relative to project root")
        target = root / rel
    else:
        target = Path(output).resolve()
    if target.suffix.lower() != ".mp4":
        raise RenderError("Output must be .mp4")
    target.parent.mkdir(parents=True, exist_ok=True)
    cache = Path(cache_dir).resolve() if cache_dir else root / ".cache" / "reels-maker"
    if use_cache:
        cache.mkdir(parents=True, exist_ok=True)
    hits = 0

    with tempfile.TemporaryDirectory(prefix="reels-maker-") as temp:
        work = Path(temp)
        segments = []
        for index, shot in enumerate(inputs.shots):
            key = _shot_key(project, shot, inputs.logo)
            stored = cache / (key + ".mp4")
            if use_cache and stored.exists() and stored.stat().st_size > 512:
                segments.append(stored)
                hits += 1
                continue
            scratch = work / f"shot_{index:03d}"
            scratch.mkdir()
            encoded = scratch / "clip.mp4"
            _encode_scene(project, shot, inputs.logo, encoded, scratch)
            if use_cache:
                # Temporary file resides next to the destination so replace is atomic.
                with tempfile.NamedTemporaryFile(prefix=key + "-", suffix=".mp4",
                                                 dir=cache, delete=False) as fh:
                    staged = Path(fh.name)
                try:
                    shutil.copyfile(encoded, staged)
                    os.replace(staged, stored)
                finally:
                    staged.unlink(missing_ok=True)
                segments.append(stored)
            else:
                segments.append(encoded)

        concat = work / "concat.txt"
        concat.write_text("".join("file '" + str(p).replace("'", "'\\''") + "'\n"
                                  for p in segments), encoding="utf-8")
        combined = work / "picture.mp4"
        execute(["-f", "concat", "-safe", "0", "-i", str(concat), "-map", "0:v:0",
                 "-an", "-c:v", "copy", str(combined)])
        finished = work / "finished.mp4"
        if inputs.music:
            song = project.music or {}
            fade = float(song.get("fade_out", 0))
            filter_audio = (f"[1:a:0]atrim=duration={project.duration:.6f},"
                            f"asetpts=PTS-STARTPTS,volume={float(song.get('volume', 1)):.4f}")
            if fade:
                filter_audio += f",afade=t=out:st={project.duration-fade:.6f}:d={fade:.6f}"
            filter_audio += "[a]"
            execute(["-i", str(combined), "-ss", f"{float(song.get('start', 0)):.6f}",
                     "-i", str(inputs.music), "-filter_complex", filter_audio,
                     "-map", "0:v:0", "-map", "[a]", "-c:v", "copy",
                     "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(finished)])
        else:
            execute(["-i", str(combined), "-map", "0:v:0", "-an", "-c:v", "copy",
                     "-movflags", "+faststart", str(finished)])
        result = _check_output(project, finished)
        # Never overwrite a previous good output until all quality gates pass.
        with tempfile.NamedTemporaryFile(prefix=".reels-maker-", suffix=".mp4",
                                         dir=target.parent, delete=False) as fh:
            staged_output = Path(fh.name)
        try:
            shutil.copyfile(finished, staged_output)
            os.replace(staged_output, target)
        finally:
            staged_output.unlink(missing_ok=True)
        result.update({"output": str(target), "cache_hits": hits,
                       "cache_misses": len(segments) - hits, "status": "ok"})
        return result
