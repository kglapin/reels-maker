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
              duration: float, *,
              sfx_tracks: list[dict] | None = None) -> dict:
    """Copy H.264 unchanged and add a limited AAC voice/music/SFX mix."""
    sfx_tracks = list(sfx_tracks or [])
    if music_file is None and voice_file is None and not sfx_tracks:
        raise RenderError("No audio tracks specified for mixing")
    if duration <= 0:
        raise RenderError("Invalid output duration")

    inputs = ["-i", str(silent_video)]
    filters: list[str] = []
    music_label = None
    voice_label = None
    sfx_labels: list[str] = []
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

    for effect in sfx_tracks:
        path = Path(effect.get("file") or effect.get("path") or "")
        start = float(effect.get("time", effect.get("start", 0)))
        if start < 0 or start >= duration:
            raise RenderError(f"SFX start {start:.3f}s falls outside the video")
        if "volume" in effect:
            volume = float(effect["volume"])
        else:
            gain_db = float(effect.get("gain_db", -18))
            volume = 10 ** (gain_db / 20)
        if not 0 <= volume <= 4:
            raise RenderError("SFX volume must be between 0 and 4")
        if not path.is_file():
            raise RenderError(f"SFX file does not exist: {path}")
        inputs += ["-i", str(path)]
        label = f"sfx{len(sfx_labels)}"
        delay_ms = round(start * 1000)
        chain = (f"[{idx}:a]aresample=48000,"
                 "aformat=channel_layouts=stereo,"
                 "asetpts=PTS-STARTPTS,"
                 f"volume={volume:.6f}")
        if delay_ms:
            chain += f",adelay={delay_ms}:all=1"
        chain += (f",apad,atrim=duration={duration:.8f},"
                  f"asetpts=PTS-STARTPTS[{label}]")
        filters.append(chain)
        sfx_labels.append(label)
        idx += 1

    mode = (project.music or {}).get("ducking", "off")
    if music_label and voice_label:
        if mode == "sidechain":
            # One audio stream cannot feed two filters directly in FFmpeg.
            # Split the narrator into the control/monitor path and audible mix.
            filters.append("[voice]asplit=2[voice_sc][voice_mix]")
            filters.append(
                "[music][voice_sc]sidechaincompress="
                "threshold=0.08:ratio=3:attack=30:release=380[ducked]"
            )
            music_label = "ducked"
            voice_label = "voice_mix"
        filters.append(f"[{music_label}][{voice_label}]"
                       "amix=inputs=2:duration=first:dropout_transition=0:"
                       "normalize=0[main]")
        main_label = "main"
    else:
        main_label = music_label or voice_label

    mix_labels = ([main_label] if main_label else []) + sfx_labels
    if not mix_labels:
        raise RenderError("No usable audio tracks specified for mixing")
    if len(mix_labels) == 1:
        filters.append(f"[{mix_labels[0]}]alimiter=limit=0.95[aout]")
    else:
        pads = "".join(f"[{label}]" for label in mix_labels)
        filters.append(
            f"{pads}amix=inputs={len(mix_labels)}:duration=first:"
            "dropout_transition=0:normalize=0,alimiter=limit=0.95[aout]")

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
        "sfx": len(sfx_labels),
        "ducking": mode if voice_file and music_file else "off",
        "sample_rate": 48000,
        "peak_limiter": 0.95,
    }
