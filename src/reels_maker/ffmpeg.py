"""Portable FFmpeg process management and metadata inspection."""
import json
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Callable


class RenderError(RuntimeError):
    pass


def drain_stderr(process: subprocess.Popen) -> Callable[[], str]:
    """Drain ``process.stderr`` on a daemon thread; return a text getter.

    FFmpeg writes periodic progress and warnings to stderr. If the pipe buffer
    fills while the parent is still streaming raw frames to the child's stdin,
    both sides deadlock. Call the returned getter only after the process has
    exited or been killed, when the read loop has reached EOF.
    """
    chunks: list[bytes] = []

    def collect() -> None:
        stream = process.stderr
        if stream is None:
            return
        for chunk in iter(lambda: stream.read(65536), b""):
            chunks.append(chunk)

    thread = threading.Thread(target=collect, name="ffmpeg-stderr-drain",
                              daemon=True)
    thread.start()

    def text() -> str:
        thread.join()
        return b"".join(chunks).decode("utf-8", "replace")

    return text


def require_tool(name: str) -> str:
    executable = shutil.which(name)
    if not executable:
        raise RenderError(f"{name} not found on PATH. Install FFmpeg and FFprobe.")
    return executable


def execute(arguments: list[str], *, quiet: bool = True) -> None:
    command = [require_tool("ffmpeg"), "-hide_banner", "-nostdin", "-y", *map(str, arguments)]
    completed = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, check=False)
    if completed.returncode:
        raise RenderError(f"FFmpeg exited {completed.returncode}:\n"
                          + completed.stderr[-5000:])
    if not quiet:
        print(completed.stderr[-1000:])


def probe(path: Path) -> dict:
    command = [require_tool("ffprobe"), "-v", "error", "-show_format",
               "-show_streams", "-of", "json", str(path)]
    p = subprocess.run(command, text=True, capture_output=True, check=False)
    if p.returncode:
        raise RenderError(f"Cannot inspect {path}: {p.stderr[-1200:]}")
    return json.loads(p.stdout)


def duration(path: Path) -> float:
    meta = probe(path)
    try:
        return float(meta["format"]["duration"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RenderError(f"Missing media duration: {path}") from exc
