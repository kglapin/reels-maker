"""Deterministic narrator+music soundtrack assembly with safe peak limiting.

Voice is a separate, explicitly positioned timeline track. Music stays on a
separate track. Optional FFmpeg sidechain compression is deliberately
opt-in: background music ducks in response to the narrator's waveform.
No beat guesses, synthesis, automatic transcript alignment or forced loudnorm.
"""
from __future__ import annotations

from pathlib import Path

from .ffmpeg import RenderError, execute
from .spec import Project


def mux_audio(project: Project, silent_video: Path, destination: Path,
              music_file: Path | None, voice_file: Path | None,
              duration: float) -> dict:
    """Copy H.264 video unchanged and add one limited AAC mix."""
    if music_file is None and voice_file is None:
        raise RenderError("No audio tracks specified for mixing")
    if duration <= 0:
        raise RenderError("Invalid output duration")

    inputs = ["-i", str(silent_video)]
    filters: list[str] = []
    music_label = None
    voice_label = None
    idx = 1
    if music_file is not None:
        music = project.music or {}
        start = float(music.get("start", 0))
        vol = float(music.get("volume", 1.0))
        fade = float(music.get("fade_out", 0))
        if fade > duration:
            raise RenderError("music.fade_out exceeds the final video after transitions")
        inputs += ["-ss", str(start), "-i", str(music_file)]
        chain = (f"[{idx}:a]aresample=48000,"
                 "aformat=channel_layouts=stereo,"
                 "asetpts=PTS-STARTPTS,"
                 f"volume={vol:.6f}")
        if fade:
            chain += (f",afade=t=out:st={duration-fade:.6f}:"
                      f"d={fade:.6f}")
        chain += (f",apad,atrim=duration={duration:.8f},"
                  "asetpts=PTS-STARTPTS[music]")
        filters.append(chain)
        music_label = "music"
        idx += 1

    if voice_file is not None:
        voice = project.voiceover or {}
        start = float(voice.get("start", 0))
        vol = float(voice.get("volume", 1.0))
        offset = float(voice.get("offset_seconds", 0))
        if offset >= duration:
            raise RenderError("voiceover.offset_seconds falls outside final video")
        delay_ms = round(offset * 1000)
        inputs += ["-ss", str(start), "-i", str(voice_file)]
        chain = (f"[{idx}:a]aresample=48000,"
                 "aformat=channel_layouts=stereo,"
                 "asetpts=PTS-STARTPTS,"
                 f"volume={vol:.6f}")
        if delay_ms:
            chain += f",adelay={delay_ms}:all=1"
        chain += (f",apad,atrim=duration={duration:.8f},"
                  "asetpts=PTS-STARTPTS[voice]")
        filters.append(chain)
        voice_label = "voice"

    mode = (project.music or {}).get("ducking", "off")
    if music_label and voice_label:
        if mode == "sidechain":
            # Deliberately moderate gain reduction, with a gradual release to
            # avoid soundtrack pumping. No high-gain artificial FX.
            filters.append(
                "[music][voice]sidechaincompress="
                "threshold=0.08:ratio=3:attack=30:release=380[ducked]"
            )
            music_label = "ducked"
        filters.append(
            f"[{music_label}][voice]"
            "amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
            "alimiter=limit=0.95[aout]")
    elif music_label:
        filters.append(f"[{music_label}]alimiter=limit=0.95[aout]")
    else:
        filters.append("[voice]alimiter=limit=0.95[aout]")

    execute(inputs + [
        "-filter_complex", ";".join(filters),
        "-map", "0:v:0", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-t", f"{duration:.8f}",
        "-movflags", "+faststart", str(destination)
    ])
    return {
        "voiceover": voice_file is not None,
        "music": music_file is not None,
        "ducking": mode if voice_file and music_file else "off",
        "sample_rate": 48000,
        "peak_limiter": 0.95,
    }
