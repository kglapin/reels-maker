"""Pillow rendering primitives for the studio scene graph.

The renderer is intentionally dependency-light: Pillow and FFmpeg only. All
geometric antialiasing is achieved by optional supersampling in the scene
renderer, while typography uses real FreeType glyphs and word-level geometry.
"""
from __future__ import annotations

import math
import os
import queue
import re
import subprocess
import threading
from collections import OrderedDict
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from time import perf_counter

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..design.color import mix, parse_hex
from ..design.format import format_value
from ..textkit.typesetter import FontBook, TextBlock, digits_width


@dataclass(frozen=True)
class Camera:
    zoom: float = 1.0
    x: float = 0.0
    y: float = 0.0
    blur: float = 0.0


@lru_cache(maxsize=128)
def _load(path: str, mtime: float) -> Image.Image:
    image = Image.open(path)
    image.load()
    return image.convert("RGBA")


def load_image(path: str | Path) -> Image.Image:
    path = str(Path(path).resolve())
    stat = os.stat(path)
    return _load(path, stat.st_mtime)


_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}
_VIDEO_DECODE_METRICS: ContextVar[dict | None] = ContextVar(
    "reels_maker_video_decode_metrics", default=None)
_VIDEO_DECODE_SESSION: ContextVar["_VideoDecodeSession | None"] = ContextVar(
    "reels_maker_video_decode_session", default=None)
_VIDEO_FRAME_CACHE: OrderedDict[tuple[str, float, float], Image.Image] = OrderedDict()
_VIDEO_FRAME_CACHE_LOCK = threading.RLock()
_VIDEO_FRAME_CACHE_SIZE = 64


def _cached_video_frame(key: tuple[str, float, float]) -> Image.Image | None:
    with _VIDEO_FRAME_CACHE_LOCK:
        image = _VIDEO_FRAME_CACHE.get(key)
        if image is not None:
            _VIDEO_FRAME_CACHE.move_to_end(key)
        return image


def _remember_video_frame(key: tuple[str, float, float], image: Image.Image) -> None:
    with _VIDEO_FRAME_CACHE_LOCK:
        _VIDEO_FRAME_CACHE[key] = image
        _VIDEO_FRAME_CACHE.move_to_end(key)
        while len(_VIDEO_FRAME_CACHE) > _VIDEO_FRAME_CACHE_SIZE:
            _VIDEO_FRAME_CACHE.popitem(last=False)


class _VideoFrameStream:
    """Forward-only FFmpeg PNG stream for monotonically sampled video frames."""

    def __init__(self, path: str, metrics: dict):
        self.path = path
        self.metrics = metrics
        self.process = None
        self.timestamps: queue.Queue[tuple[float, int, int] | None] = queue.Queue()
        self.stderr_thread = None
        self.last_requested: float | None = None
        self.timestamp_offset: float | None = None
        self.frames: OrderedDict[float, Image.Image] = OrderedDict()

    def _start(self, timestamp: float) -> None:
        command = [
            "ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "info",
            "-ss", f"{max(0.0, timestamp):.3f}", "-i", self.path,
            "-an", "-vf", "showinfo", "-fps_mode", "passthrough",
            "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1",
        ]
        self.process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.metrics["video_decode_calls"] += 1
        self.metrics["video_decoder_processes"] += 1

        def collect_timestamps():
            if self.process is None or self.process.stderr is None:
                return
            for line in self.process.stderr:
                timestamp_match = re.search(rb"pts_time:([^\s]+)", line)
                size_match = re.search(rb"\bs:(\d+)x(\d+)\b", line)
                if timestamp_match and size_match:
                    try:
                        self.timestamps.put((
                            float(timestamp_match.group(1)),
                            int(size_match.group(1)),
                            int(size_match.group(2)),
                        ))
                    except ValueError:
                        self.timestamps.put(None)

        self.stderr_thread = threading.Thread(
            target=collect_timestamps, name="video-frame-pts", daemon=True)
        self.stderr_thread.start()

    def _read_exact(self, size: int) -> bytes:
        if self.process is None or self.process.stdout is None:
            raise EOFError("Video decoder is not running")
        result = bytearray(size)
        view = memoryview(result)
        offset = 0
        while offset < size:
            read = self.process.stdout.readinto(view[offset:])
            if not read:
                raise EOFError("Video decoder ended before the requested frame")
            offset += read
        return bytes(result)

    def _read_raw_frame(self, width: int, height: int) -> Image.Image:
        if width < 1 or height < 1 or width * height * 3 > 512 * 1024 * 1024:
            raise ValueError("FFmpeg raw frame dimensions exceed the safe limit")
        pixels = self._read_exact(width * height * 3)
        return Image.frombytes("RGB", (width, height), pixels).convert("RGBA")

    def frame(self, timestamp: float) -> Image.Image | None:
        cached = self.frames.get(timestamp)
        if cached is not None:
            self.frames.move_to_end(timestamp)
            return cached
        if self.last_requested is not None and timestamp < self.last_requested:
            return None
        self.last_requested = timestamp
        if self.process is None:
            self._start(timestamp)
        while True:
            try:
                frame_info = self.timestamps.get(timeout=10.0)
            except queue.Empty as exc:
                raise ValueError("FFmpeg did not report a timestamp for a frame") from exc
            if frame_info is None:
                raise ValueError("FFmpeg returned a frame without metadata")
            frame_time, width, height = frame_info
            image = self._read_raw_frame(width, height)
            self.metrics["video_decoded_frames"] += 1
            if self.timestamp_offset is None:
                # Input-side -ss resets timestamps on some containers. The
                # first streamed frame is the same seek result as the legacy
                # one-frame command, so anchor later PTS values to this point.
                self.timestamp_offset = timestamp - frame_time
            elif frame_time + self.timestamp_offset + 1e-8 < timestamp:
                continue
            self.frames[timestamp] = image
            while len(self.frames) > _VIDEO_FRAME_CACHE_SIZE:
                self.frames.popitem(last=False)
            return image

    def close(self) -> None:
        process, self.process = self.process, None
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        if self.stderr_thread is not None:
            self.stderr_thread.join(timeout=0.2)
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()


