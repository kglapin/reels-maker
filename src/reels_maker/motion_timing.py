"""Frame-accurate, explicit editorial cue scheduling.

The engine never infers narration word times. Agents may supply verified
scene-local cue frames, or cue seconds which are snapped to the project's FPS.
Decorative layers normally start at frame 0; meaningful text defaults to a
restrained stagger. All timing routes use the same schedule and hold guard.
"""
from __future__ import annotations

from dataclasses import dataclass

MIN_SETTLED_SECONDS = .55
DECORATIVE_ROLES = frozenset(("logo", "accent"))


@dataclass(frozen=True)
class CueSchedule:
    starts: dict[str, int]
    duration_frames: int
    last_settled_frame: int
    min_hold_frames: int


def scripted_text_roles(title: dict) -> list[tuple[str, str]]:
    """Semantic roles and readable text, in editorial reveal order."""
    result: list[tuple[str, str]] = []
    if title.get("kicker"):
        result.append(("kicker", str(title["kicker"])))
    headline = title.get("headline")
    if isinstance(headline, dict):
        for i, run in enumerate(headline.get("runs", [])):
            if str(run.get("text", "")).strip():
                result.append((f"headline-{i}", str(run["text"])))
    elif headline:
        result.append(("headline", str(headline)))
    for key in ("body", "footer"):
        if title.get(key):
            result.append((key, str(title[key])))
    return result


def build_cue_schedule(settings: dict, role_names: list[str], fps: int,
                       scene_frames: int) -> CueSchedule:
    """Resolve opt-in overrides with deterministic nearest-frame quantization.

    Raises ValueError on ambiguous, unused, out-of-range or overlong cues.
    """
    if fps < 1 or scene_frames < 1:
        raise ValueError("Invalid FPS or scene frame count")
    if len(role_names) != len(set(role_names)):
        raise ValueError("Duplicate motion layer roles")
    if "cue_frames" in settings and "cue_seconds" in settings:
        raise ValueError("Choose cue_frames OR cue_seconds, not both")

    raw_frames = settings.get("cue_frames", {})
    raw_seconds = settings.get("cue_seconds", {})
    if not isinstance(raw_frames, dict) or not isinstance(raw_seconds, dict):
        raise ValueError("Motion cue map must be a JSON object")

    overrides: dict[str, int] = {}
    for key, value in raw_frames.items():
        if not isinstance(key, str) or type(value) is not int or value < 0:
            raise ValueError(f"cue_frames: invalid cue for {key!r}")
        overrides[key] = value
    for key, value in raw_seconds.items():
        if (not isinstance(key, str) or isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not 0 <= value <= 3600):
            raise ValueError(f"cue_seconds: invalid cue for {key!r}")
        overrides[key] = round(value * fps)

    unknown = set(overrides) - set(role_names)
    if unknown:
        raise ValueError("Motion cue refers to missing layer(s): "
                         + ", ".join(sorted(unknown)))

    duration = settings.get("duration_frames", max(2, round(fps * .24)))
    stagger = settings.get("stagger_frames", max(1, round(fps * .07)))
    if (type(duration) is not int or duration < 2
            or type(stagger) is not int or stagger < 0):
        raise ValueError("Invalid motion duration/stagger")

    starts: dict[str, int] = {}
    text_index = 0
    for role in role_names:
        if role in DECORATIVE_ROLES:
            default = 0
        else:
            default = text_index * stagger
            text_index += 1
        starts[role] = overrides.get(role, default)

    last = max((frame + duration for frame in starts.values()),
               default=duration)
    hold = max(1, round(MIN_SETTLED_SECONDS * fps))
    if last + hold > scene_frames:
        raise ValueError(
            "Motion cues leave less than 0.55s after the final entrance; "
            "move cues earlier or increase scene duration")
    return CueSchedule(starts, duration, last, hold)
