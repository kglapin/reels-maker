"""Environment diagnostics CLI handler."""
from __future__ import annotations

from .ffmpeg import require_tool
from .cli_common import _emit


def handle_doctor(args) -> int:
    import subprocess
    report = {}
    for name in ("ffmpeg", "ffprobe"):
        try:
            exe = require_tool(name)
            report[name] = subprocess.run(
                [exe, "-version"], capture_output=True, text=True,
                check=True).stdout.splitlines()[0]
        except (OSError, RenderError, subprocess.CalledProcessError):
            report[name] = None
    import PIL
    report["pillow"] = PIL.__version__
    valid = all(report.get(name) for name in ("ffmpeg", "ffprobe"))
    _emit({"status": "ok" if valid else "error",
           "ok": valid, "tools": report}, error=not valid)
    return 0 if valid else 3