class _VideoDecodeSession:
    def __init__(self, metrics: dict):
        self.metrics = metrics
        self.readers: dict[tuple[str, float], _VideoFrameStream] = {}
        self.disabled_paths: set[str] = set()

    def frame(self, path: str, mtime: float, timestamp: float) -> Image.Image | None:
        if path in self.disabled_paths:
            return None
        key = (path, mtime)
        reader = self.readers.get(key)
        if reader is None:
            for stale_key, stale_reader in list(self.readers.items()):
                if stale_key[0] == path:
                    stale_reader.close()
                    del self.readers[stale_key]
            reader = _VideoFrameStream(path, self.metrics)
            self.readers[key] = reader
        started = perf_counter()
        try:
            return reader.frame(timestamp)
        except (EOFError, OSError, ValueError, queue.Empty):
            reader.close()
            self.disabled_paths.add(path)
            return None
        finally:
            self.metrics["video_decode_seconds"] += perf_counter() - started

    def close(self) -> None:
        for reader in self.readers.values():
            reader.close()
        self.readers.clear()


@contextmanager
def collect_video_decode_metrics():
    """Collect FFmpeg decode work and reuse forward streams in this context."""
    metrics = {
        "video_decode_calls": 0,
        "video_decoder_processes": 0,
        "video_decoded_frames": 0,
        "video_decode_seconds": 0.0,
    }
    session = _VideoDecodeSession(metrics)
    metrics_token = _VIDEO_DECODE_METRICS.set(metrics)
    session_token = _VIDEO_DECODE_SESSION.set(session)
    try:
        yield metrics
    finally:
        session.close()
        _VIDEO_DECODE_SESSION.reset(session_token)
        _VIDEO_DECODE_METRICS.reset(metrics_token)


def _load_video_frame_cached(path: str, mtime: float, quantized_time: float) -> Image.Image:
    from io import BytesIO
    import subprocess

    cmd = [
        "ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error",
        "-ss", f"{max(0.0, quantized_time):.3f}",
        "-i", path,
        "-frames:v", "1",
        "-f", "image2pipe", "-vcodec", "png", "-",
    ]
    started = perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, check=False)
        if proc.returncode != 0 or not proc.stdout:
            raise ValueError(
                f"Could not decode video frame from {path} at {quantized_time:.3f}s")
        img = Image.open(BytesIO(proc.stdout))
        img.load()
        return img.convert("RGBA")
    finally:
        metrics = _VIDEO_DECODE_METRICS.get()
        if metrics is not None:
            metrics["video_decode_calls"] += 1
            metrics["video_decoder_processes"] += 1
            metrics["video_decoded_frames"] += 1
            metrics["video_decode_seconds"] += perf_counter() - started


