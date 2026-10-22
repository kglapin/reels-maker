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
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .ffmpeg import RenderError, duration, execute, probe, require_tool
from .paths import ROOT, resolve_asset
from .spec import Project

CACHE_SCHEMA = 1
SUPPORTED_ENCODER = "libx264"


def _color(value: str, default: str) -> tuple[int, int, int]:
    value = value if isinstance(value, str) else default
    value = value.lstrip("#")
    if len(value) != 6:
        value = default.lstrip("#")
    try:
        return tuple(bytes.fromhex(value))
    except ValueError:
        return tuple(bytes.fromhex(default.lstrip("#")))


def _font(size: int, bold: bool = False, custom: str | None = None) -> ImageFont.FreeTypeFont:
    choices = [custom] if custom else []
    choices.extend([
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ])
    for path in choices:
        if not path:
            continue
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    raise RenderError("No usable TrueType font. Install DejaVu Sans or configure font_bold/font_regular.")


def _wrap(draw: ImageDraw.ImageDraw, message: str, font: ImageFont.FreeTypeFont,
          max_width: int) -> list[str]:
    lines = []
    for paragraph in message.splitlines():
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        line = ""
        for word in words:
            proposal = f"{line} {word}".strip()
            if line and draw.textlength(proposal, font=font) > max_width:
                lines.append(line)
                line = word
            else:
                line = proposal
        lines.append(line)
    return lines


def _make_card(scene: dict, project: Project, root: Path, dest: Path) -> bool:
    title = scene.get("title") or {}
    branding = project.branding
    if not title and not branding.get("logo"):
        return False
    w, h = project.width, project.height
    image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    accent = _color(branding.get("accent", "#5fe39a"), "#5fe39a")
    margin = int(w * 0.085)
    max_width = w - 2 * margin
    scale = w / 1080
    bold_path = branding.get("font_bold")
    regular_path = branding.get("font_regular")
    headline = str(title.get("headline", ""))
    kicker = str(title.get("kicker", ""))
    body = str(title.get("body", ""))

    if headline or kicker or body:
        # Lightweight semi-transparent scrim; avoid an expensive per-pixel gradient.
        top = int(h * 0.49)
        draw.rectangle((0, top, w, h), fill=(2, 21, 17, 190))
        f_head = _font(round(72 * scale), True, bold_path)
        f_kicker = _font(round(31 * scale), True, bold_path)
        f_body = _font(round(37 * scale), False, regular_path)
        lines_head = _wrap(draw, headline, f_head, max_width)
        lines_body = _wrap(draw, body, f_body, max_width)
        line_head = round(87 * scale)
        line_body = round(54 * scale)
        block = (round(63 * scale) if kicker else 0)
        block += len(lines_head) * line_head
        block += (round(32 * scale) + len(lines_body) * line_body) if body else 0
        # Preserve safe bottom area for social controls and UI labels.
        safe_bottom = max(round(290 * h / 1920), int(h * 0.13))
        safe_top = round(h * 0.20)
        y = max(safe_top, h - safe_bottom - block)
        if y + block > h - safe_bottom + 1:
            raise RenderError("Text exceeds vertical safe area: shorten headline/body")
        draw.rounded_rectangle(
            (margin, y, margin + round(7 * scale), y + block),
            radius=round(3 * scale), fill=(*accent, 255),
        )
        x = margin + round(28 * scale)
        if kicker:
            draw.text((x, y), kicker.upper(), font=f_kicker, fill=(*accent, 255))
            y += round(63 * scale)
        for line in lines_head:
            if draw.textlength(line, font=f_head) > max_width - (x - margin):
                raise RenderError(f"Headline is too wide: {line}")
            draw.text((x, y), line, font=f_head, fill="white")
            y += line_head
        if body:
            y += round(32 * scale)
            for line in lines_body:
                if draw.textlength(line, font=f_body) > max_width - (x - margin):
                    raise RenderError(f"Body line is too wide: {line}")
                draw.text((x, y), line, font=f_body, fill="#dfefe6")
                y += line_body

    if branding.get("logo"):
        logo_path = resolve_asset(branding["logo"], root)
        with Image.open(logo_path) as raw_logo:
            logo = raw_logo.convert("RGBA")
        logo_width = round(w * 0.22)
        logo_height = round(logo.height * logo_width / logo.width)
        logo.thumbnail((logo_width, round(h * 0.13)), Image.Resampling.LANCZOS)
        image.alpha_composite(logo, (margin, round(h * 0.105)))

    image.save(dest)
    return True


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


