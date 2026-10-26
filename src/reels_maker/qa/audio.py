"""Audio checks for Studio QA."""
from __future__ import annotations

import re
import subprocess

from .models import Issue



def _audio_report(project, timeline: Timeline) -> dict:
    audio = getattr(project, "audio", None) or {}
    voiceover = audio.get("voiceover")
    music = audio.get("music")
    sfx = audio.get("sfx") or []
    report = {"voiceover": None, "music": None,
              "sfx": [{"path": item.get("file"),
                       "time": item.get("time", item.get("start", 0)),
                       "measured": False} for item in sfx],
              "status": "not_configured"}
    if voiceover:
        voice_path = voiceover.get("file") or voiceover.get("path") \
            if isinstance(voiceover, dict) else voiceover
        report["voiceover"] = _measure_audio(Path(voice_path), timeline.duration)
    if music:
        music_path = music.get("file") or music.get("path") \
            if isinstance(music, dict) else music
        report["music"] = {"path": str(music_path), "measured": False,
                           "note": "Music level is checked during final human review."}
    if voiceover or music or sfx:
        report["status"] = "technical_checks_only"
    return report


def _measure_audio(path: Path, video_duration: float) -> dict:
    if not path.is_file():
        return {"path": str(path), "status": "missing"}
    try:
        completed = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostdin", "-i", str(path),
             "-af", "volumedetect", "-f", "null", "-"],
            text=True, capture_output=True, check=False)
        if completed.returncode:
            return {"path": str(path), "status": "error",
                    "message": "FFmpeg could not measure the voiceover."}
        output = completed.stderr
        mean = re.search(r"mean_volume:\s*(-?[\d.]+) dB", output)
        peak = re.search(r"max_volume:\s*(-?[\d.]+) dB", output)
        duration = None
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            text=True, capture_output=True, check=False)
        if probe.returncode == 0:
            try:
                duration = float(probe.stdout.strip())
            except ValueError:
                duration = None
        result = {
            "path": str(path), "status": "ok",
            "duration": round(duration, 4) if duration else None,
            "mean_db": float(mean.group(1)) if mean else None,
            "peak_db": float(peak.group(1)) if peak else None,
        }
        if duration is not None and duration < video_duration - 1.0:
            result["status"] = "short"
            result["message"] = "Voiceover is shorter than the video timeline."
        if result["peak_db"] is not None and result["peak_db"] > -.1:
            result["status"] = "clipping"
            result["message"] = "Voiceover peaks at or above 0 dBFS."
        if result["mean_db"] is not None and result["mean_db"] < -30:
            result.setdefault("message", "Voiceover is unusually quiet.")
        return result
    except OSError as exc:
        return {"path": str(path), "status": "error", "message": str(exc)}