def load_video_frame(
    path: str | Path,
    timestamp: float = 0.0,
    *,
    trim_start: float = 0.0,
    trim_end: float | None = None,
) -> Image.Image:
    """Decode an RGBA frame from a video or still asset with explicit trim bounds (MD-304)."""
    resolved = Path(path).resolve()
    if not resolved.is_file():
        raise ValueError(f"Missing media asset: {resolved}")
    if trim_start < 0:
        raise ValueError("trim_start must be non-negative")
    if trim_end is not None and trim_end <= trim_start:
        raise ValueError("trim_end must exceed trim_start")
    if resolved.suffix.lower() not in _VIDEO_EXTENSIONS:
        return load_image(resolved)
    target_t = float(trim_start) + max(0.0, float(timestamp))
    if trim_end is not None:
        target_t = min(target_t, max(float(trim_start), float(trim_end) - 1e-3))
    stat = os.stat(resolved)
    key = (str(resolved), stat.st_mtime, round(target_t, 2))
    cached = _cached_video_frame(key)
    if cached is not None:
        return cached.copy()
    session = _VIDEO_DECODE_SESSION.get()
    if session is not None:
        image = session.frame(*key)
        if image is not None:
            _remember_video_frame(key, image)
            return image.copy()
    image = _load_video_frame_cached(*key)
    _remember_video_frame(key, image)
    return image.copy()


def clear_video_frame_cache() -> None:
    """Clear the shared decoded-video frame cache; useful in tests."""
    with _VIDEO_FRAME_CACHE_LOCK:
        _VIDEO_FRAME_CACHE.clear()


def crop_region(
    image: Image.Image,
    crop_box: tuple[float, float, float, float] | list[float] | None,
) -> Image.Image:
    """Apply a normalized (x0, y0, x1, y1) crop in 0..1 before cover-fitting (MD-304)."""
    if crop_box is None:
        return image
    if len(crop_box) != 4:
        raise ValueError("crop_box must be (x0, y0, x1, y1) in 0..1")
    x0, y0, x1, y1 = (float(v) for v in crop_box)
    if not (0.0 <= x0 < x1 <= 1.0 and 0.0 <= y0 < y1 <= 1.0):
        raise ValueError("crop_box coordinates must satisfy 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1")
    w, h = image.size
    box = (
        max(0, round(x0 * w)),
        max(0, round(y0 * h)),
        min(w, max(1, round(x1 * w))),
        min(h, max(1, round(y1 * h))),
    )
    return image.crop(box)


def apply_shape_mask(
    image: Image.Image,
    mask_kind: str | None,
    *,
    radius: float = 0.0,
) -> Image.Image:
    """Apply a geometric alpha mask (rect, rounded, circle, pill) to an RGBA layer (MD-304)."""
    out = image.convert("RGBA")
    kind = (mask_kind or "rect").strip().lower()
    if kind == "rect" and radius <= 0:
        return out
    w, h = out.size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    if kind == "circle":
        r = min(w, h) / 2.0
        cx, cy = w / 2.0, h / 2.0
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    elif kind == "pill":
        r = min(w, h) / 2.0
        draw.rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=255)
    elif kind in ("rounded", "rect"):
        r = max(0.0, min(float(radius), min(w, h) / 2.0))
        draw.rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=255)
    else:
        raise ValueError(f"Unsupported mask kind {mask_kind!r}")
    out.putalpha(Image.composite(out.getchannel("A"), Image.new("L", (w, h), 0), mask))
    return out


def cover(image: Image.Image, width: int, height: int,
          camera: Camera | None = None) -> Image.Image:
    """Cover-fit an image and apply a subtle camera transform."""
    if width < 1 or height < 1:
        raise ValueError("Target size must be positive")
    camera = camera or Camera()
    if camera.zoom <= 0:
        raise ValueError("Camera zoom must be positive")
    scale = max(width / image.width, height / image.height) * camera.zoom
    scaled = image.resize((max(1, round(image.width * scale)),
                           max(1, round(image.height * scale))),
                          Image.Resampling.LANCZOS)
    overflow_x = max(0, scaled.width - width)
    overflow_y = max(0, scaled.height - height)
    # camera.x/y are normalized -1..1 offsets within the available overflow.
    x = int(round((overflow_x / 2) * (1 + max(-1, min(1, camera.x)) * .8)))
    y = int(round((overflow_y / 2) * (1 + max(-1, min(1, camera.y)) * .8)))
    return scaled.crop((x, y, x + width, y + height))