def _media_video_duration(path: Path) -> float:
    return duration(path)


def preflight(project: Project, root: Path = ROOT) -> dict:
    """Validate every referenced media item before expensive rendering."""
    require_tool("ffmpeg")
    require_tool("ffprobe")
    root = Path(root).resolve()
    branding_files = []
    for key in ("logo", "font_regular", "font_bold"):
        if project.branding.get(key):
            # Font paths may be absolute system paths, but logo stays project-relative.
            if key == "logo":
                branding_files.append(resolve_asset(project.branding[key], root))
            elif not Path(project.branding[key]).is_file():
                raise RenderError(f"Missing font: {project.branding[key]}")
            else:
                branding_files.append(Path(project.branding[key]))
    sources = []
    for index, scene in enumerate(project.scenes):
        source = resolve_asset(scene["file"], root)
        src_duration = _media_video_duration(source)
        if scene.get("start", 0) + scene["duration"] > src_duration + 0.05:
            raise RenderError(f"Scene {index} exceeds source duration: {source.name}")
        if not any(s.get("codec_type") == "video" for s in probe(source).get("streams", [])):
            raise RenderError(f"No video stream in {source}")
        sources.append(source)
    music = resolve_asset(project.music["file"], root) if project.music else None
    if music:
        meta = probe(music)
        if not any(s.get("codec_type") == "audio" for s in meta.get("streams", [])):
            raise RenderError("Music file contains no audio stream")
        if float(project.music.get("start", 0)) + project.duration > _media_video_duration(music) + 0.1:
            raise RenderError("Music is shorter than requested segment")
    return {"sources": sources, "music": music, "branding_files": branding_files}


def _encode_scene(source: Path, scene: dict, project: Project,
                  root: Path, dest: Path, scratch: Path) -> None:
    w, h, fps = project.width, project.height, project.fps
    crop = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},setsar=1")
    pad = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
           f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1")
    vf = crop if scene.get("framing", "crop") == "crop" else pad
    vf += f",fps={fps},format=yuv420p"
    card = scratch / "card.png"
    show_card = _make_card(scene, project, root, card)
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
           cache: bool = True) -> dict:
    """Produce an H.264 MP4. Returns machine-readable details for agents."""
    root = Path(root).resolve()
    inputs = preflight(project, root)
    dest = (Path(output) if output is not None else root / project.output).resolve()
    if dest.suffix.lower() != ".mp4":
        raise RenderError("Output must be an .mp4 file")
    dest.parent.mkdir(parents=True, exist_ok=True)
    cache_root = (Path(cache_dir) if cache_dir else root / ".cache" / "reels-maker").resolve()
    cache_root.mkdir(parents=True, exist_ok=True)

    hits = 0
    encoded = 0
    with tempfile.TemporaryDirectory(prefix="reels-", dir=dest.parent) as work:
        scratch = Path(work)
        parts = []
        for i, (source, scene) in enumerate(zip(inputs["sources"], project.scenes)):
            scene_key = _scene_key(source, scene, project, inputs["branding_files"])
            cached_path = cache_root / f"{scene_key}.mp4"
            if cache and cached_path.is_file() and cached_path.stat().st_size > 0:
                hits += 1
                parts.append(cached_path)
                continue
            scene_dir = scratch / f"scene-{i}"
            scene_dir.mkdir()
            temp_part = scene_dir / "scene.mp4"
            _encode_scene(source, scene, project, root, temp_part, scene_dir)
            encoded += 1
            if cache:
                # Each render writes to its private workspace, then atomically publishes.
                os.replace(temp_part, cached_path)
                parts.append(cached_path)
            else:
                parts.append(temp_part)
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
        "width": project.width,
        "height": project.height,
        "fps": project.fps,
        "scenes_total": len(parts),
        "scenes_encoded": encoded,
        "cache_hits": hits,
        "size_bytes": dest.stat().st_size,
    }
