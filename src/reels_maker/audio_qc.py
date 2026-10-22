"""Read-only EBU R128 integrated loudness and true-peak analysis.

This diagnostic deliberately does NOT normalize or modify source audio.
It helps a sound designer spot unexpectedly quiet/loud exports before
publishing to social platforms, which have different downstream processing.
"""
from __future__ import annotations

import math
import re
import subprocess
from pathlib import Path

from .ffmpeg import RenderError, probe, require_tool


_LOUDNORM = re.compile(
    r'\{\s*"input_i"\s*:\s*"([^"]+)"'
    r'\s*,\s*"input_tp"\s*:\s*"([^"]+)"'
    r'\s*,\s*"input_lra"\s*:\s*"([^"]+)"',
    re.DOTALL
)


def _measure(stderr: str) -> tuple[float, float, float]:
    found = _LOUDNORM.search(stderr)
    if not found:
        raise RenderError("FFmpeg did not output EBU R128 loudness measurements")
    try:
        return tuple(float(item) for item in found.groups())
    except ValueError as exc:
        raise RenderError("Malformed FFmpeg loudness measurements") from exc


def analyze_audio_loudness(file: Path, *,
                           reference_lufs: float | None = None) -> dict:
    """Read-only loudnorm first-pass measurement, never apply its output.

    reference_lufs is an optional editorial reference, not a platform rule.
    """
    file = Path(file).resolve()
    if not file.is_file():
        raise RenderError(f"Audio/video file does not exist: {file}")
    if reference_lufs is not None:
        if (isinstance(reference_lufs, bool) or
                not isinstance(reference_lufs, (int, float)) or
                not math.isfinite(reference_lufs) or
                not -30 <= reference_lufs <= -8):
            raise RenderError("reference_lufs must be a finite value from -30 to -8")

    streams = probe(file).get("streams", [])
    audio = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if len(audio) != 1:
        raise RenderError(
            f"Audio QC requires exactly one audio stream, found {len(audio)}")
    command = [
        require_tool("ffmpeg"), "-hide_banner", "-nostdin",
        "-i", str(file), "-map", "0:a:0", "-vn",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
        "-f", "null", "-"
    ]
    completed = subprocess.run(
        command, text=True, capture_output=True, check=False)
    if completed.returncode:
        raise RenderError(
            "Audio loudness measurement failed: " + completed.stderr[-1400:])

    integrated, true_peak, loudness_range = _measure(completed.stderr)
    warnings = []
    if not math.isfinite(integrated):
        warnings.append({
            "code": "silence_or_unmeasurable",
            "message": "Integrated loudness could not be measured; inspect waveform"})
    elif integrated < -26:
        warnings.append({
            "code": "very_quiet",
            "message": "Unusually quiet mix (< -26 LUFS); check intended listening level"})
    elif integrated > -9:
        warnings.append({
            "code": "very_loud",
            "message": "Unusually loud integrated mix (> -9 LUFS); check dynamics"})
    if not math.isfinite(true_peak):
        warnings.append({
            "code": "unmeasurable_peak",
            "message": "True peak could not be measured"})
    elif true_peak > -1:
        warnings.append({
            "code": "high_true_peak",
            "message": "True peak above -1 dBTP; transcoding may create overs"})
    data = {
        "file": str(file),
        "status": "review" if warnings else "pass",
        "measurement": "ebu_r128_loudnorm_first_pass",
        "integrated_lufs": round(integrated, 2) if math.isfinite(integrated) else None,
        "true_peak_dbtp": round(true_peak, 2) if math.isfinite(true_peak) else None,
        "loudness_range_lu": (round(loudness_range, 2)
                              if math.isfinite(loudness_range) else None),
        "reference_lufs": reference_lufs,
        "difference_from_reference_lu": (
            round(integrated - reference_lufs, 2)
            if reference_lufs is not None and math.isfinite(integrated)
            else None
        ),
        "warnings": warnings,
        "warning_count": len(warnings),
        "manual_listening_required": True,
    }
    return data