def gradient_image(width: int, height: int, start: tuple[int, int, int],
                   end: tuple[int, int, int], angle: float = 90) -> Image.Image:
    """Linear two-stop gradient. Cache this at scene level, never per frame."""
    if width < 1 or height < 1:
        raise ValueError("Gradient size must be positive")
    if angle in (90, 270):
        if angle == 270:
            start, end = end, start
        strip = Image.new("RGB", (1, height))
        pixels = strip.load()
        for y in range(height):
            pixels[0, y] = mix(start, end, y / max(1, height - 1))
        return strip.resize((width, height))
    if angle in (0, 180):
        if angle == 0:
            start, end = end, start
        strip = Image.new("RGB", (width, 1))
        pixels = strip.load()
        for x in range(width):
            pixels[x, 0] = mix(start, end, x / max(1, width - 1))
        return strip.resize((width, height))
    # Diagonal: build per-row colour then expand horizontally.
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    span = width + height
    for y in range(height):
        for x in range(0, width, max(1, width // 64)):
            amount = (x + y) / max(1, span)
            draw.line((x, y, min(width, x + width // 64), y),
                      fill=mix(start, end, amount))
    return image


def shadow(image: Image.Image, radius: float = 18,
           opacity: float = .35) -> Image.Image:
    """Return a blurred black silhouette suitable for compositing beneath."""
    if opacity <= 0:
        return Image.new("RGBA", image.size, (0, 0, 0, 0))
    alpha = image.getchannel("A")
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    layer.putalpha(alpha.point(lambda value: int(value * opacity)))
    return layer.filter(ImageFilter.GaussianBlur(max(1, radius)))


def rounded(image: Image.Image, box: tuple[float, float, float, float],
            radius: float, fill, outline=None, width: int = 1,
            opacity: float = 1.0) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    x0, y0, x1, y1 = box
    radius = max(0.0, min(radius, (x1 - x0) / 2, (y1 - y0) / 2))
    fill_rgba = _rgba(fill, opacity)
    outline_rgba = _rgba(outline, opacity) if outline else None
    if fill_rgba is None and outline_rgba is None:
        return
    draw.rounded_rectangle((x0, y0, x1, y1), radius=radius,
                           fill=fill_rgba, outline=outline_rgba,
                           width=max(1, int(width)))


def circle(image: Image.Image, cx: float, cy: float, radius: float,
           fill=None, outline=None, width: int = 1,
           opacity: float = 1.0) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                 fill=_rgba(fill, opacity), outline=_rgba(outline, opacity),
                 width=max(1, int(width)))


def ring(image: Image.Image, cx: float, cy: float, radius: float,
         thickness: float, color, progress: float = 1.0,
         start_angle: float = -90, opacity: float = 1.0) -> None:
    if radius <= 0 or thickness <= 0:
        return
    progress = max(0.0, min(1.0, float(progress)))
    draw = ImageDraw.Draw(image, "RGBA")
    box = (cx - radius, cy - radius, cx + radius, cy + radius)
    stroke = max(1, int(round(thickness)))
    if progress >= .999:
        draw.ellipse(box, outline=_rgba(color, opacity), width=stroke)
        return
    if progress <= .001:
        return
    end = start_angle + 360 * progress
    draw.arc(box, start=start_angle, end=end, fill=_rgba(color, opacity),
             width=stroke)
    # Rounded caps make the progress ring feel designed, not clipped.
    for angle in (start_angle, end):
        radians = math.radians(angle)
        px = cx + radius * math.cos(radians)
        py = cy + radius * math.sin(radians)
        rr = stroke / 2
        draw.ellipse((px - rr, py - rr, px + rr, py + rr),
                     fill=_rgba(color, opacity))


def trim_polyline(points: list[tuple[float, float]], progress: float,
                  *, start: float = 0.0) -> list[tuple[float, float]]:
    """Return the arc-length trimmed sub-polyline for ``start..progress`` in 0..1 (MD-303)."""
    if len(points) < 2:
        return list(points)
    t0 = max(0.0, min(1.0, float(start)))
    t1 = max(0.0, min(1.0, float(progress)))
    if t1 <= t0 + 1e-6:
        return []
    if t0 <= 1e-6 and t1 >= .9999:
        return list(points)
    seg_lengths = [
        math.hypot(b[0] - a[0], b[1] - a[1])
        for a, b in zip(points, points[1:])
    ]
    total = sum(seg_lengths)
    if total <= 1e-6:
        return []
    d_start, d_end = t0 * total, t1 * total
    out: list[tuple[float, float]] = []
    acc = 0.0
    for (ax, ay), (bx, by), length in zip(points, points[1:], seg_lengths):
        next_acc = acc + length
        if next_acc > d_start + 1e-9 and acc < d_end - 1e-9 and length > 1e-9:
            u0 = max(0.0, min(1.0, (d_start - acc) / length))
            u1 = max(0.0, min(1.0, (d_end - acc) / length))
            p0 = (ax + (bx - ax) * u0, ay + (by - ay) * u0)
            p1 = (ax + (bx - ax) * u1, ay + (by - ay) * u1)
            if not out or math.hypot(out[-1][0] - p0[0], out[-1][1] - p0[1]) > 1e-6:
                out.append(p0)
            if math.hypot(out[-1][0] - p1[0], out[-1][1] - p1[1]) > 1e-6:
                out.append(p1)
        acc = next_acc
    return out if len(out) >= 2 else []


def morph_polyline(
    source_points: list[tuple[float, float]],
    target_points: list[tuple[float, float]],
    progress: float,
) -> list[tuple[float, float]]:
    """Interpolate between two polylines of matching vertex count at ``progress`` in 0..1 (MD-503)."""
    if len(source_points) < 2 or len(source_points) != len(target_points):
        raise ValueError("morph_polyline requires two polylines of equal length >= 2")
    p = max(0.0, min(1.0, float(progress)))
    return [
        (ax + (bx - ax) * p, ay + (by - ay) * p)
        for (ax, ay), (bx, by) in zip(source_points, target_points)
    ]


def line(image: Image.Image, points, color, width: float = 2,
         opacity: float = 1.0, closed: bool = False, fill: bool = False) -> None:
    if not points:
        return
    draw = ImageDraw.Draw(image, "RGBA")
    colour = _rgba(color, opacity)
    if fill or closed:
        draw.polygon(points, fill=colour if fill else None,
                     outline=colour if not fill else None)
        if not fill and len(points) > 1:
            draw.line(points + ([points[0]] if closed else []),
                      fill=colour, width=max(1, int(round(width))),
                      joint="curve")
        return
    draw.line(points, fill=colour, width=max(1, int(round(width))),
              joint="curve")


def text_block(image: Image.Image, block: TextBlock, origin: tuple[float, float],
               fonts: FontBook, *, tracking_offset: float = 0.0,
               color=None, opacity: float = 1.0, scale: float = 1.0,
               skip_effects: bool = False,
               character_progress: float | None = None) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    ox, oy = origin[0] * scale, origin[1] * scale
    tracking_progress = 0
    character_index = 0
    limit = (None if character_progress is None else
             max(0, int(character_progress + 1e-6)))
    for line_index, line in enumerate(block.lines):
        for word_index, word in enumerate(line.words):
            word_start = character_index
            word_end = word_start + len(word.text)
            if skip_effects and word.effect:
                tracking_progress += max(1, len(word.text))
                character_index = word_end
                if word_index + 1 < len(line.words):
                    character_index += 1
                continue
            ink = color or word.color
            alpha = int(round(255 * opacity * block.style.opacity))
            visible_chars = len(word.text)
            if limit is not None:
                visible_chars = max(0, min(visible_chars, limit - word_start))
            if visible_chars and alpha > 0:
                size = max(6, round((word.size or block.style.size) * scale))
                weight = word.weight or block.style.weight
                font = fonts.get(size, weight)
                offset = tracking_offset * tracking_progress * scale
                draw.text((ox + word.x * scale + offset,
                           oy + line.baseline * scale),
                          word.text[:visible_chars], font=font,
                          fill=(*ink, alpha), anchor="ls")
            tracking_progress += max(1, len(word.text))
            character_index = word_end
            if word_index + 1 < len(line.words):
                character_index += 1
        if line_index + 1 < len(block.lines):
            character_index += 1
    return


def text_block_mask(image: Image.Image, block: TextBlock,
                    origin: tuple[float, float], fonts: FontBook, *,
                    effect: str = "negative", tracking_offset: float = 0.0,
                    opacity: float = 1.0, scale: float = 1.0,
                    character_progress: float | None = None) -> None:
    """Draw only words carrying ``effect`` into a transparent alpha mask."""
    if effect != "negative":
        raise ValueError(f"Unsupported text mask effect {effect!r}")
    draw = ImageDraw.Draw(image, "RGBA")
    ox, oy = origin[0] * scale, origin[1] * scale
    tracking_progress = 0
    character_index = 0
    limit = (None if character_progress is None else
             max(0, int(character_progress + 1e-6)))
    for line_index, line in enumerate(block.lines):
        for word_index, word in enumerate(line.words):
            word_start = character_index
            word_end = word_start + len(word.text)
            if word.effect != effect:
                tracking_progress += max(1, len(word.text))
                character_index = word_end
                if word_index + 1 < len(line.words):
                    character_index += 1
                continue
            visible_chars = len(word.text)
            if limit is not None:
                visible_chars = max(0, min(visible_chars, limit - word_start))
            if visible_chars:
                alpha = int(round(255 * opacity * block.style.opacity))
                size = max(6, round((word.size or block.style.size) * scale))
                font = fonts.get(size, word.weight or block.style.weight)
                offset = tracking_offset * tracking_progress * scale
                draw.text((ox + word.x * scale + offset,
                           oy + line.baseline * scale),
                          word.text[:visible_chars], font=font,
                          fill=(255, 255, 255, alpha), anchor="ls")
            tracking_progress += max(1, len(word.text))
            character_index = word_end
            if word_index + 1 < len(line.words):
                character_index += 1
        if line_index + 1 < len(block.lines):
            character_index += 1


def number(image: Image.Image, value: float, rect: tuple[float, float, float, float],
           fonts: FontBook, *, fmt: dict | None = None,
           size: int = 120, color=(255, 255, 255), align: str = "center",
           opacity: float = 1.0, tracking_offset: float = 0.0,
           scale: float = 1.0) -> None:
    """Draw a tabular number whose width never jitters as digits change."""
    fmt = dict(fmt or {})
    text = format_value(value, fmt)
    x, y, w, h = (value * scale for value in rect)
    size = max(6, round(size * scale))
    tracking_offset = tracking_offset * scale
    font = fonts.get(size, "bold")
    width = digits_width(font, text)
    while width > w and size > 10:
        size = max(10, int(size * .94))
        font = fonts.get(size, "bold")
        width = digits_width(font, text)
    ascent, descent = font.getmetrics()
    text_height = ascent + descent
    if text_height > h:
        scale = h / text_height
        size = max(8, int(size * scale))
        font = fonts.get(size, "bold")
        ascent, descent = font.getmetrics()
        text_height = ascent + descent
    if align == "left":
        start = x
    elif align == "right":
        start = x + w - width
    else:
        start = x + (w - width) / 2
    baseline = y + (h - text_height) / 2 + ascent
    draw = ImageDraw.Draw(image, "RGBA")
    alpha = int(round(255 * opacity))
    digit_advance = max(font.getlength(str(digit)) for digit in "0123456789")
    cursor = start + tracking_offset
    for character in text:
        advance = digit_advance if character.isdigit() else font.getlength(character)
        draw.text((cursor, baseline), character, font=font,
                  fill=(*color, alpha), anchor="ls")
        cursor += advance


def tint(image: Image.Image, color: tuple[int, int, int],
         amount: float) -> Image.Image:
    if not 0 <= amount <= 1:
        raise ValueError("Tint amount must be between 0 and 1")
    if amount == 0:
        return image
    overlay = Image.new("RGBA", image.size, (*color, 255))
    return Image.blend(image.convert("RGBA"), overlay, amount)


def scrim(image: Image.Image, strength: float, *, from_bottom: bool = True,
          gamma: float = .85) -> Image.Image:
    """Per-context overlay instead of globally washing out every photograph."""
    if not 0 <= strength <= .95:
        raise ValueError("Scrim strength must be between 0 and 0.95")
    if strength <= 0:
        return image
    width, height = image.size
    gradient = Image.new("L", (1, height))
    pixels = gradient.load()
    for y in range(height):
        amount = y / max(1, height - 1)
        if not from_bottom:
            amount = 1 - amount
        pixels[0, y] = int(255 * strength * (amount ** gamma))
    mask = gradient.resize((width, height))
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    layer.putalpha(mask)
    return Image.alpha_composite(image.convert("RGBA"), layer)


def _rgba(color, opacity: float):
    if color is None:
        return None
    if isinstance(color, str):
        color = parse_hex(color)
    if len(color) == 4:
        r, g, b, a = color
        return (r, g, b, max(0, min(255, int(a * opacity))))
    r, g, b = color[:3]
    return (r, g, b, max(0, min(255, int(255 * opacity))))
