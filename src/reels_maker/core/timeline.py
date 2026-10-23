"""Frame-quantized timeline and cue model shared by render and QA.

The timeline is the single source of truth for scene starts, lengths and
element entrances. Rendering, contact sheets and QA never recompute time from
floating-point scene durations independently, which is what caused small
drift between previews and exported files in earlier versions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping

MAX_FPS = 120


def quantize_frames(durations: Iterable[float], fps: int) -> list[int]:
    """Convert cumulative scene durations to integer frame counts."""
    if type(fps) is not int or not 1 <= fps <= MAX_FPS:
        raise ValueError("FPS must be an integer between 1 and 120")
    elapsed = 0.0
    previous = 0
    frames: list[int] = []
    for index, duration in enumerate(durations):
        if isinstance(duration, bool) or not isinstance(duration, (int, float)):
            raise ValueError(f"Scene {index}: duration must be numeric")
        if not 0.01 <= float(duration) <= 3600:
            raise ValueError(f"Scene {index}: duration out of range")
        elapsed += float(duration)
        end = round(elapsed * fps)
        count = end - previous
        if count < 1:
            raise ValueError(f"Scene {index}: too short at {fps} FPS")
        frames.append(count)
        previous = end
    return frames


@dataclass(frozen=True)
class Cue:
    role: str
    scene: int
    local_frame: int
    source: str = "manifest"
    text: str | None = None

    def seconds(self, fps: int) -> float:
        return round(self.local_frame / fps, 6)


@dataclass(frozen=True)
class SceneTiming:
    index: int
    start_frame: int
    frames: int
    duration: float
    cues: Mapping[str, Cue] = field(default_factory=dict)

    @property
    def end_frame(self) -> int:
        return self.start_frame + self.frames

    def local_seconds(self, fps: int) -> dict[str, float]:
        return {role: round(cue.local_frame / fps, 6)
                for role, cue in self.cues.items()}


@dataclass(frozen=True)
class Timeline:
    fps: int
    scenes: tuple[SceneTiming, ...]
    total_frames: int

    @property
    def duration(self) -> float:
        return round(self.total_frames / self.fps, 6)

    def global_frame(self, scene: int, local_frame: int) -> int:
        return self.scenes[scene].start_frame + local_frame

    def scene_at(self, frame: int) -> SceneTiming | None:
        for scene in self.scenes:
            if scene.start_frame <= frame < scene.end_frame:
                return scene
        return None

    def cues(self) -> list[Cue]:
        return [cue for scene in self.scenes for cue in scene.cues.values()]

    def cue(self, scene: int, role: str) -> Cue | None:
        return self.scenes[scene].cues.get(role)

    def to_dict(self) -> dict:
        return {
            "fps": self.fps,
            "total_frames": self.total_frames,
            "total_seconds": self.duration,
            "scenes": [
                {
                    "scene": scene.index + 1,
                    "start_frame": scene.start_frame,
                    "frames": scene.frames,
                    "start_seconds": round(scene.start_frame / self.fps, 6),
                    "duration_seconds": round(scene.frames / self.fps, 6),
                    "cues": {
                        role: {
                            "local_frame": cue.local_frame,
                            "local_seconds": cue.seconds(self.fps),
                            "timeline_frame": scene.start_frame + cue.local_frame,
                            "timeline_seconds": round(
                                (scene.start_frame + cue.local_frame) / self.fps, 6),
                            "source": cue.source,
                        }
                        for role, cue in scene.cues.items()
                    },
                }
                for scene in self.scenes
            ],
        }


def _cue_frame(value, fps: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Cue {label!r} must be seconds or frames")
    if not 0 <= float(value) <= 3600:
        raise ValueError(f"Cue {label!r} is outside the allowed range")
    return round(float(value) * fps)


def resolve_cues(scene: dict, fps: int, frames: int,
                 known_roles: Iterable[str] | None = None,
                 *, source: str = "manifest",
                 scene_index: int = 0) -> dict[str, Cue]:
    """Resolve manifest cue seconds (or explicit frames) into local frames.

    ``cues`` is always interpreted as seconds. Integer frame positions use the
    separate ``cue_frames`` object, so a legitimate 31-second cue can never be
    mistaken for frame 31.
    """
    seconds = scene.get("cues")
    frame_map = scene.get("cue_frames")
    if seconds is not None and frame_map is not None:
        raise ValueError("Use scene.cues (seconds) or scene.cue_frames, not both")
    raw = seconds if seconds is not None else (frame_map or {})
    if not isinstance(raw, dict):
        raise ValueError("Scene cues must be an object")
    known = set(known_roles) if known_roles is not None else None
    cues: dict[str, Cue] = {}
    for role, value in raw.items():
        if not isinstance(role, str) or not role:
            raise ValueError("Cue roles must be non-empty strings")
        if known is not None and role not in known:
            raise ValueError(f"Cue refers to unknown element {role!r}")
        if frame_map is not None:
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"cue_frames {role!r} must be an integer")
            frame = value
        else:
            frame = _cue_frame(value, fps, role)
        if frame < 0 or frame >= frames:
            raise ValueError(
                f"Cue {role!r} falls outside scene {scene_index + 1}")
        cues[role] = Cue(role=role, scene=scene_index, local_frame=frame,
                         source=source)
    # A stable order (time then role) makes choreography deterministic even
    # when JSON keys arrive in a different order from a human editor.
    return {role: cues[role] for role in sorted(
        cues, key=lambda name: (cues[name].local_frame, name))}


def build_timeline(scenes: list[dict], fps: int,
                   cue_roles: Mapping[int, Iterable[str]] | None = None) -> Timeline:
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("A nonempty scenes list is required")
    frames = quantize_frames([scene["duration"] for scene in scenes], fps)
    timings = []
    cursor = 0
    for index, (scene, count) in enumerate(zip(scenes, frames)):
        roles = None
        if cue_roles and index in cue_roles:
            roles = cue_roles[index]
        cues = resolve_cues(scene, fps, count, roles, scene_index=index)
        timings.append(SceneTiming(
            index=index, start_frame=cursor, frames=count,
            duration=round(count / fps, 6), cues=cues))
        cursor += count
    return Timeline(fps=fps, scenes=tuple(timings), total_frames=cursor)


def sample_frames(timeline: Timeline, per_scene: int = 5,
                  include_ends: bool = True) -> list[tuple[int, int, float]]:
    """Return (scene index, local frame, local seconds) QA sample points.

    Samples include the entrance, settle and exit regions of every scene, so a
    collision that exists only while a counter grows is still detected.
    """
    if per_scene < 2:
        raise ValueError("At least two samples per scene are required")
    result: list[tuple[int, int, float]] = []
    for scene in timeline.scenes:
        last = scene.frames - 1
        points = sorted({round(last * step / (per_scene - 1))
                         for step in range(per_scene)})
        for frame in points:
            result.append((scene.index, frame, round(frame / timeline.fps, 6)))
    return result
