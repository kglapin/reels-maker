"""Beat grid for audio-reactive choreography.

Wraps :func:`audiokit.cues.plan_beat_cue_mix` into a typed structure that the
art-direction layer can query to snap entrance onsets to the nearest beat,
avoid wall-of-SFX sync, and respect voiceover ducking windows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from ..audiokit.cues import plan_beat_cue_mix

MIN_BEAT_GAP_S = 0.15


@dataclass(frozen=True)
class BeatGrid:
    """Typed view of the beat grid produced by the audio planning layer."""

    bpm: float
    beat_interval_s: float
    total_duration_s: float
    beats: tuple[float, ...]
    voiceover_windows: tuple[tuple[float, float], ...]
    sfx_events: tuple[dict[str, Any], ...]
    target_lufs: float

    def __post_init__(self) -> None:
        if self.bpm <= 0:
            raise ValueError("bpm must be positive")
        if not self.beats:
            raise ValueError("beat grid must contain at least one beat")

    def beat_before(self, seconds: float) -> float:
        """Return the latest beat at or before ``seconds``."""
        latest = self.beats[0]
        for beat in self.beats:
            if beat <= seconds + 1e-9:
                latest = beat
            else:
                break
        return latest

    def beat_after(self, seconds: float) -> float:
        """Return the earliest beat at or after ``seconds``."""
        for beat in self.beats:
            if beat >= seconds - 1e-9:
                return beat
        return self.beats[-1]

    def snap(self, seconds: float, *, direction: str = "after") -> float:
        """Snap ``seconds`` to the nearest beat.

        ``direction`` is ``"after"`` (default, entrances align to the next beat)
        or ``"before"`` (exits align to the previous beat).
        """
        if direction == "before":
            return self.beat_before(seconds)
        return self.beat_after(seconds)

    def in_voiceover(self, seconds: float) -> bool:
        """True if ``seconds`` falls inside a voiceover ducking window."""
        for start, end in self.voiceover_windows:
            if start - 1e-9 <= seconds <= end + 1e-9:
                return True
        return False

    def next_beat_outside_voiceover(
        self, seconds: float, *, max_lookahead_s: float = 2.0
    ) -> float | None:
        """Return the next beat that does not fall inside a voiceover window."""
        for beat in self.beats:
            if beat < seconds - 1e-9:
                continue
            if beat > seconds + max_lookahead_s:
                return None
            if not self.in_voiceover(beat):
                return beat
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "bpm": self.bpm,
            "beat_interval_s": round(self.beat_interval_s, 4),
            "total_duration_s": round(self.total_duration_s, 4),
            "beats": list(self.beats),
            "voiceover_windows": [list(w) for w in self.voiceover_windows],
            "sfx_events": list(self.sfx_events),
            "target_lufs": self.target_lufs,
        }


def plan_beat_grid(
    scene_durations: Iterable[float],
    *,
    bpm: float = 120.0,
    voiceover_segments: Iterable[tuple[float, float]] | None = None,
    cues: Mapping[int, Mapping[str, float]] | None = None,
    target_lufs: float = -14.0,
) -> BeatGrid:
    """Build a typed beat grid from scene durations and optional voiceover."""
    durations = [float(d) for d in scene_durations]
    raw = plan_beat_cue_mix(
        durations,
        bpm=bpm,
        voiceover_segments=list(voiceover_segments) if voiceover_segments else None,
        cues=cues,
        target_lufs=target_lufs,
    )
    windows = tuple(
        (float(env["voiceover_start"]), float(env["voiceover_end"]))
        for env in raw.get("ducking_envelopes", [])
    )
    return BeatGrid(
        bpm=float(raw["bpm"]),
        beat_interval_s=float(raw["beat_interval_s"]),
        total_duration_s=float(raw["total_duration_s"]),
        beats=tuple(raw["beat_grid"]),
        voiceover_windows=windows,
        sfx_events=tuple(raw.get("sfx_events", [])),
        target_lufs=float(raw["loudness_qc"]["target_integrated_lufs"]),
    )


__all__ = ["BeatGrid", "plan_beat_grid", "MIN_BEAT_GAP_S"]