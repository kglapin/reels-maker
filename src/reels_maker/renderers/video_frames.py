"""Still-image loading and bounded FFmpeg video-frame decoding."""
from __future__ import annotations

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

from PIL import Image

_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}
_VIDEO_DECODE_METRICS: ContextVar[dict | None] = ContextVar(
    "reels_maker_video_decode_metrics", default=None)
_VIDEO_DECODE_SESSION: ContextVar["_VideoDecodeSession | None"] = ContextVar(
    "reels_maker_video_decode_session", default=None)
_VIDEO_FRAME_CACHE: OrderedDict[tuple[str, float, float], Image.Image] = OrderedDict()
_VIDEO_FRAME_CACHE_LOCK = threading.RLock()
_VIDEO_FRAME_CACHE_SIZE = 64

@dataclass(frozen=True)
class Camera:
    zoom: float = 1.0
    x: float = 0.0
    y: float = 0.0
    blur: float = 0.0


@lru_cache(maxsize=128)
def _load(path: str, mtime_ns: int, size_bytes: int) -> Image.Image:
    image = Image.open(path)
    image.load()
    return image.convert("RGBA")


def load_image(path: str | Path) -> Image.Image:
    path = str(Path(path).resolve())
    stat = os.stat(path)
    return _load(path, stat.st_mtime_ns, stat.st_size)


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
